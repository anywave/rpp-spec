// SPDX-License-Identifier: MIT
// Test bench for rpp_consent_gate (lattice PL-154 S3 / PL-155).
// Run: iverilog -g2012 -o gate_tb rpp_consent_gate.v rpp_consent_gate_tb.v && vvp gate_tb
// Prints "PASS <name>" or "FAIL <name> ..." per check and a final "SUMMARY pass=N fail=M"; exits non-zero on failure.
`timescale 1ns/1ps
`default_nettype none

module rpp_consent_gate_tb;
    localparam MAX_AGE = 16;

    // consent states (same encoding as spiral_consent.v)
    localparam [1:0] FULL = 2'b00, DIMINISHED = 2'b01, SUSPENDED = 2'b10, EMERGENCY = 2'b11;
    // decision reasons (must match rpp_consent_gate.v)
    localparam [2:0] R_PASS = 3'd0, R_NOT_ARMED = 3'd1, R_STALE = 3'd2, R_EPOCH = 3'd3, R_CONSENT = 3'd4;

    reg clk = 0, rst_n = 0, tick = 0;
    reg in_valid = 0; reg [31:0] in_addr = 0; reg [15:0] in_epoch = 0;
    reg upd_valid = 0, upd_auth_ok = 0; reg [15:0] upd_epoch = 0; reg [8:0] upd_sector = 0; reg [1:0] upd_state = 0;
    wire out_valid, out_pass; wire [2:0] out_reason;
    wire upd_ack, upd_refused;

    rpp_consent_gate #(.MAX_AGE(MAX_AGE)) dut (
        .clk(clk), .rst_n(rst_n), .tick(tick),
        .in_valid(in_valid), .in_addr(in_addr), .in_epoch(in_epoch),
        .out_valid(out_valid), .out_pass(out_pass), .out_reason(out_reason),
        .upd_valid(upd_valid), .upd_auth_ok(upd_auth_ok), .upd_epoch(upd_epoch),
        .upd_sector(upd_sector), .upd_state(upd_state),
        .upd_ack(upd_ack), .upd_refused(upd_refused)
    );

    always #5 clk = ~clk;

    integer n_pass = 0, n_fail = 0;

    // Mobius 32-bit layout: shell[31:30] theta[29:21] phi[20:12] harmonic[11:0]
    function [31:0] mk_addr(input [1:0] shell, input [8:0] theta, input [8:0] phi, input [11:0] harm);
        mk_addr = {shell, theta, phi, harm};
    endfunction

    task check(input cond, input [8*48-1:0] name);
        begin
            if (cond) begin n_pass = n_pass + 1; $display("PASS %0s", name); end
            else begin n_fail = n_fail + 1; $display("FAIL %0s (pass=%0b reason=%0d)", name, out_pass, out_reason); end
        end
    endtask

    // one packet; the decision appears 2 clocks after in_valid (clocked sector read, then decide)
    task send_pkt(input [31:0] addr, input [15:0] epoch);
        begin
            @(negedge clk); in_valid = 1; in_addr = addr; in_epoch = epoch;
            @(negedge clk); in_valid = 0;
            @(negedge clk);
        end
    endtask

    task send_upd(input auth, input [15:0] epoch, input [8:0] sector, input [1:0] st);
        begin
            @(negedge clk); upd_valid = 1; upd_auth_ok = auth; upd_epoch = epoch; upd_sector = sector; upd_state = st;
            @(negedge clk); upd_valid = 0; upd_auth_ok = 0;
        end
    endtask

    task ticks(input integer n);
        integer i;
        begin
            for (i = 0; i < n; i = i + 1) begin @(negedge clk); tick = 1; @(negedge clk); tick = 0; end
        end
    endtask

    integer k;
    reg same;
    reg [31:0] base;

    initial begin
        repeat (3) @(negedge clk); rst_n = 1;

        // T1 fail closed from reset: nothing passes before the first authenticated update
        send_pkt(mk_addr(0, 9'd7, 9'd1, 12'd1), 16'd5);
        check(!out_pass && out_reason == R_NOT_ARMED, "T1 reset is fail-closed (NOT_ARMED)");

        // T2 an authenticated update arms epoch 5 and sets sector 7 FULL -> theta 7 passes
        send_upd(1, 16'd5, 9'd7, FULL);
        send_pkt(mk_addr(0, 9'd7, 9'd1, 12'd1), 16'd5);
        check(out_pass && out_reason == R_PASS, "T2 armed FULL sector passes");

        // T3 wrong epoch drops
        send_pkt(mk_addr(0, 9'd7, 9'd1, 12'd1), 16'd4);
        check(!out_pass && out_reason == R_EPOCH, "T3 older packet epoch drops");

        // T4 a sector never granted defaults to SUSPENDED -> drops
        send_pkt(mk_addr(0, 9'd8, 9'd1, 12'd1), 16'd5);
        check(!out_pass && out_reason == R_CONSENT, "T4 ungranted sector drops");

        // T5 an UNAUTHENTICATED update is refused and changes nothing
        send_upd(0, 16'd5, 9'd8, FULL);
        check(upd_refused, "T5a unauthenticated update refused");
        send_pkt(mk_addr(0, 9'd8, 9'd1, 12'd1), 16'd5);
        check(!out_pass && out_reason == R_CONSENT, "T5b unauthenticated update had no effect");

        // T6 rollback: an authenticated update for an OLDER epoch is refused
        send_upd(1, 16'd4, 9'd8, FULL);
        check(upd_refused, "T6a rollback update refused");
        send_pkt(mk_addr(0, 9'd8, 9'd1, 12'd1), 16'd5);
        check(!out_pass, "T6b rollback had no effect");

        // T7 EMERGENCY_OVERRIDE never grants passage (TR-139 INV-1: consent never authorizes)
        send_upd(1, 16'd5, 9'd9, EMERGENCY);
        send_pkt(mk_addr(0, 9'd9, 9'd1, 12'd1), 16'd5);
        check(!out_pass && out_reason == R_CONSENT, "T7 EMERGENCY_OVERRIDE does not pass");

        // T8 DIMINISHED does not pass in v0 (only FULL passes)
        send_upd(1, 16'd5, 9'd10, DIMINISHED);
        send_pkt(mk_addr(0, 9'd10, 9'd1, 12'd1), 16'd5);
        check(!out_pass && out_reason == R_CONSENT, "T8 DIMINISHED does not pass");

        // T9 the decision depends only on theta + epoch: shell/phi/harmonic cannot change it
        base = mk_addr(0, 9'd7, 9'd0, 12'd0);
        same = 1;
        for (k = 0; k < 64; k = k + 1) begin
            send_pkt({$random} & 32'hC01FFFFF | (32'd7 << 21), 16'd5);
            if (!out_pass) same = 0;
            send_pkt(({$random} & 32'hC01FFFFF) | (32'd8 << 21), 16'd5);
            if (out_pass) same = 0;
        end
        check(same, "T9 non-theta fields never change the decision");

        // T10 freshness: with no authenticated refresh for MAX_AGE+1 ticks, EVERYTHING drops
        ticks(MAX_AGE + 1);
        send_pkt(mk_addr(0, 9'd7, 9'd1, 12'd1), 16'd5);
        check(!out_pass && out_reason == R_STALE, "T10a stale state fails closed");
        // an authenticated refresh (same epoch) restores service
        send_upd(1, 16'd5, 9'd7, FULL);
        send_pkt(mk_addr(0, 9'd7, 9'd1, 12'd1), 16'd5);
        check(out_pass, "T10b authenticated refresh restores service");
        // an unauthenticated update does NOT refresh freshness
        ticks(MAX_AGE - 2);
        send_upd(0, 16'd5, 9'd7, FULL);
        ticks(3);
        send_pkt(mk_addr(0, 9'd7, 9'd1, 12'd1), 16'd5);
        check(!out_pass && out_reason == R_STALE, "T10c unauthenticated update does not refresh");

        // T11 a NEW epoch clears every sector to SUSPENDED (fail closed), then grants as updated
        send_upd(1, 16'd6, 9'd11, FULL);
        send_pkt(mk_addr(0, 9'd7, 9'd1, 12'd1), 16'd6);
        check(!out_pass && out_reason == R_CONSENT, "T11a new epoch cleared old grants");
        send_pkt(mk_addr(0, 9'd11, 9'd1, 12'd1), 16'd6);
        check(out_pass, "T11b new-epoch grant passes");
        send_pkt(mk_addr(0, 9'd11, 9'd1, 12'd1), 16'd5);
        check(!out_pass && out_reason == R_EPOCH, "T11c previous-epoch packets drop");

        // T12 reset returns to fail-closed
        @(negedge clk); rst_n = 0; repeat (2) @(negedge clk); rst_n = 1;
        send_pkt(mk_addr(0, 9'd11, 9'd1, 12'd1), 16'd6);
        check(!out_pass && out_reason == R_NOT_ARMED, "T12 reset is fail-closed again");

        // T13 epoch 0 is refused even when authenticated (block RAM powers up as {epoch 0, FULL})
        @(negedge clk); rst_n = 0; repeat (2) @(negedge clk); rst_n = 1;
        send_upd(1, 16'd0, 9'd20, FULL);
        check(upd_refused, "T13a authenticated epoch-0 update refused");
        send_pkt(mk_addr(0, 9'd300, 9'd1, 12'd1), 16'd0);
        check(!out_pass && out_reason == R_NOT_ARMED, "T13b zero-initialized sectors never pass");

        $display("SUMMARY pass=%0d fail=%0d", n_pass, n_fail);
        if (n_fail != 0) $fatal(1, "consent gate test bench FAILED");
        $finish;
    end
endmodule
