# Experimental fixed control envelope

`rpp-control` is an unpublished `no_std` library using only `core`, fixed arrays
and borrowed input. It allocates no heap and implements no cryptography. This
experimental format changes no published RPP address, header or wire contract.

| Bytes | Field |
|---|---|
| 0–3 | Magic `RPPC` |
| 4 | Experimental version 1 |
| 5 | Kind: 1 ALIVE, 2 MEMBER-CHANGED, 3 STOP, 4 PAUSE, 5 ROUTE-AROUND, 6 RESUME |
| 6–7 | Reserved, both zero |
| 8–15 | Sequence, unsigned 64-bit big-endian |
| 16–31 | Opaque sender identifier |
| 32–47 | Opaque recipient identifier |
| 48–111 | Opaque 64-byte signature |

These sizes, kind codes, magic and version are IMPOSED experimental choices.
There is no payload, text, extension, grant, consent, key or model field. Exact
length rejects appended content; the closed kind rejects other message types.
Opaque IDs/signatures are not interpreted as text or scanned for ASCII tokens.

`ControlFrame` is an outbound builder with a closed `ControlKind` and a signature
provided by the caller. `signing_header` returns the exact first 48 bytes for a
host's existing signing mechanism; this crate does not create a signature.

`decode(input, expected_recipient, verifier)` checks the 112-byte length before
indexing, then magic/version/kind/reserved bytes, recipient and the caller's
verification verdict. The verifier receives sender ID, the exact 48-byte header
including both endpoints, and the opaque signature. It has no default
implementation. Only successful decoding constructs `VerifiedControlFrame`,
whose private fields cannot be initialized by a transport caller.

The verified wrapper records a caller verification verdict. It does not admit
a member, grant consent, establish sequence freshness, start work, or define
STOP/RESUME effects. Hosts retain authorization, consent, per-pair replay state
and lifecycle policy. Sequence zero is structurally valid, matching the existing
overlay's first-message domain. Unknown senders are the verifier/host's concern.

Every received byte span must already be a complete frame. MTU selection,
bounded fragmentation/reassembly, identity provisioning and a reviewed verifier
backend remain adapter work once board models and transports are selected.

Eight fixed unit tests exercise field offsets, all six kinds, sequence boundaries,
unknown kinds, appended content, verification refusal, recipient binding,
malformed-header ordering and every truncated length. Each names its failing
mutation. Integration/corpus tests are under `tests/`; mock verification fixtures
are policy fixtures and provide no cryptographic security claim.
