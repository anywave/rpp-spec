use crate::{config::allowed, measure::Measurements, Config, Error};
use rpp_control::{NodeId, VerifiedControlFrame, Verifier};
use rpp_link::{DataOutcome, LinkAdapter, LinkKind, LinkReading};
use std::{
    collections::VecDeque,
    io,
    net::{SocketAddr, UdpSocket},
    time::{Duration, Instant},
};

/// Adapter-local framing, not an RPP protocol allocation. Cap includes prefix.
pub const VERSION: u8 = 1;
pub const MAX_DATAGRAM_LEN: usize = 1200;
pub const MAX_DATA_LEN: usize = MAX_DATAGRAM_LEN - 2;
const PROBE: u8 = 1;
const REPLY: u8 = 2;
const CONTROL: u8 = 3;
const DATA: u8 = 4;
const PROBE_LEN: usize = 10;
const MAX_PENDING: usize = 4;
const RECEIVE_BUDGET: usize = 32;
const ECHO_BURST: u32 = 32;

#[derive(Debug, PartialEq, Eq)]
pub enum Received {
    Data(Vec<u8>),
    Control(VerifiedControlFrame),
}
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct Counters {
    pub wrong_peer: u64,
    pub malformed: u64,
    pub refused_control: u64,
    pub queue_full: u64,
    pub echoes: u64,
    pub echo_limited: u64,
    pub connection_resets: u64,
}

pub struct UdpAdapter {
    socket: UdpSocket,
    config: Config,
    local: SocketAddr,
    nonce: u64,
    measurements: Measurements,
    counters: Counters,
    pending: VecDeque<Vec<u8>>,
    last_echo: Option<u64>,
    echo_window: Instant,
    echo_count: u32,
}
impl UdpAdapter {
    /// Validate both numeric addresses and class before any socket creation.
    pub fn bind(config: Config) -> Result<Self, Error> {
        Config::new(config.local, config.peer, config.kind, config.timeout)?;
        let socket = Self::open(config.local, config.timeout)?;
        Self::from_socket(socket, config)
    }
    fn open(local: SocketAddr, timeout: Duration) -> Result<UdpSocket, Error> {
        let socket = UdpSocket::bind(local)?;
        socket.set_read_timeout(Some(timeout))?;
        socket.set_write_timeout(Some(timeout))?;
        Ok(socket)
    }
    fn from_socket(socket: UdpSocket, config: Config) -> Result<Self, Error> {
        Ok(Self {
            local: socket.local_addr()?,
            socket,
            config,
            nonce: 0,
            measurements: Measurements::default(),
            counters: Counters::default(),
            pending: VecDeque::new(),
            last_echo: None,
            echo_window: Instant::now(),
            echo_count: 0,
        })
    }
    /// Convenience for local tests/examples: both addresses are fixed loopback.
    pub fn loopback_pair(kind: LinkKind, timeout: Duration) -> Result<(Self, Self), Error> {
        let local: SocketAddr = "127.0.0.1:0".parse().expect("literal address");
        Config::new(
            local,
            "127.0.0.1:1".parse().expect("literal address"),
            kind,
            timeout,
        )?;
        debug_assert!(allowed(local.ip()));
        let a = Self::open(local, timeout)?;
        let b = Self::open(local, timeout)?;
        let ac = Config::new(a.local_addr()?, b.local_addr()?, kind, timeout)?;
        let bc = Config::new(b.local_addr()?, a.local_addr()?, kind, timeout)?;
        Ok((Self::from_socket(a, ac)?, Self::from_socket(b, bc)?))
    }
    pub fn local_addr(&self) -> SocketAddr {
        self.local
    }
    pub fn peer_addr(&self) -> SocketAddr {
        self.config.peer
    }
    pub fn counters(&self) -> Counters {
        self.counters
    }
    fn send(&self, class: u8, payload: &[u8]) -> Result<(), Error> {
        if payload.len() > MAX_DATA_LEN {
            return Err(Error::TooLarge);
        }
        let mut wire = [0; MAX_DATAGRAM_LEN];
        wire[..2].copy_from_slice(&[VERSION, class]);
        wire[2..2 + payload.len()].copy_from_slice(payload);
        let expected = payload.len() + 2;
        let sent = self.socket.send_to(&wire[..expected], self.config.peer)?;
        if sent != expected {
            return Err(io::Error::new(io::ErrorKind::WriteZero, "short UDP datagram").into());
        }
        Ok(())
    }
    fn datagram(&mut self) -> Result<Option<Vec<u8>>, Error> {
        let mut bytes = [0; 65_536];
        let (size, peer) = match self.socket.recv_from(&mut bytes) {
            Ok(value) => value,
            Err(error) if packet_loss(error.kind()) => {
                if error.kind() == io::ErrorKind::ConnectionReset {
                    self.counters.connection_resets =
                        self.counters.connection_resets.saturating_add(1);
                }
                return Ok(None);
            }
            Err(error) => return Err(error.into()),
        };
        if peer != self.config.peer {
            self.counters.wrong_peer = self.counters.wrong_peer.saturating_add(1);
            return Ok(None);
        }
        if !(2..=MAX_DATAGRAM_LEN).contains(&size)
            || bytes[0] != VERSION
            || !(PROBE..=DATA).contains(&bytes[1])
        {
            self.counters.malformed = self.counters.malformed.saturating_add(1);
            return Ok(None);
        }
        Ok(Some(bytes[..size].to_vec()))
    }
    fn internal(&mut self, wire: &[u8]) -> Result<bool, Error> {
        if !matches!(wire[1], PROBE | REPLY) {
            return Ok(false);
        }
        if wire.len() != PROBE_LEN {
            self.counters.malformed = self.counters.malformed.saturating_add(1);
            return Ok(true);
        }
        if wire[1] == REPLY {
            return Ok(true);
        }
        let nonce = u64::from_be_bytes(wire[2..].try_into().expect("fixed probe length"));
        if self.echo_window.elapsed() >= Duration::from_secs(1) {
            self.echo_window = Instant::now();
            self.echo_count = 0;
        }
        if self.last_echo.is_some_and(|last| nonce <= last) || self.echo_count >= ECHO_BURST {
            self.counters.echo_limited = self.counters.echo_limited.saturating_add(1);
            return Ok(true);
        }
        self.last_echo = Some(nonce);
        self.echo_count += 1;
        self.send(REPLY, &wire[2..])?;
        self.counters.echoes = self.counters.echoes.saturating_add(1);
        Ok(true)
    }
    /// Receive one packet. Probes/replies never become application/control data.
    /// Control is delivered only after the caller verifier and recipient pass.
    pub fn receive<V: Verifier + ?Sized>(
        &mut self,
        recipient: &NodeId,
        verifier: &V,
    ) -> Result<Option<Received>, Error> {
        let wire = match self.pending.pop_front() {
            Some(wire) => wire,
            None => match self.datagram()? {
                Some(wire) => wire,
                None => return Ok(None),
            },
        };
        if self.internal(&wire)? {
            return Ok(None);
        }
        if wire[1] == CONTROL {
            return match rpp_control::decode(&wire[2..], recipient, verifier) {
                Ok(frame) => Ok(Some(Received::Control(frame))),
                Err(_) => {
                    self.counters.refused_control = self.counters.refused_control.saturating_add(1);
                    Ok(None)
                }
            };
        }
        Ok(Some(Received::Data(wire[2..].to_vec())))
    }
}
impl LinkAdapter for UdpAdapter {
    type Error = Error;
    fn kind(&self) -> LinkKind {
        self.config.kind
    }
    fn read(&mut self, tick: u64) -> Result<LinkReading, Error> {
        self.nonce = self.nonce.checked_add(1).ok_or(Error::NonceExhausted)?;
        let nonce = self.nonce.to_be_bytes();
        let start = Instant::now();
        let mut sample = None;
        // Send failures resolve this actual probe as loss. Never retransmit.
        if self.send(PROBE, &nonce).is_ok() {
            for _ in 0..RECEIVE_BUDGET {
                let remaining = self.config.timeout.saturating_sub(start.elapsed());
                if remaining.is_zero() {
                    break;
                }
                self.socket.set_read_timeout(Some(remaining))?;
                let Some(wire) = self.datagram()? else {
                    continue;
                };
                if wire.len() == PROBE_LEN && wire[1] == REPLY && wire[2..] == nonce {
                    sample = Some(start.elapsed().as_millis().min(u128::from(u64::MAX - 1)) as u64);
                    break;
                }
                if self.internal(&wire)? {
                    continue;
                }
                if self.pending.len() < MAX_PENDING {
                    self.pending.push_back(wire);
                } else {
                    self.counters.queue_full = self.counters.queue_full.saturating_add(1);
                }
            }
        }
        self.socket.set_read_timeout(Some(self.config.timeout))?;
        self.measurements.observe(sample);
        Ok(self.measurements.reading(tick))
    }
    fn send_verified_control_frame(&mut self, frame: &VerifiedControlFrame) -> Result<(), Error> {
        self.send(CONTROL, &frame.encode())
    }
    fn send_data(&mut self, payload: &[u8]) -> Result<DataOutcome, Error> {
        self.send(DATA, payload)?;
        Ok(DataOutcome::Sent)
    }
}
fn packet_loss(kind: io::ErrorKind) -> bool {
    matches!(
        kind,
        io::ErrorKind::WouldBlock
            | io::ErrorKind::TimedOut
            | io::ErrorKind::ConnectionReset
            | io::ErrorKind::ConnectionRefused
    )
}
#[cfg(test)]
mod tests {
    use super::*;
    use rpp_control::{ControlFrame, ControlKind, Signature, HEADER_LEN};
    use std::cell::Cell;
    struct Check(Cell<u32>);
    impl Verifier for Check {
        fn verify(&self, _: &NodeId, _: &[u8; HEADER_LEN], signature: &Signature) -> bool {
            self.0.set(self.0.get() + 1);
            signature == &[9; 64]
        }
    }
    fn endpoint() -> (UdpAdapter, UdpSocket) {
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
    /// Mutation: parse a third socket before exact-peer filtering, including oversized packets.
    #[test]
    fn foreign_packets_are_counted_before_any_parsing_or_verification() {
        let (mut adapter, peer) = endpoint();
        let third = UdpSocket::bind("127.0.0.1:0").unwrap();
        let verifier = Check(Cell::new(0));
        let frame = ControlFrame::new(ControlKind::Alive, 1, [1; 16], [2; 16], [9; 64]).encode();
        let wire = [&[VERSION, CONTROL][..], &frame].concat();
        third.send_to(&wire, adapter.local_addr()).unwrap();
        assert_eq!(adapter.receive(&[2; 16], &verifier).unwrap(), None);
        third.send_to(&[255; 1500], adapter.local_addr()).unwrap();
        assert_eq!(adapter.receive(&[2; 16], &verifier).unwrap(), None);
        assert_eq!(adapter.counters().wrong_peer, 2);
        assert_eq!(adapter.counters().malformed, 0);
        assert_eq!(verifier.0.get(), 0);
        peer.send_to(&[255; 1500], adapter.local_addr()).unwrap();
        assert_eq!(adapter.receive(&[2; 16], &verifier).unwrap(), None);
        assert_eq!(adapter.counters().malformed, 1);
    }
    /// Mutation: bypass the caller verifier/codec and deliver forged or undecodable control.
    #[test]
    fn only_decoded_verified_control_reaches_the_caller_without_replay_policy() {
        let (mut adapter, peer) = endpoint();
        let verifier = Check(Cell::new(0));
        for signature in [[0; 64], [9; 64], [9; 64]] {
            let frame =
                ControlFrame::new(ControlKind::Pause, 1, [1; 16], [2; 16], signature).encode();
            peer.send_to(
                &[&[VERSION, CONTROL][..], &frame].concat(),
                adapter.local_addr(),
            )
            .unwrap();
            let received = adapter.receive(&[2; 16], &verifier).unwrap();
            assert_eq!(received.is_some(), signature == [9; 64]);
            if let Some(Received::Control(frame)) = received {
                assert_eq!(frame.sequence(), 1);
            } else {
                assert!(received.is_none());
            }
        }
        peer.send_to(&[VERSION, CONTROL, 0], adapter.local_addr())
            .unwrap();
        assert_eq!(adapter.receive(&[2; 16], &verifier).unwrap(), None);
        assert_eq!(adapter.counters().refused_control, 2);
        assert_eq!(verifier.0.get(), 3);
    }
    /// Mutation: remove the bounded echo budget and amplify a peer flood.
    #[test]
    fn exhausted_echo_budget_refuses_a_new_nonce() {
        let (mut adapter, peer) = endpoint();
        adapter.echo_count = ECHO_BURST;
        adapter.echo_window = Instant::now() + Duration::from_secs(10);
        peer.send_to(
            &[&[VERSION, PROBE][..], &1_u64.to_be_bytes()].concat(),
            adapter.local_addr(),
        )
        .unwrap();
        assert_eq!(
            adapter.receive(&[0; 16], &Check(Cell::new(0))).unwrap(),
            None
        );
        assert_eq!(adapter.counters().echoes, 0);
        assert_eq!(adapter.counters().echo_limited, 1);
        assert!(peer.recv_from(&mut [0; 64]).is_err());
    }
    /// Mutation: propagate Windows ICMP reset instead of resolving an outstanding probe as loss.
    #[test]
    fn connection_reset_and_timeouts_are_packet_loss_not_errors() {
        assert!(packet_loss(io::ErrorKind::ConnectionReset));
        assert!(packet_loss(io::ErrorKind::TimedOut));
        assert!(!packet_loss(io::ErrorKind::PermissionDenied));
    }
}
