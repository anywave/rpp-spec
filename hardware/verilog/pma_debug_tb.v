`timescale 1ns/1ps
module pma_debug_tb;
    reg clk = 0;
    always #5 clk = ~clk;
    
    // PMA test
    reg write_en = 0;
    reg [5:0] write_addr = 0;
    reg [143:0] write_data = 0;
    wire [143:0] read_data;
    
    // Use address 2 to read
    wire [5:0] read_addr = 6'd2;
    
    PhaseMemoryAnchorRAM #(.DEPTH(64)) pma (
        .clk(clk),
        .write_en(write_en),
        .write_addr(write_addr),
        .write_data(write_data),
        .read_addr(read_addr),
        .read_data(read_data)
    );
    
    initial begin
        $dumpfile("pma_debug.vcd");
        $dumpvars(0, pma_debug_tb);
        
        $display("PMA Debug Test");
        $display("Read addr fixed at: %d", read_addr);
        
        // Initially read should be X
        #10;
        $display("Before write - read_data[143:132] = %h", read_data[143:132]);
        
        // Write to slot 2 with window_id = 0x042
        write_en = 1;
        write_addr = 6'd2;
        write_data = {12'h042, 132'h0};  // Simple: just window_id in upper bits
        $display("Writing window_id=0x042 to slot 2");
        @(posedge clk);
        
        write_en = 0;
        @(posedge clk);
        
        #10;
        $display("After write - read_data[143:132] = %h", read_data[143:132]);
        
        // Check match
        if (read_data[143:132] == 12'h042)
            $display("PASS: window_id matches!");
        else
            $display("FAIL: got %h, expected 042", read_data[143:132]);
        
        $finish;
    end
endmodule
