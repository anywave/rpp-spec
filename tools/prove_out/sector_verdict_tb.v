`timescale 1ns/1ps
module SectorVerdict;
  reg [4:0] theta, src_theta, dst_theta;
  reg [2:0] a, b, src_phi, dst_phi, src_omega, dst_omega;
  reg [7:0] src_radius, dst_radius;
  wire [2:0] sector;
  wire same_sector, adjacent, ignored_adjacent, ignored_pass;
  wire [7:0] ignored_score;
  wire [2:0] canonical_sector;
  wire canonical_same, canonical_adjacent, canonical_ignored_adj, canonical_ignored_pass;
  wire [7:0] canonical_ignored_score;
  reg [31:0] word;
  wire [4:0] decoded_theta;
  wire [2:0] decoded_phi, decoded_omega, decoded_sector;
  wire [7:0] decoded_radius;
  wire [12:0] decoded_reserved;
  wire decoded_valid;
  integer t, s, d, relation, field, value, limit, probe;
  ThetaToSector mapping(.theta(theta), .sector(sector));
  SectorAdjacency graph(.sector_a(a), .sector_b(b), .adjacent(adjacent));
  CoherenceEvaluator evaluator(.src_theta(src_theta), .dst_theta(dst_theta),
    .src_phi(src_phi), .dst_phi(dst_phi), .src_omega(src_omega), .dst_omega(dst_omega),
    .src_radius(src_radius), .dst_radius(dst_radius), .threshold(8'd0),
    .coherence_score(ignored_score), .coherence_pass(ignored_pass),
    .same_sector(same_sector), .adjacent_sectors(ignored_adjacent));
  rpp_theta_to_sector canonical_map(.theta(theta), .sector(canonical_sector));
  rpp_sector_adjacency canonical_graph(.sector_a(a), .sector_b(b), .adjacent(canonical_adjacent));
  rpp_coherence_calculator canonical_eval(.theta_src(src_theta), .theta_dst(dst_theta),
    .phi_src(src_phi), .phi_dst(dst_phi), .omega_src(src_omega), .omega_dst(dst_omega),
    .radius_src(src_radius), .radius_dst(dst_radius), .threshold(8'd0),
    .coherence_score(canonical_ignored_score), .coherence_pass(canonical_ignored_pass),
    .same_sector(canonical_same), .adjacent_sector(canonical_ignored_adj));
  rpp_address_decoder decoder(.address(word), .theta(decoded_theta), .phi(decoded_phi),
    .omega(decoded_omega), .radius(decoded_radius), .reserved(decoded_reserved),
    .sector(decoded_sector), .valid(decoded_valid), .is_null(), .is_wildcard());
  initial begin
    theta=0; a=0; b=0; src_theta=1; dst_theta=1;
    src_phi=0; dst_phi=0; src_omega=0; dst_omega=0; src_radius=0; dst_radius=0;
    for(t=0;t<32;t=t+1) begin
      theta=t; #1; $display("consolidated,MAP,%0d,%0d",t,sector);
      $display("canonical,MAP,%0d,%0d",t,canonical_sector);
    end
    for(s=1;s<=27;s=s+1) for(d=1;d<=27;d=d+1) begin
      src_theta=s; dst_theta=d; #1; $display("consolidated,SAME,%0d,%0d,%0d",s,d,same_sector);
      $display("canonical,SAME,%0d,%0d,%0d",s,d,canonical_same);
    end
    for(s=0;s<8;s=s+1) for(d=0;d<8;d=d+1) begin
      a=s; b=d; #1; $display("consolidated,ADJ,%0d,%0d,%0d",s,d,adjacent);
      $display("canonical,ADJ,%0d,%0d,%0d",s,d,canonical_adjacent);
    end
    for(relation=0;relation<2;relation=relation+1) begin
      src_theta=1; dst_theta=(relation==0)?2:4;
      for(field=0;field<3;field=field+1) begin
        limit=(field==0)?6:((field==1)?5:256);
        for(value=0;value<limit;value=value+1) begin
          src_phi=0; dst_phi=0; src_omega=0; dst_omega=0; src_radius=0; dst_radius=0;
          case(field)
            0: begin src_phi=value; dst_phi=5-value; end
            1: begin src_omega=value; dst_omega=4-value; end
            2: begin src_radius=value; dst_radius=255-value; end
          endcase
          #1; $display("consolidated,IRREL,%0d,%0d,%0d,%0d",relation,field,value,same_sector);
          $display("canonical,IRREL,%0d,%0d,%0d,%0d",relation,field,value,canonical_same);
        end
      end
    end
    for(t=0;t<32;t=t+1) for(probe=0;probe<8;probe=probe+1) begin
      case(probe)
        0: word={t[4:0],3'd0,3'd0,8'd0,13'd0};
        1: word={t[4:0],3'd5,3'd0,8'd0,13'd0};
        2: word={t[4:0],3'd0,3'd4,8'd0,13'd0};
        3: word={t[4:0],3'd0,3'd0,8'd255,13'd0};
        4: word={t[4:0],3'd0,3'd0,8'd0,13'd8191};
        5: word={t[4:0],3'd5,3'd4,8'd255,13'd8191};
        6: word={t[4:0],3'd2,3'd2,8'd128,13'd17};
        7: word={t[4:0],3'd4,3'd1,8'd127,13'd1};
      endcase
      #1; $display("decoder,DEC,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d",t,probe,word,decoded_sector,decoded_valid,decoded_theta,decoded_phi,decoded_omega,decoded_radius,decoded_reserved);
    end
    $finish(0);
  end
endmodule
