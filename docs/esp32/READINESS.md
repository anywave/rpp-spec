# Embedded library readiness — compile evidence, not a board build

CX-025 uses Rust 1.85.1 and `riscv32imc-unknown-none-elf`, appropriate to the
ESP32-C3 instruction set. It does not target classic Xtensa ESP32, link firmware,
flash a device, open a radio/socket, implement cryptography or measure a board.

## Exact source sets

The local branch `codex/cx-025-esp32-build` is stacked on CX-023:
`b330b0b0b73dffb2b87f2cb9063301de71efffb4`. Master at preparation was
`4f22f005871f7b3b15a9565206bd79e98f14b51b`, which lacks `rpp-steer`.
The product Rust tree stays exactly that CX-023 tree; CX-024 code is not copied
into this branch and no two-feature integration merge is created.

A separate **outside verification snapshot** exports those exact Rust Git blobs
and overlays the five changed Rust paths from final CX-024
`35d88575ebd5c83c1d2905b39ed6e31a50e788c4`, relative to its master base above.
It preserves CX-023's workspace and lockfile so steer remains present. All 84
Rust files in each source set have recorded hashes. This snapshot is not a Git
merge, this branch's ancestry, or evidence that a future merged tree was tested.
Both actual checkout and snapshot pass the same three-crate offline build.
Source-manifest SHA256:
`20f92a9d3884dd50b982ae4e979c7a63d7f7bb047600d2daadc245866f20fbf4`.

## Per-crate profile and memory estimate

| Crate | Bare profile / heap and std | Scoped stack/storage estimate on RISC-V | Remaining port work |
| --- | --- | --- | --- |
| `rpp-billboard` | `--no-default-features`: borrowed codec, no allocator or std. Default std enables alloc; owned `to_core` conversion needs an application allocator. | Encode has a 925-byte local scratch array. A maximum-size caller output placed on the stack adds another 925 bytes: 1,850 bytes of explicit buffers, plus compiler/callee/verifier frames. Decode has four `usize` offsets (16 bytes); a returned borrowed view is 72 bytes. | Caller verification, identity/trust/replay/expiry policy, adequate transport/queues and real firmware stack budget. |
| `rpp-frag` | No alloc/std feature. Its control dependency disables defaults. | `Reassembler<4,112>` occupies 1,080 bytes in this branch, 1,144 in the CX-024 snapshot; `Fragmenter<112>` is 20 bytes. If both plus a 20-byte wire buffer are stack-resident, explicit state/buffers total 1,120 / 1,184 bytes. Constructor moves, decode and verifier frames are extra. | Bind ingress peer, tags and ticks; provision slots/queues/timeouts and caller verification. Completed-key bookkeeping differs between the two source versions. |
| `rpp-steer` | Bare selector/ranking has no allocation or std. The default std feature exposes host trace formatting and is disabled here. | Selector is 88 bytes; one candidate is 48; `[Candidate;16]` is 768. Stack-resident state plus maximum input array accounts for 856 bytes, plus call frames. Ranking uses slices and does not grow a local array. | Feed measured readings, explicit hysteresis and host eligibility; connect actual adapters and account for atomic MTUs. |

**Method:** source inspection counts explicit fixed arrays; the safe standalone
`tools/esp32_scaffold/memory_probe.rs` emits compiler `size_of` constants into LLVM
IR using the actual RISC-V rlibs. These are object sizes and scoped stack estimates,
not measured stack frames or a formal maximum. Caller placement, compiler
optimization/temporaries, verifier, drivers, interrupts and task depth are not
bounded by this probe. Long-lived state need not occupy a small task stack.
Measure firmware stack high-water marks and heap budgets on the chosen board.
The three library builds alone do not establish whole-application allocation use.

Current fragmentation outputs only through the 112-byte control decoder. It does
not fragment 925-byte billboard envelopes. A billboard needs a sufficient
transport or separately reviewed framing. Steering ranks **one atomic underlay
payload** and performs no fragmentation; it cannot authorize BLE data. Firmware
still needs startup/linker/HAL, timers, bounded queues, adapter implementations,
a reviewed verifier, and the same consent/trust policy on every channel.

## Offline checker and CI

```sh
python tools/esp32_scaffold/check_no_std.py
python -m unittest tools.esp32_scaffold.test_check_no_std -v
```

The checker discovers **already installed** Rust/Cargo 1.85.1 with auto-install
disabled. It checks actual core/compiler-builtins archives, prefers RISC-V, and
uses `thumbv7em-none-eabihf` only when RISC-V is genuinely absent. Thumb is an
explicit compile stand-in. Missing tools or both targets produce JSON `SKIP`
with a reason and no build claim. Partial/dangling installations, malformed probe
or toolchain output, wrong pins, invocation/output/timeout errors and Cargo
failures produce `FAIL` with a nonzero exit; they cannot trigger fallback.

The fixed command builds `--lib -p rpp-billboard -p rpp-frag -p rpp-steer`
with `--no-default-features --offline --locked`. It requires all three sources
and the lockfile before allowing a skip. Build/cache paths stay outside and
disjoint from both the selected checkout and probe sources, including resolved
derived cache and LLVM output paths. Ambient
wrappers/flags are cleared; an explicit separate sysroot uses encoded arguments
so paths with spaces survive. Each command has a deadline and bounded merged
stdout/stderr. The checker never installs/downloads a tool or target.

CI runs the checker's stdlib unit tests before this compile-only check inside
its existing Rust job **after existing pinned provisioning**. Successful checks
also compile the sibling safe memory probe against the same three built rlibs,
selected target/compiler/sysroot, before temporary output cleanup. This compiles
current types; it does not assert historical table values or measure stack use.
The workflow's existing setup can use the network; the checker/build do not
install or fetch. CI checks its actual checkout, not the outside snapshot. After dependencies land or a PR base changes, integrate forward
normally and rerun the checker; the local snapshot does not replace that check.

For extracted local tools, supply `--cargo`, `--rustc`, `--sysroot` and an external
`--work-dir`. The local official compiler/core archives match saved channel
manifest hashes; no new download was needed. Windows repeats use the same Python
commands with the installed pinned rustup toolchain. No native Windows run or
physical ESP32 readiness is claimed by this document.
