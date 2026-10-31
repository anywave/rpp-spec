`timescale 1ns/1ps
module CompareCoherence;
 reg clk=0;
 always #5 clk=~clk;
 reg rst_n=0;
 reg enable=0;
 reg [4:0] entropy=0;
 reg [2:0] completion=0;
 reg [9:0] threshold=137;
 wire [9:0] exact_score, approximate_score, lut_score;
 wire exact_valid, approximate_valid, lut_valid, completion_flag;
 CoherenceEvaluatorRa exact(.clk(clk),.rst_n(rst_n),.enable(enable),
  .phase_entropy_index(entropy),.complecount_trace(completion),.threshold(threshold),
  .coherence_score(exact_score),.coherence_valid(exact_valid),.completion_flag(completion_flag),
  .entropy_contribution(),.complecount_contribution());
 CoherenceEvaluator_Ra approximate(.phase_entropy_index(entropy),.complecount_trace(completion),
  .coherence_threshold(threshold),.coherence_score(approximate_score),
  .coherence_normalized(),.coherence_valid(approximate_valid),.high_coherence(),.medium_coherence(),.low_coherence());
 CoherenceEvaluator_Ra_Precise lut(.phase_entropy_index(entropy),.complecount_trace(completion),
  .coherence_threshold(threshold),.coherence_score(lut_score),.coherence_valid(lut_valid));
 integer e,c;
 initial begin
  #2 rst_n=1; enable=1;
  for(e=0;e<32;e=e+1) begin
   for(c=0;c<8;c=c+1) begin
    @(negedge clk); entropy=e; completion=c;
    @(posedge clk); #1;
    $display("POINT,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d", e,c,exact_score,approximate_score,lut_score,exact_valid,approximate_valid,lut_valid,completion_flag);
   end
  end
  $finish;
 end
endmodule
