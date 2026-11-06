# HEDERA-DAY1-FIX-3 native ownership/build review

The native helper closes N2 without Python-side reference-count flags or signal
masking. The original callback gains its owned reference and a named capsule
destructor within one C call. Failed allocation balances that increment. An
interruption before Python stores the returned capsule lets ordinary object
cleanup invoke the native destructor. Explicit release tombstones the capsule
before dropping its callback reference; repeated release is safe. Invocation
holds a separate C reference throughout the callback, including concurrent close.

The capsule has no GC-visible callback referent or ordinary state accessor.
Native invocation also discards the original callback exception and traceback
before publishing fixed errors or fresh control exceptions. SystemExit preserves
only exact integer/None codes; KeyboardInterrupt, GeneratorExit and asyncio
CancelledError are fresh base instances. Only exact bytes signatures return.
Every public C entry checks the main interpreter. The destructor remains usable
for cleanup independently of that entry gate. Free-threaded builds are refused.

Reviewed native source SHA256:
`e3fd22111baf81ab5b1c80d4426085b63e6cd6f076144957edd0a952c87b48f9`.
No ownership or disclosure blocker was found in this final source. The root
agent owns adapter/regression integration and the eventual commit.

## Independently executed checks

All probes used harmless receiver callbacks; no SDK private key, credential,
ledger request or account was used. Results contained booleans/counts only.

| Check | Result |
| --- | --- |
| Native ownership, empty GC referents, automatic/explicit/repeated close, stale handles, invalid arguments, exact-byte result, concurrent close | 18 observations passed |
| Direct native callback exception graphs and fresh control/code behavior | 45 observations passed |
| Invalid payload causing a callback TypeError; no original frame/context and receiver release with replacement error retained | 4 observations passed |
| Forced allocation-failure source control after the real INCREF | 3 observations passed: MemoryError, balanced native pin, receiver released |
| Delegate's independent final native lifecycle/error probes | 3,008 observations passed, including 1,000 create/close/repeat/GC cycles; see hedera-fix3-native-audit.md |
| Default/native wheel metadata and source-distribution contents | 4 observations passed |
| Extracted-wheel imports in isolated Python processes | 2 observations passed: pure-wheel local signing fails closed; native-wheel invocation/close succeeds |

The actual-SIGINT line/opcode regression matrix is maintained independently by
the root and missing_repos agents; the counts above do not include that matrix
or the full repository suite.

## Build and packaging

Validated with GIL-enabled CPython 3.12.14, Linux x86_64 and the available GCC
toolchain. The active interpreter records clang, which is absent here; the local
builder safely falls back to cc while preserving its interpreter's compiler and
linker flags. Other CPython versions/platforms were not executed here. The local
builder deliberately refuses non-POSIX environments rather than claiming an
untested Windows compiler path.

Commands passed:

```
python scripts/build_hedera_native.py
python -m hatchling build -t wheel
RPP_BUILD_HEDERA_NATIVE=true python -m hatchling build -t wheel
```

Hatchling 1.33.0 was installed into an isolated workspace tooling directory for
verification; PYTHONPATH selected that directory for the CLI commands. This adds
no package runtime dependency.

The default wheel is `rpp_protocol-2.1.0-py3-none-any.whl`, declares
`Root-Is-Purelib: true`, and contains no native binary even when a local ignored
extension exists. Opt-in produces
`rpp_protocol-2.1.0-cp312-cp312-linux_x86_64.whl`, declares
`Root-Is-Purelib: false`, and contains one matching CPython extension. The source
distribution includes the C source, local builder and hatch hook, and excludes
compiled binaries. Both extracted wheels were checked from isolated working
directories so the checkout's local extension could not satisfy their imports.

The helper is an optional experimental CPython component, not a stable-ABI or
subinterpreter support claim. It preserves the prior opaque public-object/GC
boundary; arbitrary native-pointer or process-memory inspection remains outside
that boundary. No source commit, push or Rust operation was performed by this
agent.
