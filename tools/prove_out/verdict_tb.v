// Fixed differences cover every ordinary coordinate-distance equivalence class.
module CX017Affinity;
  reg [4:0] theta=1;
  reg [2:0] phi=1, omega=0;
  reg [7:0] radius=0, threshold=0;
  wire [7:0] score, canonical_score;
  wire valid, canonical_valid;
  reg [7:0] score_zero, canonical_zero;
  reg valid_zero, canonical_valid_zero;
  integer t,p,w,r;
  CoherenceEvaluator binding(.src_theta(5'd1),.src_phi(3'd1),.src_omega(3'd0),.src_radius(8'd0),
    .dst_theta(theta),.dst_phi(phi),.dst_omega(omega),.dst_radius(radius),
    .threshold(threshold),.coherence_score(score),.coherence_pass(valid),
    .same_sector(),.adjacent_sectors());
  rpp_coherence_calculator canonical(.theta_src(5'd1),.phi_src(3'd1),.omega_src(3'd0),.radius_src(8'd0),
    .theta_dst(theta),.phi_dst(phi),.omega_dst(omega),.radius_dst(radius),
    .threshold(threshold),.coherence_score(canonical_score),.coherence_pass(canonical_valid),
    .same_sector(),.adjacent_sector());
  initial begin
    for(t=0;t<14;t=t+1) for(p=0;p<6;p=p+1)
      for(w=0;w<5;w=w+1) for(r=0;r<256;r=r+1) begin
        theta=1+t; phi=1+p; omega=w; radius=r; threshold=0;
        #1; score_zero=score; valid_zero=valid; canonical_zero=canonical_score; canonical_valid_zero=canonical_valid;
        threshold=255; #1;
        $display("AFF,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d",
          t,p,w,r,score_zero,score,valid_zero,valid,canonical_zero,canonical_score,canonical_valid_zero,canonical_valid);
      end
    $finish(0);
  end
endmodule

module CX017Orientation;
  reg [4:0] a=0,b=0;
  reg [2:0] ps=1,pd=6,ws=0,wd=4;
  reg [7:0] rs=0,rd=255;
  wire [7:0] consolidated,canonical;
  integer i,j,m;
  CoherenceEvaluator first(.src_theta(a),.src_phi(ps),.src_omega(ws),.src_radius(rs),
    .dst_theta(b),.dst_phi(pd),.dst_omega(wd),.dst_radius(rd),.threshold(8'd137),
    .coherence_score(consolidated),.coherence_pass(),.same_sector(),.adjacent_sectors());
  rpp_coherence_calculator second(.theta_src(a),.phi_src(ps),.omega_src(ws),.radius_src(rs),
    .theta_dst(b),.phi_dst(pd),.omega_dst(wd),.radius_dst(rd),.threshold(8'd137),
    .coherence_score(canonical),.coherence_pass(),.same_sector(),.adjacent_sector());
  initial begin
    for(i=1;i<=27;i=i+1) for(j=1;j<=27;j=j+1) for(m=0;m<8;m=m+1) begin
      a=i;b=j;ps=(m&1)?6:1;pd=(m&1)?1:6;ws=(m&2)?4:0;wd=(m&2)?0:4;
      rs=(m&4)?255:0;rd=(m&4)?0:255;#1;
      $display("ORI,%0d,%0d,%0d,%0d,%0d",i,j,m,consolidated,canonical);
    end
    $finish(0);
  end
endmodule

module CX017Legacy;
  reg [5:0] entropy=0;
  reg [4:0] completion=0;
  wire valid;
  integer e,c;
  CoherenceEvaluator_Stub binding(.phase_entropy_index(entropy),.complecount_trace(completion),
    .pmq_threshold(7'd64),.coherence_valid(valid));
  initial begin
    for(e=0;e<64;e=e+1) for(c=0;c<32;c=c+1) begin
      entropy=e; completion=c; #1;
      $display("LEG,%0d,%0d,%0d,%0d", e,c,binding.coherence_score,valid);
    end
    $finish(0);
  end
endmodule
