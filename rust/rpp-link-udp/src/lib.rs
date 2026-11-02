//! Validated UDP configuration and bounded probe measurements.
#![forbid(unsafe_code)]
mod config;
mod measure;
pub use config::{Config, Error};
