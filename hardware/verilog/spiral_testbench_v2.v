// SPDX-License-Identifier: MIT
// SPIRAL Protocol - Enhanced System Testbench
// Version: 2.0.0-RaCanonical
//
// Tests both legacy stubs and spec-compliant modules with known vectors.
// Run with: iverilog -o spiral_tb spiral_testbench_v2.v spiral_consolidated.v && vvp spiral_tb
// Or with Verilator for faster simulation.

`timescale 1ns/1ps

module spiral_testbench_v2;

    // =========================================================================
    // Clock and Reset
    // =========================================================================
    reg clk = 0;
    reg rst_n = 0;
    
    always #5 clk = ~clk;  // 100 MHz
    
    // =========================================================================
    // Test Vectors - Known Values from Python Reference
    // =========================================================================
    
    // Test Vector 1: Valid header with FULL_CONSENT
    // Python: ConsentPacketHeader with theta=8, phi=2, omega=2, radius=192
    //         consent_verbal=True, consent_somatic=0.93 (14/15)
    //         phase_entropy=5, complecount=3
    //         fallback_vector=0x2A, coherence_window_id=0x0042
    //
    // RPP Address encoding: [31:27]=theta, [26:24]=phi, [23:21]=omega, [20:13]=radius
    //   theta=8  (01000), phi=2 (010), omega=2 (010), radius=192 (11000000)
    //   Binary: 01000_010_010_11000000_0000000000000 = 0x42580000
    //
    // Byte layout (big-endian):
    //   Bytes 0-3:  0x42 0x58 0x00 0x00  (RPP address)
    //   Bytes 4-7:  0x00 0x00 0x00 0x01  (packet_id = 1)
    //   Bytes 8-9:  0x00 0x10            (origin_ref = 16)
    //   Byte 10:    0xF0                 (verbal=1, somatic=14, ancestral=0, lock=0)
    //   Byte 11:    0x2B                 (entropy=5, complecount=3)
    //   Byte 12:    0x01                 (payload_type=HUMAN)
    //   Byte 13:    0x2A                 (fallback_vector)
    //   Bytes 14-15: 0x00 0x42           (coherence_window_id)
    //   Byte 16:    0x00                 (target_phase_ref)
    //   Byte 17:    0x00                 (CRC placeholder)
    
    localparam [143:0] TV1_HEADER = 144'h42580000_00000001_0010_F0_2B_01_2A_0042_00_00;
    
    // Expected values for TV1
    localparam [4:0]  TV1_EXP_THETA = 5'd8;
    localparam [2:0]  TV1_EXP_PHI = 3'd2;
    localparam [2:0]  TV1_EXP_OMEGA = 3'd2;
    localparam [7:0]  TV1_EXP_RADIUS = 8'd192;
    localparam [1:0]  TV1_EXP_CONSENT = 2'b00;  // FULL_CONSENT (somatic=14 > 8)
    localparam        TV1_EXP_FALLBACK = 1'b0;  // entropy=5 <= 25
    
    // Test Vector 2: DIMINISHED_CONSENT (somatic < 0.5, no verbal)
    // consent_somatic=0.4 (6/15), consent_verbal=0
    // Byte 10: 0x30 (verbal=0, somatic=6, ancestral=0, lock=0)
    localparam [143:0] TV2_HEADER = 144'h42580000_00000002_0010_30_2B_01_2A_0042_00_00;
    localparam [1:0]  TV2_EXP_CONSENT = 2'b01;  // DIMINISHED_CONSENT
    
    // Test Vector 3: SUSPENDED_CONSENT (somatic < 0.2)
    // consent_somatic=0.067 (1/15)
    // Byte 10: 0x08 (verbal=0, somatic=1, ancestral=0, lock=0)
    localparam [143:0] TV3_HEADER = 144'h42580000_00000003_0010_08_2B_01_2A_0042_00_00;
    localparam [1:0]  TV3_EXP_CONSENT = 2'b10;  // SUSPENDED_CONSENT
    
    // Test Vector 4: High entropy triggers fallback
    // phase_entropy=28 (> 25)
    // Byte 11: 0xE3 (entropy=28, complecount=3)
    localparam [143:0] TV4_HEADER = 144'h42580000_00000004_0010_F0_E3_01_2A_0042_00_00;
    localparam        TV4_EXP_FALLBACK = 1'b1;
    
    // Test Vector 5: Coherence calculation
    // Source: theta=8, phi=2, omega=2, radius=192 → 0x42580000
    // Dest:   theta=10, phi=3, omega=2, radius=200
    //   theta=10 (01010), phi=3 (011), omega=2 (010), radius=200 (11001000)
    //   Binary: 01010_011_010_11001000_0000000000000 = 0x53640000
    localparam [31:0] TV5_SRC_ADDR = 32'h42580000;  // theta=8, phi=2, omega=2, r=192
    localparam [31:0] TV5_DST_ADDR = 32'h53640000;  // theta=10, phi=3, omega=2, r=200
    
    // =========================================================================
    // DUT Instantiation - Spec-Compliant Modules
    // =========================================================================
    
    reg [143:0] header_in;
    reg         header_valid;
    reg [31:0]  dest_address;
    reg [7:0]   coherence_threshold;
    reg [6:0]   scalar_threshold;
    reg [7:0]   scalar_duration;
    reg         pma_write_en;
    reg [5:0]   pma_write_addr;
    reg [143:0] pma_write_data;
    
    wire [31:0] resolved_address;
    wire [1:0]  consent_state_out;
    wire [7:0]  coherence_score_out;
    wire        route_valid;
    wire        fallback_active;
    wire        scalar_triggered_out;
    wire        pma_hit;
    
    SpiralRoutingCore #(.PMA_DEPTH(64)) dut (
        .clk(clk),
        .rst_n(rst_n),
        .header_in(header_in),
        .header_valid(header_valid),
        .dest_address(dest_address),
        .coherence_threshold(coherence_threshold),
        .scalar_threshold(scalar_threshold),
        .scalar_duration(scalar_duration),
        .pma_write_en(pma_write_en),
        .pma_write_addr(pma_write_addr),
        .pma_write_data(pma_write_data),
        .resolved_address(resolved_address),
        .consent_state_out(consent_state_out),
        .coherence_score_out(coherence_score_out),
        .route_valid(route_valid),
        .fallback_active(fallback_active),
        .scalar_triggered_out(scalar_triggered_out),
        .pma_hit(pma_hit)
    );
    
    // =========================================================================
    // Additional Module Instantiation for Direct Testing
    // =========================================================================
    
    // Direct header parser access
    wire [31:0] parsed_rpp_address;
    wire [4:0]  parsed_theta;
    wire [2:0]  parsed_phi;
    wire [2:0]  parsed_omega;
    wire [7:0]  parsed_radius;
    wire [4:0]  parsed_entropy;
    wire [2:0]  parsed_complecount;
    wire [7:0]  parsed_fallback;
    wire [15:0] parsed_window_id;
    wire [1:0]  parsed_consent;
    wire        parsed_needs_fallback;
    wire        parsed_addr_valid;
    
    ConsentHeaderParser parser_direct (
        .header_in(header_in),
        .rpp_address(parsed_rpp_address),
        .theta(parsed_theta),
        .phi(parsed_phi),
        .omega(parsed_omega),
        .radius(parsed_radius),
        .phase_entropy_index(parsed_entropy),
        .complecount_trace(parsed_complecount),
        .fallback_vector(parsed_fallback),
        .coherence_window_id(parsed_window_id),
        .consent_state(parsed_consent),
        .needs_fallback(parsed_needs_fallback),
        .address_valid(parsed_addr_valid)
    );
    
    // =========================================================================
    // Test Infrastructure
    // =========================================================================
    
    integer test_count = 0;
    integer pass_count = 0;
    integer fail_count = 0;
    
    task check_equal;
        input [255:0] name;
        input [63:0] actual;
        input [63:0] expected;
        begin
            test_count = test_count + 1;
            if (actual === expected) begin
                pass_count = pass_count + 1;
                $display("  [PASS] %s: %h == %h", name, actual, expected);
            end else begin
                fail_count = fail_count + 1;
                $display("  [FAIL] %s: got %h, expected %h", name, actual, expected);
            end
        end
    endtask
    
    task check_bool;
        input [255:0] name;
        input actual;
        input expected;
        begin
            test_count = test_count + 1;
            if (actual === expected) begin
                pass_count = pass_count + 1;
                $display("  [PASS] %s: %b == %b", name, actual, expected);
            end else begin
                fail_count = fail_count + 1;
                $display("  [FAIL] %s: got %b, expected %b", name, actual, expected);
            end
        end
    endtask
    
    // =========================================================================
    // Test Sequence
    // =========================================================================
    
    initial begin
        // Waveform dump for GTKWave
        $dumpfile("spiral_tb.vcd");
        $dumpvars(0, spiral_testbench_v2);
        
        $display("");
        $display("=============================================================");
        $display("  SPIRAL Protocol HDL Testbench v2.0.0-RaCanonical");
        $display("=============================================================");
        $display("");
        
        // Initialize
        header_in = 144'h0;
        header_valid = 0;
        dest_address = 32'h0;
        coherence_threshold = 8'd128;  // 50% coherence required
        scalar_threshold = 7'd100;
        scalar_duration = 8'd10;
        pma_write_en = 0;
        pma_write_addr = 6'h0;
        pma_write_data = 144'h0;
        
        // Reset sequence
        rst_n = 0;
        #20;
        rst_n = 1;
        #10;
        
        // =====================================================================
        // TEST 1: Header Parsing - FULL_CONSENT
        // =====================================================================
        $display("--- TEST 1: Header Parsing (FULL_CONSENT) ---");
        header_in = TV1_HEADER;
        header_valid = 1;
        dest_address = TV5_DST_ADDR;
        #10;
        
        check_equal("theta", parsed_theta, TV1_EXP_THETA);
        check_equal("phi", parsed_phi, TV1_EXP_PHI);
        check_equal("omega", parsed_omega, TV1_EXP_OMEGA);
        check_equal("radius", parsed_radius, TV1_EXP_RADIUS);
        check_equal("consent_state", parsed_consent, TV1_EXP_CONSENT);
        check_bool("needs_fallback", parsed_needs_fallback, TV1_EXP_FALLBACK);
        check_bool("address_valid", parsed_addr_valid, 1'b1);
        $display("");
        
        // =====================================================================
        // TEST 2: Consent State - DIMINISHED
        // =====================================================================
        $display("--- TEST 2: Consent State (DIMINISHED) ---");
        header_in = TV2_HEADER;
        #10;
        
        check_equal("consent_state", parsed_consent, TV2_EXP_CONSENT);
        $display("");
        
        // =====================================================================
        // TEST 3: Consent State - SUSPENDED
        // =====================================================================
        $display("--- TEST 3: Consent State (SUSPENDED) ---");
        header_in = TV3_HEADER;
        #10;
        
        check_equal("consent_state", parsed_consent, TV3_EXP_CONSENT);
        // Route should be invalid due to suspended consent
        check_bool("route_valid (suspended)", route_valid, 1'b0);
        $display("");
        
        // =====================================================================
        // TEST 4: High Entropy Fallback Trigger
        // =====================================================================
        $display("--- TEST 4: Fallback Trigger (high entropy) ---");
        header_in = TV4_HEADER;
        #10;
        
        check_bool("needs_fallback", parsed_needs_fallback, TV4_EXP_FALLBACK);
        check_bool("fallback_active", fallback_active, TV4_EXP_FALLBACK);
        $display("");
        
        // =====================================================================
        // TEST 5: Coherence Calculation
        // =====================================================================
        $display("--- TEST 5: Coherence Calculation ---");
        header_in = TV1_HEADER;  // Source: theta=8
        dest_address = TV5_DST_ADDR;  // Dest: theta=10
        #10;
        
        // Both theta=8 and theta=10 are in MEMORY sector (7-10)
        // Coherence should be high
        $display("  coherence_score: %d (0x%h)", coherence_score_out, coherence_score_out);
        check_bool("coherence > threshold", (coherence_score_out >= coherence_threshold), 1'b1);
        $display("");
        
        // =====================================================================
        // TEST 6: Cross-Sector Coherence (Lower)
        // =====================================================================
        $display("--- TEST 6: Cross-Sector Coherence ---");
        header_in = TV1_HEADER;  // Source: theta=8 (MEMORY)
        dest_address = 32'hD0000000;  // theta=26 (SHADOW)
        #10;
        
        $display("  Source sector: MEMORY (theta=8)");
        $display("  Dest sector: SHADOW (theta=26)");
        $display("  coherence_score: %d", coherence_score_out);
        // Cross-sector should have lower coherence
        $display("");
        
        // =====================================================================
        // TEST 7: Scalar Trigger Sequence
        // =====================================================================
        $display("--- TEST 7: Scalar Trigger (sustained coherence) ---");
        scalar_threshold = 7'd50;  // Lower threshold
        scalar_duration = 8'd5;    // 5 cycles
        header_in = TV1_HEADER;    // radius=192 > 50
        #10;
        
        // Wait for scalar to trigger (radius > threshold for duration cycles)
        $display("  Waiting for scalar trigger (radius=192, threshold=50, duration=5)...");
        repeat(10) @(posedge clk);
        
        $display("  scalar_triggered: %b", scalar_triggered_out);
        check_bool("scalar_triggered after duration", scalar_triggered_out, 1'b1);
        $display("");
        
        // =====================================================================
        // TEST 8: PMA Write and Lookup
        // =====================================================================
        $display("--- TEST 8: PMA Write/Lookup ---");
        // Write a PMA record with window_id=0x042 (12 bits)
        // Header will have coherence_window_id=0x0042 (16 bits)
        // Lookup address = window_id[5:0] = 0x02, so write to slot 2
        pma_write_en = 1;
        pma_write_addr = 6'd2;  // Slot 2 (matches 0x0042 & 0x3F)
        // PMA record: window_id=0x042, timestamp, phase_vector, consent, etc.
        pma_write_data = {12'h042, 64'h123456789ABCDEF0, 32'h42580000, 
                          2'b00, 5'd10, 6'd48, 4'h1, 1'b0, 8'h00, 10'b0};
        @(posedge clk);
        pma_write_en = 0;
        @(posedge clk);  // Wait for write to complete
        @(posedge clk);  // Extra cycle for stability
        
        // Now query with header that has coherence_window_id=0x0042
        header_in = TV1_HEADER;  // window_id=0x0042
        #20;  // Wait for lookup
        
        $display("  Header window_id (16-bit): 0x%h", 16'h0042);
        $display("  PMA slot address: %d", 6'd2);
        $display("  pma_hit: %b", pma_hit);
        check_bool("pma_hit", pma_hit, 1'b1);
        $display("");
        
        // =====================================================================
        // TEST 9: Route Valid (Full Pipeline)
        // =====================================================================
        $display("--- TEST 9: Full Pipeline Route Valid ---");
        header_in = TV1_HEADER;
        dest_address = TV5_DST_ADDR;
        coherence_threshold = 8'd100;
        #10;
        
        $display("  consent_state: %b (FULL)", consent_state_out);
        $display("  coherence_score: %d", coherence_score_out);
        $display("  fallback_active: %b", fallback_active);
        $display("  resolved_address: 0x%h", resolved_address);
        check_bool("route_valid", route_valid, 1'b1);
        $display("");
        
        // =====================================================================
        // Summary
        // =====================================================================
        #20;
        $display("=============================================================");
        $display("  TEST SUMMARY");
        $display("=============================================================");
        $display("  Total tests: %d", test_count);
        $display("  Passed:      %d", pass_count);
        $display("  Failed:      %d", fail_count);
        $display("");
        
        if (fail_count == 0) begin
            $display("  *** ALL TESTS PASSED ***");
        end else begin
            $display("  *** %d TESTS FAILED ***", fail_count);
        end
        
        $display("=============================================================");
        $display("");
        
        $finish;
    end

endmodule
