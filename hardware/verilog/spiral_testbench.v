// =============================================================================
// SPIRAL Protocol - Comprehensive HDL Testbench
// =============================================================================
// Tests all modules with Ra-derived coherence formula
//
// Modules tested:
//   1. ConsentHeaderParser
//   2. CoherenceEvaluatorRa
//   3. ScalarTriggerRa
//   4. FallbackResolverRa
//   5. SpiralCoherenceIntegration
//
// =============================================================================

`default_nettype none
`timescale 1ns / 1ps

module spiral_testbench;

    // Clock and reset
    reg clk;
    reg rst_n;
    reg enable;
    
    // Test control
    integer test_count;
    integer pass_count;
    integer fail_count;
    
    // Clock generation (100 MHz)
    initial clk = 0;
    always #5 clk = ~clk;
    
    // DUT signals - CoherenceEvaluatorRa
    reg  [4:0]  eval_phase_entropy;
    reg  [2:0]  eval_complecount;
    reg  [9:0]  eval_threshold;
    wire [9:0]  eval_score;
    wire        eval_valid;
    wire        eval_completion_flag;
    wire [7:0]  eval_entropy_contrib;
    wire [8:0]  eval_comple_contrib;
    
    // DUT signals - ScalarTriggerRa
    reg  [9:0]  scalar_score;
    reg  [9:0]  scalar_threshold;
    reg  [3:0]  scalar_duration;
    wire        scalar_triggered;
    wire [3:0]  scalar_counter;
    
    // DUT signals - FallbackResolverRa
    reg         fallback_trigger;
    reg  [31:0] fallback_base_addr;
    reg  [7:0]  fallback_vector;
    wire [31:0] fallback_addr_out;
    
    // DUT signals - Integration
    reg  [4:0]  integ_entropy;
    reg  [2:0]  integ_complecount;
    reg  [7:0]  integ_fallback_vec;
    reg  [1:0]  integ_consent_state;
    reg  [31:0] integ_base_addr;
    reg  [9:0]  integ_coh_threshold;
    reg  [9:0]  integ_scalar_threshold;
    reg  [3:0]  integ_scalar_duration;
    reg         integ_etf_trigger;
    wire [9:0]  integ_coh_score;
    wire        integ_coh_valid;
    wire        integ_completion_flag;
    wire        integ_etf_active;
    wire        integ_scalar_trig;
    wire [31:0] integ_fallback_addr;
    wire        integ_routing_allowed;
    wire [1:0]  integ_routing_decision;

    // DUT signals - ConsentStateDeriver
    reg  [3:0]  csd_somatic;
    reg         csd_verbal_override;
    wire [1:0]  csd_consent_state;

    // DUT signals - ScalarTriggerRa_Khat
    reg  [9:0]  khat_score;
    reg  [9:0]  khat_threshold;
    wire        khat_triggered;
    wire [3:0]  khat_counter;

    // DUT signals - ETFController
    reg         etf_trigger;
    reg  [9:0]  etf_coh_score;
    wire        etf_active;
    wire [3:0]  etf_counter;
    
    // Instantiate DUTs
    CoherenceEvaluatorRa uut_coherence (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .phase_entropy_index(eval_phase_entropy),
        .complecount_trace(eval_complecount),
        .threshold(eval_threshold),
        .coherence_score(eval_score),
        .coherence_valid(eval_valid),
        .completion_flag(eval_completion_flag),
        .entropy_contribution(eval_entropy_contrib),
        .complecount_contribution(eval_comple_contrib)
    );
    
    ScalarTriggerRa uut_scalar (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .coherence_score(scalar_score),
        .activation_threshold(scalar_threshold),
        .coherence_duration(scalar_duration),
        .scalar_triggered(scalar_triggered),
        .cycle_counter(scalar_counter)
    );
    
    FallbackResolverRa uut_fallback (
        .trigger_fallback(fallback_trigger),
        .base_address(fallback_base_addr),
        .fallback_vector(fallback_vector),
        .rpp_fallback_address(fallback_addr_out)
    );
    
    SpiralCoherenceIntegration uut_integration (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .phase_entropy_index(integ_entropy),
        .complecount_trace(integ_complecount),
        .fallback_vector(integ_fallback_vec),
        .consent_state(integ_consent_state),
        .base_address(integ_base_addr),
        .coherence_threshold(integ_coh_threshold),
        .scalar_threshold(integ_scalar_threshold),
        .scalar_duration(integ_scalar_duration),
        .etf_trigger(integ_etf_trigger),
        .etf_active(integ_etf_active),
        .coherence_score(integ_coh_score),
        .coherence_valid(integ_coh_valid),
        .completion_flag(integ_completion_flag),
        .scalar_triggered(integ_scalar_trig),
        .rpp_fallback_address(integ_fallback_addr),
        .routing_allowed(integ_routing_allowed),
        .routing_decision(integ_routing_decision)
    );

    // ConsentStateDeriver (Golden Ratio Thresholds)
    ConsentStateDeriver uut_consent_deriver (
        .somatic_coherence(csd_somatic),
        .verbal_override(csd_verbal_override),
        .consent_state(csd_consent_state)
    );

    // ScalarTriggerRa_Khat (KHAT fixed 12 cycles)
    ScalarTriggerRa_Khat uut_khat (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .coherence_score(khat_score),
        .activation_threshold(khat_threshold),
        .scalar_triggered(khat_triggered),
        .cycle_counter(khat_counter)
    );

    // ETFController (Emergency Token Freeze)
    ETFController uut_etf (
        .clk(clk),
        .rst_n(rst_n),
        .etf_trigger(etf_trigger),
        .coherence_score(etf_coh_score),
        .etf_active(etf_active),
        .etf_counter(etf_counter)
    );

    // Waveform dump
    initial begin
        $dumpfile("spiral_testbench.vcd");
        $dumpvars(0, spiral_testbench);
    end
    
    // Test helpers
    task check;
        input [255:0] name;
        input [31:0] actual;
        input [31:0] expected;
        begin
            test_count = test_count + 1;
            if (actual === expected) begin
                pass_count = pass_count + 1;
                $display("[%0t] PASS: %s = %0d (expected %0d)", $time, name, actual, expected);
            end else begin
                fail_count = fail_count + 1;
                $display("[%0t] FAIL: %s = %0d (expected %0d)", $time, name, actual, expected);
            end
        end
    endtask
    
    task reset_duts;
        begin
            rst_n = 0;
            enable = 0;
            @(posedge clk);
            @(posedge clk);
            rst_n = 1;
            @(posedge clk);
        end
    endtask
    
    // Main test
    initial begin
        test_count = 0;
        pass_count = 0;
        fail_count = 0;
        
        // Initialize
        eval_phase_entropy = 0;
        eval_complecount = 0;
        eval_threshold = 420;
        scalar_score = 0;
        scalar_threshold = 420;
        scalar_duration = 3;
        fallback_trigger = 0;
        fallback_base_addr = 32'h12345678;
        fallback_vector = 8'h00;
        integ_entropy = 0;
        integ_complecount = 0;
        integ_fallback_vec = 8'hAB;
        integ_consent_state = 2'b00;
        integ_base_addr = 32'h12345678;
        integ_coh_threshold = 420;
        integ_scalar_threshold = 420;
        integ_scalar_duration = 3;
        integ_etf_trigger = 0;

        // ConsentStateDeriver
        csd_somatic = 0;
        csd_verbal_override = 0;

        // ScalarTriggerRa_Khat
        khat_score = 0;
        khat_threshold = 420;

        // ETFController
        etf_trigger = 0;
        etf_coh_score = 0;

        reset_duts();
        
        $display("====================================================================");
        $display("SPIRAL HDL Testbench - Ra-Derived Coherence Formula");
        $display("====================================================================");
        $display("Ra Constants: GREEN_PHI=165 (1.65), ANKH=509 (5.09)");
        $display("Max Score: 165 + 509 = 674");
        $display("");
        
        // =====================================================================
        // TEST 1: CoherenceEvaluatorRa - Score Calculation
        // =====================================================================
        $display("--------------------------------------------------------------------");
        $display("TEST 1: CoherenceEvaluatorRa - Ra-Derived Score Calculation");
        $display("--------------------------------------------------------------------");
        
        enable = 1;
        
        // Test E=0, C=0 -> score = 0
        eval_phase_entropy = 0;
        eval_complecount = 0;
        eval_threshold = 420;
        @(posedge clk); @(posedge clk);
        check("score(E=0,C=0)", eval_score, 0);
        check("valid(E=0,C=0,T=420)", eval_valid, 0);
        
        // Test E=31, C=0 -> score = 165 (max entropy contrib)
        eval_phase_entropy = 31;
        eval_complecount = 0;
        @(posedge clk); @(posedge clk);
        check("score(E=31,C=0)", eval_score, 165);
        check("entropy_contrib(E=31)", eval_entropy_contrib, 165);
        
        // Test E=0, C=7 -> score = 509 (max complecount contrib)
        eval_phase_entropy = 0;
        eval_complecount = 7;
        @(posedge clk); @(posedge clk);
        check("score(E=0,C=7)", eval_score, 509);
        check("comple_contrib(C=7)", eval_comple_contrib, 509);
        check("valid(E=0,C=7,T=420)", eval_valid, 1);
        
        // Test E=31, C=7 -> score = 674 (maximum)
        eval_phase_entropy = 31;
        eval_complecount = 7;
        @(posedge clk); @(posedge clk);
        check("score(E=31,C=7)", eval_score, 674);
        check("valid(E=31,C=7,T=420)", eval_valid, 1);
        
        // Test intermediate values
        // E=15, C=3 -> (165*15/31) + (509*3/7) = 79 + 218 = 297
        eval_phase_entropy = 15;
        eval_complecount = 3;
        @(posedge clk); @(posedge clk);
        check("score(E=15,C=3)", eval_score, 297);
        check("valid(E=15,C=3,T=420)", eval_valid, 0);
        
        // E=20, C=5 -> (165*20/31) + (509*5/7) = 106 + 363 = 469
        eval_phase_entropy = 20;
        eval_complecount = 5;
        @(posedge clk); @(posedge clk);
        check("score(E=20,C=5)", eval_score, 469);
        check("valid(E=20,C=5,T=420)", eval_valid, 1);
        
        // Test threshold boundary
        // E=25, C=4 -> (165*25/31) + (509*4/7) = 133 + 290 = 423 (just above 420)
        eval_phase_entropy = 25;
        eval_complecount = 4;
        eval_threshold = 420;
        @(posedge clk); @(posedge clk);
        check("score(E=25,C=4)", eval_score, 423);
        check("valid(E=25,C=4,T=420)", eval_valid, 1);
        
        // Same with higher threshold
        eval_threshold = 510;
        @(posedge clk); @(posedge clk);
        check("valid(E=25,C=4,T=510)", eval_valid, 0);

        // Test completion_flag (complecount == 7)
        eval_complecount = 3'd6;
        @(posedge clk); @(posedge clk);
        check("completion_flag(C=6)", eval_completion_flag, 0);

        eval_complecount = 3'd7;
        @(posedge clk); @(posedge clk);
        check("completion_flag(C=7)", eval_completion_flag, 1);

        eval_complecount = 3'd5;
        @(posedge clk); @(posedge clk);
        check("completion_flag(C=5)", eval_completion_flag, 0);

        // =====================================================================
        // TEST 2: Full Coherence Sweep (key values)
        // =====================================================================
        $display("");
        $display("--------------------------------------------------------------------");
        $display("TEST 2: CoherenceEvaluator - Threshold Sweep");
        $display("--------------------------------------------------------------------");
        
        // Sweep across key entropy/complecount combinations with threshold 420
        eval_threshold = 420;
        
        begin : coherence_sweep
            integer e, c;
            reg [9:0] expected_score;
            
            for (e = 0; e <= 31; e = e + 8) begin
                for (c = 0; c <= 7; c = c + 1) begin
                    eval_phase_entropy = e[4:0];
                    eval_complecount = c[2:0];
                    @(posedge clk); @(posedge clk);
                    
                    // Calculate expected: (165*e/31) + (509*c/7)
                    expected_score = ((165 * e) / 31) + ((509 * c) / 7);
                    
                    // Direct check with display
                    test_count = test_count + 1;
                    if (eval_score === expected_score) begin
                        pass_count = pass_count + 1;
                        $display("[%0t] PASS: sweep_score(E=%0d,C=%0d) = %0d (expected %0d)", $time, e, c, eval_score, expected_score);
                    end else begin
                        fail_count = fail_count + 1;
                        $display("[%0t] FAIL: sweep_score(E=%0d,C=%0d) = %0d (expected %0d)", $time, e, c, eval_score, expected_score);
                    end
                end
            end
        end
        
        // =====================================================================
        // TEST 3: ScalarTriggerRa - Timing
        // =====================================================================
        $display("");
        $display("--------------------------------------------------------------------");
        $display("TEST 3: ScalarTriggerRa - Duration Timing");
        $display("--------------------------------------------------------------------");
        
        reset_duts();
        enable = 1;
        
        scalar_threshold = 400;
        scalar_duration = 4'd3;
        scalar_score = 500;  // Above threshold
        
        // Should not trigger immediately
        @(posedge clk);
        check("scalar_triggered@0", scalar_triggered, 0);
        check("scalar_counter@0", scalar_counter, 1);
        
        @(posedge clk);
        check("scalar_triggered@1", scalar_triggered, 0);
        check("scalar_counter@1", scalar_counter, 2);
        
        @(posedge clk);
        check("scalar_triggered@2", scalar_triggered, 0);
        check("scalar_counter@2", scalar_counter, 3);
        
        @(posedge clk);
        check("scalar_triggered@3", scalar_triggered, 1);
        check("scalar_counter@3", scalar_counter, 4);
        
        // Drop score - should reset
        scalar_score = 300;
        @(posedge clk);
        check("scalar_triggered_after_drop", scalar_triggered, 0);
        check("scalar_counter_after_drop", scalar_counter, 0);
        
        // =====================================================================
        // TEST 4: FallbackResolverRa - XOR Logic
        // =====================================================================
        $display("");
        $display("--------------------------------------------------------------------");
        $display("TEST 4: FallbackResolverRa - XOR Address Generation");
        $display("--------------------------------------------------------------------");
        
        fallback_base_addr = 32'h12345678;
        
        // No trigger - output should be 0
        fallback_trigger = 0;
        fallback_vector = 8'hFF;
        #1;
        check("fallback_no_trigger", fallback_addr_out, 0);
        
        // Trigger with zero vector
        fallback_trigger = 1;
        fallback_vector = 8'h00;
        #1;
        check("fallback_zero_vec", fallback_addr_out, 32'h12345678);
        
        // Trigger with 0xFF vector
        fallback_vector = 8'hFF;
        #1;
        check("fallback_ff_vec", fallback_addr_out, 32'h12345678 ^ 32'h000000FF);
        
        // Trigger with 0x55 vector
        fallback_vector = 8'h55;
        #1;
        check("fallback_55_vec", fallback_addr_out, 32'h12345678 ^ 32'h00000055);
        
        // Trigger with 0xAA vector
        fallback_vector = 8'hAA;
        #1;
        check("fallback_aa_vec", fallback_addr_out, 32'h12345678 ^ 32'h000000AA);
        
        // =====================================================================
        // TEST 5: SpiralCoherenceIntegration - Routing Decisions
        // =====================================================================
        $display("");
        $display("--------------------------------------------------------------------");
        $display("TEST 5: SpiralCoherenceIntegration - Routing Logic");
        $display("--------------------------------------------------------------------");
        
        reset_duts();
        enable = 1;
        
        integ_base_addr = 32'hDEADBEEF;
        integ_fallback_vec = 8'hAB;
        integ_coh_threshold = 420;
        integ_scalar_threshold = 420;
        integ_scalar_duration = 3;
        
        // Scenario 1: High coherence, full consent -> ROUTE
        integ_entropy = 20;
        integ_complecount = 5;
        integ_consent_state = 2'b00;  // FULL_CONSENT
        @(posedge clk); @(posedge clk);
        check("routing_decision_route", integ_routing_decision, 2'b00);
        check("routing_allowed_yes", integ_routing_allowed, 1);
        check("coherence_valid_high", integ_coh_valid, 1);
        
        // Scenario 2: Low coherence -> FALLBACK
        integ_entropy = 5;
        integ_complecount = 1;
        integ_consent_state = 2'b00;
        @(posedge clk); @(posedge clk);
        check("routing_decision_fallback", integ_routing_decision, 2'b10);
        check("routing_allowed_no", integ_routing_allowed, 0);
        check("fallback_addr_generated", integ_fallback_addr, 32'hDEADBEEF ^ 32'h000000AB);
        
        // Scenario 3: High coherence, diminished consent -> DELAY
        integ_entropy = 20;
        integ_complecount = 5;
        integ_consent_state = 2'b01;  // DIMINISHED_CONSENT
        @(posedge clk); @(posedge clk);
        check("routing_decision_delay", integ_routing_decision, 2'b01);
        check("routing_allowed_dim", integ_routing_allowed, 0);
        
        // Scenario 4: Any coherence, suspended consent -> BLOCK
        integ_entropy = 31;
        integ_complecount = 7;
        integ_consent_state = 2'b10;  // SUSPENDED_CONSENT
        @(posedge clk); @(posedge clk);
        check("routing_decision_block_susp", integ_routing_decision, 2'b11);
        
        // Scenario 5: Emergency override -> BLOCK
        integ_consent_state = 2'b11;  // EMERGENCY_OVERRIDE
        @(posedge clk); @(posedge clk);
        check("routing_decision_block_emer", integ_routing_decision, 2'b11);

        // =====================================================================
        // TEST 6: ConsentStateDeriver - Golden Ratio Thresholds
        // =====================================================================
        $display("");
        $display("--------------------------------------------------------------------");
        $display("TEST 6: ConsentStateDeriver - Golden Ratio Thresholds (10/6/5)");
        $display("--------------------------------------------------------------------");

        // somatic = 15 -> FULL_CONSENT (00)
        csd_somatic = 4'd15;
        csd_verbal_override = 0;
        #10;
        check("consent(somatic=15)", csd_consent_state, 2'b00);

        // somatic = 10 -> FULL_CONSENT (threshold)
        csd_somatic = 4'd10;
        #10;
        check("consent(somatic=10)", csd_consent_state, 2'b00);

        // somatic = 9 -> DIMINISHED_CONSENT (01)
        csd_somatic = 4'd9;
        #10;
        check("consent(somatic=9)", csd_consent_state, 2'b01);

        // somatic = 6 -> DIMINISHED_CONSENT (threshold)
        csd_somatic = 4'd6;
        #10;
        check("consent(somatic=6)", csd_consent_state, 2'b01);

        // somatic = 5 -> SUSPENDED_CONSENT (10)
        csd_somatic = 4'd5;
        #10;
        check("consent(somatic=5)", csd_consent_state, 2'b10);

        // somatic = 0 -> SUSPENDED_CONSENT
        csd_somatic = 4'd0;
        #10;
        check("consent(somatic=0)", csd_consent_state, 2'b10);

        // verbal_override promotes to FULL regardless of somatic
        csd_somatic = 4'd2;
        csd_verbal_override = 1;
        #10;
        check("consent(somatic=2,verbal)", csd_consent_state, 2'b00);

        // =====================================================================
        // TEST 7: ScalarTriggerRa_Khat - KHAT Fixed 12-Cycle Duration
        // =====================================================================
        $display("");
        $display("--------------------------------------------------------------------");
        $display("TEST 7: ScalarTriggerRa_Khat - KHAT Fixed 12-Cycle Duration");
        $display("--------------------------------------------------------------------");

        reset_duts();
        enable = 1;
        khat_threshold = 400;
        khat_score = 500;  // Above threshold

        // Run 12 cycles - counter reaches 12, but trigger fires on next cycle
        repeat(12) @(posedge clk);
        check("khat_counter@12", khat_counter, 12);
        check("khat_triggered@12", khat_triggered, 0);  // Not yet (condition checked before increment)

        // 13th cycle - trigger fires (counter >= KHAT_DURATION evaluated with counter=12)
        @(posedge clk);
        check("khat_triggered@13", khat_triggered, 1);
        check("khat_counter@13", khat_counter, 13);

        // Drop score - should reset
        khat_score = 300;
        @(posedge clk);
        check("khat_reset_triggered", khat_triggered, 0);
        check("khat_reset_counter", khat_counter, 0);

        // =====================================================================
        // TEST 8: ETFController - ALPHA_INVERSE 9-Cycle Duration
        // =====================================================================
        $display("");
        $display("--------------------------------------------------------------------");
        $display("TEST 8: ETFController - ALPHA_INVERSE 9-Cycle Duration, 559 Release");
        $display("--------------------------------------------------------------------");

        reset_duts();

        // Trigger ETF
        etf_trigger = 1;
        etf_coh_score = 400;  // Below release threshold (559)
        @(posedge clk);
        etf_trigger = 0;

        check("etf_active_initial", etf_active, 1);
        check("etf_counter_initial", etf_counter, 9);

        // Run 9 cycles - counter should reach 0
        repeat(9) @(posedge clk);
        check("etf_counter_after_9", etf_counter, 0);
        check("etf_active_low_coh", etf_active, 1);  // Still active (coherence < 559)

        // Raise coherence above release threshold (559)
        etf_coh_score = 600;
        @(posedge clk);
        check("etf_active_released", etf_active, 0);  // Should release

        // Test ETF blocks routing in integration
        reset_duts();
        enable = 1;
        integ_entropy = 31;
        integ_complecount = 7;
        integ_consent_state = 2'b00;  // FULL_CONSENT
        integ_coh_threshold = 400;
        @(posedge clk); @(posedge clk);
        check("routing_before_etf", integ_routing_decision, 2'b00);  // ROUTE

        integ_etf_trigger = 1;
        @(posedge clk);
        integ_etf_trigger = 0;
        @(posedge clk);
        check("routing_during_etf", integ_routing_decision, 2'b11);  // BLOCK (ETF active)
        check("etf_dominance", integ_etf_active, 1);

        // =====================================================================
        // Summary
        // =====================================================================
        $display("");
        $display("====================================================================");
        $display("TEST SUMMARY");
        $display("====================================================================");
        $display("Total tests:  %0d", test_count);
        $display("Passed:       %0d", pass_count);
        $display("Failed:       %0d", fail_count);
        $display("Pass rate:    %0.1f%%", (pass_count * 100.0) / test_count);
        $display("====================================================================");
        
        if (fail_count == 0) begin
            $display("ALL TESTS PASSED - Ready for synthesis");
        end else begin
            $display("FAILURES DETECTED - Review required");
        end
        
        $finish;
    end

endmodule

`default_nettype wire
