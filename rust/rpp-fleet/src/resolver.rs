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
        let admitted = members.iter().map(NodeIdentity::label).collect();
        let consent_pairs = consents
            .iter()
            .map(|(a, b)| (a.label(), b.label()))
            .collect();
        Self {
            registry,
            source,
            source_label: source.label(),
            auth,
            policy: Simulator::new(admitted, consent_pairs, BTreeSet::new()),
            current_data: BTreeMap::new(),
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
        // Ask the existing policy to classify authorization/time using no paths.
        // The clone keeps this explanatory denial/no-channel probe out of the
        // real request/sequence state and avoids a second authorization matrix.
        let target_label = target.label();
        let mut gate = self.policy.clone();
        gate.send_data(
            i128::from(tick),
            &self.source_label,
            &target_label,
            &[],
            &BTreeMap::new(),
        );
        match gate.rows().last().map(|row| row.status) {
            Some(Status::Denied | Status::DeniedSelfTarget) => {
                return Ok(DataResolution {
                    status: ResolutionStatus::Denied,
                    routes: Vec::new(),
                })
            }
            Some(Status::InvalidInput) => return Err(FleetResolveError::ClockRollback),
            Some(Status::NoChannel) => {}
            _ => return Err(FleetResolveError::CorePolicy),
        }
        let links: Vec<_> = entries.iter().map(|(_, link)| link.clone()).collect();
        let first = self
            .policy
            .choose(&self.source_label, &target_label, i128::from(tick), &links)
            .map_err(|_| FleetResolveError::CorePolicy)?;
        if first.is_empty() {
            // Keep the last selected reference during an outage: independent
            // STOP/PAUSE can still concern the last active data path.
            return Ok(DataResolution {
                status: ResolutionStatus::NoChannel,
                routes: Vec::new(),
            });
        }
        self.current_data.insert(target, first.clone());
        let mut routes = Vec::new();
        let mut remaining = entries;
        let mut chosen = first;
        let mut preview = self.policy.clone();
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
            chosen = preview
                .choose(
                    &self.source_label,
                    &target_label,
                    i128::from(tick),
                    &alternatives,
                )
                .map_err(|_| FleetResolveError::CorePolicy)?;
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
        let current = self
            .current_data
            .get(&target)
            .filter(|current| current.as_slice() == known_data);
        // This is the historical last-successful data-path reference, retained
        // through outages until a newer selection replaces it. Its storage has
        // no extra TTL; current control-link freshness and all independence,
        // authorization and identity checks remain the core policy's contract.
        let reference = current.map_or(&[][..], Vec::as_slice);
        let kind = match frame.kind() {
            WireControlKind::Alive => ControlKind::Alive,
            WireControlKind::MemberChanged => ControlKind::MemberChanged,
            WireControlKind::Stop => ControlKind::Stop,
            WireControlKind::Pause => ControlKind::Pause,
            WireControlKind::RouteAround => ControlKind::RouteAround,
            WireControlKind::Resume => ControlKind::Resume,
        };
        let before = self.policy.clone();
        let notice =
            ControlFrame::notice(&self.source_label, &target.label(), kind, frame.sequence());
        let row = self.policy.send_control(
            i128::from(tick),
            &notice,
            Some(&self.auth),
            &links,
            reference,
        );
        let mut failover_order = Vec::new();
        if row.status == Status::Ok {
            let mut remaining = entries.clone();
            loop {
                // Every preview begins from PRE-CALL state. Only core policy
                // chooses alternatives; no extra real sequence/clock is spent.
                let mut preview = before.clone();
                let candidate_links = remaining
                    .iter()
                    .map(|(_, link)| link.clone())
                    .collect::<Vec<_>>();
                let candidate = preview.send_control(
                    i128::from(tick),
                    &notice,
                    Some(&self.auth),
                    &candidate_links,
                    reference,
                );
                if candidate.status != Status::Ok {
                    break;
                }
                let selected = remaining
                    .iter()
                    .find(|(_, link)| link.name == candidate.path)
                    .ok_or(FleetResolveError::RouteMismatch)?;
                failover_order.push(selected.0.id);
                remaining.retain(|(_, link)| link.name != candidate.path);
            }
        }
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
            Status::InvalidInput => return Err(FleetResolveError::ClockRollback),
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
