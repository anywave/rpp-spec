//! RPP address types and deterministic resolver and overlay policy models.
//!
//! This library operates on caller-provided values. It does not open transports,
//! perform I/O, create threads, obtain randomness, implement cryptography, or
//! provision identities, membership, credentials, or consent.
//!
//! The overlay and scenario modules model policy; they do not implement tunnels.

#![forbid(unsafe_code)]

pub mod canonical;
pub mod mobius32;
pub mod overlay;
pub mod resolver;
pub mod scenarios;
