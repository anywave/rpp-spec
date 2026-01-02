`timescale 1ns/1ps
module pma_debug_tb2;
    reg clk = 0;
    always #5 clk = ~clk;
    
    // PMA test
    reg write_en = 0;
    reg [5:0] write_addr = 0;
    reg [143:0] write_data = 0;
    reg [5:0] read_addr = 0;
    wire [143:0] read_data;
    
    PhaseMemoryAnchorRAM #(.DEPTH(64)) pma (
        .clk(clk),
        .write_en(write_en),
        .write_data(write_data),
        .write_addr(write_addr),
        .read_addr(read_addr),
        .read_data(read_data)
    );
    
    initial begin
        $dumpfile("pma_debug2.vcd");
        $dumpvars(0, pma_debug_tb2);
        
        $display("PMA Debug Test 2 - Delayed Read");
        
        // Wait for stable
        repeat(3) @(posedge clk);
        
        // Write to slot 2
        $display("T=%0t: Setting up write to slot 2", $time);
        write_addr = 6'd2;
        write_data = {12'h042, 132'hDEADBEEF};
        write_en = 1;
        @(posedge clk);  // Write happens here
        $display("T=%0t: Write triggered", $time);
        
        write_en = 0;
        @(posedge clk);  // One cycle after write
        @(posedge clk);  // Two cycles after write
        
        // Now read from slot 2
        read_addr = 6'd2;
        @(posedge clk);
        #1;  // Small delta for combinational settle
        
        $display("T=%0t: read_data[143:132] = %h", $time, read_data[143:132]);
        $display("T=%0t: read_data[131:100] = %h", $time, read_data[131:100]);
        
        if (read_data[143:132] === 12'h042)
            $display("PASS: window_id matches!");
        else if (read_data[143:132] === 12'hxxx)
            $display("FAIL: Still X - write not working");
        else
            $display("FAIL: got %h, expected 042", read_data[143:132]);
        
        // Try different slot
        write_addr = 6'd5;
        write_data = {12'hABC, 132'h12345678};
        write_en = 1;
        @(posedge clk);
        write_en = 0;
        @(posedge clk);
        
        read_addr = 6'd5;
        @(posedge clk);
        #1;
        $display("T=%0t: Slot 5 read_data[143:132] = %h", $time, read_data[143:132]);
        
        $finish;
    end
endmodule
