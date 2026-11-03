use rpp_link::LinkKind;
use std::{
    fmt, io,
    net::{IpAddr, SocketAddr},
    time::Duration,
};

#[derive(Debug)]
pub enum Error {
    PlainUnderlayRefused,
    UnsupportedKind,
    InvalidConfig,
    TooLarge,
    NonceExhausted,
    Io(io::Error),
}
impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{self:?}")
    }
}
impl std::error::Error for Error {}
impl From<io::Error> for Error {
    fn from(value: io::Error) -> Self {
        Self::Io(value)
    }
}

/// Numeric addresses only. Allowlisting is a heuristic, never tunnel evidence.
#[derive(Clone, Copy, Debug)]
pub struct Config {
    pub(crate) local: SocketAddr,
    pub(crate) peer: SocketAddr,
    pub(crate) kind: LinkKind,
    pub(crate) timeout: Duration,
}
impl Config {
    pub fn new(
        local: SocketAddr,
        peer: SocketAddr,
        kind: LinkKind,
        timeout: Duration,
    ) -> Result<Self, Error> {
        if !allowed(local.ip()) || !allowed(peer.ip()) {
            return Err(Error::PlainUnderlayRefused);
        }
        if !matches!(kind, LinkKind::Lan | LinkKind::Wifi | LinkKind::Internet) {
            return Err(Error::UnsupportedKind);
        }
        if peer.port() == 0 || timeout.is_zero() || timeout > Duration::from_millis(250) {
            return Err(Error::InvalidConfig);
        }
        Ok(Self {
            local,
            peer,
            kind,
            timeout,
        })
    }
}
pub(crate) fn allowed(ip: IpAddr) -> bool {
    match ip {
        IpAddr::V4(ip) => {
            let b = ip.octets();
            b[0] == 127 || b[0] == 100 && (64..=127).contains(&b[1])
        }
        IpAddr::V6(ip) => ip.is_loopback() || ip.segments()[..3] == [0xfd7a, 0x115c, 0xa1e0],
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    /// Mutation: accept a public/LAN/unspecified/mapped address instead of refusing before bind.
    #[test]
    fn address_classes_are_checked_without_opening_sockets() {
        let good = "127.0.0.1:1".parse().unwrap();
        for text in [
            "0.0.0.0:1",
            "192.168.1.1:1",
            "100.63.255.255:1",
            "100.128.0.0:1",
            "[::]:1",
            "[::ffff:127.0.0.1]:1",
            "[fd7a:115c:a1e1::1]:1",
        ] {
            let bad = text.parse().unwrap();
            for (local, peer) in [(bad, good), (good, bad)] {
                assert!(matches!(
                    Config::new(local, peer, LinkKind::Lan, Duration::from_millis(1)),
                    Err(Error::PlainUnderlayRefused)
                ));
            }
        }
        for text in [
            "127.255.255.254:1",
            "100.64.0.0:1",
            "100.127.255.255:1",
            "[::1]:1",
            "[fd7a:115c:a1e0:ffff::1]:1",
        ] {
            assert!(Config::new(
                text.parse().unwrap(),
                good,
                LinkKind::Internet,
                Duration::from_millis(1)
            )
            .is_ok());
        }
    }
    /// Mutation: admit BLE/LoRa or an unbounded receive timeout.
    #[test]
    fn unsupported_kinds_and_unbounded_timeouts_are_refused() {
        let a = "127.0.0.1:1".parse().unwrap();
        for kind in [LinkKind::Ble, LinkKind::Lora] {
            assert!(matches!(
                Config::new(a, a, kind, Duration::from_millis(1)),
                Err(Error::UnsupportedKind)
            ));
        }
        for timeout in [Duration::ZERO, Duration::from_secs(1)] {
            assert!(matches!(
                Config::new(a, a, LinkKind::Lan, timeout),
                Err(Error::InvalidConfig)
            ));
        }
    }
}
