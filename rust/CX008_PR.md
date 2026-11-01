# Add experimental no_std control codec and ESP32 adapter interfaces

ESP32 adapters can use provisional `rpp-control` and `rpp-link` libraries without
adding a board HAL or radio implementation to the core. The closed 112-byte
experimental control frame represents six notice kinds and has no payload field;
decoding checks its structure, recipient and an external verifier result.
Signatures remain opaque, and the library implements no cryptography.

Typed control/data send hooks and plain link readings connect host-side simulated
adapters to the existing overlay policy. Scenario CSV/Markdown/JSON bytes are
compared with the Python reference. Workspace CI includes both crates in default
and no-default-feature host checks and bare-metal RISC-V library builds; all
checks fail normally. Commands, counts, corpus hashes and limitations are in
`rust/ESP32.md` and `docs/codex/OUTBOX/CX-008-001.md`.

Host sampling/identity failures return explicit errors before policy requests and
need caller boundary metering. Slash-containing simulated adapter names are
rejected before callbacks to prevent hop-path aliases. Billboard transport uses
an opaque placeholder and assumed prior verification; it is not a wire codec,
and unsupported failure fixtures are rejected before storage or sends.

This is an unpublished frame experiment and a cross-compile check, not firmware
or board validation. The 16-byte identities and 64-byte signature field are
IMPOSED experiment choices. Membership, consent, replay protection, independent
control paths and actual verification remain host duties. RADIX still needs to
supply the board models. Existing spec, consent header, address layouts, vectors
and published constants are unchanged.

Branch `codex/esp32-groundwork` is stacked on `codex/rust-rpp-crate`.
TR reviews/merges CX-007 Part A (catalog), Part B (Rust), then its report, followed
by CX-008. Until Part B is merged, use it as this PR's base; afterward use
`master` so the displayed diff contains the groundwork only. TR creates the PR
and performs any merge.
