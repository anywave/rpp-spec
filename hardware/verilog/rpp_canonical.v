// ============================================================================
// RPP Canonical Address - Ra-Derived HDL Implementation
// ============================================================================
// Version: 1.0-RaCanonical
// Reference: RPP v1.0-RaCanonical Specification
//
// Address Layout (32 bits):
//   [31:27] θ (theta)  - 5 bits - Repitan index (1-27, 0/28-31 reserved)
//   [26:24] φ (phi)    - 3 bits - RAC level (0-5 = RAC1-RAC6, 6-7 reserved)
//   [23:21] h (omega)  - 3 bits - Omega tier (0-4, 5-7 reserved)
//   [20:13] r (radius) - 8 bits - Scalar intensity (0-255 = 0.0-1.0)
//   [12:0]  reserved   - 13 bits - CRC or future use
// ============================================================================

`timescale 1ns / 1ps

// ============================================================================
// Module: rpp_address_decoder
// ============================================================================
// Decodes a 32-bit RPP canonical address into component fields
module rpp_address_decoder (
    input  wire [31:0] address,
    
    // Decoded fields
    output wire [4:0]  theta,      // Repitan 0-31 (valid: 1-27)
    output wire [2:0]  phi,        // RAC encoded 0-7 (valid: 0-5)
    output wire [2:0]  omega,      // Omega tier 0-7 (valid: 0-4)
    output wire [7:0]  radius,     // Scalar intensity 0-255
    output wire [12:0] reserved,   // CRC/reserved field
    
    // Semantic outputs
    output wire [2:0]  sector,     // ThetaSector enum
    output wire        valid,      // All fields in Ra-valid ranges
    output wire        is_null,    // Theta = 0 (null address)
    output wire        is_wildcard // Any field uses wildcard value
);

    // Field extraction
    assign theta    = address[31:27];
    assign phi      = address[26:24];
    assign omega    = address[23:21];
    assign radius   = address[20:13];
    assign reserved = address[12:0];
    
    // Validity checks
    wire theta_valid = (theta >= 5'd1) && (theta <= 5'd27);
    wire phi_valid   = (phi <= 3'd5);
    wire omega_valid = (omega <= 3'd4);
    
    assign valid = theta_valid && phi_valid && omega_valid;
    assign is_null = (theta == 5'd0);
    assign is_wildcard = (theta == 5'd31) || (phi == 3'd7) || (omega == 3'd7);
    
    // Sector mapping (combinational)
    reg [2:0] sector_reg;
    always @(*) begin
        if (theta == 0)
            sector_reg = 3'd0;
        else if (theta <= 3)
            sector_reg = 3'd0;  // CORE
        else if (theta <= 6)
            sector_reg = 3'd1;  // GENE
        else if (theta <= 10)
            sector_reg = 3'd2;  // MEMORY
        else if (theta <= 13)
            sector_reg = 3'd3;  // WITNESS
        else if (theta <= 17)
            sector_reg = 3'd4;  // DREAM
        else if (theta <= 20)
            sector_reg = 3'd5;  // BRIDGE
        else if (theta <= 24)
            sector_reg = 3'd6;  // GUARDIAN
        else
            sector_reg = 3'd7;  // SHADOW
    end
    assign sector = sector_reg;

endmodule


// ============================================================================
// Module: rpp_address_encoder
// ============================================================================
module rpp_address_encoder (
    input  wire [4:0]  theta,
    input  wire [2:0]  phi,
    input  wire [2:0]  omega,
    input  wire [7:0]  radius,
    input  wire [12:0] reserved,
    output wire [31:0] address
);
    assign address = {theta, phi, omega, radius, reserved};
endmodule


// ============================================================================
// Module: rpp_theta_to_sector
// ============================================================================
module rpp_theta_to_sector (
    input  wire [4:0] theta,
    output reg  [2:0] sector
);
    always @(*) begin
        case (theta)
            5'd0:                             sector = 3'd0;
            5'd1, 5'd2, 5'd3:                 sector = 3'd0; // CORE
            5'd4, 5'd5, 5'd6:                 sector = 3'd1; // GENE
            5'd7, 5'd8, 5'd9, 5'd10:          sector = 3'd2; // MEMORY
            5'd11, 5'd12, 5'd13:              sector = 3'd3; // WITNESS
            5'd14, 5'd15, 5'd16, 5'd17:       sector = 3'd4; // DREAM
            5'd18, 5'd19, 5'd20:              sector = 3'd5; // BRIDGE
            5'd21, 5'd22, 5'd23, 5'd24:       sector = 3'd6; // GUARDIAN
            5'd25, 5'd26, 5'd27:              sector = 3'd7; // SHADOW
            default:                          sector = 3'd0;
        endcase
    end
endmodule


// ============================================================================
// Module: rpp_sector_adjacency
// ============================================================================
module rpp_sector_adjacency (
    input  wire [2:0] sector_a,
    input  wire [2:0] sector_b,
    output reg        adjacent
);
    always @(*) begin
        adjacent = 1'b0;
        case (sector_a)
            3'd0: adjacent = (sector_b == 3'd1) || (sector_b == 3'd2);
            3'd1: adjacent = (sector_b == 3'd0) || (sector_b == 3'd5) || (sector_b == 3'd6);
            3'd2: adjacent = (sector_b == 3'd0) || (sector_b == 3'd3) || (sector_b == 3'd5);
            3'd3: adjacent = (sector_b == 3'd2) || (sector_b == 3'd5);
            3'd4: adjacent = (sector_b == 3'd5) || (sector_b == 3'd7);
            3'd5: adjacent = (sector_b == 3'd1) || (sector_b == 3'd2) || 
                            (sector_b == 3'd3) || (sector_b == 3'd6) || (sector_b == 3'd4);
            3'd6: adjacent = (sector_b == 3'd1) || (sector_b == 3'd5);
            3'd7: adjacent = (sector_b == 3'd4);
            default: adjacent = 1'b0;
        endcase
    end
endmodule


// ============================================================================
// Module: rpp_coherence_calculator
// ============================================================================
module rpp_coherence_calculator (
    input  wire [4:0]  theta_src,
    input  wire [2:0]  phi_src,
    input  wire [2:0]  omega_src,
    input  wire [7:0]  radius_src,
    input  wire [4:0]  theta_dst,
    input  wire [2:0]  phi_dst,
    input  wire [2:0]  omega_dst,
    input  wire [7:0]  radius_dst,
    input  wire [7:0]  threshold,
    output reg  [7:0]  coherence_score,
    output wire        coherence_pass,
    output wire        same_sector,
    output wire        adjacent_sector
);

    localparam W_THETA  = 8'd77;   // 0.30 * 256
    localparam W_PHI    = 8'd102;  // 0.40 * 256
    localparam W_OMEGA  = 8'd51;   // 0.20 * 256
    localparam W_RADIUS = 8'd26;   // 0.10 * 256
    
    reg [4:0] theta_diff, theta_dist;
    reg [2:0] phi_diff, omega_diff;
    reg [7:0] radius_diff;
    reg [15:0] weighted_distance;
    
    always @(*) begin
        theta_diff = (theta_src > theta_dst) ? 
                     (theta_src - theta_dst) : (theta_dst - theta_src);
        theta_dist = (theta_diff > 5'd13) ? (5'd27 - theta_diff) : theta_diff;
        
        phi_diff = (phi_src > phi_dst) ? 
                   (phi_src - phi_dst) : (phi_dst - phi_src);
        
        omega_diff = (omega_src > omega_dst) ? 
                     (omega_src - omega_dst) : (omega_dst - omega_src);
        
        radius_diff = (radius_src > radius_dst) ? 
                      (radius_src - radius_dst) : (radius_dst - radius_src);
        
        weighted_distance = (theta_dist * 20 * W_THETA) / 256 +
                           (phi_diff * 51 * W_PHI) / 256 +
                           (omega_diff * 64 * W_OMEGA) / 256 +
                           (radius_diff * W_RADIUS) / 256;
        
        coherence_score = (weighted_distance > 255) ? 
                          8'd0 : (8'd255 - weighted_distance[7:0]);
    end
    
    assign coherence_pass = (coherence_score >= threshold);
    
    wire [2:0] sector_src, sector_dst;
    rpp_theta_to_sector u_src (.theta(theta_src), .sector(sector_src));
    rpp_theta_to_sector u_dst (.theta(theta_dst), .sector(sector_dst));
    
    assign same_sector = (sector_src == sector_dst);
    rpp_sector_adjacency u_adj (.sector_a(sector_src), .sector_b(sector_dst), .adjacent(adjacent_sector));

endmodule


// ============================================================================
// Module: rpp_fallback_calculator
// ============================================================================
module rpp_fallback_calculator (
    input  wire [4:0]  theta_pri,
    input  wire [2:0]  phi_pri,
    input  wire [2:0]  omega_pri,
    input  wire [7:0]  radius_pri,
    input  wire [7:0]  fallback_vector,
    output wire [4:0]  theta_fb,
    output wire [2:0]  phi_fb,
    output wire [2:0]  omega_fb,
    output wire [7:0]  radius_fb
);

    wire [2:0] theta_off = fallback_vector[7:5];
    wire [2:0] phi_off   = fallback_vector[4:2];
    wire [1:0] omega_off = fallback_vector[1:0];
    
    wire [4:0] theta_xor = (theta_pri - 1) ^ {2'b00, theta_off};
    wire [4:0] theta_mod = (theta_xor >= 5'd27) ? (theta_xor - 5'd27) : theta_xor;
    assign theta_fb = theta_mod + 5'd1;
    
    wire [2:0] phi_xor = phi_pri ^ phi_off;
    assign phi_fb = (phi_xor >= 3'd6) ? (phi_xor - 3'd6) : phi_xor;
    
    wire [2:0] omega_xor = omega_pri ^ {1'b0, omega_off};
    assign omega_fb = (omega_xor >= 3'd5) ? (omega_xor - 3'd5) : omega_xor;
    
    assign radius_fb = radius_pri;

endmodule


// ============================================================================
// Module: rpp_canonical_top
// ============================================================================
module rpp_canonical_top (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [31:0] address_in,
    input  wire        address_valid,
    input  wire [31:0] address_cmp,
    input  wire [7:0]  fallback_vector,
    input  wire [7:0]  coherence_threshold,
    
    output reg  [4:0]  theta,
    output reg  [2:0]  phi,
    output reg  [2:0]  omega,
    output reg  [7:0]  radius,
    output reg  [2:0]  sector,
    output reg         valid,
    output reg         is_null,
    output reg  [7:0]  coherence_score,
    output reg         coherence_pass,
    output reg  [31:0] fallback_address,
    output reg         ready
);

    wire [4:0]  theta_w, theta_cmp;
    wire [2:0]  phi_w, phi_cmp;
    wire [2:0]  omega_w, omega_cmp;
    wire [7:0]  radius_w, radius_cmp;
    wire [12:0] reserved_w;
    wire [2:0]  sector_w;
    wire        valid_w, is_null_w;
    wire [7:0]  coherence_w;
    wire        coherence_pass_w;
    wire [4:0]  theta_fb;
    wire [2:0]  phi_fb, omega_fb;
    wire [7:0]  radius_fb;
    wire [31:0] fallback_addr_w;

    rpp_address_decoder u_dec (
        .address(address_in), .theta(theta_w), .phi(phi_w), .omega(omega_w),
        .radius(radius_w), .reserved(reserved_w), .sector(sector_w),
        .valid(valid_w), .is_null(is_null_w), .is_wildcard()
    );
    
    rpp_address_decoder u_dec_cmp (
        .address(address_cmp), .theta(theta_cmp), .phi(phi_cmp), .omega(omega_cmp),
        .radius(radius_cmp), .reserved(), .sector(), .valid(), .is_null(), .is_wildcard()
    );
    
    rpp_coherence_calculator u_coh (
        .theta_src(theta_w), .phi_src(phi_w), .omega_src(omega_w), .radius_src(radius_w),
        .theta_dst(theta_cmp), .phi_dst(phi_cmp), .omega_dst(omega_cmp), .radius_dst(radius_cmp),
        .threshold(coherence_threshold), .coherence_score(coherence_w),
        .coherence_pass(coherence_pass_w), .same_sector(), .adjacent_sector()
    );
    
    rpp_fallback_calculator u_fb (
        .theta_pri(theta_w), .phi_pri(phi_w), .omega_pri(omega_w), .radius_pri(radius_w),
        .fallback_vector(fallback_vector),
        .theta_fb(theta_fb), .phi_fb(phi_fb), .omega_fb(omega_fb), .radius_fb(radius_fb)
    );
    
    rpp_address_encoder u_enc_fb (
        .theta(theta_fb), .phi(phi_fb), .omega(omega_fb), .radius(radius_fb),
        .reserved(13'd0), .address(fallback_addr_w)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            theta <= 5'd0; phi <= 3'd0; omega <= 3'd0; radius <= 8'd0;
            sector <= 3'd0; valid <= 1'b0; is_null <= 1'b1;
            coherence_score <= 8'd0; coherence_pass <= 1'b0;
            fallback_address <= 32'd0; ready <= 1'b0;
        end else if (address_valid) begin
            theta <= theta_w; phi <= phi_w; omega <= omega_w; radius <= radius_w;
            sector <= sector_w; valid <= valid_w; is_null <= is_null_w;
            coherence_score <= coherence_w; coherence_pass <= coherence_pass_w;
            fallback_address <= fallback_addr_w; ready <= 1'b1;
        end else begin
            ready <= 1'b0;
        end
    end

endmodule
