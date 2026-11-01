//! Endpoint metadata and prior capability inputs, without transport drivers.
//!
//! A WebSocket gateway is a caller-declared LAN profile. Its `ws://` URI is
//! descriptive; the scheme proves neither locality nor authenticated reachability.

use alloc::{format, string::String};
use rpp_core::overlay::Underlay;
use rpp_link::{LinkKind, LinkReading};

use crate::limits::MAX_URI_LEN;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum EndpointKind {
    Lan,
    Wifi,
    Internet,
    Ble,
    Lora,
    WebSocketGateway,
}

impl EndpointKind {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Lan => "LAN",
            Self::Wifi => "Wi-Fi",
            Self::Internet => "internet",
            Self::Ble => "BLE",
            Self::Lora => "LoRa",
            Self::WebSocketGateway => "WebSocketGateway",
        }
    }

    pub fn link_kind(self) -> LinkKind {
        match self {
            Self::Lan | Self::WebSocketGateway => LinkKind::Lan,
            Self::Wifi => LinkKind::Wifi,
            Self::Internet => LinkKind::Internet,
            Self::Ble => LinkKind::Ble,
            Self::Lora => LinkKind::Lora,
        }
    }

    pub(crate) fn underlay(self) -> Underlay {
        match self.link_kind() {
            LinkKind::Lan => Underlay::Lan,
            LinkKind::Wifi => Underlay::Wifi,
            LinkKind::Internet => Underlay::Internet,
            LinkKind::Ble => Underlay::Bluetooth,
            LinkKind::Lora => Underlay::Lora,
        }
    }
}

/// These are caller-supplied prior-verification outcomes, not new verification.
/// A failure-domain number must describe actual shared failure dependencies;
/// different modality names alone do not imply independence. Default zero is a
/// shared unknown domain, and all verification capabilities default to false.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct EndpointCapabilities {
    pub tunnel_verified: bool,
    pub reviewed_adapter: bool,
    pub observation_verified: bool,
    /// Prior compatible control-codec/adapter capability, never admission.
    pub control_capable: bool,
    pub failure_domain: u32,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Endpoint {
    pub id: u32,
    pub kind: EndpointKind,
    pub uri: String,
    pub last_reading: LinkReading,
    pub capabilities: EndpointCapabilities,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum EndpointError {
    Capacity,
    InvalidUri,
    InvalidReading,
}

/// Fleet-specific input checks; core LinkReading policy remains unchanged.
pub(crate) fn validate_reading(reading: LinkReading) -> Result<(), EndpointError> {
    if !reading.valid() || reading.latency_ms == u64::MAX || reading.jitter_ms == u64::MAX {
        return Err(EndpointError::InvalidReading);
    }
    Ok(())
}

fn validate_uri(kind: EndpointKind, uri: &str) -> Result<(), EndpointError> {
    // Check the borrowed length before scanning or allocating an owned URI.
    if uri.len() > MAX_URI_LEN {
        return Err(EndpointError::Capacity);
    }
    if uri.is_empty() || !uri.bytes().all(|byte| (0x20..=0x7e).contains(&byte)) {
        return Err(EndpointError::InvalidUri);
    }
    let (scheme, rest) = uri.split_once("://").ok_or(EndpointError::InvalidUri)?;
    if scheme.is_empty()
        || !scheme.as_bytes()[0].is_ascii_alphabetic()
        || !scheme
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'+' | b'-' | b'.'))
        || (kind == EndpointKind::WebSocketGateway && scheme != "ws")
    {
        return Err(EndpointError::InvalidUri);
    }
    let authority = rest.split(['/', '?', '#']).next().unwrap_or("");
    if authority.is_empty() || authority.contains('@') || authority.bytes().any(|byte| byte == b' ')
    {
        return Err(EndpointError::InvalidUri);
    }
    let network_port = !matches!(kind, EndpointKind::Ble | EndpointKind::Lora);
    let (host, suffix) = if let Some(bracketed) = authority.strip_prefix('[') {
        let (host, suffix) = bracketed.split_once(']').ok_or(EndpointError::InvalidUri)?;
        if host.contains(['[', ']']) || (!suffix.is_empty() && !suffix.starts_with(':')) {
            return Err(EndpointError::InvalidUri);
        }
        (host, suffix.strip_prefix(':'))
    } else {
        if authority.contains(['[', ']']) {
            return Err(EndpointError::InvalidUri);
        }
        match authority.split_once(':') {
            Some((host, port)) => (host, Some(port)),
            None => (authority, None),
        }
    };
    if host.is_empty()
        || (network_port
            && suffix.is_some_and(|port| {
                port.is_empty()
                    || !port.bytes().all(|byte| byte.is_ascii_digit())
                    || port.parse::<u16>().is_err()
            }))
    {
        return Err(EndpointError::InvalidUri);
    }
    Ok(())
}

impl Endpoint {
    pub fn new(
        id: u32,
        kind: EndpointKind,
        uri: impl AsRef<str>,
        last_reading: LinkReading,
        capabilities: EndpointCapabilities,
    ) -> Result<Self, EndpointError> {
        let uri = uri.as_ref();
        validate_uri(kind, uri)?;
        validate_reading(last_reading)?;
        Ok(Self {
            id,
            kind,
            uri: String::from(uri),
            last_reading,
            capabilities,
        })
    }

    pub fn valid(&self) -> bool {
        self.validate().is_ok()
    }

    pub fn validate(&self) -> Result<(), EndpointError> {
        validate_uri(self.kind, &self.uri)?;
        validate_reading(self.last_reading)
    }

    /// Safe reversible name scoped by the registry-unique canonical word.
    /// Arbitrary URI text never participates in route parsing, and no identity
    /// bytes are truncated or hashed into this operational link name.
    pub fn link_name(&self, canonical_word: u32) -> String {
        format!("n{canonical_word:08x}-ep{:08x}", self.id)
    }

    pub(crate) fn failure_domain_name(&self) -> String {
        format!("domain{:08x}", self.capabilities.failure_domain)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn reading() -> LinkReading {
        LinkReading {
            latency_ms: 1,
            loss_ppm: 0,
            jitter_ms: 0,
            available: true,
            observed: 1,
        }
    }

    fn endpoint(kind: EndpointKind, uri: &str) -> Result<Endpoint, EndpointError> {
        Endpoint::new(1, kind, uri, reading(), EndpointCapabilities::default())
    }

    const KINDS: [EndpointKind; 6] = [
        EndpointKind::Lan,
        EndpointKind::Wifi,
        EndpointKind::Internet,
        EndpointKind::Ble,
        EndpointKind::Lora,
        EndpointKind::WebSocketGateway,
    ];

    #[test]
    fn uri_capacity_accepts_limit_and_rejects_one_past_and_literal_struct() {
        // Mutation: remove the borrowed length guard, or skip it for literal Endpoint validation.
        let prefix = "ws://host/";
        let exact = alloc::format!("{prefix}{}", "x".repeat(MAX_URI_LEN - prefix.len()));
        let oversized = alloc::format!("{exact}x");
        for kind in KINDS {
            let mut value = endpoint(kind, &exact).unwrap();
            assert_eq!(value.uri.len(), MAX_URI_LEN);
            assert_eq!(endpoint(kind, &oversized), Err(EndpointError::Capacity));
            value.uri = oversized.clone();
            assert_eq!(value.validate(), Err(EndpointError::Capacity));
        }
    }

    #[test]
    fn uri_rejects_non_ascii_invisible_and_control_characters() {
        // Mutation: restore control-character-only filtering and admit invisible Unicode/bidi text.
        for uri in [
            "ws://host/\u{200b}",
            "ws://host/\u{202e}",
            "ws://host/\u{2066}",
            "ws://host/\u{feff}",
            "ws://h\u{00f6}st/path",
            "ws://host/\u{001b}",
            "ws://host/\u{0000}",
            "ws://host/\u{007f}",
            "ws://host/\n",
            "ws://host/\r",
        ] {
            assert_eq!(
                endpoint(EndpointKind::WebSocketGateway, uri),
                Err(EndpointError::InvalidUri)
            );
        }
    }

    #[test]
    fn gateway_authority_requires_a_host_without_userinfo() {
        // Mutation: accept nonempty authority text as a host, allowing userinfo or a port with no host.
        for uri in [
            "ws://@x",
            "ws://:",
            "ws://:80",
            "ws:///path",
            "ws://?query",
            "ws://#fragment",
            "ws://user@host/path",
            "ws://host:",
            "ws://host:65536/path",
            "ws://[]:80/path",
            "ws://[::1/path",
            "ws://[::1]:",
            "ws://[::1]extra/path",
            "ws://a b/path",
            "http://host/path",
        ] {
            assert_eq!(
                endpoint(EndpointKind::WebSocketGateway, uri),
                Err(EndpointError::InvalidUri)
            );
        }
        for uri in [
            "ws://host",
            "ws://voice-gateway.lan/xiaozhi",
            "ws://host:0/",
            "ws://host:65535/",
            "ws://[::1]:8000/rpp",
        ] {
            assert!(endpoint(EndpointKind::WebSocketGateway, uri).is_ok());
        }
    }

    #[test]
    fn every_endpoint_kind_requires_a_nonempty_hierarchical_host() {
        // Mutation: apply authority/userinfo checks only to WebSocket gateways.
        for kind in KINDS {
            for uri in ["host-only", "ws://", "ws://:", "ws://user@host/path"] {
                assert_eq!(endpoint(kind, uri), Err(EndpointError::InvalidUri));
            }
        }
        assert!(endpoint(EndpointKind::Ble, "bt://AA:BB:CC:DD:EE:FF/control").is_ok());
        assert!(endpoint(EndpointKind::Lora, "lora://fleet:channel/1").is_ok());
        assert!(endpoint(EndpointKind::Internet, "ipv6://[2001:db8::1]:9000/rpp").is_ok());
    }

    #[test]
    fn printable_ascii_path_boundaries_remain_accepted() {
        // Mutation: reject the permitted printable ASCII space or tilde boundary in path metadata.
        assert!(endpoint(EndpointKind::WebSocketGateway, "ws://host/ ~").is_ok());
        assert_eq!(
            endpoint(EndpointKind::WebSocketGateway, "ws:// host/path"),
            Err(EndpointError::InvalidUri)
        );
    }

    #[test]
    fn fleet_reading_rejects_sentinels_without_changing_core_validity() {
        // Mutation: delegate only to core ppm validation and allow u64::MAX latency/jitter sentinels.
        for invalid in [
            LinkReading {
                latency_ms: u64::MAX,
                ..reading()
            },
            LinkReading {
                jitter_ms: u64::MAX,
                ..reading()
            },
        ] {
            assert!(invalid.valid());
            assert_eq!(
                validate_reading(invalid),
                Err(EndpointError::InvalidReading)
            );
            assert_eq!(
                Endpoint::new(
                    1,
                    EndpointKind::Lan,
                    "lan://host",
                    invalid,
                    EndpointCapabilities::default()
                ),
                Err(EndpointError::InvalidReading)
            );
        }
        assert_eq!(
            validate_reading(LinkReading {
                loss_ppm: 1_000_001,
                ..reading()
            }),
            Err(EndpointError::InvalidReading)
        );
        assert_eq!(
            validate_reading(LinkReading {
                latency_ms: u64::MAX - 1,
                jitter_ms: u64::MAX - 1,
                loss_ppm: 1_000_000,
                ..reading()
            }),
            Ok(())
        );
    }

    #[test]
    fn literal_endpoint_readings_share_constructor_validation() {
        // Mutation: validate sentinels in new() but let public struct fields bypass validate().
        let mut value = endpoint(EndpointKind::Lan, "lan://host").unwrap();
        value.last_reading.latency_ms = u64::MAX;
        assert_eq!(value.validate(), Err(EndpointError::InvalidReading));
        value.last_reading = LinkReading {
            jitter_ms: u64::MAX,
            ..reading()
        };
        assert_eq!(value.validate(), Err(EndpointError::InvalidReading));
    }
}
