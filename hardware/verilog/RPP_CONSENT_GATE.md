# RPP consent gate v0 (`rpp_consent_gate.v`)

Lattice PL-154 S3 / PL-155 (RADIX, 2026-10-07: consent gate, Mobius 32-bit frozen). Written by PL (RTX3).

## What it does

For every RPP packet, decide PASS or DROP from consent state the GATE holds, never from anything the packet says about
itself (TR-139 INV-1). Address layout: Mobius 32-bit, shell[31:30] theta[29:21] phi[20:12] harmonic[11:0]; consent is
held per theta sector (512). Only FULL passes. The gate fails closed: nothing passes before the first authenticated
update or once updates stop for longer than MAX_AGE ticks. Unauthenticated updates and older-epoch (rollback) updates
are refused. Epoch 0 is refused because ECP5 block RAM powers up as {epoch 0, FULL}. Each sector entry carries the
epoch it was granted in, so a new epoch invalidates all old grants at once.

Not in v0: signature verification. `upd_auth_ok` is the verdict of a separate verifier, whose cryptography is chosen
by measuring its LUT/clock cost next.

## Verified (simulation, Icarus Verilog 14, OSS CAD Suite 2026-09-24)

`iverilog -g2012 -Wall -o gate_tb rpp_consent_gate.v rpp_consent_gate_tb.v && vvp gate_tb` -> **20/20 PASS**
(T1-T13: fail-closed reset, armed pass, epoch, ungranted sector, unauthenticated update, rollback, EMERGENCY_OVERRIDE,
DIMINISHED, non-theta field independence over 128 random packets, staleness + refresh, new-epoch invalidation, reset,
epoch 0).

Mutation check: 6 deliberate bugs (no auth check, epoch 0 allowed, any state passes, staleness ignored, rollback
allowed, unauthenticated refresh), each **caught** by its tests.

## Measured (synthesis + place-and-route, Yosys 0.69 + nextpnr-ecp5, LFE5U-12F CABGA256)

| | |
|---|---|
| LUTs (TRELLIS_COMB) | 124 / 24288 |
| Flip-flops | 99 / 24288 |
| Block RAM (DP16KD) | 1 / 56 |
| Max clock | 90.2 MHz |
| Throughput / latency | 1 decision per clock (~90 M/s) / 2 clocks (~22 ns) |

I/O count (88) reflects this standalone top level; in a system the ports are internal.

Flow note: this Windows nightly's ABC9 asserts (timBox.c) during LUT mapping, so the measured netlist uses classic
`abc -lut 4` between stages:
`synth_lattice -family ecp5 -run begin:map_luts; abc -lut 4 -dress; clean; synth_lattice -family ecp5 -json gate.json -run map_cells:`
then `nextpnr-ecp5 --12k --package CABGA256 --json gate.json --freq 90`.
