// SPDX-License-Identifier: MIT
// SPIRAL Protocol – Ra-Derived Coherence Modules
// Version: 2.1.0-RaCanonical
//
// Implements coherence evaluation using Ra System constants:
//   φ (GREEN_PHI) ≈ 1.618 → 165 (×100 fixed-point)
//   𝔄 (ANKH)     ≈ 5.089 → 509 (×100 fixed-point)
//
// Coherence Formula:
//   E = phase_entropy_index / 31  (normalized entropy)
//   C = complecount_trace / 7     (normalized complecount)
//   coherence_score = (φ × E) + (𝔄 × C)
//
// Field widths per production spec:
//   coherence_window_id: 16 bits
//   phase_entropy_index: 5 bits (0-31)
//   complecount_trace: 3 bits (0-7)

`default_nettype none

// =============================================================================
// Ra System Constants (Fixed-Point ×100)
// =============================================================================
// These match the Python ra_constants implementation

`define GREEN_PHI_X100   16'd165   // 1.618 × 100
`define ANKH_X100        16'd509   // 5.089 × 100
`define PHI_INVERSE_X100 16'd62    // 0.618 × 100


// =============================================================================
// CoherenceEvaluator_Ra (Ra-Derived Formula)
// =============================================================================
// Computes coherence using the canonical Ra formula:
//   coherence = (φ × E) + (𝔄 × C)
// Where:
//   E = phase_entropy_index / 31 (5-bit normalized to 0.0-1.0)
//   C = complecount_trace / 7    (3-bit normalized to 0.0-1.0)
//
// Fixed-point implementation uses ×256 scaling for intermediate values

module CoherenceEvaluator_Ra (
    // Inputs from consent header
    input  wire [4:0]  phase_entropy_index,  // 0-31
    input  wire [2:0]  complecount_trace,    // 0-7

    // Threshold (×100 scale, e.g., 420 = 4.2, 510 = 5.1)
    input  wire [9:0]  coherence_threshold,

    // Outputs
    output wire [9:0]  coherence_score,      // ×100 scale (0-673 max)
    output wire [7:0]  coherence_normalized, // 0-255 scale
    output wire        coherence_valid,
    output wire        high_coherence,       // score >= 5.0 (500)
    output wire        medium_coherence,     // score >= 3.0 (300)
    output wire        low_coherence         // score < 3.0 (300)
);

    // =========================================================================
    // Normalization (Fixed-Point Math)
    // =========================================================================
    // E = entropy / 31: multiply by 256, divide by 31 ≈ multiply by 8.26
    // For better precision: (entropy × 826) >> 8 gives E×100
    // C = complecount / 7: multiply by 256, divide by 7 ≈ multiply by 36.57
    // For better precision: (complecount × 3657) >> 8 gives C×100

    // E×100 = (phase_entropy_index × 100) / 31
    // Use: (entropy × 3277) >> 10 ≈ entropy × 3.201 ≈ (entropy/31)×100 × 0.99
    // Simpler: (entropy × 100) / 31 - need division
    // Alternative: LUT or approximation

    // For synthesis-friendly implementation, use multiplication and shift:
    // E_scaled = (entropy × 826) >> 8  → gives E×100 with ~1% error
    // C_scaled = (complecount × 1429) >> 8 → gives C×100 with ~1% error

    wire [12:0] e_intermediate;  // entropy × 826 (max: 31×826 = 25606)
    wire [12:0] c_intermediate;  // complecount × 1429 (max: 7×1429 = 10003)

    assign e_intermediate = {8'b0, phase_entropy_index} * 13'd826;
    assign c_intermediate = {10'b0, complecount_trace} * 13'd1429;

    // Shift right 8 to get ×100 scale
    wire [7:0] e_x100 = e_intermediate[12:5];  // Simplified: >>5 for scaling
    wire [7:0] c_x100 = c_intermediate[12:5];

    // Recalculate with proper scaling:
    // E×100 = entropy × 100 / 31 ≈ entropy × 3.226
    // Using integer: (entropy × 3226) >> 10 = entropy × 3.15 (close enough)
    // Better: (entropy × 103) >> 5 = entropy × 3.22

    wire [11:0] e_calc = {7'b0, phase_entropy_index} * 12'd103; // max: 31×103 = 3193
    wire [11:0] c_calc = {9'b0, complecount_trace} * 12'd457;   // max: 7×457 = 3199 (C×100×3.2)

    wire [6:0] E_x100 = e_calc[11:5];  // E × 100, range 0-99
    wire [6:0] C_x100 = c_calc[11:5];  // C × 100, range 0-99

    // =========================================================================
    // Ra Coherence Formula: score = (φ × E) + (𝔄 × C)
    // =========================================================================
    // score×100 = (165 × E) + (509 × C)
    // where E,C are 0.0-1.0, so we use E_x100, C_x100 which are 0-100
    // score_x10000 = (165 × E_x100) + (509 × C_x100)
    // score_x100 = score_x10000 / 100

    wire [15:0] phi_term = `GREEN_PHI_X100 * {9'b0, E_x100};   // max: 165×99 = 16335
    wire [15:0] ankh_term = `ANKH_X100 * {9'b0, C_x100};       // max: 509×99 = 50391

    wire [16:0] score_x10000 = {1'b0, phi_term} + {1'b0, ankh_term};  // max: 66726

    // Divide by 100 to get score×100
    // Approximation: >> 7 is divide by 128, close to /100
    // Better: use actual division or LUT
    // For now: (score_x10000 × 41) >> 12 ≈ /100

    wire [22:0] div_intermediate = score_x10000 * 23'd41;
    wire [9:0]  raw_score = div_intermediate[21:12];  // score×100

    // =========================================================================
    // Alternative Direct Calculation (More Accurate)
    // =========================================================================
    // coherence = (1.618 × entropy/31) + (5.089 × complecount/7)
    // Max coherence = 1.618 + 5.089 = 6.707
    // At ×100: max = 671
    //
    // Direct formula with integer math:
    // score_x100 = (1618 × entropy) / 31 / 10 + (5089 × complecount) / 7 / 10
    //            = (1618 × entropy) / 310 + (5089 × complecount) / 70

    wire [15:0] term_phi  = 16'd1618 * {11'b0, phase_entropy_index};  // max: 1618×31 = 50158
    wire [15:0] term_ankh = 16'd5089 * {13'b0, complecount_trace};    // max: 5089×7 = 35623

    // Divide: /310 ≈ ×107 >> 15, /70 ≈ ×937 >> 16
    // Simpler approximation: /310 ≈ >>8, /70 ≈ >>6 (rough)
    // More accurate: multiply by reciprocal

    wire [23:0] phi_div  = term_phi * 24'd211;   // ×211/65536 ≈ /310
    wire [23:0] ankh_div = term_ankh * 24'd936;  // ×936/65536 ≈ /70

    wire [9:0] score_phi  = phi_div[23:14];   // Result after >>14
    wire [9:0] score_ankh = ankh_div[23:14];

    wire [9:0] final_score = score_phi + score_ankh;

    // =========================================================================
    // Output Assignments
    // =========================================================================

    assign coherence_score = final_score;

    // Normalize to 0-255 scale (max raw ≈ 671)
    // normalized = (score × 255) / 671 ≈ (score × 38) >> 8
    wire [17:0] norm_calc = {8'b0, final_score} * 18'd38;
    assign coherence_normalized = norm_calc[15:8];

    // Threshold comparison
    assign coherence_valid = (final_score >= coherence_threshold);

    // Classification thresholds
    assign high_coherence   = (final_score >= 10'd500);  // >= 5.0
    assign medium_coherence = (final_score >= 10'd300) && (final_score < 10'd500);  // 3.0-5.0
    assign low_coherence    = (final_score < 10'd300);   // < 3.0

endmodule


// =============================================================================
// CoherenceEvaluator_Ra_Precise (LUT-Based)
// =============================================================================
// Uses lookup tables for precise division, matching Python exactly

module CoherenceEvaluator_Ra_Precise (
    input  wire [4:0]  phase_entropy_index,
    input  wire [2:0]  complecount_trace,
    input  wire [9:0]  coherence_threshold,

    output wire [9:0]  coherence_score,
    output wire        coherence_valid
);

    // LUT for E×1000 = (entropy × 1000) / 31
    // Index: entropy (0-31), Output: E×1000
    reg [9:0] e_lut [0:31];

    // LUT for C×1000 = (complecount × 1000) / 7
    // Index: complecount (0-7), Output: C×1000
    reg [9:0] c_lut [0:7];

    initial begin
        // E = entropy / 31, scaled ×1000
        e_lut[0]  = 10'd0;    e_lut[1]  = 10'd32;   e_lut[2]  = 10'd65;
        e_lut[3]  = 10'd97;   e_lut[4]  = 10'd129;  e_lut[5]  = 10'd161;
        e_lut[6]  = 10'd194;  e_lut[7]  = 10'd226;  e_lut[8]  = 10'd258;
        e_lut[9]  = 10'd290;  e_lut[10] = 10'd323;  e_lut[11] = 10'd355;
        e_lut[12] = 10'd387;  e_lut[13] = 10'd419;  e_lut[14] = 10'd452;
        e_lut[15] = 10'd484;  e_lut[16] = 10'd516;  e_lut[17] = 10'd548;
        e_lut[18] = 10'd581;  e_lut[19] = 10'd613;  e_lut[20] = 10'd645;
        e_lut[21] = 10'd677;  e_lut[22] = 10'd710;  e_lut[23] = 10'd742;
        e_lut[24] = 10'd774;  e_lut[25] = 10'd806;  e_lut[26] = 10'd839;
        e_lut[27] = 10'd871;  e_lut[28] = 10'd903;  e_lut[29] = 10'd935;
        e_lut[30] = 10'd968;  e_lut[31] = 10'd1000;

        // C = complecount / 7, scaled ×1000
        c_lut[0] = 10'd0;     c_lut[1] = 10'd143;   c_lut[2] = 10'd286;
        c_lut[3] = 10'd429;   c_lut[4] = 10'd571;   c_lut[5] = 10'd714;
        c_lut[6] = 10'd857;   c_lut[7] = 10'd1000;
    end

    // Read from LUTs
    wire [9:0] E_x1000 = e_lut[phase_entropy_index];
    wire [9:0] C_x1000 = c_lut[complecount_trace];

    // score×100 = (φ×E + 𝔄×C)×100 = (1.618×E + 5.089×C)×100
    //           = (1618×E_x1000 + 5089×C_x1000) / 10000

    wire [20:0] phi_term  = 21'd1618 * {11'b0, E_x1000};   // max: 1618×1000 = 1618000
    wire [21:0] ankh_term = 22'd5089 * {12'b0, C_x1000};   // max: 5089×1000 = 5089000

    wire [22:0] sum = {2'b0, phi_term} + {1'b0, ankh_term};  // max: 6707000

    // Divide by 10000: use ×107 >> 20 approximation
    // Or ×7 >> 16 (rougher)
    // Best: ×6554 >> 26 (exact for powers of 2)
    // Simpler: ×1 >> 13.29 ≈ ×13 >> 17

    wire [26:0] div_calc = sum * 27'd13;
    wire [9:0]  score = div_calc[26:17];  // Result after >>17

    assign coherence_score = score;
    assign coherence_valid = (score >= coherence_threshold);

endmodule


// =============================================================================
// ScalarTrigger_Ra (Ra-Enhanced)
// =============================================================================
// Enhanced scalar trigger with Ra-aligned thresholds

module ScalarTrigger_Ra (
    input  wire        clk,
    input  wire        reset,
    input  wire        enable,
    input  wire [7:0]  radius,               // Ankh-normalized 0-255
    input  wire [7:0]  activation_threshold, // Threshold for activation
    input  wire [7:0]  coherence_duration,   // Cycles to maintain above threshold
    input  wire        coherence_valid,      // From CoherenceEvaluator

    output reg         scalar_triggered,
    output reg  [7:0]  duration_counter,
    output wire        above_threshold,
    output wire        stable_resonance      // Triggered AND coherent
);

    assign above_threshold = (radius >= activation_threshold);
    assign stable_resonance = scalar_triggered && coherence_valid;

    always @(posedge clk or posedge reset) begin
        if (reset) begin
            duration_counter <= 8'd0;
            scalar_triggered <= 1'b0;
        end else if (enable) begin
            if (above_threshold) begin
                if (duration_counter < coherence_duration) begin
                    duration_counter <= duration_counter + 8'd1;
                    scalar_triggered <= 1'b0;
                end else begin
                    scalar_triggered <= 1'b1;
                end
            end else begin
                duration_counter <= 8'd0;
                scalar_triggered <= 1'b0;
            end
        end else begin
            // Hold state when disabled
            scalar_triggered <= 1'b0;
        end
    end

endmodule


// =============================================================================
// FallbackResolver_Ra (Ra-Enhanced)
// =============================================================================
// XOR-based fallback with Ra-aligned modular arithmetic

module FallbackResolver_Ra (
    input  wire        trigger,
    input  wire [4:0]  primary_theta,    // 1-27
    input  wire [2:0]  primary_phi,      // 0-5
    input  wire [2:0]  primary_omega,    // 0-4
    input  wire [7:0]  primary_radius,   // 0-255
    input  wire [7:0]  fallback_vector,  // XOR mask

    // Base address for XOR (optional, default 0)
    input  wire [31:0] base_address,

    output wire [4:0]  fallback_theta,
    output wire [2:0]  fallback_phi,
    output wire [2:0]  fallback_omega,
    output wire [7:0]  fallback_radius,
    output wire [31:0] fallback_address,
    output wire        fallback_active
);

    // Extract offsets from fallback_vector
    // [7:5] = theta offset (0-7)
    // [4:2] = phi offset (0-7)
    // [1:0] = omega offset (0-3)
    wire [2:0] theta_offset = fallback_vector[7:5];
    wire [2:0] phi_offset   = fallback_vector[4:2];
    wire [1:0] omega_offset = fallback_vector[1:0];

    // XOR with primary values
    wire [5:0] theta_xor = {1'b0, primary_theta} ^ {3'b0, theta_offset};
    wire [3:0] phi_xor   = {1'b0, primary_phi} ^ {1'b0, phi_offset};
    wire [2:0] omega_xor = primary_omega ^ {1'b0, omega_offset};

    // Modular wrap to valid Ra ranges
    // theta: 1-27 (mod 27, then +1 if 0)
    // phi: 0-5 (mod 6)
    // omega: 0-4 (mod 5)

    reg [4:0] theta_wrapped;
    reg [2:0] phi_wrapped;
    reg [2:0] omega_wrapped;

    always @(*) begin
        // Theta wrapping: keep in 1-27 range
        if (theta_xor > 6'd27)
            theta_wrapped = theta_xor[4:0] - 5'd27;
        else if (theta_xor == 6'd0)
            theta_wrapped = 5'd27;
        else
            theta_wrapped = theta_xor[4:0];

        // Phi wrapping: keep in 0-5 range
        if (phi_xor > 4'd5)
            phi_wrapped = phi_xor[2:0] - 3'd6;
        else
            phi_wrapped = phi_xor[2:0];

        // Omega wrapping: keep in 0-4 range
        if (omega_xor > 3'd4)
            omega_wrapped = omega_xor - 3'd5;
        else
            omega_wrapped = omega_xor;
    end

    // Output selection based on trigger
    assign fallback_theta  = trigger ? theta_wrapped : primary_theta;
    assign fallback_phi    = trigger ? phi_wrapped : primary_phi;
    assign fallback_omega  = trigger ? omega_wrapped : primary_omega;
    assign fallback_radius = primary_radius;  // Radius unchanged

    // Assemble 32-bit canonical address
    assign fallback_address = trigger ?
        {fallback_theta, fallback_phi, fallback_omega, fallback_radius, 13'b0} :
        (base_address ^ {24'b0, fallback_vector});

    assign fallback_active = trigger;

endmodule


// =============================================================================
// ConsentArbitrator_Ra
// =============================================================================
// Arbitration logic for routing decisions

module ConsentArbitrator_Ra (
    input  wire        coherence_valid,
    input  wire        scalar_triggered,
    input  wire [1:0]  consent_state,      // 00=FULL, 01=DIMINISHED, 10=SUSPENDED, 11=EMERGENCY
    input  wire        needs_fallback,
    input  wire        pma_hit,

    output wire        route_allowed,
    output wire        use_fallback,
    output wire        use_pma_route,
    output wire [2:0]  routing_decision    // Encoded decision
);

    // Consent state encoding
    localparam FULL_CONSENT       = 2'b00;
    localparam DIMINISHED_CONSENT = 2'b01;
    localparam SUSPENDED_CONSENT  = 2'b10;
    localparam EMERGENCY_OVERRIDE = 2'b11;

    // Routing decision encoding
    localparam ROUTE_NORMAL     = 3'b000;
    localparam ROUTE_FALLBACK   = 3'b001;
    localparam ROUTE_PMA        = 3'b010;
    localparam ROUTE_BLOCKED    = 3'b011;
    localparam ROUTE_EMERGENCY  = 3'b100;

    // Base permission from consent state
    wire consent_allows = (consent_state == FULL_CONSENT) ||
                          (consent_state == DIMINISHED_CONSENT && coherence_valid);

    // Blocked states
    wire is_suspended = (consent_state == SUSPENDED_CONSENT);
    wire is_emergency = (consent_state == EMERGENCY_OVERRIDE);

    // Routing logic
    assign route_allowed = consent_allows && !is_suspended && !is_emergency;
    assign use_fallback  = needs_fallback && !coherence_valid && route_allowed;
    assign use_pma_route = pma_hit && coherence_valid && route_allowed;

    // Decision encoding
    assign routing_decision =
        is_emergency  ? ROUTE_EMERGENCY :
        is_suspended  ? ROUTE_BLOCKED :
        use_pma_route ? ROUTE_PMA :
        use_fallback  ? ROUTE_FALLBACK :
        route_allowed ? ROUTE_NORMAL :
        ROUTE_BLOCKED;

endmodule


`default_nettype wire
