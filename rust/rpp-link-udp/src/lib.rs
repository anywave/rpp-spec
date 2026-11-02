//! Real synchronous UDP, restricted to loopback or tailnet address ranges.
//! Range checks do not prove encryption, membership, consent or peer identity.
#![forbid(unsafe_code)]
mod config;
mod measure;
mod socket;
pub use config::{Config, Error};
pub use socket::{Counters, Received, UdpAdapter, MAX_DATAGRAM_LEN, MAX_DATA_LEN, VERSION};
#[cfg(feature = "fleet-demo")]
pub mod demo;
