# Add caller-assigned fleet addresses and live endpoint resolution

Connect/device callers can associate opaque lender/device IDs with explicit
canonical addresses and choose among endpoint records using existing core
overlay policy. The provisional `rpp-fleet` library preserves address bytes as
readings change, rejects local identity/address/control-ID collisions and
reports endpoint/failover selection or explicit no-channel. LAN, Wi-Fi,
internet, BLE, LoRa and Xiaozhi-use-case LAN WebSocket gateway records are
metadata; no transport, board, network or cryptography is implemented.

The named `explicit-caller-assignment-v1` mode requires a matching owner binding;
there is no identity-only hash derivation, cryptographic ownership proof or
global uniqueness claim. Control selection requires the closed control type,
current host authorization and a known independent data-path context. It reuses
core routing/consent/tunnel policy rather than defining another policy engine.

An exact proposed/informative resolver diff is supplied for review and remains
unapplied. `rust/FLEET.md` documents the source trace, record schema, trust
boundaries and integration gaps. The CX-010 outbox records gate commands,
scenario/golden hashes and named mutation results. Cross-compilation checks the
library; board and hosted execution are not claimed.

Branch `codex/rpp-fleet` → `master`, base `0d262bf` after CX-009. Existing spec,
Python runtime behavior, address layouts, consent header, vectors and published
constants are unchanged. TR creates the PR and performs any merge.
