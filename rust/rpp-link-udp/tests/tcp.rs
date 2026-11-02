use rpp_control::{ControlFrame, ControlKind, NodeId, Signature, Verifier, HEADER_LEN};
use rpp_link::{LinkAdapter, LinkKind};
use rpp_link_udp::{
    framed, Config, FallbackAdapter, FallbackConfig, Received, TcpAdapter, Transport,
};
use std::{
    io::{self, Read, Write},
    net::{Shutdown, SocketAddr, TcpListener, TcpStream, UdpSocket},
    thread,
    time::{Duration, Instant},
};
const TIMEOUT: Duration = Duration::from_millis(250);
struct Check;
impl Verifier for Check {
    fn verify(&self, _: &NodeId, _: &[u8; HEADER_LEN], signature: &Signature) -> bool {
        signature == &[9; 64]
    }
}
fn fixture_peer_allowed(peer: SocketAddr) -> bool {
    peer.ip().is_loopback()
}
fn accept(listener: &TcpListener) -> io::Result<TcpStream> {
    listener.set_nonblocking(true)?;
    let deadline = Instant::now() + Duration::from_secs(3);
    loop {
        match listener.accept() {
            Ok((stream, _)) => return Ok(stream),
            Err(error)
                if error.kind() == io::ErrorKind::WouldBlock && Instant::now() < deadline =>
            {
                thread::sleep(Duration::from_millis(2));
            }
            Err(error) => return Err(error),
        }
    }
}
fn wake(address: SocketAddr) {
    if let Ok(mut stream) = TcpStream::connect_timeout(&address, TIMEOUT) {
        if stream.set_write_timeout(Some(TIMEOUT)).is_ok() {
            let stop = framed::encode(&[1, 4]).unwrap();
            let _ = stream.write_all(&[stop.as_slice(), stop.as_slice()].concat());
        }
    }
}
fn pair() -> (TcpAdapter, TcpStream) {
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let peer = TcpStream::connect(listener.local_addr().unwrap()).unwrap();
    peer.set_read_timeout(Some(Duration::from_secs(2))).unwrap();
    peer.set_write_timeout(Some(TIMEOUT)).unwrap();
    let stream = accept(&listener).unwrap();
    (
        TcpAdapter::from_stream(stream, LinkKind::Lan, TIMEOUT).unwrap(),
        peer,
    )
}
fn read_wire(peer: &mut TcpStream) -> io::Result<Vec<u8>> {
    let mut prefix = [0; 2];
    peer.read_exact(&mut prefix)?;
    let length = usize::from(u16::from_be_bytes(prefix));
    if !(2..=1200).contains(&length) {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            "fixture frame bound",
        ));
    }
    let mut bytes = vec![0; length];
    peer.read_exact(&mut bytes)?;
    Ok(bytes)
}
fn control(recipient: u8, signature: u8) -> Vec<u8> {
    let bytes = ControlFrame::new(
        ControlKind::Pause,
        1,
        [1; 16],
        [recipient; 16],
        [signature; 64],
    )
    .encode();
    [&[1, 3][..], &bytes].concat()
}
/// Mutations: little-endian prefix, cap+1, or accepting truncated/invalid domains.
#[test]
fn framing_bounds_truncations_and_coalescing_are_unambiguous() {
    let wire = [&[1, 4][..], &[7; 1198]].concat();
    let frame = framed::encode(&wire).unwrap();
    assert_eq!(&frame[..2], &1200_u16.to_be_bytes());
    let joined = [frame.as_slice(), frame.as_slice()].concat();
    assert_eq!(framed::decode_one(&joined), Ok((wire.as_slice(), 1202)));
    for end in 0..frame.len() {
        assert!(framed::decode_one(&frame[..end]).is_err());
    }
    for length in [0_u16, 1, 1201, u16::MAX] {
        assert_eq!(
            framed::decode_one(&length.to_be_bytes()),
            Err(framed::FrameError::InvalidLength)
        );
    }
    for wire in [
        vec![0, 4],
        vec![1, 0],
        vec![1, 5],
        vec![1, 1],
        vec![1, 2],
        vec![1, 3],
        vec![1; 1201],
    ] {
        assert!(framed::encode(&wire).is_err());
    }
}
/// Mutations: leave a failed frame stream reusable or resume at leftover bytes.
#[test]
fn truncated_or_oversized_streams_close_without_resynchronization() {
    for bytes in [
        vec![0],
        vec![0, 3, 1],
        1201_u16.to_be_bytes().to_vec(),
        vec![0, 2, 0, 4],
    ] {
        let (mut adapter, mut peer) = pair();
        peer.write_all(&bytes).unwrap();
        peer.shutdown(Shutdown::Write).unwrap();
        assert!(adapter.receive(&[2; 16], &Check).is_err());
        assert!(adapter.is_closed());
        assert!(adapter.send_data(b"never replay").is_err());
        assert!(adapter.receive(&[2; 16], &Check).is_err());
    }
}
/// Mutations: verifier/recipient bypass, control-as-data, or consuming a coalesced successor.
#[test]
fn control_requires_the_caller_verifier_and_recipient_on_a_coalesced_stream() {
    let (mut adapter, mut peer) = pair();
    let wires = [control(2, 0), control(3, 9), control(2, 9), vec![1, 4, 7]];
    for wire in &wires {
        peer.write_all(&framed::encode(wire).unwrap()).unwrap();
    }
    assert_eq!(adapter.receive(&[2; 16], &Check).unwrap(), None);
    assert_eq!(adapter.receive(&[2; 16], &Check).unwrap(), None);
    assert!(
        matches!(adapter.receive(&[2; 16], &Check).unwrap(), Some(Received::Control(frame)) if frame.sequence() == 1)
    );
    assert_eq!(
        adapter.receive(&[2; 16], &Check).unwrap(),
        Some(Received::Data(vec![7]))
    );
    assert_eq!(adapter.counters().refused_control, 2);
}
/// Mutations: accept a stale reply nonce or retain an unbounded application queue.
#[test]
fn current_probe_nonce_and_four_pending_frames_are_independent() {
    let (mut adapter, mut peer) = pair();
    let worker = thread::spawn(move || -> io::Result<Vec<u8>> {
        let probe = read_wire(&mut peer)?;
        let mut wrong = probe.clone();
        wrong[1] = 2;
        wrong[9] ^= 1;
        let mut batch = framed::encode(&wrong).unwrap();
        for value in 0..5 {
            batch.extend(framed::encode(&[1, 4, value]).unwrap());
        }
        let mut reply = probe.clone();
        reply[1] = 2;
        batch.extend(framed::encode(&reply).unwrap());
        peer.write_all(&batch)?;
        Ok(probe)
    });
    let reading = adapter.read(7);
    let probe = worker.join().unwrap().unwrap();
    assert_eq!(probe, [&[1, 1][..], &1_u64.to_be_bytes()].concat());
    let reading = reading.unwrap();
    assert!(reading.available);
    assert_eq!(reading.observed, 7);
    assert_eq!(adapter.counters().queue_full, 1);
    for value in 0..4 {
        assert_eq!(
            adapter.receive(&[2; 16], &Check).unwrap(),
            Some(Received::Data(vec![value]))
        );
    }
}
/// Mutations: echo repeated nonces, leak probes, or change equal-size reply framing.
#[test]
fn probes_stay_internal_and_duplicates_do_not_echo_twice() {
    let (mut adapter, mut peer) = pair();
    for nonce in [1_u64, 1, 2] {
        let wire = [&[1, 1][..], &nonce.to_be_bytes()].concat();
        peer.write_all(&framed::encode(&wire).unwrap()).unwrap();
        assert_eq!(adapter.receive(&[2; 16], &Check).unwrap(), None);
    }
    let first = read_wire(&mut peer).unwrap();
    let second = read_wire(&mut peer).unwrap();
    assert_eq!(first, [&[1, 2][..], &1_u64.to_be_bytes()].concat());
    assert_eq!(second, [&[1, 2][..], &2_u64.to_be_bytes()].concat());
    assert_eq!(
        (adapter.counters().echoes, adapter.counters().echo_limited),
        (2, 1)
    );
}
/// Mutation: retransmit an application frame after a successful/ambiguous write.
#[test]
fn application_send_writes_one_frame_without_replay() {
    let (mut adapter, peer) = pair();
    adapter.send_data(b"once").unwrap();
    drop(adapter);
    let mut bytes = Vec::new();
    peer.take(2405).read_to_end(&mut bytes).unwrap();
    assert_eq!(
        bytes,
        framed::encode(&[1, 4, b'o', b'n', b'c', b'e']).unwrap()
    );
}
/// Mutation: skip probe-based TCP fallback or forward the application over UDP too.
#[test]
fn silent_open_udp_falls_back_before_application_within_two_seconds() {
    let udp = UdpSocket::bind("127.0.0.1:0").unwrap();
    udp.set_nonblocking(true).unwrap();
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let address = listener.local_addr().unwrap();
    let worker = thread::spawn(move || -> Result<_, rpp_link_udp::Error> {
        let stream = accept(&listener)?;
        let mut adapter = TcpAdapter::from_stream(stream, LinkKind::Lan, TIMEOUT)?;
        let probe = adapter.receive(&[2; 16], &Check)?;
        let data = adapter.receive(&[2; 16], &Check)?;
        Ok((probe, data, adapter.counters()))
    });
    let config = Config::new(
        "127.0.0.1:0".parse().unwrap(),
        udp.local_addr().unwrap(),
        LinkKind::Lan,
        TIMEOUT,
    )
    .unwrap();
    let start = Instant::now();
    let mut result = FallbackAdapter::connect(FallbackConfig::new(config, address).unwrap(), 0);
    let elapsed = start.elapsed();
    let transport = result.as_ref().ok().map(FallbackAdapter::transport);
    let mut sent = Ok(());
    if transport == Some(Transport::Tcp) {
        sent = result.as_mut().unwrap().send_data(b"once").map(|_| ());
    } else {
        wake(address);
    }
    let server = worker.join().unwrap();
    sent.expect("fixture application write failed");
    assert_eq!(transport, Some(Transport::Tcp));
    assert!(elapsed < Duration::from_secs(2));
    let (probe, data, counters) = server.unwrap();
    assert_eq!(probe, None);
    assert_eq!(data, Some(Received::Data(b"once".to_vec())));
    assert_eq!(counters.echoes, 1);
    let mut datagram = [0; 1200];
    let (length, _) = udp.recv_from(&mut datagram).unwrap();
    assert_eq!(
        &datagram[..length],
        &[&[1, 1][..], &1_u64.to_be_bytes()].concat()
    );
    assert!(
        matches!(udp.recv_from(&mut datagram), Err(error) if error.kind() == io::ErrorKind::WouldBlock)
    );
}
/// Mutation: permit tailnet/nonloopback fallback configuration before socket creation.
#[test]
fn fallback_preflight_refuses_nonloopback_udp_and_tcp_without_io() {
    assert!(fixture_peer_allowed("127.0.0.1:1".parse().unwrap()));
    assert!(fixture_peer_allowed("[::1]:1".parse().unwrap()));
    assert!(!fixture_peer_allowed("192.0.2.1:1".parse().unwrap()));
    assert!(!fixture_peer_allowed("100.64.0.1:1".parse().unwrap()));
    let local = "127.0.0.1:1".parse().unwrap();
    let tailnet = "100.64.0.1:1".parse().unwrap();
    for (bind, peer, tcp) in [
        (tailnet, local, local),
        (local, tailnet, local),
        (local, local, tailnet),
    ] {
        let config = Config::new(bind, peer, LinkKind::Lan, TIMEOUT).unwrap();
        assert!(FallbackConfig::new(config, tcp).is_err());
    }
}

/// Mutation: choose TCP despite a successful exact UDP probe.
#[test]
fn successful_udp_probe_keeps_tcp_unused() {
    let udp = UdpSocket::bind("127.0.0.1:0").unwrap();
    udp.set_read_timeout(Some(Duration::from_secs(2))).unwrap();
    udp.set_write_timeout(Some(TIMEOUT)).unwrap();
    let udp_peer = udp.local_addr().unwrap();
    let responder = thread::spawn(move || -> io::Result<()> {
        let mut wire = [0; 10];
        let (_, peer) = udp.recv_from(&mut wire)?;
        if !fixture_peer_allowed(peer) {
            return Err(io::ErrorKind::PermissionDenied.into());
        }
        wire[1] = 2;
        udp.send_to(&wire, peer)?;
        Ok(())
    });
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let address = listener.local_addr().unwrap();
    let server = thread::spawn(move || -> Result<(), rpp_link_udp::Error> {
        let stream = accept(&listener)?;
        let mut tcp = TcpAdapter::from_stream(stream, LinkKind::Lan, TIMEOUT)?;
        tcp.receive(&[2; 16], &Check)?;
        tcp.receive(&[2; 16], &Check)?;
        Ok(())
    });
    let config = Config::new(
        "127.0.0.1:0".parse().unwrap(),
        udp_peer,
        LinkKind::Lan,
        TIMEOUT,
    )
    .unwrap();
    let mut result = FallbackAdapter::connect(FallbackConfig::new(config, address).unwrap(), 0);
    let selected = result.as_ref().ok().map(FallbackAdapter::transport);
    let mut sent = Ok(());
    if selected == Some(Transport::Tcp) {
        sent = result
            .as_mut()
            .unwrap()
            .send_data(b"unexpected TCP")
            .map(|_| ());
    } else {
        wake(address);
    }
    let server_result = server.join().unwrap();
    responder.join().unwrap().unwrap();
    sent.expect("fixture application write failed");
    assert_eq!(selected, Some(Transport::Udp));
    assert!(server_result.is_ok());
}
