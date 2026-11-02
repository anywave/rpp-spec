//! Experimental ranking below caller eligibility, not consent or tunnel policy.
//! Inputs are caller measurements. This crate sends nothing and grants no retry.
#![no_std]
#![forbid(unsafe_code)]

#[cfg(feature = "std")]
extern crate std;

use rpp_link::{LinkKind, LinkReading};
mod ranking;
pub use ranking::best_link;

/// Local work bound, not a published protocol constant.
pub const MAX_LINKS: usize = 16;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum MessageClass {
    Control,
    Bulk,
    Billboard,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq, Ord, PartialOrd)]
pub enum CostClass {
    Unmetered,
    Metered,
    ControlOnly,
}
/// Already eligible under the caller's trust/consent policy. MTU is the maximum
/// ONE atomic underlay payload; throughput is independently measured kilobits/s.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct Candidate {
    pub id: u32,
    pub kind: LinkKind,
    pub reading: LinkReading,
    pub mtu: u16,
    pub throughput_kbps: u64,
    pub cost: CostClass,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Error {
    TooManyLinks,
    DuplicateId,
    InvalidReading,
    InvalidMtu,
    EmptyPayload,
    InvalidMargin,
    ClockRollback,
}
