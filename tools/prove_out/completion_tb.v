`timescale 1ns/1ps
// CX-005 evidence only: exercise unchanged shipped modules, never synthesize this TB.
module CompletionEvidence;
  reg clk=0;
  always #5 clk=~clk;
  reg rst_n=0, enable=1;
  reg [4:0] entropy=0;
  reg [2:0] completion=0;
  reg [9:0] threshold=0;
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
  reg [3:0] somatic=15;
  reg verbal=0;
  wire [1:0] state;
  ConsentStateDeriver deriver(.somatic_coherence(somatic),.verbal_override(verbal),.consent_state(state));
  reg [4:0] theta=1;
  reg [2:0] phi=0, omega=0;
  reg [7:0] vector=0;
  wire [4:0] ft;
  wire [2:0] fp,fo;
  wire [7:0] fr;
  FallbackResolver_Ra fallback(.trigger(1'b1),.primary_theta(theta),.primary_phi(phi),
    .primary_omega(omega),.primary_radius(8'd128),.fallback_vector(vector),.base_address(32'd0),
    .fallback_theta(ft),.fallback_phi(fp),.fallback_omega(fo),.fallback_radius(fr),
    .fallback_address(),.fallback_active());
  reg [9:0] trigger_score=136;
  wire triggered;
  wire [3:0] counter;
  ScalarTriggerRa_Khat khat(.clk(clk),.rst_n(rst_n),.enable(enable),
    .coherence_score(trigger_score),.activation_threshold(10'd137),
    .scalar_triggered(triggered),.cycle_counter(counter));
  integer e,c,k,t,p,o,v,s,b,n;
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
          $display("SCORE,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d",e,c,threshold,exact_score,approximate_score,lut_score,exact_valid,approximate_valid,lut_valid,completion_flag);
        end
      end
    end
    for(s=0;s<16;s=s+1) begin
      for(b=0;b<2;b=b+1) begin
        somatic=s; verbal=b; #1;
        $display("DERIVE,%0d,%0d,%0d",s,b,state);
      end
    end
    for(t=1;t<=27;t=t+1) begin
      for(p=0;p<6;p=p+1) begin
        for(o=0;o<5;o=o+1) begin
          for(v=0;v<256;v=v+1) begin
            theta=t;phi=p;omega=o;vector=v;#1;
            $display("FALLBACK,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d",t,p,o,v,ft,fp,fo,fr);
          end
        end
      end
    end
    @(negedge clk); rst_n=0; #1; rst_n=1;
    for(n=0;n<34;n=n+1) begin
      @(negedge clk); trigger_score=(n==16 || n==33) ? 136 : 137;
      @(posedge clk); #1;
      $display("TRIGGER,%0d,%0d,%0d,%0d",n,trigger_score,triggered,counter);
    end
    $finish;
  end
endmodule
