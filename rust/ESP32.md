# ESP32 adapter groundwork — CX-008

This adds provisional `rpp-control` and `rpp-link` libraries to the Rust workspace,
stacked on `codex/rust-rpp-crate`. Their names may change when PL/FP lifts the
workspace into its separate repository. Publishing remains disabled.

Both crate roots declare `#![no_std]`, use fixed-size codec types and forbid unsafe
code. `rpp-link` imports `std` explicitly only behind its host-simulation feature.
They provide an experimental control codec and adapter interfaces, with host-side
simulations. They supply no board support, vendor HAL, radio driver, firmware
image, tunnel, cipher, handshake, signing implementation or key exchange.
RADIX's board models are still unknown.

The existing RPP address formats, consent header, specification, golden vectors
and published constants are unchanged. The frame below is an **unpublished
experiment**, not an adopted RPP wire format. The 112-byte frame, 16-byte
identities and 64-byte signature field are **IMPOSED experimental choices** for
this implementation; they are not newly published protocol constants or a claim
that a particular signature scheme or device has been selected.

## Control codec and its boundary

`rpp-control` represents exactly six control kinds:

| Code | Rust variant | Meaning available to an authorized host |
|---:|---|---|
| 1 | `Alive` | Liveness notice |
| 2 | `MemberChanged` | Invalidate/recheck membership state; cannot admit a member |
| 3 | `Stop` | Stop notice |
| 4 | `Pause` | Temporary pause notice |
| 5 | `RouteAround` | Request selection among otherwise eligible routes |
| 6 | `Resume` | Lift an authorized temporary pause; cannot start a new operation, undo STOP/revocation or restore consent |

The codec parses notices; it does not execute these actions or maintain an
operation state machine. The host must check whether a verified notice is
authorized and applicable to the current operation before acting on it.

The fixed frame is 112 bytes, with no variable-length payload:

| Half-open byte range | Bytes | Field |
|---|---:|---|
| `[0, 4)` | 4 | Experimental magic `RPPC` |
| `[4, 5)` | 1 | Experimental frame version `1` |
| `[5, 6)` | 1 | Closed kind code `1..=6` |
| `[6, 8)` | 2 | Reserved, both zero |
| `[8, 16)` | 8 | Sequence number, unsigned big-endian `u64` |
| `[16, 32)` | 16 | Opaque sender `NodeId` |
| `[32, 48)` | 16 | Opaque recipient `NodeId` |
| `[48, 112)` | 64 | Opaque `Signature` |

`FRAME_LEN` and `HEADER_LEN` expose this experiment's 112-byte frame and 48-byte
header sizes. The verification input is exactly bytes `[0, 48)`, including the
magic, version, kind, zero reserved bytes, sequence and both identities. No
endianness conversion or text normalization is performed on opaque fields.

There is no START kind, payload string, grant, consent, key, model, prompt or
answer field. Unknown kinds and additional/trailing bytes are rejected. This is
**structural exclusion**, not ASCII scanning: an opaque identity or signature
may coincidentally contain those byte sequences without becoming an instruction
or payload. Filtering signature bytes for words would reject legitimate opaque
values and would not establish signature validity.

`ControlFrame::new` constructs an outbound frame from typed fields and a supplied
opaque signature. `header`/`signing_header` expose the exact header bytes to an
external signing system, and `encode` returns a fixed-size frame. None of these
methods creates or validates a signature.

`rpp_control::decode(input, expected_recipient, verifier)` checks the structure
and recipient, then calls the supplied `Verifier`. Its successful result is a
`VerifiedControlFrame` with private construction, getters and `encode`; callers
cannot obtain that marker from a public unchecked wrapper constructor.

The external verification hook is:

```rust,ignore
fn verify(
    &self,
    sender: &NodeId,
    header: &[u8; 48],
    signature: &[u8; 64],
) -> bool;
```

The host supplies a reviewed verifier and its existing identity/key binding.
Test verifiers are fixtures. A `true` fixture, an all-zero signature, or the
private result type does not itself establish real authenticity. The crate
implements no cryptography and specifies no key algorithm, credential store,
enrollment, rotation or trust-root mechanism.

Decode errors distinguish `Truncated`, `Oversize`, `BadMagic`,
`UnsupportedVersion`, `UnknownKind`, `NonzeroReserved`, `WrongRecipient` and
`InvalidSignature`. The codec changes no receiver/operation state and dispatches
no action. The codec has no replay cache, session state, membership list or consent
authority; a valid signature alone cannot supply any of those.

## Link adapters and host policy

`rpp-link` describes current readings as plain values and separates control-frame
sends from application-data sends. An adapter implementation will supply its
device's readings and perform the selected send through its own platform API.
The library performs neither operation against a real device.

The underlay kinds are LAN, Wi-Fi, BLE, LoRa and internet. A kind identifies a
carrier; it does not prove tunnel capability, independent hardware, discovery,
current availability or permission to use that carrier. In particular, BLE GATT
and bare LoRa are not automatically IP tunnel paths.

The allocation-free interface consists of `LinkKind::{Lan, Wifi, Ble, Lora,
Internet}` and `LinkReading { latency_ms, loss_ppm, jitter_ms, available,
observed }`. Latency and jitter are unsigned `u64` milliseconds, loss is `u32`
parts per million with `valid()` requiring `loss_ppm <= 1_000_000`, and
`observed` is a host logical `u64` tick. These are measurements supplied by the
caller, not authenticated observations. The host supplies the mapping from an
adapter to peer identities, capability and failure domain.

An adapter implements `LinkAdapter` with its own `Error` type:

```rust,ignore
fn kind(&self) -> LinkKind;
fn read(&mut self, tick: u64) -> Result<LinkReading, Self::Error>;
fn send_verified_control_frame(
    &mut self,
    frame: &VerifiedControlFrame,
) -> Result<(), Self::Error>;
fn send_data(&mut self, payload: &[u8]) -> Result<DataOutcome, Self::Error>;
```

`DataOutcome` distinguishes `Sent` from `Failed { emitted_tokens: u64 }`.
`dispatch(adapter, TrafficPath, Outbound)` rejects a control/data class mismatch
before calling either send hook. `Outbound::Control` accepts only a reference to
`VerifiedControlFrame`; an unchecked outbound builder does not satisfy this
type. An outbound sender can supply its externally signed frame to the decoder
and verifier before passing it to this dispatch interface. Successful decode
still leaves current authorization and replay checks to the host.

The adapter boundary preserves these responsibilities:

| Adapter/library boundary | Host responsibility |
|---|---|
| Plain latency, loss, jitter, availability and link-kind readings | Obtain trustworthy measurements, state their time/unit/capability, enforce freshness and reject clock rollback |
| Typed control-frame send | Select the control path, retain traffic class and recipient, check current consent/trust and provide an independent failure domain when available |
| Application-data send | Supply authorized data only on the selected data path, account for actual progress and preserve the first-token retry boundary |
| Reported send result | Feed the actual outcome to retry/breaker/meter policy; do not silently retry after output or discard a failed-attempt meter row |
| Decoded verified control notice | Check replay/sequence state, issuer authority, membership, consent and applicability before changing any operation state |

The reference integration drives CX-007's overlay policy through host-side
simulated adapters in the `std`-gated `rpp_link::simulated` module. This host
simulation is excluded from the bare-metal no-default-feature build. Control
frames use the typed control-send path; the data-send
path is used for application data. This is a tested dispatch boundary, not a
claim that arbitrary caller-supplied bytes carry an automatically detectable
semantic traffic class. An application must not encode a control frame and
smuggle it through the data API to bypass control policy.

The host module exposes `SimulatedAdapter`, `HostBridge`, `AdapterAudit`, `run`
and `artifacts`. `HostBridge::send_data`, `choose_data_reference`,
`send_verified_control` and `send_billboard` drive the policy using scripted
adapters; `policy` and `audit` expose policy rows and adapter activity separately.
The reference script retains all **17 policy rows / 16 requests**. These policy
rows do not automatically meter every error at the host integration boundary.

Sampling failures and unmapped control identities return `HostError` before a
policy request is made. The caller must meter those boundary rejections itself;
there is no automatically created policy row for them. The simulated adapter
bank also rejects any adapter name containing `/` with
`HostError::UnsupportedLinkName` before **any** read callback, policy call or
send. This is an **IMPOSED host-fixture domain restriction**: existing core meter
paths use `/` as a separator, so a name such as `a/b` could alias two hops `a` and
`b`. Core link names and protocol formats are unchanged. The caller must also
meter this rejection. Clock rollback reaches the existing policy, retains its
`INVALID_INPUT` row and produces no adapter send.

Billboard transport in this host module uses the literal opaque data placeholder
`opaque-billboard-fixture` and a previously verified `Auth::fixture` assumption.
It is not a billboard wire codec, receipt/signature verifier or production
serialization of a fact/rule. `Delivered` and `HeldUntilSince` both count as
accepted transport delivery; the latter remains inactive until `since`.
Billboard transport-failure fixtures are unsupported and return
`HostError::UnsupportedBillboardFailure` before policy storage or sends. These
host-boundary failures also require caller metering. The fixture therefore
proves the scripted routing/storage/expiry behavior and preserves its meter
rows; it does not prove arbitrary partial-failure delivery or authenticity.

The same trust and consent requirements apply to every underlay and relay.
Changing a radio, receiving ALIVE or MEMBER-CHANGED, reconnecting, or accepting a
signature never creates membership, conveys a grant or replaces a consent
action. Hosts track sequence freshness within their authorized identity/session
context; restart or `u64` exhaustion cannot silently reset that context or
authorize an operation.

Control independence means a distinct failure domain from the chosen data path,
not a different URI or enum variant. Where no independent eligible path exists,
report that limitation. Local stop/revocation behavior remains necessary during
a complete partition. An observed or signed notice is not proof that a remote
device received or acted on it.

## Evidence and reproducible checks

The committed control corpus is generated by rpp-spec-side Python scaffolding;
the Rust crates and final builds do not require Python. The corpus supplies
fixed inputs and expected outcomes for round trips, closed kinds, malformed and
oversize frames, recipient checks and externally supplied verification results.
This is bounded table coverage, not a claim of exhaustive fuzzing or a security
audit. Every test names a mutation that would violate its assertion.

The exact rows and corpus SHA-256 are in
[`control-manifest.json`](rpp-control/tests/data/control-manifest.json), beside
[`control-corpus.tsv`](rpp-control/tests/data/control-corpus.tsv). To regenerate
without overwriting committed evidence, run from the repository root:

```sh
python tools/esp32_scaffold/control_corpus.py --output-dir <scratch-control-corpus>
```

The adapter scenario tests compare their in-memory CSV, Markdown and JSON bytes
with the committed `tools/overlay_sim` reference artifacts, including LF endings
and ordering. Reference behavior includes measured-link selection, relay,
pre-first-token fallback, breakers and complete meter rows, independent control,
billboard expiry and clock-rollback refusal. All readings, send outcomes and
verification results in these tests are scripted; they are not device readings.

From `rust/`, with rustup installed:

```sh
rustup toolchain install 1.85.1 --profile minimal --component rustfmt --component clippy --target riscv32imc-unknown-none-elf
cargo +1.85.1 fmt --all -- --check
cargo +1.85.1 clippy --workspace --all-targets --offline --locked -- -D warnings
cargo +1.85.1 test --workspace --offline --locked
cargo +1.85.1 test --workspace --no-default-features --offline --locked
cargo +1.85.1 test --workspace --no-default-features --features alloc --offline --locked
cargo +1.85.1 build --workspace --no-default-features --target riscv32imc-unknown-none-elf --offline --locked
cargo +1.85.1 build --workspace --no-default-features --features alloc --target riscv32imc-unknown-none-elf --offline --locked
```

The workspace CI covers all member crates on Ubuntu and Windows, with pinned
Rust, a SHA-pinned read-only checkout and ordinary failing checks. No gate is
advisory. Exact executed counts, corpus hashes, scenario byte comparisons and
Python gates belong to [the CX-008 report](../docs/codex/OUTBOX/CX-008-001.md).
The commands here are reproduction instructions, not an additional claim that
hardware or hosted CI ran.

The `riscv32imc-unknown-none-elf` result is a library cross-compile check for the
RISC-V ESP32-C3/C6 class, not a linked or bootable firmware image. It provides no
HAL, linker script, allocator, interrupt handling or radio stack. The codec and
control/link interfaces need no heap. Calling CX-007's optional `alloc` policy
models requires an application-provided allocator and device memory budget.
Xtensa ESP32/ESP32-S3 requires separate toolchain and board work and is not part
of this CI check. No board run, timing, throughput or radio-range claim follows.

## What a real ESP32 adapter still needs

RADIX must supply the exact board/module and chip variant, available RAM/flash,
connected radios and their interfaces/pins, and the intended firmware/toolchain
environment. Until then, selecting a vendor HAL or assuming an ESP32 family is
premature.

With those facts, adapter work can be scoped to the board: implement link
readings and the two typed send paths, connect the existing verifier and identity
binding, supply time/replay storage and consent/trust policy, handle buffers and
memory limits, and test actual failure domains and send outcomes. Firmware must
also select its own runtime, linker/startup configuration and any required
allocator. The codec receives complete frames: a transport whose MTU cannot
carry 112 bytes at once needs bounded fragmentation/reassembly before decoding.
No transport fragmentation format is implemented or selected here.
These choices require integration evidence before any deployment or
interoperability claim; this groundwork does not make them on RADIX's behalf.
