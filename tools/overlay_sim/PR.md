# Proposed PR: Design a multi-channel overlay and simulate its failover policy

The resolver currently names modalities without specifying overlay identity,
self-forming tunnels, measured route selection or independent control paths.
Add a proposed design and a deterministic, stdlib-only simulator covering data
failover, relay routes, status-only radio control and authorized billboard expiry.
Spec additions remain an exact proposed diff; adopting them requires RADIX.

Validation: 30 simulator cases; twelve killed mutants, zero survivors, twelve clean
controls; 17 meter rows across 16 scripted requests; three byte-identical output
artifacts. Existing suite remains 1256 passed, golden vectors 5/0, Ruff 0.14.10
exits 0. Final combined-branch drift/diff results and the tested commit appear in
`docs/codex/OUTBOX/CX-005-001.md`. The simulator implements no cryptography or real
network transport and changes no packaged runtime behavior.
