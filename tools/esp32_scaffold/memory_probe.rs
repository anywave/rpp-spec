//! Safe compile-only object-layout probe; these constants are not stack frames.
#![no_std]
#![forbid(unsafe_code)]

use core::mem::size_of;

macro_rules! layout {
    ($name:ident, $kind:ty) => {
        pub static $name: [u8; size_of::<$kind>()] = [0; size_of::<$kind>()];
    };
}
layout!(BILLBOARD_FIELDS, rpp_billboard::Fields<'static>);
layout!(BILLBOARD_VIEW, rpp_billboard::VerifiedBillboard<'static>);
layout!(BILLBOARD_SCRATCH, [u8; rpp_billboard::MAX_FRAME_LEN]);
layout!(FRAGMENTER, rpp_frag::Fragmenter<'static, 112>);
layout!(REASSEMBLER_4_112, rpp_frag::Reassembler<4, 112>);
layout!(SELECTOR, rpp_steer::Selector);
layout!(CANDIDATE, rpp_steer::Candidate);
layout!(CANDIDATES_16, [rpp_steer::Candidate; 16]);

// Independent caller reservation profiles, not compiler stack-frame bounds.
#[cfg(target_arch = "riscv32")]
mod reservations {
    use super::*;
    const BILLBOARD_USED: usize = 2 * rpp_billboard::MAX_FRAME_LEN;
    const FRAG_USED: usize = size_of::<rpp_frag::Reassembler<4, 112>>()
        + size_of::<rpp_frag::Fragmenter<'static, 112>>()
        + 20;
    const STEER_USED: usize =
        size_of::<rpp_steer::Selector>() + 16 * size_of::<rpp_steer::Candidate>();
    const _: () = assert!(BILLBOARD_USED <= 2035, "RPP_BILLBOARD_BUDGET_EXCEEDED");
    const _: () = assert!(FRAG_USED <= 1232, "RPP_FRAG_BUDGET_EXCEEDED");
    const _: () = assert!(STEER_USED <= 942, "RPP_STEER_BUDGET_EXCEEDED");
}
