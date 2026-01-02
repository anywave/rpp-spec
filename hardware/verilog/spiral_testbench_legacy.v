// SPDX-License-Identifier: MIT
// SPIRAL Protocol - Legacy Stub Testbench (Original)
// 
// This testbench uses the legacy stub interfaces.
// For spec-compliant testing, use spiral_testbench_v2.v

`timescale 1ns/1ps

module spiral_testbench_legacy;

    reg clk = 0;
    reg reset = 1;
    reg enable = 0;
    
    // Clock generation
    always #5 clk = ~clk; // 100MHz
    
    // Consent Header Example (Random Encoded)
    wire [143:0] consent_header = 144'hCAFEBABE_1234567890ABCDEF_00112233445566778899AABBCCDDEEFF;
    
    // Parsed Fields
    wire [11:0] coherence_window_id;
    wire [5:0]  phase_entropy_index;
    wire [7:0]  fallback_vector;
    wire [4:0]  complecount_trace;
    wire [3:0]  payload_type;
    wire [1:0]  consent_state;
    
    ConsentHeaderParser_Stub parser (
        .consent_header(consent_header),
        .coherence_window_id(coherence_window_id),
        .phase_entropy_index(phase_entropy_index),
        .fallback_vector(fallback_vector),
        .complecount_trace(complecount_trace),
        .payload_type(payload_type),
        .consent_state(consent_state)
    );
    
    // Coherence Evaluator
    wire coherence_valid;
    reg [6:0] pmq_threshold = 7'd45;
    
    CoherenceEvaluator_Stub coherence_eval (
        .phase_entropy_index(phase_entropy_index),
        .complecount_trace(complecount_trace),
        .pmq_threshold(pmq_threshold),
        .coherence_valid(coherence_valid)
    );
    
    // Scalar Trigger
    wire scalar_triggered;
    reg [7:0] radius = 8'd50;
    reg [6:0] activation_threshold = 7'd40;
    reg [7:0] coherence_duration = 8'd3;
    
    ScalarTrigger scalar_block (
        .clk(clk),
        .reset(reset),
        .enable(enable),
        .radius(radius),
        .activation_threshold(activation_threshold),
        .coherence_duration(coherence_duration),
        .scalar_triggered(scalar_triggered)
    );
    
    // Fallback Resolver
    wire [31:0] rpp_fallback_address;
    
    FallbackResolver_Stub fallback_mod (
        .trigger_fallback(~coherence_valid),
        .fallback_vector(fallback_vector),
        .rpp_fallback_address(rpp_fallback_address)
    );
    
    initial begin
        $dumpfile("spiral_legacy.vcd");
        $dumpvars(0, spiral_testbench_legacy);
        
        $display("SPIRAL Legacy Testbench Start");
        $display("Using stub modules with arbitrary bit positions");
        $display("");
        
        #20 reset = 0;
        #10 enable = 1;
        #100;
        
        $display("Parsed from header 0x%h:", consent_header);
        $display("  coherence_window_id: 0x%h", coherence_window_id);
        $display("  phase_entropy_index: %d", phase_entropy_index);
        $display("  fallback_vector:     0x%h", fallback_vector);
        $display("  complecount_trace:   %d", complecount_trace);
        $display("  payload_type:        %d", payload_type);
        $display("  consent_state:       %d", consent_state);
        $display("");
        $display("Coherence evaluation:");
        $display("  pmq_threshold:       %d", pmq_threshold);
        $display("  coherence_valid:     %b", coherence_valid);
        $display("");
        $display("Scalar trigger:");
        $display("  radius:              %d", radius);
        $display("  activation_threshold:%d", activation_threshold);
        $display("  coherence_duration:  %d", coherence_duration);
        $display("  scalar_triggered:    %b", scalar_triggered);
        $display("");
        $display("Fallback resolver:");
        $display("  trigger_fallback:    %b", ~coherence_valid);
        $display("  fallback_addr:       0x%h", rpp_fallback_address);
        
        $finish;
    end

endmodule
