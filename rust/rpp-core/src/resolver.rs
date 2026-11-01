//! Pure modality selection over discovery and attempt outcomes supplied by a host.
//!
//! This does not discover endpoints, authenticate a caller, perform I/O, cache
//! data or implement a network adapter. Input discovery/outcomes must concern
//! the requested address; the identity layer supplies the consent/trust gate.

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Modality {
    Ipv4,
    Ipv6,
    File,
    S3,
    Redis,
    Spintronic,
    LoRaWan,
    Ipfs,
    Quantum,
    Bluetooth,
    Hedera,
    Unknown,
}

impl Modality {
    pub fn scheme(self) -> &'static str {
        match self {
            Self::Ipv4 => "ipv4",
            Self::Ipv6 => "ipv6",
            Self::File => "file",
            Self::S3 => "s3",
            Self::Redis => "redis",
            Self::Spintronic => "spintronic",
            Self::LoRaWan => "lora",
            Self::Ipfs => "ipfs",
            Self::Quantum => "quantum",
            Self::Bluetooth => "bt",
            Self::Hedera => "hedera",
            Self::Unknown => "unknown",
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct AccessGate {
    pub authorized: bool,
    pub consented: bool,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DiscoveredEndpoint {
    pub modality: Modality,
    pub uri: String,
    pub available: bool,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum AttemptResult {
    Found,
    NotFound,
    Unavailable,
    Denied,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct AttemptOutcome {
    pub modality: Modality,
    pub result: AttemptResult,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ResolutionErrorCode {
    ConsentDenied,
    TrustDenied,
    AdapterDenied,
    NoModality,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ResolvedLocation {
    pub modality: Modality,
    pub uri: String,
    pub tried_modalities: Vec<Modality>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ResolutionError {
    pub code: ResolutionErrorCode,
    pub tried_modalities: Vec<Modality>,
}

/// Missing discovery or attempt input is unavailable; it never implies success.
/// Each selected modality is recorded once, including unavailable resolution
/// attempts. NotFound/Unavailable fall through; a denial terminates selection.
pub fn resolve(
    discovered: &[DiscoveredEndpoint],
    preferred_modalities: Option<&[Modality]>,
    default_order: &[Modality],
    outcomes: &[AttemptOutcome],
    gate: AccessGate,
) -> Result<ResolvedLocation, ResolutionError> {
    let fail = |code, tried_modalities| {
        Err(ResolutionError {
            code,
            tried_modalities,
        })
    };
    if !gate.consented {
        return fail(ResolutionErrorCode::ConsentDenied, Vec::new());
    }
    if !gate.authorized {
        return fail(ResolutionErrorCode::TrustDenied, Vec::new());
    }
    let order = preferred_modalities.unwrap_or(default_order);
    let mut tried = Vec::new();
    for modality in order {
        if tried.contains(modality) {
            continue;
        }
        tried.push(*modality);
        if *modality == Modality::Unknown {
            continue;
        }
        let prefix = format!("{}://", modality.scheme());
        let Some(endpoint) = discovered.iter().find(|endpoint| {
            endpoint.modality == *modality
                && endpoint.available
                && endpoint.uri.starts_with(&prefix)
                && endpoint.uri.len() > prefix.len()
        }) else {
            continue;
        };
        let Some(outcome) = outcomes
            .iter()
            .find(|outcome| outcome.modality == *modality)
        else {
            continue;
        };
        match outcome.result {
            AttemptResult::Found => {
                return Ok(ResolvedLocation {
                    modality: *modality,
                    uri: endpoint.uri.clone(),
                    tried_modalities: tried,
                })
            }
            AttemptResult::NotFound | AttemptResult::Unavailable => {}
            AttemptResult::Denied => return fail(ResolutionErrorCode::AdapterDenied, tried),
        }
    }
    fail(ResolutionErrorCode::NoModality, tried)
}
