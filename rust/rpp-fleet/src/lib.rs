//! Proposed fleet address bindings and endpoint records over existing RPP policy.
//!
//! Identity bytes and transport-verification results come from the host. This
//! library performs no I/O, networking, cryptography, enrollment or consent grant.
//! Explicit address assignment is an informative proposal, not a specification
//! derivation rule or a cryptographic binding between an identity and an address.

#![no_std]
#![forbid(unsafe_code)]

#[cfg(feature = "alloc")]
extern crate alloc;

#[cfg(feature = "alloc")]
pub mod endpoint;
pub mod identity;
#[cfg(feature = "alloc")]
pub mod registry;
#[cfg(feature = "alloc")]
pub mod resolver;
