use rpp_link::LinkKind;
use rpp_link_udp::{Config, FallbackConfig};
use std::{net::SocketAddr, time::Duration};
const TIMEOUT: Duration = Duration::from_millis(250);
fn fixture_peer_allowed(peer: SocketAddr) -> bool { peer.ip().is_loopback() }
/// Mutation: permit nonloopback configuration or fixture reply sources.
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
