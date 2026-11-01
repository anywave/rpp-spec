//! Heap-free, synchronous adapter hooks. No driver, radio, network or cryptography.
//!
//! Readings are supplied by a host; freshness, tunnel capability, membership,
//! consent and path independence remain overlay policy decisions. The typed
//! dispatcher enforces traffic class before calling an adapter. Opaque data is
//! already-classified application data, not a decoder for arbitrary wire bytes.

#![forbid(unsafe_code)]
#![no_std]

#[cfg(feature = "std")]
extern crate std;

use rpp_control::VerifiedControlFrame;

#[cfg(feature = "std")]
pub mod simulated;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum LinkKind {
    Lan,
    Wifi,
    Ble,
    Lora,
    Internet,
}

/// Fixed-size scalar readings: milliseconds, loss parts per million and host
/// logical observation ticks. No floating point, strings or heap allocation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct LinkReading {
    pub latency_ms: u64,
    pub loss_ppm: u32,
    pub jitter_ms: u64,
    pub available: bool,
    pub observed: u64,
}

impl LinkReading {
    pub fn valid(self) -> bool {
        self.loss_ppm <= 1_000_000
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DataOutcome {
    Sent,
    Failed { emitted_tokens: u64 },
}

/// Actual drivers are deliberately left to the host/platform. Control can enter
/// this interface only after rpp-control's verifier callback accepted the frame.
pub trait LinkAdapter {
    type Error;
    fn kind(&self) -> LinkKind;
    fn read(&mut self, tick: u64) -> Result<LinkReading, Self::Error>;
    fn send_verified_control_frame(
        &mut self,
        frame: &VerifiedControlFrame,
    ) -> Result<(), Self::Error>;
    fn send_data(&mut self, payload: &[u8]) -> Result<DataOutcome, Self::Error>;
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum TrafficPath {
    Data,
    Control,
}

#[derive(Clone, Copy, Debug)]
pub enum Outbound<'a> {
    Data(&'a [u8]),
    Control(&'a VerifiedControlFrame),
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DispatchOutcome {
    Data(DataOutcome),
    Control,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum DispatchError<E> {
    WrongTrafficClass,
    Adapter(E),
}

pub fn dispatch<A: LinkAdapter>(
    adapter: &mut A,
    path: TrafficPath,
    frame: Outbound<'_>,
) -> Result<DispatchOutcome, DispatchError<A::Error>> {
    // The class check precedes the adapter callback; no control is sent as data.
    if path == TrafficPath::Data && matches!(frame, Outbound::Control(_)) {
        return Err(DispatchError::WrongTrafficClass);
    }
    if path == TrafficPath::Control && matches!(frame, Outbound::Data(_)) {
        return Err(DispatchError::WrongTrafficClass);
    }
    match frame {
        Outbound::Data(payload) => adapter
            .send_data(payload)
            .map(DispatchOutcome::Data)
            .map_err(DispatchError::Adapter),
        Outbound::Control(frame) => adapter
            .send_verified_control_frame(frame)
            .map(|()| DispatchOutcome::Control)
            .map_err(DispatchError::Adapter),
    }
}
