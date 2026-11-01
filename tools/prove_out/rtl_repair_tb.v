`timescale 1ns/1ps
// CX-006 finite scoreboard evidence. All inputs and thresholds are scripted.
module RTLScalingRepair;
  reg clk=0;
  always #5 clk=~clk;
  reg rst_n=0;
  reg [4:0] entropy=0;
  reg [2:0] completion=0;
  reg [9:0] threshold=0;
  wire [9:0] registered_score, combinational_score, compatibility_score;
  wire registered_valid, combinational_valid, compatibility_valid;
  wire [7:0] normalized;
  wire high_band, medium_band, low_band;
  CoherenceEvaluatorRa registered(.clk(clk),.rst_n(rst_n),.enable(1'b1),
    .phase_entropy_index(entropy),.complecount_trace(completion),.threshold(threshold),
    .coherence_score(registered_score),.coherence_valid(registered_valid),.completion_flag(),
    .entropy_contribution(),.complecount_contribution());
  CoherenceEvaluator_Ra combinational(.phase_entropy_index(entropy),.complecount_trace(completion),
    .coherence_threshold(threshold),.coherence_score(combinational_score),
    .coherence_normalized(normalized),.coherence_valid(combinational_valid),
    .high_coherence(high_band),.medium_coherence(medium_band),.low_coherence(low_band));
  CoherenceEvaluator_Ra_Precise compatibility(.phase_entropy_index(entropy),.complecount_trace(completion),
    .coherence_threshold(threshold),.coherence_score(compatibility_score),.coherence_valid(compatibility_valid));
  integer e,c,k;
  integer thresholds[0:11];
  initial begin
    thresholds[0]=0; thresholds[1]=136; thresholds[2]=137; thresholds[3]=138;
    thresholds[4]=299; thresholds[5]=300; thresholds[6]=499; thresholds[7]=500;
    thresholds[8]=673; thresholds[9]=674; thresholds[10]=675; thresholds[11]=1023;
    #1 rst_n=0; #1 rst_n=1;
    for(k=0;k<12;k=k+1) begin
      for(e=0;e<32;e=e+1) begin
        for(c=0;c<8;c=c+1) begin
          @(negedge clk); entropy=e; completion=c; threshold=thresholds[k];
          @(posedge clk); #1;
          $display("SCORE,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d",
            e,c,threshold,registered_score,combinational_score,compatibility_score,
            registered_valid,combinational_valid,compatibility_valid,
            normalized,high_band,medium_band,low_band);
        end
      end
    end
    $finish;
  end
endmodule
