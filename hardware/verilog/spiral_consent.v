// SPDX-License-Identifier: MIT
// SPIRAL Protocol – Consent Header & PMA HDL Modules
// Version: 1.0.0-RaCanonical
// 
// These modules implement the SPIRAL Consent Packet Header (18 bytes)
// and Phase Memory Anchor (PMA) storage, matching the Python reference
// implementation in consent_header.py and pma.py.
//
// Byte Layout (Consent Header):
//   Bytes 0-3:   RPP Canonical Address (32 bits)
//   Bytes 4-7:   Packet ID (32 bits)
//   Bytes 8-9:   Origin Avatar Reference (16 bits)
//   Byte 10:     Consent Fields (8 bits)
//   Byte 11:     Phase Entropy + Complecount (8 bits)
//   Byte 12:     Temporal + Payload Type (8 bits)
//   Byte 13:     Fallback Vector (8 bits)
//   Bytes 14-15: Coherence Window ID (16 bits)
//   Byte 16:     Target Phase Reference (8 bits)
//   Byte 17:     Header CRC (8 bits)

`default_nettype none

// =============================================================================
// Consent State Encoding (matches Python ConsentState)
// =============================================================================
// FULL_CONSENT      = 2'b00
// DIMINISHED_CONSENT = 2'b01
// SUSPENDED_CONSENT  = 2'b10
// EMERGENCY_OVERRIDE = 2'b11

// =============================================================================
// Consent Header Parser
// =============================================================================
// Extracts fields from 144-bit (18-byte) Consent Header
// Input is big-endian byte array: header[143:0] where header[143:136] = byte 0

module ConsentHeaderParser (
    input  wire [143:0] header_in,
    
    // RPP Address fields (bytes 0-3)
    output wire [4:0]  rpp_theta,
    output wire [2:0]  rpp_phi,
    output wire [2:0]  rpp_omega,
    output wire [7:0]  rpp_radius,
    output wire [12:0] rpp_reserved,
    
    // Packet identification (bytes 4-9)
    output wire [31:0] packet_id,
    output wire [15:0] origin_ref,
    
    // Consent fields (byte 10)
    output wire        consent_verbal,
    output wire [3:0]  consent_somatic,    // 0-15 -> 0.0-1.0
    output wire [1:0]  consent_ancestral,
    output wire        temporal_lock,
    
    // Entropy fields (byte 11)
    output wire [4:0]  phase_entropy_index,
    output wire [2:0]  complecount_trace,
    
    // Temporal/Payload (byte 12)
    output wire [3:0]  payload_type,
    
    // Routing (bytes 13-16)
    output wire [7:0]  fallback_vector,
    output wire [15:0] coherence_window_id,
    output wire [7:0]  target_phase_ref,
    
    // CRC (byte 17)
    output wire [7:0]  header_crc,
    
    // Derived consent state
    output wire [1:0]  consent_state,
    output wire        needs_fallback,
    output wire        has_pma_link
);

    // =========================================================================
    // Byte Extraction (Big-Endian)
    // header_in[143:136] = byte 0 (MSB)
    // header_in[7:0]     = byte 17 (LSB)
    // =========================================================================
    
    wire [7:0] byte0  = header_in[143:136];  // RPP address [31:24]
    wire [7:0] byte1  = header_in[135:128];  // RPP address [23:16]
    wire [7:0] byte2  = header_in[127:120];  // RPP address [15:8]
    wire [7:0] byte3  = header_in[119:112];  // RPP address [7:0]
    wire [7:0] byte4  = header_in[111:104];  // Packet ID [31:24]
    wire [7:0] byte5  = header_in[103:96];   // Packet ID [23:16]
    wire [7:0] byte6  = header_in[95:88];    // Packet ID [15:8]
    wire [7:0] byte7  = header_in[87:80];    // Packet ID [7:0]
    wire [7:0] byte8  = header_in[79:72];    // Origin Ref [15:8]
    wire [7:0] byte9  = header_in[71:64];    // Origin Ref [7:0]
    wire [7:0] byte10 = header_in[63:56];    // Consent fields
    wire [7:0] byte11 = header_in[55:48];    // Entropy + complecount
    wire [7:0] byte12 = header_in[47:40];    // Temporal + payload
    wire [7:0] byte13 = header_in[39:32];    // Fallback vector
    wire [7:0] byte14 = header_in[31:24];    // Window ID [15:8]
    wire [7:0] byte15 = header_in[23:16];    // Window ID [7:0]
    wire [7:0] byte16 = header_in[15:8];     // Target phase ref
    wire [7:0] byte17 = header_in[7:0];      // CRC
    
    // =========================================================================
    // RPP Address (bytes 0-3) - Ra-derived canonical format
    // [31:27] theta, [26:24] phi, [23:21] omega, [20:13] radius, [12:0] reserved
    // =========================================================================
    
    wire [31:0] rpp_address = {byte0, byte1, byte2, byte3};
    
    assign rpp_theta    = rpp_address[31:27];
    assign rpp_phi      = rpp_address[26:24];
    assign rpp_omega    = rpp_address[23:21];
    assign rpp_radius   = rpp_address[20:13];
    assign rpp_reserved = rpp_address[12:0];
    
    // =========================================================================
    // Packet ID (bytes 4-7)
    // =========================================================================
    
    assign packet_id = {byte4, byte5, byte6, byte7};
    
    // =========================================================================
    // Origin Avatar Reference (bytes 8-9)
    // =========================================================================
    
    assign origin_ref = {byte8, byte9};
    
    // =========================================================================
    // Consent Fields (byte 10)
    // [7]     consent_verbal
    // [6:3]   consent_somatic (0-15)
    // [2:1]   consent_ancestral
    // [0]     temporal_lock
    // =========================================================================
    
    assign consent_verbal    = byte10[7];
    assign consent_somatic   = byte10[6:3];
    assign consent_ancestral = byte10[2:1];
    assign temporal_lock     = byte10[0];
    
    // =========================================================================
    // Entropy Fields (byte 11)
    // [7:3]   phase_entropy_index (0-31)
    // [2:0]   complecount_trace (0-7)
    // =========================================================================
    
    assign phase_entropy_index = byte11[7:3];
    assign complecount_trace   = byte11[2:0];
    
    // =========================================================================
    // Temporal/Payload (byte 12)
    // [7:4]   reserved
    // [3:0]   payload_type
    // =========================================================================
    
    assign payload_type = byte12[3:0];
    
    // =========================================================================
    // Routing Fields (bytes 13-16)
    // =========================================================================
    
    assign fallback_vector      = byte13;
    assign coherence_window_id  = {byte14, byte15};
    assign target_phase_ref     = byte16;
    
    // =========================================================================
    // CRC (byte 17)
    // =========================================================================
    
    assign header_crc = byte17;
    
    // =========================================================================
    // Derived Consent State
    // 
    // Logic from Python consent_header.py:
    //   if consent_somatic < 0.2 (< 3 in 4-bit):
    //       state = SUSPENDED_CONSENT
    //   elif consent_somatic < 0.5 (< 8) and not consent_verbal:
    //       state = DIMINISHED_CONSENT
    //   else:
    //       state = FULL_CONSENT
    // =========================================================================
    
    wire somatic_below_02 = (consent_somatic < 4'd3);   // < 0.2
    wire somatic_below_05 = (consent_somatic < 4'd8);   // < 0.5
    
    assign consent_state = 
        somatic_below_02 ? 2'b10 :  // SUSPENDED_CONSENT
        (somatic_below_05 && !consent_verbal) ? 2'b01 :  // DIMINISHED_CONSENT
        2'b00;  // FULL_CONSENT
    
    // =========================================================================
    // Derived Flags
    // =========================================================================
    
    // Fallback trigger: phase_entropy_index > 25
    assign needs_fallback = (phase_entropy_index > 5'd25);
    
    // PMA linkage: coherence_window_id != 0
    assign has_pma_link = (coherence_window_id != 16'd0);

endmodule


// =============================================================================
// Consent Header Builder
// =============================================================================
// Assembles 144-bit header from individual fields

module ConsentHeaderBuilder (
    // RPP Address fields
    input  wire [4:0]  rpp_theta,
    input  wire [2:0]  rpp_phi,
    input  wire [2:0]  rpp_omega,
    input  wire [7:0]  rpp_radius,
    input  wire [12:0] rpp_reserved,
    
    // Packet identification
    input  wire [31:0] packet_id,
    input  wire [15:0] origin_ref,
    
    // Consent fields
    input  wire        consent_verbal,
    input  wire [3:0]  consent_somatic,
    input  wire [1:0]  consent_ancestral,
    input  wire        temporal_lock,
    
    // Entropy fields
    input  wire [4:0]  phase_entropy_index,
    input  wire [2:0]  complecount_trace,
    
    // Payload
    input  wire [3:0]  payload_type,
    
    // Routing
    input  wire [7:0]  fallback_vector,
    input  wire [15:0] coherence_window_id,
    input  wire [7:0]  target_phase_ref,
    
    // Output
    output wire [143:0] header_out,
    output wire [7:0]   computed_crc
);

    // Build RPP address
    wire [31:0] rpp_address = {rpp_theta, rpp_phi, rpp_omega, rpp_radius, rpp_reserved};
    
    // Build individual bytes
    wire [7:0] byte0  = rpp_address[31:24];
    wire [7:0] byte1  = rpp_address[23:16];
    wire [7:0] byte2  = rpp_address[15:8];
    wire [7:0] byte3  = rpp_address[7:0];
    wire [7:0] byte4  = packet_id[31:24];
    wire [7:0] byte5  = packet_id[23:16];
    wire [7:0] byte6  = packet_id[15:8];
    wire [7:0] byte7  = packet_id[7:0];
    wire [7:0] byte8  = origin_ref[15:8];
    wire [7:0] byte9  = origin_ref[7:0];
    wire [7:0] byte10 = {consent_verbal, consent_somatic, consent_ancestral, temporal_lock};
    wire [7:0] byte11 = {phase_entropy_index, complecount_trace};
    wire [7:0] byte12 = {4'b0000, payload_type};
    wire [7:0] byte13 = fallback_vector;
    wire [7:0] byte14 = coherence_window_id[15:8];
    wire [7:0] byte15 = coherence_window_id[7:0];
    wire [7:0] byte16 = target_phase_ref;
    
    // CRC-8 over bytes 0-16 (instantiate CRC module)
    wire [135:0] crc_input = {byte0, byte1, byte2, byte3, byte4, byte5, byte6, byte7,
                              byte8, byte9, byte10, byte11, byte12, byte13, byte14, 
                              byte15, byte16};
    
    CRC8_CCITT crc_calc (
        .data_in(crc_input),
        .crc_out(computed_crc)
    );
    
    // Assemble full header
    assign header_out = {byte0, byte1, byte2, byte3, byte4, byte5, byte6, byte7,
                         byte8, byte9, byte10, byte11, byte12, byte13, byte14, 
                         byte15, byte16, computed_crc};

endmodule


// =============================================================================
// CRC-8/CCITT Calculator
// =============================================================================
// Polynomial: 0x07 (x^8 + x^2 + x + 1)
// Computes CRC over 136 bits (17 bytes) of header data

module CRC8_CCITT (
    input  wire [135:0] data_in,
    output wire [7:0]   crc_out
);

    // Combinational CRC calculation
    // This uses a parallel implementation for single-cycle computation
    
    // Extract individual bytes
    wire [7:0] b0  = data_in[135:128];
    wire [7:0] b1  = data_in[127:120];
    wire [7:0] b2  = data_in[119:112];
    wire [7:0] b3  = data_in[111:104];
    wire [7:0] b4  = data_in[103:96];
    wire [7:0] b5  = data_in[95:88];
    wire [7:0] b6  = data_in[87:80];
    wire [7:0] b7  = data_in[79:72];
    wire [7:0] b8  = data_in[71:64];
    wire [7:0] b9  = data_in[63:56];
    wire [7:0] b10 = data_in[55:48];
    wire [7:0] b11 = data_in[47:40];
    wire [7:0] b12 = data_in[39:32];
    wire [7:0] b13 = data_in[31:24];
    wire [7:0] b14 = data_in[23:16];
    wire [7:0] b15 = data_in[15:8];
    wire [7:0] b16 = data_in[7:0];
    
    // CRC-8/CCITT computation using cascaded XORs
    // Each stage: crc = crc8_byte(crc ^ byte)
    
    wire [7:0] crc0, crc1, crc2, crc3, crc4, crc5, crc6, crc7;
    wire [7:0] crc8, crc9, crc10, crc11, crc12, crc13, crc14, crc15, crc16;
    
    CRC8_Byte stage0  (.crc_in(8'h00),   .byte_in(b0),  .crc_out(crc0));
    CRC8_Byte stage1  (.crc_in(crc0),    .byte_in(b1),  .crc_out(crc1));
    CRC8_Byte stage2  (.crc_in(crc1),    .byte_in(b2),  .crc_out(crc2));
    CRC8_Byte stage3  (.crc_in(crc2),    .byte_in(b3),  .crc_out(crc3));
    CRC8_Byte stage4  (.crc_in(crc3),    .byte_in(b4),  .crc_out(crc4));
    CRC8_Byte stage5  (.crc_in(crc4),    .byte_in(b5),  .crc_out(crc5));
    CRC8_Byte stage6  (.crc_in(crc5),    .byte_in(b6),  .crc_out(crc6));
    CRC8_Byte stage7  (.crc_in(crc6),    .byte_in(b7),  .crc_out(crc7));
    CRC8_Byte stage8  (.crc_in(crc7),    .byte_in(b8),  .crc_out(crc8));
    CRC8_Byte stage9  (.crc_in(crc8),    .byte_in(b9),  .crc_out(crc9));
    CRC8_Byte stage10 (.crc_in(crc9),    .byte_in(b10), .crc_out(crc10));
    CRC8_Byte stage11 (.crc_in(crc10),   .byte_in(b11), .crc_out(crc11));
    CRC8_Byte stage12 (.crc_in(crc11),   .byte_in(b12), .crc_out(crc12));
    CRC8_Byte stage13 (.crc_in(crc12),   .byte_in(b13), .crc_out(crc13));
    CRC8_Byte stage14 (.crc_in(crc13),   .byte_in(b14), .crc_out(crc14));
    CRC8_Byte stage15 (.crc_in(crc14),   .byte_in(b15), .crc_out(crc15));
    CRC8_Byte stage16 (.crc_in(crc15),   .byte_in(b16), .crc_out(crc16));
    
    assign crc_out = crc16;

endmodule


// =============================================================================
// CRC-8 Single Byte Calculator
// =============================================================================
// Computes CRC-8/CCITT for one byte using polynomial 0x07

module CRC8_Byte (
    input  wire [7:0] crc_in,
    input  wire [7:0] byte_in,
    output wire [7:0] crc_out
);

    wire [7:0] d = crc_in ^ byte_in;
    
    // Bit-by-bit CRC update (polynomial 0x07)
    // Each iteration: crc = (crc << 1) ^ (crc[7] ? 0x07 : 0x00)
    
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
// PMA Record Parser
// =============================================================================
// Extracts fields from 144-bit (18-byte) Phase Memory Anchor record
//
// Bit Layout (from PMA-SCHEMA-v1.md):
//   [143:132] window_id (12 bits)
//   [131:68]  timestamp (64 bits, nanoseconds)
//   [67:36]   phase_vector (32 bits, RPP address)
//   [35:34]   consent_state (2 bits)
//   [33:29]   complecount_score (5 bits)
//   [28:23]   coherence_score (6 bits)
//   [22:19]   payload_type (4 bits)
//   [18]      fallback_triggered (1 bit)
//   [17:10]   crc (8 bits)
//   [9:0]     reserved (10 bits)

module PMARecordParser (
    input  wire [143:0] pma_in,
    
    // Identification
    output wire [11:0] window_id,
    output wire [63:0] timestamp,
    
    // Phase vector (RPP address breakdown)
    output wire [31:0] phase_vector,
    output wire [4:0]  pv_theta,
    output wire [2:0]  pv_phi,
    output wire [2:0]  pv_omega,
    output wire [7:0]  pv_radius,
    
    // State
    output wire [1:0]  consent_state,
    output wire [4:0]  complecount_score,
    output wire [5:0]  coherence_score,
    output wire [3:0]  payload_type,
    output wire        fallback_triggered,
    
    // Integrity
    output wire [7:0]  record_crc
);

    // Direct bit extraction
    assign window_id          = pma_in[143:132];
    assign timestamp          = pma_in[131:68];
    assign phase_vector       = pma_in[67:36];
    assign consent_state      = pma_in[35:34];
    assign complecount_score  = pma_in[33:29];
    assign coherence_score    = pma_in[28:23];
    assign payload_type       = pma_in[22:19];
    assign fallback_triggered = pma_in[18];
    assign record_crc         = pma_in[17:10];
    // reserved = pma_in[9:0]
    
    // Phase vector breakdown
    assign pv_theta  = phase_vector[31:27];
    assign pv_phi    = phase_vector[26:24];
    assign pv_omega  = phase_vector[23:21];
    assign pv_radius = phase_vector[20:13];

endmodule


// =============================================================================
// PMA Record Builder
// =============================================================================
// Assembles 144-bit PMA record from individual fields

module PMARecordBuilder (
    // Identification
    input  wire [11:0] window_id,
    input  wire [63:0] timestamp,
    
    // Phase vector
    input  wire [31:0] phase_vector,
    
    // State
    input  wire [1:0]  consent_state,
    input  wire [4:0]  complecount_score,
    input  wire [5:0]  coherence_score,
    input  wire [3:0]  payload_type,
    input  wire        fallback_triggered,
    
    // Output
    output wire [143:0] pma_out,
    output wire [7:0]   computed_crc
);

    // Build record without CRC first
    wire [143:0] pma_no_crc = {
        window_id,           // [143:132] 12 bits
        timestamp,           // [131:68]  64 bits
        phase_vector,        // [67:36]   32 bits
        consent_state,       // [35:34]   2 bits
        complecount_score,   // [33:29]   5 bits
        coherence_score,     // [28:23]   6 bits
        payload_type,        // [22:19]   4 bits
        fallback_triggered,  // [18]      1 bit
        8'h00,               // [17:10]   CRC placeholder
        10'b0                // [9:0]     reserved
    };
    
    // Compute CRC over bytes 0-16 (bits 143:18)
    // This requires extracting as bytes
    wire [125:0] crc_data = pma_no_crc[143:18];  // 126 bits, but we need byte alignment
    
    // For simplicity, compute CRC over the relevant portion
    // PMA CRC covers window_id through fallback_triggered
    assign computed_crc = 8'h00;  // TODO: Implement PMA-specific CRC
    
    // Assemble final record
    assign pma_out = {
        window_id,
        timestamp,
        phase_vector,
        consent_state,
        complecount_score,
        coherence_score,
        payload_type,
        fallback_triggered,
        computed_crc,
        10'b0
    };

endmodule


// =============================================================================
// PMA Circular Buffer (Dual-Port RAM)
// =============================================================================
// Stores up to DEPTH PMA records with write_ptr wraparound

module PMACircularBuffer #(
    parameter DEPTH = 256,           // Number of records
    parameter ADDR_WIDTH = 8         // log2(DEPTH)
) (
    input  wire                   clk,
    input  wire                   rst_n,
    
    // Write port
    input  wire                   write_en,
    input  wire [143:0]           write_data,
    output reg  [ADDR_WIDTH-1:0]  write_ptr,
    
    // Read port (by address)
    input  wire [ADDR_WIDTH-1:0]  read_addr,
    output wire [143:0]           read_data,
    
    // Lookup port (by window_id)
    input  wire [11:0]            lookup_window_id,
    output wire [143:0]           lookup_data,
    output wire                   lookup_valid,
    
    // Status
    output reg  [ADDR_WIDTH:0]    count  // Number of valid records
);

    // Memory array
    reg [143:0] mem [0:DEPTH-1];
    
    // Window ID index (CAM-like lookup, simplified)
    reg [11:0] window_ids [0:DEPTH-1];
    reg        valid_flags [0:DEPTH-1];
    
    integer i;
    
    // Write logic
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            write_ptr <= 0;
            count <= 0;
            for (i = 0; i < DEPTH; i = i + 1) begin
                valid_flags[i] <= 1'b0;
            end
        end else if (write_en) begin
            mem[write_ptr] <= write_data;
            window_ids[write_ptr] <= write_data[143:132];  // Extract window_id
            valid_flags[write_ptr] <= 1'b1;
            
            // Advance write pointer (circular)
            write_ptr <= (write_ptr == DEPTH - 1) ? 0 : write_ptr + 1;
            
            // Update count
            if (count < DEPTH) begin
                count <= count + 1;
            end
        end
    end
    
    // Direct address read
    assign read_data = mem[read_addr];
    
    // Window ID lookup (linear search - could optimize with CAM)
    reg [143:0] lookup_result;
    reg         lookup_found;
    
    always @(*) begin
        lookup_found = 1'b0;
        lookup_result = 144'b0;
        for (i = 0; i < DEPTH; i = i + 1) begin
            if (valid_flags[i] && window_ids[i] == lookup_window_id) begin
                lookup_found = 1'b1;
                lookup_result = mem[i];
            end
        end
    end
    
    assign lookup_data = lookup_result;
    assign lookup_valid = lookup_found;

endmodule


// =============================================================================
// Consent Header Validator
// =============================================================================
// Validates header CRC and consent rules

module ConsentHeaderValidator (
    input  wire [143:0] header_in,
    input  wire         validate_en,
    
    output wire         crc_valid,
    output wire         consent_valid,  // Rule C1: low somatic requires complecount
    output wire         header_valid    // All checks pass
);

    // Parse header
    wire [7:0] stored_crc = header_in[7:0];
    wire [3:0] consent_somatic = header_in[62:59];  // byte10[6:3]
    wire [2:0] complecount_trace = header_in[50:48]; // byte11[2:0]
    
    // Compute expected CRC
    wire [135:0] crc_input = header_in[143:8];
    wire [7:0] computed_crc;
    
    CRC8_CCITT crc_check (
        .data_in(crc_input),
        .crc_out(computed_crc)
    );
    
    assign crc_valid = (computed_crc == stored_crc);
    
    // Rule C1: consent_somatic < 0.3 (< 5/16) requires complecount > 0
    wire somatic_low = (consent_somatic < 4'd5);
    assign consent_valid = !somatic_low || (complecount_trace > 3'd0);
    
    assign header_valid = crc_valid && consent_valid;

endmodule


// =============================================================================
// Top-Level Consent + PMA Controller
// =============================================================================

module SpiralConsentController #(
    parameter PMA_DEPTH = 256
) (
    input  wire         clk,
    input  wire         rst_n,
    
    // Header input
    input  wire [143:0] header_in,
    input  wire         header_valid_in,
    
    // Parsed outputs
    output wire [4:0]   theta_out,
    output wire [2:0]   phi_out,
    output wire [2:0]   omega_out,
    output wire [7:0]   radius_out,
    output wire [1:0]   consent_state_out,
    output wire         needs_fallback_out,
    
    // PMA outputs
    output wire [15:0]  pma_window_id,
    output wire         pma_linked,
    
    // Validation
    output wire         header_accepted,
    output wire         ready
);

    // Parse header
    wire [4:0] rpp_theta, phase_entropy;
    wire [2:0] rpp_phi, rpp_omega, complecount;
    wire [7:0] rpp_radius, fallback_vec;
    wire [1:0] consent_state;
    wire [15:0] coherence_wid;
    wire needs_fallback, has_pma;
    
    ConsentHeaderParser parser (
        .header_in(header_in),
        .rpp_theta(rpp_theta),
        .rpp_phi(rpp_phi),
        .rpp_omega(rpp_omega),
        .rpp_radius(rpp_radius),
        .phase_entropy_index(phase_entropy),
        .complecount_trace(complecount),
        .fallback_vector(fallback_vec),
        .coherence_window_id(coherence_wid),
        .consent_state(consent_state),
        .needs_fallback(needs_fallback),
        .has_pma_link(has_pma)
    );
    
    // Validate header
    wire crc_ok, consent_ok, valid;
    
    ConsentHeaderValidator validator (
        .header_in(header_in),
        .validate_en(header_valid_in),
        .crc_valid(crc_ok),
        .consent_valid(consent_ok),
        .header_valid(valid)
    );
    
    // Output assignments
    assign theta_out = rpp_theta;
    assign phi_out = rpp_phi;
    assign omega_out = rpp_omega;
    assign radius_out = rpp_radius;
    assign consent_state_out = consent_state;
    assign needs_fallback_out = needs_fallback;
    assign pma_window_id = coherence_wid;
    assign pma_linked = has_pma;
    assign header_accepted = valid && header_valid_in;
    assign ready = 1'b1;

endmodule

`default_nettype wire
