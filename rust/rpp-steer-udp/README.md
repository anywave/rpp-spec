# Measured UDP steering bridge (CX-026)

This detached, std-only crate samples the existing UDP adapter and passes its
`LinkReading` to the existing selector. It sends probes; it does not dispatch
application traffic, establish tunnels, verify identity, or grant consent.
Both configured IPs must be loopback before sockets open. Caller admission,
trust, and consent remain prerequisites on every candidate.

| Selector input | Source |
| --- | --- |
| RTT, loss, jitter, availability, observed tick | Unchanged UDP `LinkReading` |
| MTU | `MAX_DATA_LEN = 1198`, configured atomic payload ceiling; not PMTU discovery |
| Throughput, cost, link ID | Explicit caller input; not inferred from RTT/loss |
| Hold and margins | Explicit existing `Hysteresis`; no defaults |

Bulk eligibility has explicit lower/upper loss bands, initially closed. A final
batch reading at/below the lower threshold opens it; an open gate closes only
above the upper threshold. Closed gates stay closed within the band. Control
and billboard candidates bypass this bulk gate; their existing selector rules
still apply. Withheld candidates retain their raw availability in observations.
Loss bands do not alter the core ranking or its hold/margin rules.

A decision batch contains 1..32 probes per endpoint and at most 64 total, evaluated
once using each final reading. Invalid policies, endpoints, counts, empty payloads,
and clock rollback fail before probe I/O. Accepted batches commit wrapper state;
a later I/O failure can leave physical UDP history changed, without committing
wrapper selection/gate/clock state. Callers control batch frequency and duration.
`Bridge::probe_counts()` exposes saturating per-endpoint read attempts, completed
reads, latest matching replies (`available`), losses, and errors. These are adapter
outcomes, not kernel-confirmed send counters. Diagnostics retain physical I/O
activity even when a batch aborts; rejected preflight calls perform no reads.

The test fixture uses two real IPv4 loopback peers. A drops probes 3, 6, 7 and echoes
others; B echoes. At A counts 2, 4, 8, 10, 31, 32 the measured loss is respectively
0, 250000, 375000, 300000, 96774, 93750 ppm. Fixed **scripted**, independently supplied
capacities 1000/800, hold 3, margin 100, and bands 100000/300000 produce
A Initial, A Best, B Ineligible, B Best, B Hold, A Improved. Both final readings
remain available. RTT/jitter vary and are excluded from deterministic assertions.
These fixtures simulate loss, capacity, and logical ticks; no LAN is contacted.
The responder blocks with a long timeout configured once. Shutdown uses an exact
stop datagram from a retained, prebound loopback waker after close is requested;
queued probes are processed before stop, and each worker is joined once. Worker
counts and errors are retained. The timeout is a backstop, not a hard global
shutdown deadline. Native Windows repeats remain a separate validation step.

The checkout is based on CX-023; its UDP dependency is not present until PR#30
merges. Normal relative path dependencies deliberately make standalone builds
and the lift check fail there. Local evidence uses an outside exact Git-blob
snapshot of this tree plus UDP core 36c5adec, sharing one `rpp-link` crate identity.
No dependency source is copied into this product tree. After integration, run:

```text
cargo +1.85.1 fmt --manifest-path rust/rpp-steer-udp/Cargo.toml -- --check
cargo +1.85.1 clippy --manifest-path rust/rpp-steer-udp/Cargo.toml --all-targets --locked -- -D warnings
cargo +1.85.1 test --manifest-path rust/rpp-steer-udp/Cargo.toml --locked
```
