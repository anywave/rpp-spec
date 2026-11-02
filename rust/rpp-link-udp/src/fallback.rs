use crate::{Config, Error, Received, TcpAdapter, UdpAdapter};
use rpp_control::{NodeId, VerifiedControlFrame, Verifier};
use rpp_link::{DataOutcome, LinkAdapter, LinkKind, LinkReading};
use std::net::SocketAddr;

/// Probe before sending any application frame; no runtime application failover.
#[derive(Clone, Copy, Debug)]
pub struct FallbackConfig {
    udp: Config,
    tcp_peer: SocketAddr,
}
impl FallbackConfig {
    pub fn new(udp: Config, tcp_peer: SocketAddr) -> Result<Self, Error> {
        if !udp.local.ip().is_loopback() || !udp.peer.ip().is_loopback() {
            return Err(Error::PlainUnderlayRefused);
        }
        crate::tcp::validate(tcp_peer, udp.kind, udp.timeout)?;
        Ok(Self { udp, tcp_peer })
    }
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Transport {
    Udp,
    Tcp,
}
enum Active {
    Udp(UdpAdapter),
    Tcp(TcpAdapter),
}
pub struct FallbackAdapter {
    active: Active,
}
impl FallbackAdapter {
    pub fn connect(config: FallbackConfig, tick: u64) -> Result<Self, Error> {
        let mut udp = UdpAdapter::bind(config.udp)?;
        if udp.read(tick)?.available {
            return Ok(Self {
                active: Active::Udp(udp),
            });
        }
        let mut tcp = TcpAdapter::connect(config.tcp_peer, config.udp.kind, config.udp.timeout)?;
        tcp.read(tick)?;
        Ok(Self {
            active: Active::Tcp(tcp),
        })
    }
    pub fn transport(&self) -> Transport {
        match self.active {
            Active::Udp(_) => Transport::Udp,
            Active::Tcp(_) => Transport::Tcp,
        }
    }
    pub fn receive<V: Verifier + ?Sized>(
        &mut self,
        recipient: &NodeId,
        verifier: &V,
    ) -> Result<Option<Received>, Error> {
        match &mut self.active {
            Active::Udp(a) => a.receive(recipient, verifier),
            Active::Tcp(a) => a.receive(recipient, verifier),
        }
    }
}
impl LinkAdapter for FallbackAdapter {
    type Error = Error;
    fn kind(&self) -> LinkKind {
        match &self.active {
            Active::Udp(a) => a.kind(),
            Active::Tcp(a) => a.kind(),
        }
    }
    fn read(&mut self, tick: u64) -> Result<LinkReading, Error> {
        match &mut self.active {
            Active::Udp(a) => a.read(tick),
            Active::Tcp(a) => a.read(tick),
        }
    }
    fn send_verified_control_frame(&mut self, frame: &VerifiedControlFrame) -> Result<(), Error> {
        match &mut self.active {
            Active::Udp(a) => a.send_verified_control_frame(frame),
            Active::Tcp(a) => a.send_verified_control_frame(frame),
        }
    }
    fn send_data(&mut self, payload: &[u8]) -> Result<DataOutcome, Error> {
        match &mut self.active {
            Active::Udp(a) => a.send_data(payload),
            Active::Tcp(a) => a.send_data(payload),
        }
    }
}
