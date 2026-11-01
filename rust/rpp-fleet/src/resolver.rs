//! Fleet records adapted to the existing deterministic overlay policy.
//!
//! This layer adds no score, threshold, transport, cipher or discovery service.
//! Registry presence never supplies admission or consent. Direct endpoint links
//! are the current record scope; multi-hop relay topology remains outside it.

use alloc::{
    collections::{BTreeMap, BTreeSet},
    string::String,
    vec::Vec,
};
use rpp_control::{ControlKind as WireControlKind, VerifiedControlFrame};
use rpp_core::overlay::{Auth, ControlFrame, ControlKind, Link, MeterRow, Simulator, Status};
use rpp_link::{
    dispatch, DispatchError, DispatchOutcome, LinkAdapter, LinkReading, Outbound, TrafficPath,
};

use crate::{
    endpoint::{Endpoint, EndpointKind},
    identity::NodeIdentity,
    limits::MAX_RETAINED_METER_ROWS,
    registry::{Registry, RegistryError},
};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ResolutionStatus {
    Ready,
    Denied,
    NoChannel,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum FleetResolveError {
    UnregisteredSource,
    UnregisteredTarget,
    InvalidEndpoint,
    ClockRollback,
    InvalidInput,
    InvalidDataReference,
    ControlOnDataPath,
    FrameIdentityMismatch,
    CorePolicy,
    RouteMismatch,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ResolvedEndpoint {
    pub endpoint_id: u32,
    pub kind: EndpointKind,
    pub uri: String,
    path: Vec<Link>,
}

impl ResolvedEndpoint {
    pub fn path(&self) -> &[Link] {
        &self.path
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DataResolution {
    pub status: ResolutionStatus,
    pub routes: Vec<ResolvedEndpoint>,
}

impl DataResolution {
    pub fn selected(&self) -> Option<&ResolvedEndpoint> {
        self.routes.first()
    }
    pub fn failover_order(&self) -> Vec<u32> {
        self.routes.iter().map(|x| x.endpoint_id).collect()
    }
}

/// A checked control route retains the already-verified frame and provides only
/// a control-path dispatch handoff. It cannot be constructed by a caller.
/// The host must bind its adapter to this endpoint and check current host
/// authorization before physical effects. Core acceptance reserves model
/// sequence/state; it is not a transport receipt.
#[derive(Debug, Eq, PartialEq)]
pub struct VerifiedControlRoute<'frame> {
    endpoint: ResolvedEndpoint,
    frame: &'frame VerifiedControlFrame,
}

#[derive(Debug, Eq, PartialEq)]
pub enum ControlDispatchError<E> {
    AdapterKindMismatch,
    Link(DispatchError<E>),
}

impl<'frame> VerifiedControlRoute<'frame> {
    pub fn endpoint(&self) -> &ResolvedEndpoint {
        &self.endpoint
    }
    pub fn frame(&self) -> &'frame VerifiedControlFrame {
        self.frame
    }
    pub fn dispatch<A: LinkAdapter>(
        self,
        adapter: &mut A,
    ) -> Result<DispatchOutcome, ControlDispatchError<A::Error>> {
        if adapter.kind() != self.endpoint.kind.link_kind() {
            return Err(ControlDispatchError::AdapterKindMismatch);
        }
        dispatch(adapter, TrafficPath::Control, Outbound::Control(self.frame))
            .map_err(ControlDispatchError::Link)
    }
}

#[derive(Debug, Eq, PartialEq)]
pub struct ControlResolution<'frame> {
    pub status: ResolutionStatus,
    pub route: Option<VerifiedControlRoute<'frame>>,
    /// Informational alternatives only: no dispatch/retry capability is issued.
    pub failover_order: Vec<u32>,
    pub meter: MeterRow,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct FleetResolverStats {
    pub retained_meter_rows: usize,
    pub known_data_references: usize,
    pub current_data_references: usize,
    pub admitted_members: usize,
    pub consent_pairs: usize,
}

pub struct FleetResolver<'registry> {
    registry: &'registry mut Registry,
    source: NodeIdentity,
    source_label: String,
    auth: Auth,
    policy: Simulator,
    current_data: BTreeMap<NodeIdentity, Vec<Link>>,
}

impl<'registry> FleetResolver<'registry> {
    /// Members, consent pairs and Auth are prior host decisions, not facts
    /// inferred from registration, URI, keys or an address assignment.
    pub fn new(
        registry: &'registry mut Registry,
        source: NodeIdentity,
        auth: Auth,
        members: &[NodeIdentity],
        consents: &[(NodeIdentity, NodeIdentity)],
    ) -> Self {
        // Filter and deduplicate opaque identities before allocating labels.
        // Registration is only an upper bound: it supplies no extra admission
        // or consent beyond the caller's explicit inputs.
        let admitted_ids: BTreeSet<_> = members
            .iter()
            .copied()
            .filter(|identity| registry.get(identity).is_some())
            .collect();
        let consent_ids: BTreeSet<_> = consents
            .iter()
            .copied()
            .filter(|(a, b)| registry.get(a).is_some() && registry.get(b).is_some())
            .collect();
        let admitted = admitted_ids.iter().map(NodeIdentity::label).collect();
        let consent_pairs = consent_ids
            .iter()
            .map(|(a, b)| (a.label(), b.label()))
            .collect();
        let source_label = source.label();
        // Invalid prior context is denied without retaining caller-controlled
        // String capacity. Reconstruct the valid label instead of keeping it.
        let auth = if auth.signature_verified && auth.issuer == source_label {
            Auth {
                issuer: source_label.clone(),
                signature_verified: true,
            }
        } else {
            Auth {
                issuer: String::new(),
                signature_verified: false,
            }
        };
        Self {
            registry,
            source,
            source_label,
            auth,
            policy: Simulator::new(admitted, consent_pairs, BTreeSet::new()),
            current_data: BTreeMap::new(),
        }
    }

    pub fn stats(&self) -> FleetResolverStats {
        FleetResolverStats {
            retained_meter_rows: self.policy.rows().len(),
            known_data_references: self.policy.known_data_path_count(),
            current_data_references: self.current_data.len(),
            admitted_members: self.policy.members().len(),
            consent_pairs: self.policy.consents().len(),
        }
    }

    fn invalid_input_error(&self, tick: u64) -> FleetResolveError {
        if tick < self.policy.clock() {
            FleetResolveError::ClockRollback
        } else {
            FleetResolveError::InvalidInput
        }
    }

    /// Structural registry bindings stay borrowed for this policy lifetime.
    pub fn registry(&self) -> &Registry {
        self.registry
    }

    /// Live readings can change through the registry's validated update, without
    /// replacing identities, canonical bindings or endpoint ownership.
    pub fn update_reading(
        &mut self,
        identity: &NodeIdentity,
        endpoint_id: u32,
        reading: LinkReading,
    ) -> Result<(), RegistryError> {
        self.registry.update_reading(identity, endpoint_id, reading)
    }

    pub fn policy_rows(&self) -> &[MeterRow] {
        self.policy.rows()
    }

    fn endpoint_links(
        &self,
        target: NodeIdentity,
    ) -> Result<Vec<(Endpoint, Link)>, FleetResolveError> {
        if self.registry.get(&self.source).is_none() {
            return Err(FleetResolveError::UnregisteredSource);
        }
        let node = self
            .registry
            .get(&target)
            .ok_or(FleetResolveError::UnregisteredTarget)?;
        let target_label = target.label();
        let target_word = node.address().to_word();
        let mut seen = BTreeSet::new();
        let mut links = Vec::new();
        for endpoint in node.endpoints() {
            if !endpoint.valid() || !seen.insert(endpoint.id) {
                return Err(FleetResolveError::InvalidEndpoint);
            }
            let mut link = Link::new(
                &endpoint.link_name(target_word),
                &self.source_label,
                &target_label,
                endpoint.kind.underlay(),
            );
            let reading = endpoint.last_reading;
            link.latency = reading.latency_ms;
            link.loss_ppm = reading.loss_ppm;
            link.jitter = reading.jitter_ms;
            link.available = reading.available;
            link.observed = reading.observed;
            link.failure_domain = endpoint.failure_domain_name();
            link.tunnel_verified = endpoint.capabilities.tunnel_verified;
            link.reviewed_adapter = endpoint.capabilities.reviewed_adapter;
            link.observation_verified = endpoint.capabilities.observation_verified;
            links.push((endpoint.clone(), link));
        }
        Ok(links)
    }

    fn resolved(endpoint: &Endpoint, path: Vec<Link>) -> ResolvedEndpoint {
        ResolvedEndpoint {
            endpoint_id: endpoint.id,
            kind: endpoint.kind,
            uri: endpoint.uri.clone(),
            path,
        }
    }

    pub fn resolve_data(
        &mut self,
        target: NodeIdentity,
        tick: u64,
    ) -> Result<DataResolution, FleetResolveError> {
        let entries = self.endpoint_links(target)?;
        if !self.auth.signature_verified || self.auth.issuer != self.source_label {
            return Ok(DataResolution {
                status: ResolutionStatus::Denied,
                routes: Vec::new(),
            });
        }
        let target_label = target.label();
        let links: Vec<_> = entries.iter().map(|(_, link)| link.clone()).collect();
        // Read-only core preview classifies the same request without cloning
        // retained history or allocating a throwaway meter/request record.
        let selection =
            self.policy
                .preview_data(i128::from(tick), &self.source_label, &target_label, &links);
        match selection.status {
            Status::Denied | Status::DeniedSelfTarget => {
                return Ok(DataResolution {
                    status: ResolutionStatus::Denied,
                    routes: Vec::new(),
                })
            }
            Status::InvalidInput => return Err(self.invalid_input_error(tick)),
            Status::NoChannel => {
                return Ok(DataResolution {
                    status: ResolutionStatus::NoChannel,
                    routes: Vec::new(),
                })
            }
            Status::Ok => {}
            _ => return Err(FleetResolveError::CorePolicy),
        }
        let first = self
            .policy
            .choose_latest(&self.source_label, &target_label, i128::from(tick), &links)
            .map_err(|_| self.invalid_input_error(tick))?;
        if first.is_empty() {
            return Err(FleetResolveError::CorePolicy);
        }
        self.current_data.insert(target, first.clone());
        let mut routes = Vec::new();
        let mut remaining = entries;
        let mut chosen = first;
        loop {
            // Fleet endpoints are direct links. Match the complete generated
            // name, never split opaque URI text or arbitrary user names.
            let selected = remaining
                .iter()
                .find(|(_, link)| chosen.len() == 1 && link.name == chosen[0].name)
                .ok_or(FleetResolveError::RouteMismatch)?;
            routes.push(Self::resolved(&selected.0, chosen.clone()));
            remaining.retain(|(_, link)| !chosen.iter().any(|used| used.name == link.name));
            let alternatives: Vec<_> = remaining.iter().map(|(_, link)| link.clone()).collect();
            let alternative = self.policy.preview_data(
                i128::from(tick),
                &self.source_label,
                &target_label,
                &alternatives,
            );
            chosen = match alternative.status {
                Status::Ok => alternative.path,
                Status::NoChannel => Vec::new(),
                Status::InvalidInput => return Err(self.invalid_input_error(tick)),
                _ => return Err(FleetResolveError::CorePolicy),
            };
            if chosen.is_empty() {
                break;
            }
        }
        Ok(DataResolution {
            status: ResolutionStatus::Ready,
            routes,
        })
    }

    pub fn resolve_control<'frame>(
        &mut self,
        target: NodeIdentity,
        tick: u64,
        frame: &'frame VerifiedControlFrame,
        known_data: &[Link],
        path: TrafficPath,
    ) -> Result<ControlResolution<'frame>, FleetResolveError> {
        self.policy.retain_meter_rows(MAX_RETAINED_METER_ROWS);
        // Preserve this guard before any accepted sequence/state transition.
        if path == TrafficPath::Data {
            return Err(FleetResolveError::ControlOnDataPath);
        }
        if frame.sender() != self.source.device_id() || frame.recipient() != target.device_id() {
            return Err(FleetResolveError::FrameIdentityMismatch);
        }
        // Compatibility is a prior endpoint capability. All authorization,
        // known-path, failure-domain, tunnel, replay and ranking checks stay in
        // the existing core control policy.
        let entries: Vec<_> = self
            .endpoint_links(target)?
            .into_iter()
            .filter(|(endpoint, _)| endpoint.capabilities.control_capable)
            .collect();
        let links = entries
            .iter()
            .map(|(_, link)| link.clone())
            .collect::<Vec<_>>();
        // Reject absent, forged, wrong-target and superseded references as an
        // explicit caller error before any core sequence, request or clock state.
        let reference = self
            .current_data
            .get(&target)
            .filter(|current| !known_data.is_empty() && current.as_slice() == known_data)
            .ok_or(FleetResolveError::InvalidDataReference)?
            .as_slice();
        // This historical last-successful reference has no new TTL. Current
        // control eligibility and independence stay entirely in core policy.
        let kind = match frame.kind() {
            WireControlKind::Alive => ControlKind::Alive,
            WireControlKind::MemberChanged => ControlKind::MemberChanged,
            WireControlKind::Stop => ControlKind::Stop,
            WireControlKind::Pause => ControlKind::Pause,
            WireControlKind::RouteAround => ControlKind::RouteAround,
            WireControlKind::Resume => ControlKind::Resume,
        };
        let notice =
            ControlFrame::notice(&self.source_label, &target.label(), kind, frame.sequence());
        let mut failover_order = Vec::new();
        let mut remaining = entries
            .iter()
            .map(|(_, link)| link.clone())
            .collect::<Vec<_>>();
        loop {
            // Immutable core preview uses the unchanged PRE-CALL sequence and
            // clock context, without copying retained simulator state.
            let candidate = self.policy.preview_control(
                i128::from(tick),
                &notice,
                Some(&self.auth),
                &remaining,
                reference,
            );
            if candidate.status != Status::Ok {
                break;
            }
            let selected = entries
                .iter()
                .find(|(_, link)| candidate.path.len() == 1 && link.name == candidate.path[0].name)
                .ok_or(FleetResolveError::RouteMismatch)?;
            failover_order.push(selected.0.id);
            remaining.retain(|link| !candidate.path.iter().any(|chosen| chosen.name == link.name));
        }
        // Exactly one real transition; returned rows retain their global IDs
        // while this bounded local diagnostic window drops older copies.
        let row = self.policy.send_control(
            i128::from(tick),
            &notice,
            Some(&self.auth),
            &links,
            reference,
        );
        self.policy.retain_meter_rows(MAX_RETAINED_METER_ROWS);
        let (status, route) = match row.status {
            Status::Ok => {
                let endpoint = entries
                    .iter()
                    .find(|(_, link)| link.name == row.path)
                    .ok_or(FleetResolveError::RouteMismatch)?;
                let resolved = Self::resolved(&endpoint.0, alloc::vec![endpoint.1.clone()]);
                (
                    ResolutionStatus::Ready,
                    Some(VerifiedControlRoute {
                        endpoint: resolved,
                        frame,
                    }),
                )
            }
            Status::Denied | Status::DeniedSelfTarget => (ResolutionStatus::Denied, None),
            Status::NoIndependentChannel | Status::NoChannel => (ResolutionStatus::NoChannel, None),
            Status::InvalidInput => return Err(self.invalid_input_error(tick)),
            _ => return Err(FleetResolveError::CorePolicy),
        };
        Ok(ControlResolution {
            status,
            route,
            failover_order,
            meter: row,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn malformed_core_input_at_current_clock_is_not_clock_rollback() {
        // Mutation invalid-input-as-rollback: a non-past CoreInvalidInput must
        // remain generic InvalidInput; integration tests cover actual rollback.
        let mut registry = Registry::new();
        let source = NodeIdentity::new([1; 16], [2; 16]);
        let auth = Auth::fixture(&source.label(), true);
        let resolver = FleetResolver::new(&mut registry, source, auth, &[], &[]);
        assert_eq!(
            resolver.invalid_input_error(0),
            FleetResolveError::InvalidInput
        );
        assert_eq!(
            resolver.invalid_input_error(1),
            FleetResolveError::InvalidInput
        );
    }
}
