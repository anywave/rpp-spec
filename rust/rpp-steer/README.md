# Experimental measured-link steering

`rpp-steer` ranks **caller-eligible** links without sending anything. It is a
separate experimental selector, not a replacement for core overlay policy,
consent, membership, tunnel verification, independent control paths or retry
rules. Selection grants none of those permissions. There are no drivers, radios,
network calls, cryptography, randomness or model calls.

The core is `no_std`, allocation-free and forbids unsafe code. It reuses the
unchanged `rpp_link::{LinkKind, LinkReading}`. Default `std` adds only a scripted
simulator and example; the dependency on `rpp-link` disables its default features
and does not activate link simulation or fragmentation. Bare and alloc-only
workspace builds use the same core. The library has no alloc feature or allocator.

## Inputs and decisions

`Candidate` adds a unique u32 ID, atomic-payload MTU, cost class and independently
measured `throughput_kbps` to each reading. RTT and jitter are milliseconds;
loss is parts per million. Throughput is a caller measurement in kilobits/second:
it is never inferred from RTT or MTU. Availability is supplied by the caller.
`choose(tick, class, wire_bytes, candidates)` returns an optional ID and a typed
reason with a static `as_str()`. It never silently substitutes another class.

| Class | Rank, in order |
| --- | --- |
| Control | Lower loss, lower RTT, lower jitter, lower cost class, smaller ID |
| Bulk | Higher measured throughput, then the control rank |
| Billboard | Control rank, restricted to non-BLE, non-ControlOnly links |

These decisions describe local policy over supplied readings, not measured radio
performance. No link is selected when all eligible candidates are down, too small
or forbidden for the class. `best_link` provides the same stateless ordering.

## IMPOSED choices for this slice

- There are at most 16 candidates; duplicate IDs, zero MTU, loss above 1,000,000,
  future observations and zero payload length reject the whole bank. Observations
  and selector calls share caller logical ticks. No observation TTL is invented:
  the caller enforces freshness before admission. Error paths change no state.
- BLE is control-only even if mislabeled Unmetered. Every ControlOnly link is
  also excluded from bulk and billboards. Zero throughput is bulk-ineligible;
  control/billboard ranking does not require a throughput estimate.
- Cost breaks remaining ties in this order: Unmetered, Metered, ControlOnly.
  Equal scores choose the smaller ID independently of input order.
- Callers explicitly supply `Hysteresis`; it has no Default. Hold units are
  logical ticks, with independent state per class. Margins are absolute loss ppm
  for control/billboard and measured kbps for bulk. A better candidate must meet
  both `elapsed >= hold` and `improvement >= margin`. A secondary-only improvement
  can switch only at zero margin. A u64::MAX bulk margin is allowed but cannot
  be met by two positive u64 speeds; no addition or signed negation is used.
- A missing, down, newly forbidden or too-small incumbent bypasses hold/margin
  immediately. No-channel clears its class state. Rollback is checked first;
  all other validation precedes every state/clock update.
- `wire_bytes` means ONE atomic underlay payload, not a logical reassembled
  frame. The BLE-only fixture selects 20-byte fragment-sized control chunks;
  its 112-byte control request has no channel at MTU 20. This slice neither
  fragments nor integrates `rpp-frag`, and billboards never use BLE.

## Scripted evidence and repeat commands

The default-std `sim` module provides 12 scripted steps: Wi-Fi drop/recovery,
LAN flapping and BLE only. Its explicit fixture parameters are hold 3 ticks,
control/billboard margins 10 ppm and bulk margin 500 kbps. The 36 class decisions
include hold, margin, immediate failover and explicit no-channel results.
`tests/data/steer-decisions.csv` is a Rust-generated regression snapshot, not an
independent Python oracle. Its exact LF bytes are protected by `.gitattributes`.
The std simulator repeats those bytes; an always-enabled host test replays the
same log through the bare core. The existing 17 Python-oracle files are untouched.

From the repository root with Rust 1.85.1:

```sh
cargo +1.85.1 test --manifest-path rust/Cargo.toml -p rpp-steer --offline --locked
cargo +1.85.1 test --manifest-path rust/Cargo.toml -p rpp-steer --no-default-features --offline --locked
cargo +1.85.1 run --manifest-path rust/Cargo.toml -p rpp-steer --example trace_log --offline --locked
```

The workspace CI already runs default/std, explicit link simulation, bare and
alloc-only profiles plus both riscv32 cross-builds. Default/std automatically
exercises this simulator; no extra steer simulation feature is required.
The stdlib `tools.steer_scaffold.mutation_check` runner executes named Rust
assertion counterfactuals in external copies, with passing baselines and
unaffected controls. Compiler errors and arbitrary panics are not kills.
Board input providers and safe integration beneath existing policy remain future work.
