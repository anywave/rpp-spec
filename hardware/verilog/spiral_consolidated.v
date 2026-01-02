// SPDX-License-Identifier: MIT
// SPIRAL Protocol – Consolidated HDL Modules
// Version: 2.0.0-RaCanonical
//
// This file contains:
//   PART A: Original stub modules (preserved exactly)
//   PART B: Spec-compliant modules (Ra-derived)
//   PART C: Integration/Top-level modules
//
// =============================================================================
// COMPATIBILITY NOTE
// =============================================================================
// The stub modules use an arbitrary bit layout for rapid prototyping.
// The spec-compliant modules follow CONSENT-HEADER-v1.md and PMA-SCHEMA-v1.md
// with byte-aligned fields matching the Python reference implementation.
//
// For production, use the spec-compliant modules. For testing legacy
// integrations, the stub modules remain available with _Stub suffix.
// =============================================================================

`default_nettype none

// #############################################################################
// PART A: ORIGINAL STUB MODULES (Your Exact Code, Preserved)
// #############################################################################

module ConsentHeaderParser_Stub (
    input  wire [143:0] consent_header,
    output wire [11:0]  coherence_window_id,
    output wire [5:0]   phase_entropy_index,
    output wire [7:0]   fallback_vector,
    output wire [4:0]   complecount_trace,
    output wire [3:0]   payload_type,
    output wire [1:0]   consent_state
);
    assign coherence_window_id  = consent_header[143:132];
    assign phase_entropy_index  = consent_header[131:126];
    assign fallback_vector      = consent_header[125:118];
    assign complecount_trace    = consent_header[117:113];
    assign payload_type         = consent_header[112:109];
    assign consent_state        = consent_header[108:107];
endmodule


module PhaseMemoryAnchorRAM #(parameter DEPTH = 64) (
    input  wire        clk,
    input  wire        write_en,
    input  wire [5:0]  write_addr,
    input  wire [143:0] write_data,
    input  wire [5:0]  read_addr,
    output wire [143:0] read_data
);
    reg [143:0] pmem [0:DEPTH-1];
    
    always @(posedge clk) begin
        if (write_en)
            pmem[write_addr] <= write_data;
    end
    
    assign read_data = pmem[read_addr];
endmodule


module CoherenceEvaluator_Stub (
    input  wire [5:0]  phase_entropy_index,
    input  wire [4:0]  complecount_trace,
    input  wire [6:0]  pmq_threshold,
    output wire        coherence_valid
);
    wire [6:0] coherence_score;
    assign coherence_score = {phase_entropy_index, 1'b0} + {2'b00, complecount_trace};
    assign coherence_valid = (coherence_score >= pmq_threshold);
endmodule


module FallbackResolver_Stub (
    input  wire        trigger_fallback,
    input  wire [7:0]  fallback_vector,
    output wire [31:0] rpp_fallback_address
);
    wire [31:0] base_address = 32'h00000000;
    assign rpp_fallback_address = trigger_fallback ? 
        (base_address ^ {24'b0, fallback_vector}) : 32'bz;
endmodule


module ScalarTrigger (
    input  wire        clk,
    input  wire        reset,
    input  wire        enable,
    input  wire [7:0]  radius,
    input  wire [6:0]  activation_threshold,
    input  wire [7:0]  coherence_duration,
    output reg         scalar_triggered
);
    reg [7:0] coherence_counter;
    
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            coherence_counter <= 0;
            scalar_triggered <= 0;
        end else if (enable) begin
            if (radius >= {1'b0, activation_threshold}) begin
                if (coherence_counter < coherence_duration)
                    coherence_counter <= coherence_counter + 1;
                else
                    scalar_triggered <= 1;
            end else begin
                coherence_counter <= 0;
                scalar_triggered <= 0;
            end
        end else begin
            scalar_triggered <= 0;
        end
    end
endmodule


// #############################################################################
// PART B: SPEC-COMPLIANT MODULES (Ra-Derived)
// #############################################################################

// =============================================================================
// ConsentHeaderParser (Spec-Compliant)
// =============================================================================
// Byte layout per CONSENT-HEADER-v1.md:
//   Bytes 0-3:   RPP Address [theta:5|phi:3|omega:3|radius:8|reserved:13]
//   Bytes 4-7:   Packet ID
//   Bytes 8-9:   Origin Reference
//   Byte 10:     [verbal:1|somatic:4|ancestral:2|temporal_lock:1]
//   Byte 11:     [entropy:5|complecount:3]
//   Byte 12:     [reserved:4|payload_type:4]
//   Byte 13:     Fallback Vector
//   Bytes 14-15: Coherence Window ID
//   Byte 16:     Target Phase Reference
//   Byte 17:     CRC-8

module ConsentHeaderParser (
    input  wire [143:0] header_in,
    
    // RPP Address components
    output wire [31:0] rpp_address,
    output wire [4:0]  theta,
    output wire [2:0]  phi,
    output wire [2:0]  omega,
    output wire [7:0]  radius,
    output wire [12:0] reserved_bits,
    
    // Packet identification
    output wire [31:0] packet_id,
    output wire [15:0] origin_ref,
    
    // Consent fields
    output wire        consent_verbal,
    output wire [3:0]  consent_somatic,
    output wire [1:0]  consent_ancestral,
    output wire        temporal_lock,
    
    // Entropy/complecount
    output wire [4:0]  phase_entropy_index,
    output wire [2:0]  complecount_trace,
    
    // Payload
    output wire [3:0]  payload_type,
    
    // Routing
    output wire [7:0]  fallback_vector,
    output wire [15:0] coherence_window_id,
    output wire [7:0]  target_phase_ref,
    output wire [7:0]  header_crc,
    
    // Derived signals
    output wire [1:0]  consent_state,
    output wire        needs_fallback,
    output wire        has_pma_link,
    output wire        address_valid
);

    // Byte extraction (big-endian)
    wire [7:0] b0  = header_in[143:136];
    wire [7:0] b1  = header_in[135:128];
    wire [7:0] b2  = header_in[127:120];
    wire [7:0] b3  = header_in[119:112];
    wire [7:0] b4  = header_in[111:104];
    wire [7:0] b5  = header_in[103:96];
    wire [7:0] b6  = header_in[95:88];
    wire [7:0] b7  = header_in[87:80];
    wire [7:0] b8  = header_in[79:72];
    wire [7:0] b9  = header_in[71:64];
    wire [7:0] b10 = header_in[63:56];
    wire [7:0] b11 = header_in[55:48];
    wire [7:0] b12 = header_in[47:40];
    wire [7:0] b13 = header_in[39:32];
    wire [7:0] b14 = header_in[31:24];
    wire [7:0] b15 = header_in[23:16];
    wire [7:0] b16 = header_in[15:8];
    wire [7:0] b17 = header_in[7:0];
    
    // RPP Address
    assign rpp_address   = {b0, b1, b2, b3};
    assign theta         = rpp_address[31:27];
    assign phi           = rpp_address[26:24];
    assign omega         = rpp_address[23:21];
    assign radius        = rpp_address[20:13];
    assign reserved_bits = rpp_address[12:0];
    
    // Identification
    assign packet_id  = {b4, b5, b6, b7};
    assign origin_ref = {b8, b9};
    
    // Consent (byte 10)
    assign consent_verbal    = b10[7];
    assign consent_somatic   = b10[6:3];
    assign consent_ancestral = b10[2:1];
    assign temporal_lock     = b10[0];
    
    // Entropy (byte 11)
    assign phase_entropy_index = b11[7:3];
    assign complecount_trace   = b11[2:0];
    
    // Payload (byte 12)
    assign payload_type = b12[3:0];
    
    // Routing
    assign fallback_vector     = b13;
    assign coherence_window_id = {b14, b15};
    assign target_phase_ref    = b16;
    assign header_crc          = b17;
    
    // Consent state derivation
    wire low_somatic  = (consent_somatic < 4'd3);   // < 0.2
    wire mid_somatic  = (consent_somatic < 4'd8);   // < 0.5
    
    assign consent_state = low_somatic ? 2'b10 :    // SUSPENDED
                           (mid_somatic && !consent_verbal) ? 2'b01 : // DIMINISHED
                           2'b00;                   // FULL
    
    // Derived flags
    assign needs_fallback = (phase_entropy_index > 5'd25);
    assign has_pma_link   = (coherence_window_id != 16'd0);
    assign address_valid  = (theta >= 5'd1) && (theta <= 5'd27) &&
                            (phi <= 3'd5) && (omega <= 3'd4);

endmodule


// =============================================================================
// CoherenceEvaluator (Ra-Weighted)
// =============================================================================
// Implements Ra System coherence formula:
//   coherence = 1.0 - weighted_distance
// Where:
//   distance = w_θ×θ_dist + w_φ×φ_dist + w_h×h_dist + w_r×r_dist
// Weights: θ=0.30, φ=0.40, h=0.20, r=0.10

module CoherenceEvaluator (
    // Source phase vector
    input  wire [4:0]  src_theta,
    input  wire [2:0]  src_phi,
    input  wire [2:0]  src_omega,
    input  wire [7:0]  src_radius,
    
    // Destination phase vector
    input  wire [4:0]  dst_theta,
    input  wire [2:0]  dst_phi,
    input  wire [2:0]  dst_omega,
    input  wire [7:0]  dst_radius,
    
    // Threshold (0-255)
    input  wire [7:0]  threshold,
    
    // Outputs
    output wire [7:0]  coherence_score,
    output wire        coherence_pass,
    output wire        same_sector,
    output wire        adjacent_sectors
);

    // Weights (8-bit, represents ×256)
    localparam [7:0] W_THETA  = 8'd77;   // 0.30
    localparam [7:0] W_PHI    = 8'd102;  // 0.40
    localparam [7:0] W_OMEGA  = 8'd51;   // 0.20
    localparam [7:0] W_RADIUS = 8'd26;   // 0.10
    
    // ===== Theta distance (circular on 27-Repitan ring) =====
    wire [4:0] t_diff_a = (src_theta > dst_theta) ? (src_theta - dst_theta) : (dst_theta - src_theta);
    wire [4:0] t_diff_b = 5'd27 - t_diff_a;
    wire [4:0] theta_dist = (t_diff_a < t_diff_b) ? t_diff_a : t_diff_b;
    // Normalize: max=13 → 255 (×19.6 ≈ ×20)
    wire [8:0] theta_norm = {4'b0, theta_dist} * 9'd20;
    wire [7:0] theta_d8 = (theta_norm > 9'd255) ? 8'd255 : theta_norm[7:0];
    
    // ===== Phi distance (linear, max=5) =====
    wire [2:0] phi_diff = (src_phi > dst_phi) ? (src_phi - dst_phi) : (dst_phi - src_phi);
    // Normalize: max=5 → 255 (×51)
    wire [7:0] phi_d8 = {5'b0, phi_diff} * 8'd51;
    
    // ===== Omega distance (linear, max=4) =====
    wire [2:0] omega_diff = (src_omega > dst_omega) ? (src_omega - dst_omega) : (dst_omega - src_omega);
    // Normalize: max=4 → 255 (×64)
    wire [8:0] omega_norm = {6'b0, omega_diff} * 9'd64;
    wire [7:0] omega_d8 = (omega_norm > 9'd255) ? 8'd255 : omega_norm[7:0];
    
    // ===== Radius distance (linear, max=255) =====
    wire [7:0] radius_diff = (src_radius > dst_radius) ? 
                              (src_radius - dst_radius) : 
                              (dst_radius - src_radius);
    wire [7:0] radius_d8 = radius_diff;
    
    // ===== Weighted distance calculation =====
    // Each term: weight × distance / 256 (fixed-point multiply)
    wire [15:0] term_theta  = W_THETA  * theta_d8;
    wire [15:0] term_phi    = W_PHI    * phi_d8;
    wire [15:0] term_omega  = W_OMEGA  * omega_d8;
    wire [15:0] term_radius = W_RADIUS * radius_d8;
    
    // Sum all terms (upper 8 bits after divide by 256)
    wire [17:0] total_weighted = term_theta + term_phi + term_omega + term_radius;
    wire [7:0]  weighted_dist = total_weighted[15:8];  // Divide by 256
    
    // Coherence = 255 - distance
    assign coherence_score = 8'd255 - weighted_dist;
    assign coherence_pass  = (coherence_score >= threshold);
    
    // ===== Sector detection =====
    // Map Repitans to sectors for comparison
    wire [2:0] src_sector, dst_sector;
    
    ThetaToSector src_map (.theta(src_theta), .sector(src_sector));
    ThetaToSector dst_map (.theta(dst_theta), .sector(dst_sector));
    
    assign same_sector = (src_sector == dst_sector);
    
    // Adjacency check
    SectorAdjacency adj_check (
        .sector_a(src_sector),
        .sector_b(dst_sector),
        .adjacent(adjacent_sectors)
    );

endmodule


// =============================================================================
// ThetaToSector (Repitan → 8 Sectors)
// =============================================================================
// Maps 27 Repitans to 8 semantic sectors per Ra System

module ThetaToSector (
    input  wire [4:0] theta,
    output reg  [2:0] sector
);
    // Sector encoding:
    // 0=CORE, 1=GENE, 2=MEMORY, 3=WITNESS, 4=DREAM, 5=BRIDGE, 6=GUARDIAN, 7=SHADOW
    
    always @(*) begin
        case (theta)
            5'd1, 5'd2, 5'd3:                       sector = 3'd0; // CORE
            5'd4, 5'd5, 5'd6:                       sector = 3'd1; // GENE
            5'd7, 5'd8, 5'd9, 5'd10:                sector = 3'd2; // MEMORY
            5'd11, 5'd12, 5'd13:                    sector = 3'd3; // WITNESS
            5'd14, 5'd15, 5'd16, 5'd17:             sector = 3'd4; // DREAM
            5'd18, 5'd19, 5'd20:                    sector = 3'd5; // BRIDGE
            5'd21, 5'd22, 5'd23, 5'd24:             sector = 3'd6; // GUARDIAN
            5'd25, 5'd26, 5'd27:                    sector = 3'd7; // SHADOW
            default:                                 sector = 3'd0; // Invalid → CORE
        endcase
    end
endmodule


// =============================================================================
// SectorAdjacency (Ra Topology)
// =============================================================================
// Adjacency per SPIRAL-Architecture.md sector map

module SectorAdjacency (
    input  wire [2:0] sector_a,
    input  wire [2:0] sector_b,
    output wire       adjacent
);
    // Adjacency matrix (8×8, symmetric)
    // CORE-GENE, CORE-MEMORY, GENE-GUARDIAN, GENE-BRIDGE,
    // MEMORY-WITNESS, MEMORY-BRIDGE, WITNESS-BRIDGE, WITNESS-DREAM,
    // DREAM-SHADOW, DREAM-BRIDGE, BRIDGE-GUARDIAN, GUARDIAN-SHADOW
    
    reg adj_result;
    
    always @(*) begin
        case ({sector_a, sector_b})
            // CORE (0) adjacent to GENE (1), MEMORY (2)
            {3'd0, 3'd1}, {3'd1, 3'd0}: adj_result = 1'b1;
            {3'd0, 3'd2}, {3'd2, 3'd0}: adj_result = 1'b1;
            
            // GENE (1) adjacent to GUARDIAN (6), BRIDGE (5)
            {3'd1, 3'd6}, {3'd6, 3'd1}: adj_result = 1'b1;
            {3'd1, 3'd5}, {3'd5, 3'd1}: adj_result = 1'b1;
            
            // MEMORY (2) adjacent to WITNESS (3), BRIDGE (5)
            {3'd2, 3'd3}, {3'd3, 3'd2}: adj_result = 1'b1;
            {3'd2, 3'd5}, {3'd5, 3'd2}: adj_result = 1'b1;
            
            // WITNESS (3) adjacent to BRIDGE (5), DREAM (4)
            {3'd3, 3'd5}, {3'd5, 3'd3}: adj_result = 1'b1;
            {3'd3, 3'd4}, {3'd4, 3'd3}: adj_result = 1'b1;
            
            // DREAM (4) adjacent to SHADOW (7), BRIDGE (5)
            {3'd4, 3'd7}, {3'd7, 3'd4}: adj_result = 1'b1;
            {3'd4, 3'd5}, {3'd5, 3'd4}: adj_result = 1'b1;
            
            // GUARDIAN (6) adjacent to SHADOW (7), BRIDGE (5)
            {3'd6, 3'd7}, {3'd7, 3'd6}: adj_result = 1'b1;
            {3'd6, 3'd5}, {3'd5, 3'd6}: adj_result = 1'b1;
            
            default: adj_result = 1'b0;
        endcase
    end
    
    assign adjacent = adj_result;
endmodule


// =============================================================================
// FallbackResolver (Spec-Compliant)
// =============================================================================
// XOR-based fallback with modulo wrapping to valid Ra ranges
// Vector layout: [7:5]=theta_offset, [4:2]=phi_offset, [1:0]=omega_offset

module FallbackResolver (
    input  wire        trigger,
    input  wire [4:0]  primary_theta,
    input  wire [2:0]  primary_phi,
    input  wire [2:0]  primary_omega,
    input  wire [7:0]  primary_radius,
    input  wire [7:0]  fallback_vector,
    
    output wire [4:0]  fallback_theta,
    output wire [2:0]  fallback_phi,
    output wire [2:0]  fallback_omega,
    output wire [7:0]  fallback_radius,
    output wire [31:0] fallback_address
);

    // Extract offsets from vector
    wire [2:0] theta_offset = fallback_vector[7:5];
    wire [2:0] phi_offset   = fallback_vector[4:2];
    wire [1:0] omega_offset = fallback_vector[1:0];
    
    // XOR and wrap to valid ranges
    wire [5:0] theta_raw = {1'b0, primary_theta} ^ {3'b0, theta_offset};
    wire [3:0] phi_raw   = {1'b0, primary_phi} ^ {1'b0, phi_offset};
    wire [2:0] omega_raw = primary_omega ^ {1'b0, omega_offset};
    
    // Modulo wrap: theta mod 27 (1-27), phi mod 6 (0-5), omega mod 5 (0-4)
    // Simplified: use conditional subtraction
    wire [4:0] theta_wrapped = (theta_raw > 6'd27) ? (theta_raw[4:0] - 5'd27) :
                               (theta_raw == 6'd0) ? 5'd27 : theta_raw[4:0];
    wire [2:0] phi_wrapped   = (phi_raw > 4'd5) ? (phi_raw[2:0] - 3'd6) : phi_raw[2:0];
    wire [2:0] omega_wrapped = (omega_raw > 3'd4) ? (omega_raw - 3'd5) : omega_raw;
    
    // Output selection
    assign fallback_theta  = trigger ? theta_wrapped : primary_theta;
    assign fallback_phi    = trigger ? phi_wrapped : primary_phi;
    assign fallback_omega  = trigger ? omega_wrapped : primary_omega;
    assign fallback_radius = primary_radius;  // Radius unchanged
    
    // Assemble 32-bit address
    assign fallback_address = {
        fallback_theta,    // [31:27]
        fallback_phi,      // [26:24]
        fallback_omega,    // [23:21]
        fallback_radius,   // [20:13]
        13'b0              // [12:0] reserved
    };

endmodule


// =============================================================================
// PMARecordParser
// =============================================================================
// Extracts fields from 144-bit PMA record per PMA-SCHEMA-v1.md

module PMARecordParser (
    input  wire [143:0] pma_in,
    
    output wire [11:0]  window_id,
    output wire [63:0]  timestamp,
    output wire [31:0]  phase_vector,
    output wire [4:0]   pv_theta,
    output wire [2:0]   pv_phi,
    output wire [2:0]   pv_omega,
    output wire [7:0]   pv_radius,
    output wire [1:0]   consent_state,
    output wire [4:0]   complecount_score,
    output wire [5:0]   coherence_score,
    output wire [3:0]   payload_type,
    output wire         fallback_triggered,
    output wire [7:0]   record_crc
);

    assign window_id          = pma_in[143:132];
    assign timestamp          = pma_in[131:68];
    assign phase_vector       = pma_in[67:36];
    assign consent_state      = pma_in[35:34];
    assign complecount_score  = pma_in[33:29];
    assign coherence_score    = pma_in[28:23];
    assign payload_type       = pma_in[22:19];
    assign fallback_triggered = pma_in[18];
    assign record_crc         = pma_in[17:10];
    
    // Phase vector breakdown
    assign pv_theta  = phase_vector[31:27];
    assign pv_phi    = phase_vector[26:24];
    assign pv_omega  = phase_vector[23:21];
    assign pv_radius = phase_vector[20:13];

endmodule


// #############################################################################
// PART C: INTEGRATION MODULES
// #############################################################################

// =============================================================================
// CRC-8/CCITT Calculator (Single Byte)
// =============================================================================

module CRC8_Byte (
    input  wire [7:0] crc_in,
    input  wire [7:0] byte_in,
    output wire [7:0] crc_out
);
    wire [7:0] d = crc_in ^ byte_in;
    
    // Polynomial 0x07: bit-serial computation
    wire [7:0] r0 = d[7] ? {d[6:0], 1'b0} ^ 8'h07 : {d[6:0], 1'b0};
    wire [7:0] r1 = r0[7] ? {r0[6:0], 1'b0} ^ 8'h07 : {r0[6:0], 1'b0};
    wire [7:0] r2 = r1[7] ? {r1[6:0], 1'b0} ^ 8'h07 : {r1[6:0], 1'b0};
    wire [7:0] r3 = r2[7] ? {r2[6:0], 1'b0} ^ 8'h07 : {r2[6:0], 1'b0};
    wire [7:0] r4 = r3[7] ? {r3[6:0], 1'b0} ^ 8'h07 : {r3[6:0], 1'b0};
    wire [7:0] r5 = r4[7] ? {r4[6:0], 1'b0} ^ 8'h07 : {r4[6:0], 1'b0};
    wire [7:0] r6 = r5[7] ? {r5[6:0], 1'b0} ^ 8'h07 : {r5[6:0], 1'b0};
    wire [7:0] r7 = r6[7] ? {r6[6:0], 1'b0} ^ 8'h07 : {r6[6:0], 1'b0};
    
    assign crc_out = r7;
endmodule


// =============================================================================
// SpiralRoutingCore (Top-Level Integration)
// =============================================================================
// Combines header parsing, coherence evaluation, fallback resolution,
// and PMA lookup into a single routing pipeline.

module SpiralRoutingCore #(
    parameter PMA_DEPTH = 64
) (
    input  wire         clk,
    input  wire         rst_n,
    
    // Header input
    input  wire [143:0] header_in,
    input  wire         header_valid,
    
    // Destination for coherence check
    input  wire [31:0]  dest_address,
    
    // Configuration
    input  wire [7:0]   coherence_threshold,
    input  wire [6:0]   scalar_threshold,
    input  wire [7:0]   scalar_duration,
    
    // PMA write port (for external updates)
    input  wire         pma_write_en,
    input  wire [5:0]   pma_write_addr,
    input  wire [143:0] pma_write_data,
    
    // Outputs
    output wire [31:0]  resolved_address,
    output wire [1:0]   consent_state_out,
    output wire [7:0]   coherence_score_out,
    output wire         route_valid,
    output wire         fallback_active,
    output wire         scalar_triggered_out,
    output wire         pma_hit
);

    // ===== Header Parsing =====
    wire [31:0] rpp_addr;
    wire [4:0]  src_theta;
    wire [2:0]  src_phi, src_omega;
    wire [7:0]  src_radius;
    wire [4:0]  entropy;
    wire [2:0]  complecount;
    wire [7:0]  fb_vector;
    wire [15:0] window_id;
    wire [1:0]  consent_st;
    wire        needs_fb, has_pma, addr_valid;
    
    ConsentHeaderParser parser (
        .header_in(header_in),
        .rpp_address(rpp_addr),
        .theta(src_theta),
        .phi(src_phi),
        .omega(src_omega),
        .radius(src_radius),
        .phase_entropy_index(entropy),
        .complecount_trace(complecount),
        .fallback_vector(fb_vector),
        .coherence_window_id(window_id),
        .consent_state(consent_st),
        .needs_fallback(needs_fb),
        .has_pma_link(has_pma),
        .address_valid(addr_valid)
    );
    
    // ===== Destination Parsing =====
    wire [4:0] dst_theta  = dest_address[31:27];
    wire [2:0] dst_phi    = dest_address[26:24];
    wire [2:0] dst_omega  = dest_address[23:21];
    wire [7:0] dst_radius = dest_address[20:13];
    
    // ===== Coherence Evaluation =====
    wire [7:0] coh_score;
    wire       coh_pass, same_sect, adj_sect;
    
    CoherenceEvaluator coherence (
        .src_theta(src_theta),
        .src_phi(src_phi),
        .src_omega(src_omega),
        .src_radius(src_radius),
        .dst_theta(dst_theta),
        .dst_phi(dst_phi),
        .dst_omega(dst_omega),
        .dst_radius(dst_radius),
        .threshold(coherence_threshold),
        .coherence_score(coh_score),
        .coherence_pass(coh_pass),
        .same_sector(same_sect),
        .adjacent_sectors(adj_sect)
    );
    
    // ===== Fallback Resolution =====
    wire [4:0]  fb_theta;
    wire [2:0]  fb_phi, fb_omega;
    wire [7:0]  fb_radius;
    wire [31:0] fb_addr;
    
    FallbackResolver fallback (
        .trigger(needs_fb),
        .primary_theta(src_theta),
        .primary_phi(src_phi),
        .primary_omega(src_omega),
        .primary_radius(src_radius),
        .fallback_vector(fb_vector),
        .fallback_theta(fb_theta),
        .fallback_phi(fb_phi),
        .fallback_omega(fb_omega),
        .fallback_radius(fb_radius),
        .fallback_address(fb_addr)
    );
    
    // ===== PMA Lookup =====
    wire [143:0] pma_read_data;
    
    PhaseMemoryAnchorRAM #(.DEPTH(PMA_DEPTH)) pma_ram (
        .clk(clk),
        .write_en(pma_write_en),
        .write_addr(pma_write_addr),
        .write_data(pma_write_data),
        .read_addr(window_id[5:0]),  // Lower 6 bits for 64-entry RAM
        .read_data(pma_read_data)
    );
    
    // Check if PMA entry matches window_id
    wire [11:0] pma_window = pma_read_data[143:132];
    assign pma_hit = has_pma && (pma_window == window_id[11:0]);
    
    // ===== Scalar Trigger =====
    wire scalar_trig;
    
    ScalarTrigger scalar (
        .clk(clk),
        .reset(~rst_n),
        .enable(header_valid && addr_valid),
        .radius(src_radius),
        .activation_threshold(scalar_threshold),
        .coherence_duration(scalar_duration),
        .scalar_triggered(scalar_trig)
    );
    
    // ===== Output Assignment =====
    assign resolved_address   = needs_fb ? fb_addr : rpp_addr;
    assign consent_state_out  = consent_st;
    assign coherence_score_out = coh_score;
    assign route_valid        = header_valid && addr_valid && 
                                 (consent_st != 2'b10) &&  // Not SUSPENDED
                                 (consent_st != 2'b11) &&  // Not EMERGENCY
                                 coh_pass;
    assign fallback_active    = needs_fb;
    assign scalar_triggered_out = scalar_trig;

endmodule

`default_nettype wire
