//! Endpoint metadata and prior capability inputs, without transport drivers.
//!
//! A WebSocket gateway is a caller-declared LAN profile. Its `ws://` URI is
//! descriptive; the scheme proves neither locality nor authenticated reachability.

use alloc::{format, string::String};
use rpp_core::overlay::Underlay;
use rpp_link::{LinkKind, LinkReading};

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
    InvalidUri,
    InvalidReading,
}

impl Endpoint {
    pub fn new(
        id: u32,
        kind: EndpointKind,
        uri: impl Into<String>,
        last_reading: LinkReading,
        capabilities: EndpointCapabilities,
    ) -> Result<Self, EndpointError> {
        let endpoint = Self {
            id,
            kind,
            uri: uri.into(),
            last_reading,
            capabilities,
        };
        endpoint.validate()?;
        Ok(endpoint)
    }

    pub fn valid(&self) -> bool {
        self.validate().is_ok()
    }

    pub fn validate(&self) -> Result<(), EndpointError> {
        if self.uri.is_empty() || self.uri.chars().any(char::is_control) {
            return Err(EndpointError::InvalidUri);
        }
        if self.kind == EndpointKind::WebSocketGateway {
            let authority = self
                .uri
                .strip_prefix("ws://")
                .unwrap_or("")
                .split('/')
                .next()
                .unwrap_or("");
            if authority.is_empty() || authority.chars().any(char::is_whitespace) {
                return Err(EndpointError::InvalidUri);
            }
        }
        if !self.last_reading.valid() {
            return Err(EndpointError::InvalidReading);
        }
        Ok(())
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
