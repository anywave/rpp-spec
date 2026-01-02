`timescale 1ns/1ps
module pma_debug;
    reg clk = 0;
    always #5 clk = ~clk;
    
    // PMA RAM instance
    reg write_en = 0;
    reg [5:0] write_addr;
    reg [143:0] write_data;
    reg [5:0] read_addr;
    wire [143:0] read_data;
    
    PhaseMemoryAnchorRAM #(.DEPTH(64)) pma (
        .clk(clk),
        .write_en(write_en),
        .write_addr(write_addr),
        .write_data(write_data),
        .read_addr(read_addr),
        .read_data(read_data)
    );
    
    initial begin
        $display("PMA Debug Test");
        
        // Write to slot 2
        write_addr = 6'd2;
        write_data = {12'h042, 132'h0};  // window_id=0x042
        write_en = 1;
        @(posedge clk);
        write_en = 0;
        @(posedge clk);
        
        // Read from slot 2
        read_addr = 6'd2;
        @(posedge clk);
        #1;
        
        $display("read_data[143:132] = 0x%h (expected 0x042)", read_data[143:132]);
        $display("read_data is x: %b", (read_data === 144'bx));
        
        // Check comparison
        $display("Comparison (0x042 == 0x042): %b", (read_data[143:132] == 12'h042));
        
        $finish;
    end
endmodule
