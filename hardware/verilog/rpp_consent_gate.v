// SPDX-License-Identifier: MIT
// RPP line-rate consent gate, v0 (lattice PL-154 S3; RADIX rulings PL-155: consent gate, Mobius 32-bit frozen).
//
// What it does: for every RPP packet, decide PASS or DROP from consent state the GATE holds, never from anything the
// packet says about itself (TR-139 INV-1: consent fields never become authorization inputs). The state is set only by
// AUTHENTICATED updates; the gate fails CLOSED when it has none (after reset) or when they stop (staleness).
//
// Address layout (Mobius 32-bit, docs/RPP-PROFILE-MOBIUS.md): shell[31:30] theta[29:21] phi[20:12] harmonic[11:0].
// Consent is held per theta sector (512 sectors). Only FULL passes; DIMINISHED, SUSPENDED and EMERGENCY_OVERRIDE drop.
// EMERGENCY_OVERRIDE in particular never grants passage.
//
// Not in v0 (named): signature verification. `upd_auth_ok` is the verdict of a separate verifier whose cryptography is
// chosen by measurement (LUT/clock budget); this module trusts nothing else. One gate per privileged route (TR-139
// INV-2) is a placement rule for the system around this module.
//
// Timing: a decision appears 2 clocks after `in_valid` (clocked sector read, then decide), so the sector table infers
// block RAM (512 x 18 bits) on ECP5.
`timescale 1ns/1ps
`default_nettype none

module rpp_consent_gate #(
    parameter integer MAX_AGE = 1024,   // ticks without an authenticated update before the state is stale
    parameter integer EPOCH_W = 16
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               tick,        // freshness time base (one pulse per time unit)

    // packet in
    input  wire               in_valid,
    input  wire [31:0]        in_addr,
    input  wire [EPOCH_W-1:0] in_epoch,

    // decision out (2 clocks after in_valid)
    output reg                out_valid,
    output reg                out_pass,
    output reg  [2:0]         out_reason,

    // consent state update (already signature-checked by the verifier -> upd_auth_ok)
    input  wire               upd_valid,
    input  wire               upd_auth_ok,
    input  wire [EPOCH_W-1:0] upd_epoch,
    input  wire [8:0]         upd_sector,
    input  wire [1:0]         upd_state,
    output reg                upd_ack,
    output reg                upd_refused
);
    localparam [1:0] FULL = 2'b00;
    localparam [2:0] R_PASS = 3'd0, R_NOT_ARMED = 3'd1, R_STALE = 3'd2, R_EPOCH = 3'd3, R_CONSENT = 3'd4;
    localparam integer AGE_W = $clog2(MAX_AGE + 2);

    // per-sector entry: {epoch granted in, state}. An entry from an older epoch reads as not granted, so a new epoch
    // invalidates every grant without clearing 512 entries.
    reg [EPOCH_W+1:0] sector_mem [0:511];

    reg               armed;
    reg [EPOCH_W-1:0] cur_epoch;
    reg [AGE_W-1:0]   age;
    wire              stale = (age > MAX_AGE);

    // ---- updates -------------------------------------------------------------------------------------------------
    // Epoch 0 is never valid: ECP5 block RAM powers up as all zeros, which this encoding reads as {epoch 0, FULL}.
    // Refusing epoch 0 means a power-up entry can never match the current epoch.
    wire upd_accept = upd_valid && upd_auth_ok && (upd_epoch != {EPOCH_W{1'b0}}) && (!armed || upd_epoch >= cur_epoch);

    always @(posedge clk) begin
        if (upd_accept) sector_mem[upd_sector] <= {upd_epoch, upd_state};
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            armed <= 1'b0; cur_epoch <= {EPOCH_W{1'b0}}; age <= {AGE_W{1'b0}};
            upd_ack <= 1'b0; upd_refused <= 1'b0;
        end else begin
            upd_ack     <= upd_accept;
            upd_refused <= upd_valid && !upd_accept;
            if (upd_accept) begin
                armed <= 1'b1;
                if (!armed || upd_epoch > cur_epoch) cur_epoch <= upd_epoch;
                age <= {AGE_W{1'b0}};                       // only an AUTHENTICATED update refreshes freshness
            end else if (tick && !stale) begin
                age <= age + 1'b1;                          // saturates one past MAX_AGE
            end
        end
    end

    // ---- packets: stage 1 (clocked sector read) --------------------------------------------------------------------
    reg               s1_valid;
    reg [EPOCH_W-1:0] s1_epoch;
    reg [EPOCH_W+1:0] s1_entry;

    always @(posedge clk) begin
        s1_entry <= sector_mem[in_addr[29:21]];              // theta
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            s1_valid <= 1'b0; s1_epoch <= {EPOCH_W{1'b0}};
        end else begin
            s1_valid <= in_valid;
            s1_epoch <= in_epoch;
        end
    end

    // ---- packets: stage 2 (decide) ---------------------------------------------------------------------------------
    wire [EPOCH_W-1:0] entry_epoch = s1_entry[EPOCH_W+1:2];
    wire [1:0]         entry_state = s1_entry[1:0];

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            out_valid <= 1'b0; out_pass <= 1'b0; out_reason <= R_NOT_ARMED;
        end else begin
            out_valid <= s1_valid;
            if (s1_valid) begin
                if (!armed)                                                   begin out_pass <= 1'b0; out_reason <= R_NOT_ARMED; end
                else if (stale)                                               begin out_pass <= 1'b0; out_reason <= R_STALE;     end
                else if (s1_epoch != cur_epoch)                               begin out_pass <= 1'b0; out_reason <= R_EPOCH;     end
                else if (entry_epoch != cur_epoch || entry_state != FULL)     begin out_pass <= 1'b0; out_reason <= R_CONSENT;   end
                else                                                          begin out_pass <= 1'b1; out_reason <= R_PASS;      end
            end
        end
    end

    // ---- simulation mirrors hardware: block RAM powers up as all zeros ({epoch 0, FULL}) -----------------------------
    // Safe only because epoch 0 is refused above (test T13). Do not change one without the other.
    integer i;
    initial for (i = 0; i < 512; i = i + 1) sector_mem[i] = {(EPOCH_W+2){1'b0}};
endmodule
