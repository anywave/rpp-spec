#![cfg(feature = "sim")]
use rpp_control::{decode, ControlFrame, ControlKind, NodeId, Signature, Verifier, HEADER_LEN};
use rpp_link::{
    dispatch,
    simulated::ble::{Ble, Error, MTU},
    DispatchError, DispatchOutcome, Outbound, TrafficPath,
};
struct Check(bool);
impl Verifier for Check {
    fn verify(&self, _: &NodeId, _: &[u8; HEADER_LEN], _: &Signature) -> bool {
        self.0
    }
}
fn frame() -> rpp_control::VerifiedControlFrame {
    let wire = ControlFrame::new(ControlKind::Stop, 9, [1; 16], [2; 16], [3; 64]).encode();
    decode(&wire, &[2; 16], &Check(true)).unwrap()
}
#[test]
fn simulated_ble_fragments_control_at_mtu20_and_decodes_again() {
    // Mutations BLE-bypasses-fragmentation/verifier: one full frame cannot be a notification.
    let mut ble = Ble::new([1; 16], [2; 16], Check(true));
    assert_eq!(
        dispatch(&mut ble, TrafficPath::Control, Outbound::Control(&frame())),
        Ok(DispatchOutcome::Control)
    );
    assert_eq!(ble.fragments().len(), 8);
    assert!(ble.fragments().iter().all(|f| f.len() <= MTU));
    assert_eq!(ble.received().unwrap().encode(), frame().encode());
    let mut denied = Ble::new([1; 16], [2; 16], Check(false));
    assert_eq!(
        dispatch(
            &mut denied,
            TrafficPath::Control,
            Outbound::Control(&frame())
        ),
        Err(DispatchError::Adapter(Error::Fragment(
            rpp_frag::Error::Decode(rpp_control::DecodeError::InvalidSignature)
        )))
    );
    assert!(denied.received().is_none());
}
#[test]
fn data_over_simulated_ble_is_refused_without_fragments() {
    // Mutation data-over-BLE: neither data intent nor control disguised as data may send.
    let mut ble = Ble::new([1; 16], [2; 16], Check(true));
    assert_eq!(
        dispatch(&mut ble, TrafficPath::Data, Outbound::Data(b"data")),
        Err(DispatchError::Adapter(Error::DataUnsupported))
    );
    assert_eq!(
        dispatch(&mut ble, TrafficPath::Data, Outbound::Control(&frame())),
        Err(DispatchError::WrongTrafficClass)
    );
    assert!(ble.fragments().is_empty());
    assert!(ble.received().is_none());
    let link = rpp_core::overlay::Link::new("bt", "A", "B", rpp_core::overlay::Underlay::Bluetooth);
    let mut scenario = rpp_link::simulated::SimulatedAdapter::from_link(link);
    assert_eq!(
        dispatch(&mut scenario, TrafficPath::Data, Outbound::Data(b"data")),
        Err(DispatchError::Adapter(
            rpp_link::simulated::AdapterError::Ble(Error::DataUnsupported)
        ))
    );
    assert!(scenario.sent().is_empty());
}
