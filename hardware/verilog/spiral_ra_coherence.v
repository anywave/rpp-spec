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
// Exact shared policy score for the finite header input domain
// =============================================================================
// Matches Python's separately truncated terms:
//   floor(GREEN_PHI_X100 * entropy / 31) + floor(ANKH_X100 * complecount / 7).
// Constant unsigned division avoids reciprocal approximation and product loss.
// Published constants and public wrapper ports remain unchanged.

module CoherenceScoreRaExact (
    input  wire [4:0] phase_entropy_index,
    input  wire [2:0] complecount_trace,
    output wire [9:0] score
);
    // Maximum products: 165*31=5115 (13 bits), 509*7=3563 (12 bits).
    wire [12:0] entropy_product = `GREEN_PHI_X100 * phase_entropy_index;
    wire [11:0] completion_product = `ANKH_X100 * complecount_trace;
    wire [7:0] entropy_term = entropy_product / 13'd31;
    wire [8:0] completion_term = completion_product / 12'd7;
    // Each division truncates before addition; the maximum sum is 674.
    assign score = {2'b0, entropy_term} + {1'b0, completion_term};
endmodule


// =============================================================================
// CoherenceEvaluator_Ra (public combinational binding)
// =============================================================================
// The historical reciprocal implementation is replaced by the exact policy.

module CoherenceEvaluator_Ra (
    input  wire [4:0] phase_entropy_index,
    input  wire [2:0] complecount_trace,
    input  wire [9:0] coherence_threshold,
    output wire [9:0] coherence_score,      // 0-674 policy points
    output wire [7:0] coherence_normalized,
    output wire       coherence_valid,
    output wire       high_coherence,
    output wire       medium_coherence,
    output wire       low_coherence
);
    wire [9:0] final_score;
    CoherenceScoreRaExact policy_score (
        .phase_entropy_index(phase_entropy_index),
        .complecount_trace(complecount_trace),
        .score(final_score)
    );
    assign coherence_score = final_score;

    // Existing normalization and output gate expressions are unchanged.
    wire [17:0] norm_calc = {8'b0, final_score} * 18'd38;
    assign coherence_normalized = norm_calc[15:8];
    assign coherence_valid = (final_score >= coherence_threshold);
    assign high_coherence   = (final_score >= 10'd500);
    assign medium_coherence = (final_score >= 10'd300) && (final_score < 10'd500);
    assign low_coherence    = (final_score < 10'd300);
endmodule


// =============================================================================
// CoherenceEvaluator_Ra_Precise (public compatibility binding)
// =============================================================================
// Retain the public module name; rounded normalized LUTs cannot reproduce the
// policy's per-term floor at every input, so share the exact integer score path.

module CoherenceEvaluator_Ra_Precise (
    input  wire [4:0] phase_entropy_index,
    input  wire [2:0] complecount_trace,
    input  wire [9:0] coherence_threshold,
    output wire [9:0] coherence_score,
    output wire       coherence_valid
);
    wire [9:0] score;
    CoherenceScoreRaExact policy_score (
        .phase_entropy_index(phase_entropy_index),
        .complecount_trace(complecount_trace),
        .score(score)
    );
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
