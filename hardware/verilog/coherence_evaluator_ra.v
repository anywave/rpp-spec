// =============================================================================
// SPIRAL Protocol - Ra-Derived Coherence Evaluator
// =============================================================================
// 
// Computes coherence score using Ra System harmonic constants:
//   GREEN_PHI (phi) = 1.618 -> scaled to 165 (x100)
//   ANKH (A)        = 5.089 -> scaled to 509 (x100)
//
// Formula:
//   E = phase_entropy_index / 31  (normalized 0.0 to 1.0)
//   C = complecount_trace / 7     (normalized 0.0 to 1.0)
//   coherence_score = (phi * E) + (A * C)
//
// In fixed-point (x100 scale):
//   score = (165 * E / 31) + (509 * C / 7)
//   Maximum score = 165 + 509 = 674
//
// Threshold examples (scaled x100):
//   4.2 -> 420
//   5.1 -> 510
//   6.0 -> 600
//
// =============================================================================

`default_nettype none
`timescale 1ns / 1ps

module CoherenceEvaluatorRa (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        enable,
    
    // Inputs from header parser
    input  wire [4:0]  phase_entropy_index,  // 0-31
    input  wire [2:0]  complecount_trace,    // 0-7
    
    // Threshold (scaled x100)
    input  wire [9:0]  threshold,            // 0-1023, typical 420-600
    
    // Outputs
    output reg  [9:0]  coherence_score,      // 0-674 (scaled x100)
    output reg         coherence_valid,
    output reg         completion_flag,      // HIGH when complecount == 7 (full completion)

    // Debug outputs
    output reg  [7:0]  entropy_contribution,    // 0-165
    output reg  [8:0]  complecount_contribution // 0-509
);

    // Ra System Constants (scaled x100)
    localparam [7:0]  GREEN_PHI_SCALED = 8'd165;  // 1.65 x 100
    localparam [8:0]  ANKH_SCALED = 9'd509;       // 5.09 x 100
    
    // Normalization divisors
    localparam [4:0]  ENTROPY_MAX = 5'd31;
    localparam [2:0]  COMPLECOUNT_MAX = 3'd7;
    
    // Intermediate calculation wires
    wire [12:0] phi_times_E;      // 165 * 31 = 5115 max (13 bits)
    wire [11:0] ankh_times_C;     // 509 * 7 = 3563 max (12 bits)
    
    wire [7:0]  entropy_term;     // phi_times_E / 31, max 165
    wire [8:0]  complecount_term; // ankh_times_C / 7, max 509
    
    wire [9:0]  total_score;      // entropy_term + complecount_term, max 674
    
    // Multiply phase_entropy_index by GREEN_PHI
    assign phi_times_E = GREEN_PHI_SCALED * phase_entropy_index;
    
    // Multiply complecount_trace by ANKH
    assign ankh_times_C = ANKH_SCALED * complecount_trace;
    
    // Divide by normalization factors
    // entropy_contribution = (165 * E) / 31
    assign entropy_term = phi_times_E / ENTROPY_MAX;
    
    // complecount_contribution = (509 * C) / 7
    assign complecount_term = ankh_times_C / COMPLECOUNT_MAX;
    
    // Total coherence score
    assign total_score = {2'b00, entropy_term} + {1'b0, complecount_term};
    
    // Registered outputs
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            coherence_score <= 10'd0;
            coherence_valid <= 1'b0;
            completion_flag <= 1'b0;
            entropy_contribution <= 8'd0;
            complecount_contribution <= 9'd0;
        end else if (enable) begin
            coherence_score <= total_score;
            coherence_valid <= (total_score >= threshold);
            completion_flag <= (complecount_trace == 3'd7);  // Full completion when C=7
            entropy_contribution <= entropy_term;
            complecount_contribution <= complecount_term;
        end
    end

endmodule


// =============================================================================
// Scalar Trigger
// =============================================================================
// Triggers when coherence remains above threshold for N consecutive cycles

module ScalarTriggerRa (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        enable,
    
    // Coherence input
    input  wire [9:0]  coherence_score,
    input  wire [9:0]  activation_threshold,
    
    // Duration requirement
    input  wire [3:0]  coherence_duration,  // 1-15 cycles
    
    // Outputs
    output reg         scalar_triggered,
    output reg  [3:0]  cycle_counter
);

    wire score_above_threshold = (coherence_score >= activation_threshold);
    
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            scalar_triggered <= 1'b0;
            cycle_counter <= 4'd0;
        end else if (enable) begin
            if (score_above_threshold) begin
                // Always increment counter while above threshold (saturate at max)
                if (cycle_counter < 4'd15) begin
                    cycle_counter <= cycle_counter + 4'd1;
                end

                // Trigger when counter has reached duration threshold
                if (cycle_counter >= coherence_duration) begin
                    scalar_triggered <= 1'b1;
                end
            end else begin
                // Reset on score drop
                cycle_counter <= 4'd0;
                scalar_triggered <= 1'b0;
            end
        end
    end

endmodule


// =============================================================================
// Scalar Trigger (KHAT Fixed Duration)
// =============================================================================
// KHAT = √10 ≈ 3.162 → scaled 316 → 316 mod 16 = 12 cycles
// Fixed 12-cycle duration for harmonic octave + triad alignment

module ScalarTriggerRa_Khat (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        enable,

    // Coherence input
    input  wire [9:0]  coherence_score,
    input  wire [9:0]  activation_threshold,

    // Outputs
    output reg         scalar_triggered,
    output reg  [3:0]  cycle_counter
);

    // KHAT-derived duration threshold (√10 → 316 mod 16 = 12)
    localparam [3:0] KHAT_DURATION = 4'd12;

    wire score_above_threshold = (coherence_score >= activation_threshold);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            scalar_triggered <= 1'b0;
            cycle_counter <= 4'd0;
        end else if (enable) begin
            if (score_above_threshold) begin
                // Increment counter while above threshold (saturate at 15)
                if (cycle_counter < 4'd15) begin
                    cycle_counter <= cycle_counter + 4'd1;
                end

                // Trigger when KHAT duration met
                if (cycle_counter >= KHAT_DURATION) begin
                    scalar_triggered <= 1'b1;
                end
            end else begin
                // Reset on score drop
                cycle_counter <= 4'd0;
                scalar_triggered <= 1'b0;
            end
        end
    end

endmodule


// =============================================================================
// Fallback Resolver
// =============================================================================
// Generates fallback address when coherence check fails

module FallbackResolverRa (
    input  wire        trigger_fallback,
    input  wire [31:0] base_address,
    input  wire [7:0]  fallback_vector,
    
    output wire [31:0] rpp_fallback_address
);

    // XOR-based fallback addressing
    assign rpp_fallback_address = trigger_fallback ? 
                                  (base_address ^ {24'b0, fallback_vector}) : 
                                  32'd0;

endmodule


// =============================================================================
// SPIRAL Coherence Integration Top Module
// =============================================================================

module SpiralCoherenceIntegration (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        enable,

    // Header inputs (from ConsentHeaderParser)
    input  wire [4:0]  phase_entropy_index,
    input  wire [2:0]  complecount_trace,
    input  wire [7:0]  fallback_vector,
    input  wire [1:0]  consent_state,
    input  wire [31:0] base_address,

    // Configuration
    input  wire [9:0]  coherence_threshold,    // Scaled x100 (e.g., 420)
    input  wire [9:0]  scalar_threshold,       // Activation threshold
    input  wire [3:0]  scalar_duration,        // Cycles required

    // ETF (Emergency Token Freeze)
    input  wire        etf_trigger,            // Emergency freeze signal
    output wire        etf_active,             // ETF currently active

    // Outputs
    output wire [9:0]  coherence_score,
    output wire        coherence_valid,
    output wire        completion_flag,      // HIGH when complecount == 7
    output wire        scalar_triggered,
    output wire [31:0] rpp_fallback_address,
    output wire        routing_allowed,
    output wire [1:0]  routing_decision  // 00=ROUTE, 01=DELAY, 10=FALLBACK, 11=BLOCK
);

    // Consent state encoding
    localparam [1:0] FULL_CONSENT      = 2'b00;
    localparam [1:0] DIMINISHED_CONSENT = 2'b01;
    localparam [1:0] SUSPENDED_CONSENT = 2'b10;
    localparam [1:0] EMERGENCY_OVERRIDE = 2'b11;
    
    // Coherence evaluator
    wire [7:0] entropy_contrib;
    wire [8:0] complecount_contrib;
    
    CoherenceEvaluatorRa coherence_eval (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .phase_entropy_index(phase_entropy_index),
        .complecount_trace(complecount_trace),
        .threshold(coherence_threshold),
        .coherence_score(coherence_score),
        .coherence_valid(coherence_valid),
        .completion_flag(completion_flag),
        .entropy_contribution(entropy_contrib),
        .complecount_contribution(complecount_contrib)
    );
    
    // Scalar trigger
    ScalarTriggerRa scalar_trig (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .coherence_score(coherence_score),
        .activation_threshold(scalar_threshold),
        .coherence_duration(scalar_duration),
        .scalar_triggered(scalar_triggered),
        .cycle_counter()  // Not connected
    );
    
    // Fallback resolver
    wire trigger_fallback = !coherence_valid;

    FallbackResolverRa fallback_res (
        .trigger_fallback(trigger_fallback),
        .base_address(base_address),
        .fallback_vector(fallback_vector),
        .rpp_fallback_address(rpp_fallback_address)
    );

    // ETF Controller (Emergency Token Freeze)
    wire [3:0] etf_counter;

    ETFController etf_ctrl (
        .clk(clk),
        .rst_n(rst_n),
        .etf_trigger(etf_trigger),
        .coherence_score(coherence_score),
        .etf_active(etf_active),
        .etf_counter(etf_counter)
    );

    // Routing decision logic
    // Order of Operations: ETF > ACSP > Shield > TCL > Execute
    wire consent_allows = (consent_state == FULL_CONSENT);
    wire consent_delays = (consent_state == DIMINISHED_CONSENT);
    wire consent_blocks = (consent_state == SUSPENDED_CONSENT) ||
                          (consent_state == EMERGENCY_OVERRIDE);

    assign routing_allowed = coherence_valid && consent_allows && !etf_active;

    // Routing decision encoding (ETF has highest priority)
    assign routing_decision = etf_active ? 2'b11 :            // BLOCK (ETF overrides all)
                              consent_blocks ? 2'b11 :        // BLOCK (SUSPENDED/EMERGENCY)
                              !coherence_valid ? 2'b10 :      // FALLBACK (low coherence)
                              consent_delays ? 2'b01 :        // DELAY (DIMINISHED)
                              2'b00;                          // ROUTE (all clear)

endmodule


// =============================================================================
// Consent State Deriver (Golden Ratio Thresholds)
// =============================================================================
// Derives consent_state from somatic_coherence using Ra-aligned thresholds
// Based on Golden Ratio bifurcation: φ ≈ 0.618, 1-φ ≈ 0.382, φ² ≈ 0.144

module ConsentStateDeriver (
    input  wire [3:0]  somatic_coherence,  // 4-bit field (0-15)
    input  wire        verbal_override,     // Can promote to FULL regardless of somatic
    output reg  [1:0]  consent_state
);

    // Ra-aligned consent thresholds (Golden Ratio bifurcation)
    localparam [3:0] SOMATIC_FULL_THRESHOLD = 4'd10;   // φ ≈ 0.618 → ceil(0.618×16)
    localparam [3:0] SOMATIC_DIM_MIN = 4'd6;           // 1-φ ≈ 0.382 → floor(0.382×16)
    // SUSPENDED: 0-5 (φ² boundary)

    // Consent state encoding
    localparam [1:0] FULL_CONSENT       = 2'b00;
    localparam [1:0] DIMINISHED_CONSENT = 2'b01;
    localparam [1:0] SUSPENDED_CONSENT  = 2'b10;

    always @(*) begin
        if (verbal_override)
            consent_state = FULL_CONSENT;
        else if (somatic_coherence >= SOMATIC_FULL_THRESHOLD)
            consent_state = FULL_CONSENT;
        else if (somatic_coherence >= SOMATIC_DIM_MIN)
            consent_state = DIMINISHED_CONSENT;
        else
            consent_state = SUSPENDED_CONSENT;
    end

endmodule


// =============================================================================
// ETF Controller (Emergency Token Freeze)
// =============================================================================
// ALPHA_INVERSE-derived constants: 137 mod 16 = 9 cycles, release at 559

module ETFController (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        etf_trigger,         // Emergency freeze signal
    input  wire [9:0]  coherence_score,
    output reg         etf_active,
    output reg  [3:0]  etf_counter
);

    // ALPHA_INVERSE-derived ETF constants (fine-structure constant inverse)
    localparam [3:0]  ETF_DURATION = 4'd9;           // 137 mod 16 = 9 cycles
    localparam [9:0]  ETF_RELEASE_THRESHOLD = 10'd559;  // 674 × (137/165)

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            etf_active <= 1'b0;
            etf_counter <= 4'd0;
        end else if (etf_trigger && !etf_active) begin
            // Enter ETF state
            etf_active <= 1'b1;
            etf_counter <= ETF_DURATION;
        end else if (etf_active) begin
            // ETF release conditions:
            // 1. Duration elapsed AND coherence above release threshold
            if (etf_counter > 4'd0) begin
                etf_counter <= etf_counter - 4'd1;
            end else if (coherence_score >= ETF_RELEASE_THRESHOLD) begin
                etf_active <= 1'b0;  // Mirror check passed - release
            end
            // Else: remain in ETF (coherence insufficient for release)
        end
    end

endmodule


`default_nettype wire
