`timescale 1ns/1ps
module integration_pma_tb;
    reg clk = 0;
    reg rst_n = 0;
    always #5 clk = ~clk;
    
    // Header with window_id=0x0042 -> RAM addr = 2
    localparam [143:0] TV1_HEADER = 144'h42580000_00000001_0010_F0_2B_01_2A_0042_00_00;
    
    reg [143:0] header_in;
    reg header_valid = 0;
    reg [31:0] dest_address = 0;
    reg [7:0] coherence_threshold = 8'd128;
    reg [6:0] scalar_threshold = 7'd100;
    reg [7:0] scalar_duration = 8'd10;
    reg pma_write_en = 0;
    reg [5:0] pma_write_addr = 0;
    reg [143:0] pma_write_data = 0;
    
    wire [31:0] resolved_address;
    wire [1:0] consent_state_out;
    wire [7:0] coherence_score_out;
    wire route_valid;
    wire fallback_active;
    wire scalar_triggered_out;
    wire pma_hit;
    
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
    
    initial begin
        $dumpfile("integration_pma.vcd");
        $dumpvars(0, integration_pma_tb);
        
        $display("=== PMA Integration Test ===");
        
        // Reset
        header_in = 0;
        rst_n = 0;
        repeat(3) @(posedge clk);
        rst_n = 1;
        repeat(2) @(posedge clk);
        
        // Step 1: Write PMA record to slot 2 with window_id = 0x042
        $display("Step 1: Writing PMA record to slot 2");
        pma_write_en = 1;
        pma_write_addr = 6'd2;  // Slot 2 matches window_id[5:0] = 0x02
        pma_write_data = {12'h042, 132'hDEADBEEF};  // window_id=0x042 in upper 12 bits
        @(posedge clk);
        $display("  T=%0t: Write triggered", $time);
        
        pma_write_en = 0;
        repeat(3) @(posedge clk);
        $display("  T=%0t: Write complete, waiting", $time);
        
        // Step 2: Apply header that references window_id=0x0042
        $display("Step 2: Applying header with window_id=0x0042");
        header_in = TV1_HEADER;
        header_valid = 1;
        dest_address = 32'h52680000;  // Some destination
        repeat(2) @(posedge clk);
        #1;
        
        $display("  T=%0t: Checking pma_hit", $time);
        $display("  pma_hit: %b", pma_hit);
        
        // Debug internal signals
        $display("");
        $display("Debug:");
        $display("  header window_id (from parser): should be 0x0042");
        $display("  window_id[5:0] (RAM addr): should be 0x02");
        $display("  PMA record window_id: should be 0x042");
        
        if (pma_hit === 1'b1)
            $display("PASS: pma_hit is 1");
        else if (pma_hit === 1'bx)
            $display("FAIL: pma_hit is X (undefined)");
        else
            $display("FAIL: pma_hit is 0 (no match)");
        
        $finish;
    end
endmodule
