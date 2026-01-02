// SPDX-License-Identifier: MIT
// SPIRAL Protocol - Canonical Testbench
// Production Layout + Ra-Derived Coherence

`timescale 1ns / 1ps
`default_nettype none

module spiral_testbench_canonical;

    // =========================================================================
    // Clock and Reset
    // =========================================================================
    reg clk = 0;
    reg reset = 1;
    reg enable = 0;
    
    always #5 clk = ~clk;  // 100MHz clock
    
    // =========================================================================
    // Consent Header Parser Signals
    // =========================================================================
    reg  [143:0] consent_header;
    
    wire [4:0]   rpp_theta;
    wire [2:0]   rpp_phi;
    wire [2:0]   rpp_omega;
    wire [7:0]   rpp_radius;
    wire [12:0]  rpp_reserved;
    wire [31:0]  packet_id;
    wire [15:0]  origin_ref;
    wire         consent_verbal;
    wire [3:0]   consent_somatic;
    wire [1:0]   consent_ancestral;
    wire         temporal_lock;
    wire [4:0]   phase_entropy_index;
    wire [2:0]   complecount_trace;
    wire [3:0]   payload_type;
    wire [7:0]   fallback_vector;
    wire [15:0]  coherence_window_id;
    wire [7:0]   target_phase_ref;
    wire [7:0]   header_crc;
    wire [1:0]   consent_state;
    wire         needs_fallback;
    wire         has_pma_link;
    
    // =========================================================================
    // Ra Coherence Evaluator Signals
    // =========================================================================
    reg  [9:0]   coherence_threshold;
    wire [9:0]   coherence_score;
    wire [7:0]   coherence_normalized;
    wire         coherence_valid;
    wire         high_coherence;
    wire         medium_coherence;
    wire         low_coherence;
    
    // =========================================================================
    // Scalar Trigger Signals
    // =========================================================================
    reg  [7:0]   activation_threshold;
    reg  [3:0]   coherence_duration;
    wire         scalar_triggered;
    wire [3:0]   cycle_counter;
    
    // =========================================================================
    // Fallback Resolver Signals
    // =========================================================================
    reg  [31:0]  base_address;
    wire [31:0]  rpp_fallback_address;
    
    // =========================================================================
    // PMA RAM Signals
    // =========================================================================
    reg  [5:0]   pma_write_addr;
    reg  [5:0]   pma_read_addr;
    reg          pma_write_enable;
    reg  [143:0] pma_write_data;
    wire [143:0] pma_read_data;
    
    // =========================================================================
    // Module Instantiations
    // =========================================================================
    
    ConsentHeaderParser parser (
        .consent_header(consent_header),
        .rpp_theta(rpp_theta),
        .rpp_phi(rpp_phi),
        .rpp_omega(rpp_omega),
        .rpp_radius(rpp_radius),
        .rpp_reserved(rpp_reserved),
        .packet_id(packet_id),
        .origin_ref(origin_ref),
        .consent_verbal(consent_verbal),
        .consent_somatic(consent_somatic),
        .consent_ancestral(consent_ancestral),
        .temporal_lock(temporal_lock),
        .phase_entropy_index(phase_entropy_index),
        .complecount_trace(complecount_trace),
        .payload_type(payload_type),
        .fallback_vector(fallback_vector),
        .coherence_window_id(coherence_window_id),
        .target_phase_ref(target_phase_ref),
        .header_crc(header_crc),
        .consent_state(consent_state),
        .needs_fallback(needs_fallback),
        .has_pma_link(has_pma_link)
    );
    
    CoherenceEvaluator_Ra coherence_eval (
        .phase_entropy_index(phase_entropy_index),
        .complecount_trace(complecount_trace),
        .coherence_threshold(coherence_threshold),
        .coherence_score(coherence_score),
        .coherence_normalized(coherence_normalized),
        .coherence_valid(coherence_valid),
        .high_coherence(high_coherence),
        .medium_coherence(medium_coherence),
        .low_coherence(low_coherence)
    );
    
    ScalarTrigger scalar_trig (
        .clk(clk),
        .reset(reset),
        .enable(enable),
        .coherence_valid(coherence_valid),
        .rpp_radius(rpp_radius),
        .activation_threshold(activation_threshold),
        .coherence_duration(coherence_duration),
        .scalar_triggered(scalar_triggered),
        .cycle_counter(cycle_counter)
    );
    
    FallbackResolver fallback (
        .trigger_fallback(~coherence_valid),
        .base_address(base_address),
        .fallback_vector(fallback_vector),
        .rpp_fallback_address(rpp_fallback_address)
    );
    
    PhaseMemoryAnchorRAM pma_ram (
        .clk(clk),
        .write_enable(pma_write_enable),
        .write_addr(pma_write_addr),
        .write_data(pma_write_data),
        .read_addr(pma_read_addr),
        .read_data(pma_read_data)
    );
    
    // =========================================================================
    // Test Counters
    // =========================================================================
    integer tests_passed = 0;
    integer tests_failed = 0;
    integer test_num = 0;
    
    // =========================================================================
    // VCD Dump
    // =========================================================================
    initial begin
        $dumpfile("spiral_canonical.vcd");
        $dumpvars(0, spiral_testbench_canonical);
    end
    
    // =========================================================================
    // Helper Tasks
    // =========================================================================
    
    task check_signal;
        input [255:0] name;
        input [31:0] actual;
        input [31:0] expected;
        begin
            test_num = test_num + 1;
            if (actual === expected) begin
                tests_passed = tests_passed + 1;
                $display("[%0t] PASS #%0d: %s = %0d", $time, test_num, name, actual);
            end else begin
                tests_failed = tests_failed + 1;
                $display("[%0t] FAIL #%0d: %s = %0d (expected %0d)", 
                         $time, test_num, name, actual, expected);
            end
        end
    endtask
    
    task build_header;
        input [4:0]  t_theta;
        input [2:0]  t_phi;
        input [2:0]  t_omega;
        input [7:0]  t_radius;
        input [12:0] t_reserved;
        input [31:0] t_packet_id;
        input [15:0] t_origin_ref;
        input        t_verbal;
        input [3:0]  t_somatic;
        input [1:0]  t_ancestral;
        input        t_temporal;
        input [4:0]  t_entropy;
        input [2:0]  t_comple;
        input [3:0]  t_payload;
        input [7:0]  t_fallback;
        input [15:0] t_window_id;
        input [7:0]  t_phase_ref;
        input [7:0]  t_crc;
        begin
            consent_header = {
                t_theta, t_phi, t_omega, t_radius, t_reserved,  // bytes 0-3 (32 bits)
                t_packet_id,                                     // bytes 4-7 (32 bits)
                t_origin_ref,                                    // bytes 8-9 (16 bits)
                t_verbal, t_somatic, t_ancestral, t_temporal,   // byte 10 (8 bits)
                t_entropy, t_comple,                             // byte 11 (8 bits)
                4'b0000, t_payload,                              // byte 12 (8 bits)
                t_fallback,                                      // byte 13 (8 bits)
                t_window_id,                                     // bytes 14-15 (16 bits)
                t_phase_ref,                                     // byte 16 (8 bits)
                t_crc                                            // byte 17 (8 bits)
            };
        end
    endtask
    
    // =========================================================================
    // Main Test Sequence
    // =========================================================================
    initial begin
        $display("======================================================================");
        $display("SPIRAL Protocol HDL Testbench (Production Canonical + Ra Coherence)");
        $display("======================================================================");
        $display("Ra Constants: GREEN_PHI=1.65, ANKH=5.09");
        $display("Max coherence score: 674 (scaled x100)");
        $display("");
        
        // Initialize
        consent_header = 144'h0;
        coherence_threshold = 10'd420;  // 4.2
        activation_threshold = 8'd128;
        coherence_duration = 4'd3;
        base_address = 32'h12345678;
        pma_write_addr = 6'd0;
        pma_read_addr = 6'd0;
        pma_write_enable = 0;
        pma_write_data = 144'h0;
        
        // Reset sequence
        reset = 1;
        #20;
        reset = 0;
        enable = 1;
        #10;
        
        // =====================================================================
        // TEST 1: Consent Header Parser (Production Layout)
        // =====================================================================
        $display("\n[%0t] TEST 1: ConsentHeaderParser", $time);
        $display("----------------------------------------------------------------------");
        
        // Test case 1a: Full consent, moderate values
        build_header(
            5'd9,      // theta
            3'd3,      // phi  
            3'd2,      // omega
            8'd128,    // radius
            13'd0,     // reserved
            32'h12345678,  // packet_id
            16'hABCD,  // origin_ref
            1'b1,      // consent_verbal
            4'd15,     // consent_somatic (full)
            2'd0,      // consent_ancestral
            1'b0,      // temporal_lock
            5'd15,     // phase_entropy_index
            3'd4,      // complecount_trace
            4'd1,      // payload_type
            8'hAA,     // fallback_vector
            16'h1234,  // coherence_window_id
            8'h55,     // target_phase_ref
            8'hFF      // crc
        );
        #10;
        
        check_signal("rpp_theta", rpp_theta, 5'd9);
        check_signal("rpp_phi", rpp_phi, 3'd3);
        check_signal("rpp_omega", rpp_omega, 3'd2);
        check_signal("rpp_radius", rpp_radius, 8'd128);
        check_signal("phase_entropy_index", phase_entropy_index, 5'd15);
        check_signal("complecount_trace", complecount_trace, 3'd4);
        check_signal("coherence_window_id", coherence_window_id, 16'h1234);
        check_signal("consent_state (FULL)", consent_state, 2'd0);
        
        // Test case 1b: Diminished consent
        build_header(
            5'd0, 3'd0, 3'd0, 8'd0, 13'd0,
            32'd0, 16'd0,
            1'b0,      // NO verbal consent
            4'd7,      // somatic < 8 (0.5)
            2'd0, 1'b0,
            5'd20, 3'd5,
            4'd0, 8'd0, 16'd0, 8'd0, 8'd0
        );
        #10;
        check_signal("consent_state (DIMINISHED)", consent_state, 2'd1);
        
        // Test case 1c: Suspended consent
        build_header(
            5'd0, 3'd0, 3'd0, 8'd0, 13'd0,
            32'd0, 16'd0,
            1'b1,      // verbal yes
            4'd2,      // somatic < 3 (0.2)
            2'd0, 1'b0,
            5'd25, 3'd6,
            4'd0, 8'd0, 16'd0, 8'd0, 8'd0
        );
        #10;
        check_signal("consent_state (SUSPENDED)", consent_state, 2'd2);
        
        // Test case 1d: Max theta (27 Repitans)
        build_header(
            5'd27, 3'd6, 3'd4, 8'd200, 13'd0,
            32'd0, 16'd0,
            1'b1, 4'd15, 2'd0, 1'b0,
            5'd10, 3'd3,
            4'd0, 8'd0, 16'hFFFF, 8'd0, 8'd0
        );
        #10;
        check_signal("rpp_theta (max Ra)", rpp_theta, 5'd27);
        check_signal("coherence_window_id (max)", coherence_window_id, 16'hFFFF);
        
        // =====================================================================
        // TEST 2: Ra-Derived Coherence Evaluator
        // =====================================================================
        $display("\n[%0t] TEST 2: CoherenceEvaluator_Ra", $time);
        $display("----------------------------------------------------------------------");
        $display("Formula: score = (165 * E/31) + (509 * C/7)");
        
        // Test 2a: E=0, C=0 -> score=0
        build_header(
            5'd0, 3'd0, 3'd0, 8'd0, 13'd0,
            32'd0, 16'd0,
            1'b1, 4'd15, 2'd0, 1'b0,
            5'd0,   // entropy = 0
            3'd0,   // complecount = 0
            4'd0, 8'd0, 16'd0, 8'd0, 8'd0
        );
        coherence_threshold = 10'd420;  // 4.2
        #10;
        check_signal("coherence_score (E=0,C=0)", coherence_score, 10'd0);
        check_signal("coherence_valid (below 4.2)", coherence_valid, 1'b0);
        check_signal("low_coherence", low_coherence, 1'b1);
        
        // Test 2b: E=31, C=7 -> score=674 (max)
        build_header(
            5'd0, 3'd0, 3'd0, 8'd0, 13'd0,
            32'd0, 16'd0,
            1'b1, 4'd15, 2'd0, 1'b0,
            5'd31,  // entropy = max
            3'd7,   // complecount = max
            4'd0, 8'd0, 16'd0, 8'd0, 8'd0
        );
        #10;
        // Expected: 165 + 509 = 674
        $display("  coherence_score = %0d (expected ~674)", coherence_score);
        check_signal("coherence_valid (above 4.2)", coherence_valid, 1'b1);
        check_signal("high_coherence (>=5.0)", high_coherence, 1'b1);
        
        // Test 2c: Threshold sweep at E=20, C=5
        // Expected: (165*20/31) + (509*5/7) = 106 + 363 = 469
        build_header(
            5'd0, 3'd0, 3'd0, 8'd0, 13'd0,
            32'd0, 16'd0,
            1'b1, 4'd15, 2'd0, 1'b0,
            5'd20,  // entropy = 20
            3'd5,   // complecount = 5
            4'd0, 8'd0, 16'd0, 8'd0, 8'd0
        );
        #10;
        $display("  E=20, C=5 -> coherence_score = %0d (expected ~469)", coherence_score);
        
        coherence_threshold = 10'd420;  // 4.2
        #10;
        check_signal("valid@T=4.2", coherence_valid, 1'b1);
        
        coherence_threshold = 10'd510;  // 5.1
        #10;
        check_signal("valid@T=5.1", coherence_valid, 1'b0);
        
        // =====================================================================
        // TEST 3: Fallback Resolver
        // =====================================================================
        $display("\n[%0t] TEST 3: FallbackResolver", $time);
        $display("----------------------------------------------------------------------");
        
        // Set low coherence to trigger fallback
        build_header(
            5'd0, 3'd0, 3'd0, 8'd0, 13'd0,
            32'd0, 16'd0,
            1'b1, 4'd15, 2'd0, 1'b0,
            5'd0, 3'd0,  // Low coherence
            4'd0, 8'hAB, 16'd0, 8'd0, 8'd0
        );
        coherence_threshold = 10'd420;
        base_address = 32'h12345678;
        #10;
        
        // XOR: 0x12345678 ^ 0xAB = 0x123456D3
        check_signal("fallback_address", rpp_fallback_address, 32'h123456D3);
        
        // =====================================================================
        // TEST 4: PMA RAM
        // =====================================================================
        $display("\n[%0t] TEST 4: PhaseMemoryAnchorRAM", $time);
        $display("----------------------------------------------------------------------");
        
        // Write test pattern
        pma_write_addr = 6'd5;
        pma_write_data = 144'hCAFEBABE_DEADBEEF_12345678_AABBCCDD_5566;
        pma_write_enable = 1;
        @(posedge clk);
        pma_write_enable = 0;
        
        // Read back
        pma_read_addr = 6'd5;
        @(posedge clk);
        #1;
        
        check_signal("pma_read[143:112]", pma_read_data[143:112], 32'hCAFEBABE);
        check_signal("pma_read[111:80]", pma_read_data[111:80], 32'hDEADBEEF);
        
        // =====================================================================
        // TEST 5: Integration Scenarios
        // =====================================================================
        $display("\n[%0t] TEST 5: Integration Scenarios", $time);
        $display("----------------------------------------------------------------------");
        
        // Scenario 5a: Full consent + high coherence -> route OK
        build_header(
            5'd9, 3'd3, 3'd2, 8'd150, 13'd0,
            32'hAABBCCDD, 16'h1234,
            1'b1, 4'd15, 2'd0, 1'b0,  // Full consent
            5'd25, 3'd6,               // High coherence (133+436=569)
            4'd1, 8'h55, 16'h2345, 8'hAA, 8'd0
        );
        coherence_threshold = 10'd420;
        #10;
        
        $display("  Scenario: Full consent, high coherence");
        $display("    consent_state=%0d, coherence_valid=%0d, score=%0d",
                 consent_state, coherence_valid, coherence_score);
        check_signal("can_route (full+valid)", 
                     (consent_state == 2'd0) && coherence_valid, 1'b1);
        
        // Scenario 5b: Suspended consent blocks even with high coherence
        build_header(
            5'd9, 3'd3, 3'd2, 8'd150, 13'd0,
            32'hAABBCCDD, 16'h1234,
            1'b1, 4'd2, 2'd0, 1'b0,  // Suspended (somatic < 3)
            5'd31, 3'd7,             // Max coherence
            4'd1, 8'h55, 16'h2345, 8'hAA, 8'd0
        );
        #10;
        
        $display("  Scenario: Suspended consent, max coherence");
        $display("    consent_state=%0d, coherence_valid=%0d", 
                 consent_state, coherence_valid);
        check_signal("blocked_by_consent", consent_state, 2'd2);
        
        // =====================================================================
        // Summary
        // =====================================================================
        #100;
        $display("\n======================================================================");
        $display("TEST SUMMARY");
        $display("======================================================================");
        $display("Total tests:  %0d", tests_passed + tests_failed);
        $display("Passed:       %0d", tests_passed);
        $display("Failed:       %0d", tests_failed);
        if (tests_failed == 0)
            $display("Result:       ALL TESTS PASSED");
        else
            $display("Result:       SOME TESTS FAILED");
        $display("======================================================================");
        
        $finish;
    end

endmodule

`default_nettype wire
