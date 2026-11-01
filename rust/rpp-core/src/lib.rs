//! RPP address types and deterministic resolver and overlay policy models.
//!
//! This library operates on caller-provided values. It does not open transports,
//! perform I/O, create threads, obtain randomness, implement cryptography, or
//! provision identities, membership, credentials, or consent.
//!
//! The overlay and scenario modules model policy; they do not implement tunnels.

#![forbid(unsafe_code)]
#![cfg_attr(not(feature = "std"), no_std)]

#[cfg(feature = "alloc")]
extern crate alloc;

pub mod canonical;
pub mod mobius32;
#[cfg(feature = "alloc")]
pub mod overlay;
#[cfg(feature = "alloc")]
pub mod resolver;
#[cfg(feature = "alloc")]
pub mod scenarios;
