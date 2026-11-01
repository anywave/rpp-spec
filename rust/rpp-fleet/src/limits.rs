//! Local resource bounds for the proposed fleet profile, not RPP wire constants.
//!
//! Sixteen nodes with four endpoints each allow 12,288 bytes of URI payload at
//! the 192-byte limit. Allocator/container and policy metadata are additional;
//! applications still measure total heap and stack use on their actual board.

/// Maximum registered nodes in one fleet registry.
pub const MAX_NODES: usize = 16;
/// Maximum endpoint records owned by one registered node.
pub const MAX_ENDPOINTS_PER_NODE: usize = 4;
/// Maximum printable-ASCII URI bytes retained by an endpoint record.
pub const MAX_URI_LEN: usize = 192;
/// Internal diagnostic history; every control result still returns its meter row.
pub const MAX_RETAINED_METER_ROWS: usize = 16;
