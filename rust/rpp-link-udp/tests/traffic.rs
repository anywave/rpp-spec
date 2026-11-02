use rpp_control::{NodeId, Signature, Verifier, HEADER_LEN};
use rpp_link::{
    dispatch, DataOutcome, DispatchError, LinkAdapter, LinkKind, Outbound, TrafficPath,
};
use rpp_link_udp::{Config, Error, UdpAdapter, VERSION};
use std::{cell::Cell, net::UdpSocket, time::Duration};

struct Deny(Cell<u32>);
impl Verifier for Deny {
    fn verify(&self, _: &NodeId, _: &[u8; HEADER_LEN], _: &Signature) -> bool {
        self.0.set(self.0.get() + 1);
        false
    }
}
fn pair() -> (UdpAdapter, UdpSocket) {
    let peer = UdpSocket::bind("127.0.0.1:0").unwrap();
    peer.set_read_timeout(Some(Duration::from_millis(10)))
        .unwrap();
    let config = Config::new(
        "127.0.0.1:0".parse().unwrap(),
        peer.local_addr().unwrap(),
        LinkKind::Lan,
        Duration::from_millis(10),
    )
    .unwrap();
    (UdpAdapter::bind(config).unwrap(), peer)
}
/// Mutations: send >1200 wire bytes, stream/retransmit, or admit data on dispatch's control path.
#[test]
fn data_is_one_bounded_datagram_and_dispatch_blocks_control_path_data() {
    let (mut adapter, peer) = pair();
    let mut bytes = [0; 1400];
    assert_eq!(adapter.send_data(&[7; 1198]).unwrap(), DataOutcome::Sent);
    let (length, _) = peer.recv_from(&mut bytes).unwrap();
    assert_eq!(length, 1200);
    assert_eq!(&bytes[..2], &[VERSION, 4]);
    assert_eq!(&bytes[2..length], &[7; 1198]);
    assert!(matches!(
        adapter.send_data(&[7; 1199]),
        Err(Error::TooLarge)
    ));
    assert!(matches!(
        dispatch(
            &mut adapter,
            TrafficPath::Control,
            Outbound::Data(b"opaque")
        ),
        Err(DispatchError::WrongTrafficClass)
    ));
    assert!(peer.recv_from(&mut bytes).is_err());
}
/// Mutations: surface probe as control, enlarge a reply, or reply twice to the same nonce.
#[test]
fn probes_are_internal_equal_size_and_each_nonce_gets_at_most_one_reply() {
    let (mut adapter, peer) = pair();
    let verifier = Deny(Cell::new(0));
    let probe = [&[VERSION, 1][..], &1_u64.to_be_bytes()].concat();
    peer.send_to(&probe, adapter.local_addr()).unwrap();
    assert!(adapter.receive(&[0; 16], &verifier).unwrap().is_none());
    let mut bytes = [0; 64];
    let received = peer.recv_from(&mut bytes);
    assert!(received.is_ok());
    let (length, _) = received.unwrap();
    assert_eq!(length, probe.len());
    assert_eq!(&bytes[..2], &[VERSION, 2]);
    assert_eq!(&bytes[2..length], &probe[2..]);
    peer.send_to(&probe, adapter.local_addr()).unwrap();
    assert!(adapter.receive(&[0; 16], &verifier).unwrap().is_none());
    assert!(peer.recv_from(&mut bytes).is_err());
    assert_eq!(adapter.counters().echoes, 1);
    assert_eq!(verifier.0.get(), 0);
}
/// Mutation: echo to an unconfigured source or reflect its probe to the configured peer.
#[test]
fn a_third_socket_cannot_trigger_any_echo_destination() {
    let (mut adapter, peer) = pair();
    let third = UdpSocket::bind("127.0.0.1:0").unwrap();
    third
        .set_read_timeout(Some(Duration::from_millis(10)))
        .unwrap();
    third
        .send_to(
            &[&[VERSION, 1][..], &1_u64.to_be_bytes()].concat(),
            adapter.local_addr(),
        )
        .unwrap();
    assert!(adapter
        .receive(&[0; 16], &Deny(Cell::new(0)))
        .unwrap()
        .is_none());
    let mut bytes = [0; 64];
    assert!(third.recv_from(&mut bytes).is_err());
    assert!(peer.recv_from(&mut bytes).is_err());
    assert_eq!(adapter.counters().wrong_peer, 1);
    assert_eq!(adapter.counters().echoes, 0);
}
