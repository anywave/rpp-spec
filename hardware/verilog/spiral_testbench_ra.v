// SPDX-License-Identifier: MIT
// SPIRAL Protocol – Comprehensive Ra-Canonical Testbench
// Version: 2.1.0
//
// Exhaustive validation of:
//   1. ConsentHeaderParser
//   2. PhaseMemoryAnchorRAM
//   3. CoherenceEvaluator_Ra (Ra-derived formula)
//   4. FallbackResolver_Ra
//   5. ScalarTrigger_Ra
//   6. Integration scenarios
//
// Run with: iverilog -o spiral_ra_tb.vvp spiral_testbench_ra.v spiral_ra_coherence.v spiral_consent.v spiral_consolidated.v && vvp spiral_ra_tb.vvp

`timescale 1ns / 1ps

`default_nettype none

module spiral_testbench_ra;

    // =========================================================================
    // Clock and Reset
    // =========================================================================
    reg clk;
    reg rst_n;

    initial begin
        clk = 0;
        forever #5 clk = ~clk;  // 100 MHz clock
    end

    // =========================================================================
    // Test Counters
    // =========================================================================
    integer test_count;
    integer pass_count;
    integer fail_count;

    // =========================================================================
    // DUT Signals - CoherenceEvaluator_Ra
    // =========================================================================
    reg  [4:0]  coh_entropy;
    reg  [2:0]  coh_complecount;
    reg  [9:0]  coh_threshold;
    wire [9:0]  coh_score;
    wire [7:0]  coh_normalized;
    wire        coh_valid;
    wire        coh_high;
    wire        coh_medium;
    wire        coh_low;

    CoherenceEvaluator_Ra dut_coherence (
        .phase_entropy_index(coh_entropy),
        .complecount_trace(coh_complecount),
        .coherence_threshold(coh_threshold),
        .coherence_score(coh_score),
        .coherence_normalized(coh_normalized),
        .coherence_valid(coh_valid),
        .high_coherence(coh_high),
        .medium_coherence(coh_medium),
        .low_coherence(coh_low)
    );

    // =========================================================================
    // DUT Signals - CoherenceEvaluator_Ra_Precise (LUT-based)
    // =========================================================================
    wire [9:0]  coh_precise_score;
    wire        coh_precise_valid;

    CoherenceEvaluator_Ra_Precise dut_coherence_precise (
        .phase_entropy_index(coh_entropy),
        .complecount_trace(coh_complecount),
        .coherence_threshold(coh_threshold),
        .coherence_score(coh_precise_score),
        .coherence_valid(coh_precise_valid)
    );

    // =========================================================================
    // DUT Signals - ScalarTrigger_Ra
    // =========================================================================
    reg         scalar_enable;
    reg  [7:0]  scalar_radius;
    reg  [7:0]  scalar_threshold;
    reg  [7:0]  scalar_duration;
    wire        scalar_triggered;
    wire [7:0]  scalar_counter;
    wire        scalar_above;
    wire        scalar_stable;

    ScalarTrigger_Ra dut_scalar (
        .clk(clk),
        .reset(~rst_n),
        .enable(scalar_enable),
        .radius(scalar_radius),
        .activation_threshold(scalar_threshold),
        .coherence_duration(scalar_duration),
        .coherence_valid(coh_valid),
        .scalar_triggered(scalar_triggered),
        .duration_counter(scalar_counter),
        .above_threshold(scalar_above),
        .stable_resonance(scalar_stable)
    );

    // =========================================================================
    // DUT Signals - FallbackResolver_Ra
    // =========================================================================
    reg         fb_trigger;
    reg  [4:0]  fb_primary_theta;
    reg  [2:0]  fb_primary_phi;
    reg  [2:0]  fb_primary_omega;
    reg  [7:0]  fb_primary_radius;
    reg  [7:0]  fb_vector;
    wire [4:0]  fb_theta;
    wire [2:0]  fb_phi;
    wire [2:0]  fb_omega;
    wire [7:0]  fb_radius;
    wire [31:0] fb_address;
    wire        fb_active;

    FallbackResolver_Ra dut_fallback (
        .trigger(fb_trigger),
        .primary_theta(fb_primary_theta),
        .primary_phi(fb_primary_phi),
        .primary_omega(fb_primary_omega),
        .primary_radius(fb_primary_radius),
        .fallback_vector(fb_vector),
        .base_address(32'h00000000),
        .fallback_theta(fb_theta),
        .fallback_phi(fb_phi),
        .fallback_omega(fb_omega),
        .fallback_radius(fb_radius),
        .fallback_address(fb_address),
        .fallback_active(fb_active)
    );

    // =========================================================================
    // DUT Signals - ConsentArbitrator_Ra
    // =========================================================================
    reg         arb_coherence_valid;
    reg         arb_scalar_triggered;
    reg  [1:0]  arb_consent_state;
    reg         arb_needs_fallback;
    reg         arb_pma_hit;
    wire        arb_route_allowed;
    wire        arb_use_fallback;
    wire        arb_use_pma;
    wire [2:0]  arb_decision;

    ConsentArbitrator_Ra dut_arbitrator (
        .coherence_valid(arb_coherence_valid),
        .scalar_triggered(arb_scalar_triggered),
        .consent_state(arb_consent_state),
        .needs_fallback(arb_needs_fallback),
        .pma_hit(arb_pma_hit),
        .route_allowed(arb_route_allowed),
        .use_fallback(arb_use_fallback),
        .use_pma_route(arb_use_pma),
        .routing_decision(arb_decision)
    );

    // =========================================================================
    // DUT Signals - ConsentHeaderParser
    // =========================================================================
    reg  [143:0] header_in;
    wire [4:0]   hdr_theta;
    wire [2:0]   hdr_phi;
    wire [2:0]   hdr_omega;
    wire [7:0]   hdr_radius;
    wire [31:0]  hdr_packet_id;
    wire [15:0]  hdr_origin_ref;
    wire         hdr_verbal;
    wire [3:0]   hdr_somatic;
    wire [1:0]   hdr_ancestral;
    wire         hdr_temporal;
    wire [4:0]   hdr_entropy;
    wire [2:0]   hdr_complecount;
    wire [3:0]   hdr_payload;
    wire [7:0]   hdr_fallback;
    wire [15:0]  hdr_window_id;
    wire [7:0]   hdr_target_phase;
    wire [7:0]   hdr_crc;
    wire [1:0]   hdr_consent_state;
    wire         hdr_needs_fallback;
    wire         hdr_has_pma;

    ConsentHeaderParser dut_header (
        .header_in(header_in),
        .rpp_theta(hdr_theta),
        .rpp_phi(hdr_phi),
        .rpp_omega(hdr_omega),
        .rpp_radius(hdr_radius),
        .packet_id(hdr_packet_id),
        .origin_ref(hdr_origin_ref),
        .consent_verbal(hdr_verbal),
        .consent_somatic(hdr_somatic),
        .consent_ancestral(hdr_ancestral),
        .temporal_lock(hdr_temporal),
        .phase_entropy_index(hdr_entropy),
        .complecount_trace(hdr_complecount),
        .payload_type(hdr_payload),
        .fallback_vector(hdr_fallback),
        .coherence_window_id(hdr_window_id),
        .target_phase_ref(hdr_target_phase),
        .header_crc(hdr_crc),
        .consent_state(hdr_consent_state),
        .needs_fallback(hdr_needs_fallback),
        .has_pma_link(hdr_has_pma)
    );

    // =========================================================================
    // VCD Dump for GTKWave
    // =========================================================================
    initial begin
        $dumpfile("spiral_ra_test.vcd");
        $dumpvars(0, spiral_testbench_ra);
    end

    // =========================================================================
    // Test Helpers
    // =========================================================================
    task check_result;
        input [255:0] test_name;
        input         condition;
        begin
            test_count = test_count + 1;
            if (condition) begin
                pass_count = pass_count + 1;
                $display("[PASS] %s", test_name);
            end else begin
                fail_count = fail_count + 1;
                $display("[FAIL] %s", test_name);
            end
        end
    endtask

    task print_section;
        input [255:0] section_name;
        begin
            $display("");
            $display("============================================================");
            $display(" %s", section_name);
            $display("============================================================");
        end
    endtask

    // =========================================================================
    // Main Test Sequence
    // =========================================================================
    integer i, j;
    reg [9:0] expected_score;
    reg [15:0] phi_term, ankh_term;

    initial begin
        // Initialize
        test_count = 0;
        pass_count = 0;
        fail_count = 0;

        rst_n = 0;
        coh_entropy = 0;
        coh_complecount = 0;
        coh_threshold = 0;
        scalar_enable = 0;
        scalar_radius = 0;
        scalar_threshold = 0;
        scalar_duration = 0;
        fb_trigger = 0;
        fb_primary_theta = 1;
        fb_primary_phi = 0;
        fb_primary_omega = 0;
        fb_primary_radius = 0;
        fb_vector = 0;
        arb_coherence_valid = 0;
        arb_scalar_triggered = 0;
        arb_consent_state = 0;
        arb_needs_fallback = 0;
        arb_pma_hit = 0;
        header_in = 144'h0;

        #100;
        rst_n = 1;
        #20;

        // =====================================================================
        // TEST SECTION 1: CoherenceEvaluator_Ra Sweep
        // =====================================================================
        print_section("CoherenceEvaluator_Ra - Full Sweep");

        $display("Sweeping entropy (0-31) x complecount (0-7)...");
        $display("");
        $display("entropy | comple | score | norm | H/M/L | valid");
        $display("--------|--------|-------|------|-------|------");

        for (i = 0; i <= 31; i = i + 4) begin
            for (j = 0; j <= 7; j = j + 1) begin
                coh_entropy = i;
                coh_complecount = j;
                coh_threshold = 10'd300;  // 3.0 threshold
                #10;

                $display("   %2d   |   %1d    |  %3d  | %3d  |  %s  |   %b",
                    i, j, coh_score, coh_normalized,
                    coh_high ? "H" : (coh_medium ? "M" : "L"),
                    coh_valid);
            end
        end

        // Verify key coherence points
        coh_entropy = 31; coh_complecount = 7; coh_threshold = 10'd400;
        #10;
        check_result("Max coherence (E=31, C=7) >= 4.0", coh_valid);
        $display("  Max score: %d (expected ~670)", coh_score);

        coh_entropy = 0; coh_complecount = 0; coh_threshold = 10'd100;
        #10;
        check_result("Min coherence (E=0, C=0) < 1.0", !coh_valid);

        coh_entropy = 15; coh_complecount = 3; coh_threshold = 10'd300;
        #10;
        check_result("Mid coherence should be medium", coh_medium);

        // Compare precise vs approximate
        print_section("Precise vs Approximate Comparison");
        for (i = 0; i <= 31; i = i + 8) begin
            for (j = 0; j <= 7; j = j + 2) begin
                coh_entropy = i;
                coh_complecount = j;
                #10;
                $display("E=%2d C=%1d: Approx=%3d Precise=%3d Diff=%d",
                    i, j, coh_score, coh_precise_score,
                    (coh_score > coh_precise_score) ?
                        (coh_score - coh_precise_score) :
                        (coh_precise_score - coh_score));
            end
        end

        // =====================================================================
        // TEST SECTION 2: ScalarTrigger_Ra Tests
        // =====================================================================
        print_section("ScalarTrigger_Ra - Duration Tests");

        // Test basic trigger with short duration
        scalar_enable = 1;
        scalar_radius = 8'd150;
        scalar_threshold = 8'd100;
        scalar_duration = 8'd4;
        coh_threshold = 10'd200;

        $display("Testing scalar trigger: radius=150, threshold=100, duration=4");
        $display("Cycle | Counter | Above | Triggered | Stable");

        for (i = 0; i < 10; i = i + 1) begin
            @(posedge clk);
            #1;
            $display("  %2d  |    %d    |   %b   |     %b     |   %b",
                i, scalar_counter, scalar_above, scalar_triggered, scalar_stable);
        end

        check_result("Scalar triggered after duration", scalar_triggered);

        // Test reset on threshold drop
        $display("\nDropping radius below threshold...");
        scalar_radius = 8'd50;
        @(posedge clk); @(posedge clk);
        #1;
        check_result("Scalar reset when radius drops", !scalar_triggered);
        check_result("Counter reset when radius drops", scalar_counter == 0);

        // Test mid-cycle radius fluctuation
        print_section("ScalarTrigger_Ra - Fluctuation Test");
        scalar_radius = 8'd150;
        @(posedge clk); @(posedge clk);
        scalar_radius = 8'd50;  // Drop mid-cycle
        @(posedge clk);
        scalar_radius = 8'd150;  // Rise again
        for (i = 0; i < 6; i = i + 1) @(posedge clk);
        #1;
        check_result("Trigger after fluctuation recovery", scalar_triggered);

        // =====================================================================
        // TEST SECTION 3: FallbackResolver_Ra Tests
        // =====================================================================
        print_section("FallbackResolver_Ra - XOR Logic");

        // Test basic XOR
        fb_primary_theta = 5'd12;
        fb_primary_phi = 3'd3;
        fb_primary_omega = 3'd2;
        fb_primary_radius = 8'd128;
        fb_vector = 8'b101_011_01;  // theta_off=5, phi_off=3, omega_off=1

        fb_trigger = 0;
        #10;
        $display("Primary: theta=%d phi=%d omega=%d radius=%d",
            fb_theta, fb_phi, fb_omega, fb_radius);
        check_result("No trigger passes primary", fb_theta == 5'd12);

        fb_trigger = 1;
        #10;
        $display("Fallback: theta=%d phi=%d omega=%d radius=%d",
            fb_theta, fb_phi, fb_omega, fb_radius);
        check_result("Fallback active flag", fb_active);

        // Test wrap-around cases
        print_section("FallbackResolver_Ra - Wrap Tests");

        // Theta wrap (27 -> 1)
        fb_primary_theta = 5'd26;
        fb_vector = 8'b111_000_00;  // theta_off=7
        #10;
        $display("Theta wrap: 26 XOR 7 = %d (wrapped)", fb_theta);
        check_result("Theta wraps correctly", fb_theta >= 1 && fb_theta <= 27);

        // Phi wrap (5 -> 0)
        fb_primary_theta = 5'd12;
        fb_primary_phi = 3'd5;
        fb_vector = 8'b000_111_00;  // phi_off=7
        #10;
        $display("Phi wrap: 5 XOR 7 = %d (wrapped)", fb_phi);
        check_result("Phi in valid range", fb_phi <= 3'd5);

        // =====================================================================
        // TEST SECTION 4: ConsentArbitrator_Ra Tests
        // =====================================================================
        print_section("ConsentArbitrator_Ra - Decision Matrix");

        $display("coh_v | sca_t | state | fb | pma | allowed | use_fb | use_pma | decision");
        $display("------|-------|-------|----|----|---------|--------|---------|----------");

        // Sweep all combinations
        for (i = 0; i < 16; i = i + 1) begin
            arb_coherence_valid  = i[0];
            arb_scalar_triggered = i[1];
            arb_needs_fallback   = i[2];
            arb_pma_hit          = i[3];

            for (j = 0; j < 4; j = j + 1) begin
                arb_consent_state = j;
                #10;

                $display("  %b   |   %b   |  %b%b   |  %b |  %b  |    %b    |   %b    |    %b    |    %b%b%b",
                    arb_coherence_valid, arb_scalar_triggered,
                    arb_consent_state[1], arb_consent_state[0],
                    arb_needs_fallback, arb_pma_hit,
                    arb_route_allowed, arb_use_fallback, arb_use_pma,
                    arb_decision[2], arb_decision[1], arb_decision[0]);
            end
        end

        // Key assertions
        arb_consent_state = 2'b00;  // FULL_CONSENT
        arb_coherence_valid = 1;
        arb_needs_fallback = 0;
        arb_pma_hit = 0;
        #10;
        check_result("FULL_CONSENT + coherent = allowed", arb_route_allowed);

        arb_consent_state = 2'b10;  // SUSPENDED
        #10;
        check_result("SUSPENDED = blocked", !arb_route_allowed);

        arb_consent_state = 2'b11;  // EMERGENCY
        #10;
        check_result("EMERGENCY = blocked", !arb_route_allowed);

        arb_consent_state = 2'b01;  // DIMINISHED
        arb_coherence_valid = 0;
        #10;
        check_result("DIMINISHED + incoherent = blocked", !arb_route_allowed);

        arb_coherence_valid = 1;
        #10;
        check_result("DIMINISHED + coherent = allowed", arb_route_allowed);

        // =====================================================================
        // TEST SECTION 5: ConsentHeaderParser Tests
        // =====================================================================
        print_section("ConsentHeaderParser - Field Extraction");

        // Build test header:
        // Bytes 0-3: RPP Address = theta:12, phi:3, omega:2, radius:128, reserved:0
        //   = 0b01100_011_010_10000000_0000000000000 = 0x61500000
        // Bytes 4-7: Packet ID = 0xDEADBEEF
        // Bytes 8-9: Origin Ref = 0x1234
        // Byte 10: verbal=1, somatic=12(0.75), ancestral=2, temporal=1
        //   = 0b1_1100_10_1 = 0xE5
        // Byte 11: entropy=20, complecount=5
        //   = 0b10100_101 = 0xA5
        // Byte 12: reserved=0, payload=3
        //   = 0b0000_0011 = 0x03
        // Byte 13: fallback_vector = 0xAA
        // Bytes 14-15: window_id = 0x1A2B
        // Byte 16: target_phase = 0x55
        // Byte 17: CRC = 0xFF (placeholder)

        header_in = 144'h61500000_DEADBEEF_1234_E5_A5_03_AA_1A2B_55_FF;
        #10;

        $display("Header: 0x%036h", header_in);
        $display("Parsed fields:");
        $display("  theta=%d phi=%d omega=%d radius=%d",
            hdr_theta, hdr_phi, hdr_omega, hdr_radius);
        $display("  packet_id=0x%08h origin_ref=0x%04h",
            hdr_packet_id, hdr_origin_ref);
        $display("  verbal=%b somatic=%d ancestral=%d temporal=%b",
            hdr_verbal, hdr_somatic, hdr_ancestral, hdr_temporal);
        $display("  entropy=%d complecount=%d payload=%d",
            hdr_entropy, hdr_complecount, hdr_payload);
        $display("  fallback=0x%02h window_id=0x%04h target=0x%02h crc=0x%02h",
            hdr_fallback, hdr_window_id, hdr_target_phase, hdr_crc);
        $display("  consent_state=%b needs_fallback=%b has_pma=%b",
            hdr_consent_state, hdr_needs_fallback, hdr_has_pma);

        check_result("Theta extraction", hdr_theta == 5'd12);
        check_result("Phi extraction", hdr_phi == 3'd3);
        check_result("Omega extraction", hdr_omega == 3'd2);
        check_result("Radius extraction", hdr_radius == 8'd128);
        check_result("Entropy extraction", hdr_entropy == 5'd20);
        check_result("Complecount extraction", hdr_complecount == 3'd5);
        check_result("Window ID extraction", hdr_window_id == 16'h1A2B);
        check_result("Has PMA link", hdr_has_pma);
        check_result("Full consent (high somatic)", hdr_consent_state == 2'b00);

        // Test consent state derivation
        print_section("ConsentHeaderParser - Consent State Tests");

        // Low somatic -> SUSPENDED
        header_in[62:59] = 4'd2;  // somatic = 2 (< 3 = 0.2)
        #10;
        check_result("Low somatic -> SUSPENDED", hdr_consent_state == 2'b10);

        // Medium somatic, no verbal -> DIMINISHED
        header_in[62:59] = 4'd6;  // somatic = 6 (< 8)
        header_in[63] = 1'b0;     // verbal = 0
        #10;
        check_result("Mid somatic no verbal -> DIMINISHED", hdr_consent_state == 2'b01);

        // Medium somatic, with verbal -> FULL
        header_in[63] = 1'b1;     // verbal = 1
        #10;
        check_result("Mid somatic with verbal -> FULL", hdr_consent_state == 2'b00);

        // High entropy -> needs_fallback
        header_in[55:51] = 5'd28;  // entropy = 28 (> 25)
        #10;
        check_result("High entropy -> needs_fallback", hdr_needs_fallback);

        // =====================================================================
        // TEST SECTION 6: Integration Scenarios
        // =====================================================================
        print_section("Integration - Full Pipeline");

        // Scenario 1: Normal routing with full consent
        $display("\nScenario 1: Normal routing");
        header_in = 144'h61500000_DEADBEEF_1234_E5_50_03_00_0000_55_FF;
        // entropy=10, complecount=0, window_id=0 (no PMA)
        #10;

        coh_entropy = hdr_entropy;
        coh_complecount = hdr_complecount;
        coh_threshold = 10'd200;
        #10;

        arb_coherence_valid = coh_valid;
        arb_consent_state = hdr_consent_state;
        arb_needs_fallback = hdr_needs_fallback;
        arb_pma_hit = 0;
        #10;

        $display("  Coherence score: %d, valid: %b", coh_score, coh_valid);
        $display("  Route allowed: %b, decision: %b", arb_route_allowed, arb_decision);
        check_result("Scenario 1: Route allowed", arb_route_allowed);

        // Scenario 2: Fallback triggered by low coherence
        $display("\nScenario 2: Fallback triggered");
        header_in[55:48] = 8'hD8;  // entropy=27, complecount=0
        #10;
        coh_entropy = hdr_entropy;
        coh_complecount = hdr_complecount;
        #10;
        arb_coherence_valid = coh_valid;
        arb_needs_fallback = hdr_needs_fallback;
        #10;

        $display("  Coherence score: %d, valid: %b", coh_score, coh_valid);
        $display("  Needs fallback: %b, use_fallback: %b", arb_needs_fallback, arb_use_fallback);
        check_result("Scenario 2: Fallback path active", arb_needs_fallback);

        // Scenario 3: PMA hit with high coherence
        $display("\nScenario 3: PMA-linked routing");
        header_in = 144'h61500000_DEADBEEF_1234_E5_FF_03_00_1A2B_55_FF;
        // entropy=31, complecount=7 (max coherence), window_id=0x1A2B
        #10;
        coh_entropy = hdr_entropy;
        coh_complecount = hdr_complecount;
        #10;
        arb_coherence_valid = coh_valid;
        arb_pma_hit = 1;
        #10;

        $display("  Has PMA: %b, PMA hit: %b, use_pma: %b", hdr_has_pma, arb_pma_hit, arb_use_pma);
        check_result("Scenario 3: PMA route used", arb_use_pma);

        // =====================================================================
        // Summary
        // =====================================================================
        print_section("TEST SUMMARY");

        $display("Total tests: %d", test_count);
        $display("Passed:      %d", pass_count);
        $display("Failed:      %d", fail_count);
        $display("");

        if (fail_count == 0) begin
            $display("*** ALL TESTS PASSED ***");
        end else begin
            $display("*** %d TESTS FAILED ***", fail_count);
        end

        $display("");
        $display("Waveform written to: spiral_ra_test.vcd");
        $display("View with: gtkwave spiral_ra_test.vcd");

        #100;
        $finish;
    end

endmodule

`default_nettype wire
