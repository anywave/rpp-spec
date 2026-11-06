This native-ownership audit predates the final diagnostic cleanup. Its capsule binding/refcount design is retained. Final source `4d8a65d09e561f804116a50f6e3c79873ca79f04` was separately rechecked for public state, lifecycle and rich diagnostics; see [F3-REVIEW.md](F3-REVIEW.md) and [INDEPENDENT-REVIEW.md](INDEPENDENT-REVIEW.md).

# FIX-2 independent CPython capsule API and lifecycle audit

Reviewed 2026-11-06 against working `rpp/adapters/hedera_safe.py`, SHA-256
`83c7fa95ae11e13de657f20e0d193cfc87d4b056835215eaffc865543b10eb27`.
Runtime tested: CPython 3.12.14. No repository files were changed, no SDK/private
keys were constructed, no credentials were inspected, and no ledger calls ran.

**Result: no blocking capsule ownership or stale-handle issue found in this
implementation.** The final design uses an unnamed capsule and changes its
pointer to non-null integer `1` before releasing the manually owned callback.
It has no native destructor or Python `CFUNCTYPE` callback. Thus the earlier
proposed capsule-name lifetime hazard does not apply to the implemented code.

## Authoritative API facts

All sources below were fetched successfully through the configured proxy from
the official CPython repository, tag `v3.12.14`:

- [Capsule API documentation](https://github.com/python/cpython/blob/v3.12.14/Doc/c-api/capsule.rst):
  `PyCapsule_New(void *, const char *, PyCapsule_Destructor)` returns a new
  Python reference; the pointer cannot be NULL. A non-null name must outlive
  the capsule. `GetPointer(PyObject *, const char *)` returns the stored raw
  pointer only when names match. `SetPointer(PyObject *, void *)` refuses NULL.
  `SetName(PyObject *, const char *)` stores a borrowed name, without freeing
  the old name. `IsValid(PyObject *, const char *)` checks capsule type,
  non-null pointer, and exact name match, without raising.
- [Capsule implementation](https://github.com/python/cpython/blob/v3.12.14/Objects/capsule.c#L43-L95)
  confirms `New` copies raw pointer/name fields without owning the pointed-to
  object. [SetPointer](https://github.com/python/cpython/blob/v3.12.14/Objects/capsule.c#L134-L152)
  replaces only the raw pointer. [Deallocation and repr](https://github.com/python/cpython/blob/v3.12.14/Objects/capsule.c#L250-L281)
  neither dereference nor release the stored pointer when destructor is NULL;
  repr prints the capsule's own address and name, not the callback object.
- [Reference-counting API](https://github.com/python/cpython/blob/v3.12.14/Doc/c-api/refcounting.rst#L171-L184)
  declares `void Py_IncRef(PyObject *)` and `void Py_DecRef(PyObject *)`.
  Binding them as `argtypes=[ctypes.c_void_p]`, `restype=None`, and passing
  `id(operation)` is appropriate for a pinned, live CPython object pointer.
  This avoids incidental `py_object` argument conversions. Every explicit pin
  must have exactly one explicit unpin; capsules do not provide it implicitly.
- [ctypes result conversion](https://github.com/python/cpython/blob/v3.12.14/Modules/_ctypes/callproc.c#L978-L1004)
  explicitly balances the `O_get` increment for a `restype=ctypes.py_object`
  function result. Consequently `PyCapsule_New.restype=ctypes.py_object`
  correctly transfers the new capsule reference to Python without a leak or
  a second required decrement.
- [ctypes py_object getter](https://github.com/python/cpython/blob/v3.12.14/Modules/_ctypes/cfield.c#L1054-L1076)
  explicitly returns `Py_NewRef(ob)`. Therefore
  `ctypes.cast(pointer, ctypes.py_object).value` creates the local strong
  callback reference needed before releasing the shared lock. It survives a
  concurrent capsule close and is released when that invocation finishes.
- [PyDLL documentation](https://github.com/python/cpython/blob/v3.12.14/Doc/library/ctypes.rst#L1428-L1438)
  specifies that PyDLL calls retain the GIL and translate a CPython error flag
  into a Python exception. CDLL would be inappropriate for these calls.

Downloaded primary sources are retained in `/workspace/work/hedera-cpython-api/`.

## Ownership and failure-path findings

1. Initialization takes one explicit callback reference, creates an unnamed
   capsule, and stores only that capsule in the id registry. The local callback
   reference then expires normally. A failed capsule allocation unpins; a failed
   registry insertion calls the same release routine. Failed earlier setup has
   no native reference to release.
2. Release holds the same RLock as pointer acquisition, replaces the callback
   pointer with `1`, then decrements the callback. The order makes state
   consistent before a decrement can run arbitrary destruction code. Repeated
   release observes the tombstone and does not decrement again. A saved capsule
   still has a valid non-null C pointer, but the only module invocation path
   explicitly rejects `1` before casting it. It must continue doing so.
3. `__del__` removes the registry entry before release. The registry does not
   retain the signer itself, so normal signer destruction is not prevented by
   a reference cycle. `_close_signers` additionally releases live registry
   entries at normal interpreter exit.
4. The final code never stores borrowed C-string names and uses no native
   destructor callback. This avoids both a dangling capsule-name buffer and a
   `CFUNCTYPE` trampoline called after its Python owner is gone.
5. This is an ordinary public repr/state boundary, not isolation from deliberate
   `ctypes` pointer access, mutation of private module internals, debugging, or
   direct process-environment reads. Native dereferencing bypasses that boundary.

## Independent harmless-callback probes

All 21 boolean observations across three isolated invocations passed (the
empty-registry observation appears in two runs). No key data appeared in output.

- Correct capsule reference count before/after registry removal; original
  callback retained while active; receiver released after close; saved capsule
  tombstoned; double close safe; saved handle refused; 1,000 create/destroy
  operations released all receiver weakrefs; registry empty.
- Injected `MemoryError` from capsule creation and from registry insertion each
  released the harmless receiver after local references expired. A paused
  invocation retained its receiver while another thread closed the signer,
  completed successfully, then released the receiver; registry empty.
- A fresh `python -X faulthandler` subprocess with a live signer exited normally
  with empty stderr. A verifier registered before module import ran after the
  module's atexit cleanup and observed receiver released, registry empty, and a
  saved capsule tombstoned.

## Limits

These ownership probes were run on CPython 3.12.14, not free-threaded CPython,
other Python implementations, subinterpreters, or alternate operating systems.
The code refuses non-CPython runtimes and fails closed when required native
symbols are unavailable. That check does not establish free-threaded support.
Normal atexit cleanup was verified; `os._exit`, fatal signals, process kills, and
interpreter corruption do not execute ordinary Python finalizers. No durable
secret cleanup guarantee is claimed for those paths. Manual native reference
ownership also requires the private registry and native API bindings to remain
intact; they are not a security boundary against arbitrary Python code execution.
