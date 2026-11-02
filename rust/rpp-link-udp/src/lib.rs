//! Real UDP restricted to loopback/tailnet, plus loopback-only TCP fallback.
//! Range checks do not prove encryption, membership, consent or peer identity.
#![forbid(unsafe_code)]
mod config;
pub mod framed;
mod measure;
mod socket;
mod tcp;
pub use config::{Config, Error};
pub use socket::{Counters, Received, UdpAdapter, MAX_DATAGRAM_LEN, MAX_DATA_LEN, VERSION};
pub use tcp::TcpAdapter;
#[cfg(feature = "fleet-demo")]
pub mod demo;
