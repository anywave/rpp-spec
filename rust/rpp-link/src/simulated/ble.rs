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

#[cfg(test)]
mod tests {
    use super::*;
    use rpp_control::{decode, ControlFrame, ControlKind, Signature, HEADER_LEN};
    struct Check;
    impl Verifier for Check {
        fn verify(&self, _: &NodeId, _: &[u8; HEADER_LEN], signature: &Signature) -> bool {
            *signature == [3; 64]
        }
    }
    /// Mutation: hide ExpiredKey, consume the new fragment, or claim delivery on expiry.
    #[test]
    fn expired_old_peer_key_propagates_without_delivering_new_control() {
        let peer = [1; 16];
        let target = [2; 16];
        let bytes = ControlFrame::new(ControlKind::Pause, 8, peer, target, [3; 64]).encode();
        let verified = decode(&bytes, &target, &Check).unwrap();
        let mut ble = Ble::new(peer, target, Check);
        let mut writer = Fragmenter::<112>::new(&bytes, 7, MTU).unwrap();
        let mut first = [0; MTU];
        let n = writer.write_next(&mut first).unwrap().unwrap();
        assert!(ble
            .receiver
            .push(peer, &first[..n], 0, &target, &Check)
            .unwrap()
            .is_none());
        ble.tag = Some(8);
        ble.read(10).unwrap();
        assert_eq!(
            ble.send_verified_control_frame(&verified),
            Err(Error::Fragment(rpp_frag::Error::ExpiredKey {
                peer,
                tag: 7
            }))
        );
        assert_eq!(ble.receiver.retained_slots(), 0);
        assert_eq!(ble.received(), None);
    }
}
