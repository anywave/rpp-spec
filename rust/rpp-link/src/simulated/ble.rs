//! In-memory MTU-20 notifications only; no BLE stack, radio or measurements.
use crate::{DataOutcome, LinkAdapter, LinkKind, LinkReading};
use rpp_control::{NodeId, VerifiedControlFrame, Verifier};
use rpp_frag::{Fragmenter, Reassembler};
use std::vec::Vec;
pub const MTU: usize = 20;
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Error {
    DataUnsupported,
    TagExhausted,
    Fragment(rpp_frag::Error),
}
pub struct Ble<V: Verifier> {
    verifier: V,
    recipient: NodeId,
    peer: NodeId,
    receiver: Reassembler<1>,
    tick: u64,
    tag: Option<u16>,
    fragments: Vec<Vec<u8>>,
    received: Option<VerifiedControlFrame>,
}
impl<V: Verifier> Ble<V> {
    pub fn new(peer: NodeId, recipient: NodeId, verifier: V) -> Self {
        Self {
            verifier,
            recipient,
            peer,
            receiver: Reassembler::new(10).unwrap(),
            tick: 0,
            tag: Some(0),
            fragments: Vec::new(),
            received: None,
        }
    }
    pub fn fragments(&self) -> &[Vec<u8>] {
        &self.fragments
    }
    pub fn received(&self) -> Option<&VerifiedControlFrame> {
        self.received.as_ref()
    }
}
impl<V: Verifier> LinkAdapter for Ble<V> {
    type Error = Error;
    fn kind(&self) -> LinkKind {
        LinkKind::Ble
    }
    fn read(&mut self, tick: u64) -> Result<LinkReading, Error> {
        if tick < self.tick {
            return Err(Error::Fragment(rpp_frag::Error::ClockRollback));
        }
        self.tick = tick;
        Ok(LinkReading {
            latency_ms: 1,
            loss_ppm: 0,
            jitter_ms: 0,
            available: true,
            observed: tick,
        })
    }
    fn send_verified_control_frame(&mut self, frame: &VerifiedControlFrame) -> Result<(), Error> {
        let tag = self.tag.ok_or(Error::TagExhausted)?;
        self.tag = tag.checked_add(1);
        let bytes = frame.encode();
        let mut writer = Fragmenter::<112>::new(&bytes, tag, MTU).map_err(Error::Fragment)?;
        let mut output = [0; MTU];
        while let Some(n) = writer.write_next(&mut output).map_err(Error::Fragment)? {
            self.fragments.push(output[..n].to_vec());
            if let Some(frame) = self
                .receiver
                .push(
                    self.peer,
                    &output[..n],
                    self.tick,
                    &self.recipient,
                    &self.verifier,
                )
                .map_err(Error::Fragment)?
            {
                self.received = Some(frame);
            }
        }
        Ok(())
    }
    fn send_data(&mut self, _: &[u8]) -> Result<DataOutcome, Error> {
        Err(Error::DataUnsupported)
    }
}
