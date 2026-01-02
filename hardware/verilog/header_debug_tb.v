`timescale 1ns/1ps
module header_debug_tb;
    
    // TV1_HEADER from testbench
    localparam [143:0] TV1_HEADER = 144'h42500000_00000001_0010_F0_2B_01_2A_0042_00_00;
    
    wire [31:0] rpp_address;
    wire [4:0] theta;
    wire [2:0] phi, omega;
    wire [7:0] radius;
    wire [4:0] phase_entropy_index;
    wire [2:0] complecount_trace;
    wire [7:0] fallback_vector;
    wire [15:0] coherence_window_id;
    wire [1:0] consent_state;
    wire needs_fallback, has_pma_link;
    
    ConsentHeaderParser parser (
        .header_in(TV1_HEADER),
        .rpp_address(rpp_address),
        .theta(theta),
        .phi(phi),
        .omega(omega),
        .radius(radius),
        .phase_entropy_index(phase_entropy_index),
        .complecount_trace(complecount_trace),
        .fallback_vector(fallback_vector),
        .coherence_window_id(coherence_window_id),
        .consent_state(consent_state),
        .needs_fallback(needs_fallback),
        .has_pma_link(has_pma_link)
    );
    
    initial begin
        #10;
        $display("=== Header Parse Debug ===");
        $display("Input header: %h", TV1_HEADER);
        $display("");
        $display("Byte breakdown:");
        $display("  Bytes 0-3 (RPP):     %h", TV1_HEADER[143:112]);
        $display("  Bytes 4-7 (pkt_id):  %h", TV1_HEADER[111:80]);
        $display("  Bytes 8-9 (origin):  %h", TV1_HEADER[79:64]);
        $display("  Byte 10 (consent):   %h", TV1_HEADER[63:56]);
        $display("  Byte 11 (entropy):   %h", TV1_HEADER[55:48]);
        $display("  Byte 12 (payload):   %h", TV1_HEADER[47:40]);
        $display("  Byte 13 (fallback):  %h", TV1_HEADER[39:32]);
        $display("  Bytes 14-15 (wid):   %h", TV1_HEADER[31:16]);
        $display("  Byte 16 (phase):     %h", TV1_HEADER[15:8]);
        $display("  Byte 17 (crc):       %h", TV1_HEADER[7:0]);
        $display("");
        $display("Parsed values:");
        $display("  rpp_address:         %h", rpp_address);
        $display("  theta:               %d", theta);
        $display("  phi:                 %d", phi);
        $display("  omega:               %d", omega);
        $display("  radius:              %d", radius);
        $display("  phase_entropy:       %d", phase_entropy_index);
        $display("  complecount:         %d", complecount_trace);
        $display("  fallback_vector:     %h", fallback_vector);
        $display("  coherence_window_id: %h (16-bit)", coherence_window_id);
        $display("  window_id[11:0]:     %h (12-bit)", coherence_window_id[11:0]);
        $display("  window_id[5:0]:      %h (6-bit, RAM addr)", coherence_window_id[5:0]);
        $display("  consent_state:       %d", consent_state);
        $display("  needs_fallback:      %b", needs_fallback);
        $display("  has_pma_link:        %b", has_pma_link);
        $finish;
    end
endmodule
