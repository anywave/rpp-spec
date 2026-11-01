//! Host-only deterministic adapters. No sockets, HAL, Bluetooth, LoRa or board code.
//! Readings and send outcomes are fixtures. rpp-control's verifier below compares
//! predeclared fixture bytes; it implements no signing algorithm or cryptography.
//!
//! Successful sampling leads to complete CX007 policy-request rows. A sampling
//! error or unmapped control identity returns HostError before a policy request;
//! the host caller must meter that boundary rejection. Clock rollback is passed
//! to CX007 and retains its INVALID_INPUT row, with no adapter send. Billboard
//! transport-failure fixtures are unsupported and rejected before storage/send.
//! Adapter names containing `/` are a rejected host-fixture limitation because
//! CX007 meter paths use that separator; rejection precedes every read/policy/send
//! callback. This narrows the host adapter domain without changing core names.

use std::{
    collections::{BTreeMap, BTreeSet},
    string::{String, ToString},
    vec,
    vec::Vec,
};

use rpp_control::{
    decode, ControlFrame as WireControlFrame, ControlKind as WireControlKind, NodeId, Signature,
    VerifiedControlFrame, Verifier, HEADER_LEN,
};
use rpp_core::{
    overlay::{
        Auth, Billboard, BillboardKind, ControlFrame, ControlKind, Link, MeterRow, Simulator,
        Status, Underlay,
    },
    scenarios::{self, Artifacts, ScenarioRun},
};

use crate::{
    dispatch, DataOutcome, DispatchOutcome, LinkAdapter, LinkKind, LinkReading, Outbound,
    TrafficPath,
};

pub const A_ID: NodeId = [b'A'; 16];
pub const B_ID: NodeId = [b'B'; 16];
pub const R_ID: NodeId = [b'R'; 16];

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum AdapterError {
    InvalidReading,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum SendRecord {
    Data {
        bytes: usize,
        outcome: DataOutcome,
    },
    Control {
        kind: WireControlKind,
        sequence: u64,
    },
}

#[derive(Clone, Debug)]
pub struct SimulatedAdapter {
    metadata: Link,
    reading: LinkReading,
    data_outcome: DataOutcome,
    reads: u64,
    sent: Vec<SendRecord>,
}

impl SimulatedAdapter {
    pub fn from_link(link: Link) -> Self {
        let reading = LinkReading {
            latency_ms: link.latency,
            loss_ppm: link.loss_ppm,
            jitter_ms: link.jitter,
            available: link.available,
            observed: link.observed,
        };
        Self {
            metadata: link,
            reading,
            data_outcome: DataOutcome::Sent,
            reads: 0,
            sent: Vec::new(),
        }
    }
    pub fn with_reading(mut self, reading: LinkReading) -> Self {
        self.reading = reading;
        self
    }
    pub fn with_outcome(mut self, outcome: DataOutcome) -> Self {
        self.data_outcome = outcome;
        self
    }
    pub fn reads(&self) -> u64 {
        self.reads
    }
    pub fn sent(&self) -> &[SendRecord] {
        &self.sent
    }
    pub fn name(&self) -> &str {
        &self.metadata.name
    }
}

impl LinkAdapter for SimulatedAdapter {
    type Error = AdapterError;
    fn kind(&self) -> LinkKind {
        match self.metadata.underlay {
            Underlay::Lan => LinkKind::Lan,
            Underlay::Wifi => LinkKind::Wifi,
            Underlay::Bluetooth => LinkKind::Ble,
            Underlay::Lora => LinkKind::Lora,
            Underlay::Internet => LinkKind::Internet,
        }
    }
    fn read(&mut self, _tick: u64) -> Result<LinkReading, Self::Error> {
        self.reads += 1;
        if !self.reading.valid() {
            return Err(AdapterError::InvalidReading);
        }
        Ok(self.reading)
    }
    fn send_verified_control_frame(
        &mut self,
        frame: &VerifiedControlFrame,
    ) -> Result<(), Self::Error> {
        self.sent.push(SendRecord::Control {
            kind: frame.kind(),
            sequence: frame.sequence(),
        });
        Ok(())
    }
    fn send_data(&mut self, payload: &[u8]) -> Result<DataOutcome, Self::Error> {
        self.sent.push(SendRecord::Data {
            bytes: payload.len(),
            outcome: self.data_outcome,
        });
        Ok(self.data_outcome)
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum HostError {
    Reading(AdapterError),
    Policy,
    MissingAdapter,
    Dispatch,
    UnknownIdentity,
    OutcomeMismatch,
    UnsupportedBillboardFailure,
    UnsupportedLinkName,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Attempt {
    pub path: String,
    pub failed_tokens: Option<u64>,
}

#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct AdapterAudit {
    pub readings: u64,
    pub data_hops: u64,
    pub control_hops: u64,
    pub attempts: Vec<Attempt>,
}

pub struct HostBridge {
    policy: Simulator,
    identities: BTreeMap<NodeId, String>,
    audit: AdapterAudit,
}

impl HostBridge {
    pub fn new(policy: Simulator, identities: BTreeMap<NodeId, String>) -> Self {
        Self {
            policy,
            identities,
            audit: AdapterAudit::default(),
        }
    }
    pub fn policy(&self) -> &Simulator {
        &self.policy
    }
    pub fn audit(&self) -> &AdapterAudit {
        &self.audit
    }

    fn sample(
        &mut self,
        tick: u64,
        adapters: &mut [SimulatedAdapter],
    ) -> Result<Vec<Link>, HostError> {
        // Validate the whole bank before reading any adapter: slash-delimited
        // CX007 meter routes cannot safely identify a literal slash-named link.
        if adapters.iter().any(|adapter| adapter.name().contains('/')) {
            return Err(HostError::UnsupportedLinkName);
        }
        let mut links = Vec::new();
        for adapter in adapters {
            let reading = adapter.read(tick).map_err(HostError::Reading)?;
            self.audit.readings += 1;
            let mut link = adapter.metadata.clone();
            link.underlay = match adapter.kind() {
                LinkKind::Lan => Underlay::Lan,
                LinkKind::Wifi => Underlay::Wifi,
                LinkKind::Ble => Underlay::Bluetooth,
                LinkKind::Lora => Underlay::Lora,
                LinkKind::Internet => Underlay::Internet,
            };
            link.latency = reading.latency_ms;
            link.loss_ppm = reading.loss_ppm;
            link.jitter = reading.jitter_ms;
            link.available = reading.available;
            link.observed = reading.observed;
            links.push(link);
        }
        Ok(links)
    }

    pub fn choose_data_reference(
        &mut self,
        tick: u64,
        source: &str,
        target: &str,
        adapters: &mut [SimulatedAdapter],
    ) -> Result<Vec<Link>, HostError> {
        let links = self.sample(tick, adapters)?;
        self.policy
            .choose(source, target, i128::from(tick), &links)
            .map_err(|_| HostError::Policy)
    }

    pub fn send_data(
        &mut self,
        tick: u64,
        source: &str,
        target: &str,
        adapters: &mut [SimulatedAdapter],
    ) -> Result<(), HostError> {
        let links = self.sample(tick, adapters)?;
        let start = self.policy.rows().len();
        let mut failures = BTreeMap::new();
        let mut attempts = Vec::new();
        // Validate before any dispatch. choose() performs membership, endpoint
        // consent, relay consent, freshness, tunnel and breaker checks.
        if tick >= self.policy.clock()
            && links.iter().all(Link::valid)
            && links.iter().map(|x| &x.name).collect::<BTreeSet<_>>().len() == links.len()
        {
            let mut excluded = BTreeSet::new();
            loop {
                let remaining: Vec<_> = links
                    .iter()
                    .filter(|x| !excluded.contains(&x.name))
                    .cloned()
                    .collect();
                let path = self
                    .policy
                    .choose(source, target, i128::from(tick), &remaining)
                    .map_err(|_| HostError::Policy)?;
                if path.is_empty() {
                    break;
                }
                let mut failure = None;
                for hop in &path {
                    let adapter = adapters
                        .iter_mut()
                        .find(|x| x.name() == hop.name)
                        .ok_or(HostError::MissingAdapter)?;
                    let sent = dispatch(
                        adapter,
                        TrafficPath::Data,
                        Outbound::Data(b"opaque-data-fixture"),
                    )
                    .map_err(|_| HostError::Dispatch)?;
                    self.audit.data_hops += 1;
                    match sent {
                        DispatchOutcome::Data(DataOutcome::Sent) => {}
                        DispatchOutcome::Data(DataOutcome::Failed { emitted_tokens }) => {
                            failures.insert(hop.name.clone(), i128::from(emitted_tokens));
                            failure = Some((hop.name.clone(), emitted_tokens));
                            break;
                        }
                        DispatchOutcome::Control => return Err(HostError::Dispatch),
                    }
                }
                attempts.push(Attempt {
                    path: path
                        .iter()
                        .map(|x| x.name.as_str())
                        .collect::<Vec<_>>()
                        .join("/"),
                    failed_tokens: failure.as_ref().map(|x| x.1),
                });
                match failure {
                    Some((name, 0)) => {
                        excluded.insert(name);
                    }
                    Some((_, _)) | None => break,
                }
            }
        }
        // The actual adapter outcomes are now fed to the existing CX007 model,
        // rather than choosing routes by replaying a precomputed meter ledger.
        self.policy
            .send_data(i128::from(tick), source, target, &links, &failures);
        let model_attempts: Vec<_> = self.policy.rows()[start..]
            .iter()
            .filter(|r| matches!(r.status, Status::Ok | Status::Failed))
            .map(|r| Attempt {
                path: r.path.clone(),
                failed_tokens: (r.status == Status::Failed).then_some(r.tokens),
            })
            .collect();
        if attempts != model_attempts {
            return Err(HostError::OutcomeMismatch);
        }
        self.audit.attempts.extend(attempts);
        Ok(())
    }

    pub fn send_verified_control(
        &mut self,
        tick: u64,
        frame: &VerifiedControlFrame,
        adapters: &mut [SimulatedAdapter],
        data_path: &[Link],
    ) -> Result<MeterRow, HostError> {
        let source = self
            .identities
            .get(frame.sender())
            .ok_or(HostError::UnknownIdentity)?
            .clone();
        let target = self
            .identities
            .get(frame.recipient())
            .ok_or(HostError::UnknownIdentity)?
            .clone();
        let links = self.sample(tick, adapters)?;
        let kind = match frame.kind() {
            WireControlKind::Alive => ControlKind::Alive,
            WireControlKind::MemberChanged => ControlKind::MemberChanged,
            WireControlKind::Stop => ControlKind::Stop,
            WireControlKind::Pause => ControlKind::Pause,
            WireControlKind::RouteAround => ControlKind::RouteAround,
            WireControlKind::Resume => ControlKind::Resume,
        };
        let row = self.policy.send_control(
            i128::from(tick),
            &ControlFrame::notice(&source, &target, kind, frame.sequence()),
            Some(&Auth::fixture(&source, true)),
            &links,
            data_path,
        );
        if row.status == Status::Ok {
            for name in row.path.split('/') {
                let adapter = adapters
                    .iter_mut()
                    .find(|x| x.name() == name)
                    .ok_or(HostError::MissingAdapter)?;
                dispatch(adapter, TrafficPath::Control, Outbound::Control(frame))
                    .map_err(|_| HostError::Dispatch)?;
                self.audit.control_hops += 1;
            }
        }
        Ok(row)
    }

    pub fn send_billboard(
        &mut self,
        tick: u64,
        board: &Billboard,
        adapters: &mut [SimulatedAdapter],
    ) -> Result<MeterRow, HostError> {
        let links = self.sample(tick, adapters)?;
        // CX007's billboard model does not model partial transport failures.
        // Reject such a host fixture before policy storage or any send.
        if adapters
            .iter()
            .any(|adapter| adapter.data_outcome != DataOutcome::Sent)
        {
            return Err(HostError::UnsupportedBillboardFailure);
        }
        let row = self.policy.deliver_billboard(
            i128::from(tick),
            Some(board),
            Some(&Auth::fixture("A", true)),
            "A",
            "B",
            &links,
        );
        if matches!(row.status, Status::Delivered | Status::HeldUntilSince) {
            for name in row.path.split('/') {
                let adapter = adapters
                    .iter_mut()
                    .find(|x| x.name() == name)
                    .ok_or(HostError::MissingAdapter)?;
                dispatch(
                    adapter,
                    TrafficPath::Data,
                    Outbound::Data(b"opaque-billboard-fixture"),
                )
                .map_err(|_| HostError::Dispatch)?;
                self.audit.data_hops += 1;
            }
        }
        Ok(row)
    }

    fn reject_control_input(
        &mut self,
        tick: u64,
        kind: &str,
        adapters: &mut [SimulatedAdapter],
    ) -> Result<(), HostError> {
        let links = self.sample(tick, adapters)?;
        // Unsupported kinds have no rpp-control VerifiedControlFrame. This
        // accounts for the rejected request without an adapter send.
        self.policy.send_control(
            i128::from(tick),
            &ControlFrame::from_kind("A", "B", kind, 1),
            Some(&Auth::fixture("A", true)),
            &links,
            &[],
        );
        Ok(())
    }
}

struct ExactFixtureVerifier {
    sender: NodeId,
    header: [u8; HEADER_LEN],
    signature: Signature,
}
impl Verifier for ExactFixtureVerifier {
    fn verify(&self, sender: &NodeId, header: &[u8; HEADER_LEN], signature: &Signature) -> bool {
        sender == &self.sender && header == &self.header && signature == &self.signature
    }
}

/// Read-only verification fixture: byte equality is not a signature algorithm.
pub fn verified_fixture(kind: WireControlKind, sequence: u64) -> VerifiedControlFrame {
    let wire = WireControlFrame::new(kind, sequence, A_ID, B_ID, [0x5a; 64]);
    let verifier = ExactFixtureVerifier {
        sender: A_ID,
        header: wire.header(),
        signature: [0x5a; 64],
    };
    decode(&wire.encode(), &B_ID, &verifier).expect("fixed verification fixture")
}

fn adapter(name: &str, underlay: Underlay, tick: u64, latency: u64) -> SimulatedAdapter {
    let mut link = Link::new(name, "A", "B", underlay);
    link.observed = tick;
    link.latency = latency;
    SimulatedAdapter::from_link(link)
}
fn bank(links: Vec<Link>) -> Vec<SimulatedAdapter> {
    links.into_iter().map(SimulatedAdapter::from_link).collect()
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct AdapterScenario {
    pub run: ScenarioRun,
    pub audit: AdapterAudit,
}

pub fn run() -> AdapterScenario {
    let mut bridge = HostBridge::new(
        scenarios::simulator(),
        BTreeMap::from([(A_ID, "A".into()), (B_ID, "B".into()), (R_ID, "R".into())]),
    );
    let mut lan = Link::new("lan", "A", "B", Underlay::Lan);
    lan.failure_domain = "local-ip".into();
    let mut wifi = Link::new("wifi", "A", "B", Underlay::Wifi);
    wifi.failure_domain = "local-ip".into();
    wifi.latency = 20;
    let mut links = bank(vec![lan, wifi]);
    links.extend([
        adapter("internet", Underlay::Internet, 0, 160),
        adapter("bt", Underlay::Bluetooth, 0, 90),
        adapter("lora", Underlay::Lora, 0, 400),
    ]);
    let data = bridge
        .choose_data_reference(0, "A", "B", &mut links)
        .expect("fixed sample");
    bridge
        .send_data(0, "A", "B", &mut links)
        .expect("fixed data");
    bridge
        .send_verified_control(
            0,
            &verified_fixture(WireControlKind::Alive, 0),
            &mut links,
            &data,
        )
        .expect("fixed control");
    bridge
        .send_verified_control(
            0,
            &verified_fixture(WireControlKind::RouteAround, 1),
            &mut [adapter("lora", Underlay::Lora, 0, 400)],
            &data,
        )
        .expect("fixed radio control");
    let mut degraded = Link::new("lan", "A", "B", Underlay::Lan);
    degraded.observed = 1;
    degraded.latency = 100;
    degraded.jitter = 50;
    degraded.loss_ppm = 200_000;
    let mut degraded = bank(vec![degraded]);
    degraded.extend([
        adapter("wifi", Underlay::Wifi, 1, 20),
        adapter("internet", Underlay::Internet, 1, 60),
    ]);
    bridge
        .send_data(1, "A", "B", &mut degraded)
        .expect("fixed degradation");
    let mut ar = Link::new("a-r", "A", "R", Underlay::Internet);
    ar.observed = 2;
    ar.latency = 30;
    let mut rb = Link::new("r-b", "R", "B", Underlay::Internet);
    rb.observed = 2;
    rb.latency = 30;
    bridge
        .send_data(2, "A", "B", &mut bank(vec![ar, rb]))
        .expect("fixed relay");
    bridge
        .send_data(
            3,
            "A",
            "B",
            &mut [
                adapter("lan", Underlay::Lan, 3, 10)
                    .with_outcome(DataOutcome::Failed { emitted_tokens: 0 }),
                adapter("internet", Underlay::Internet, 3, 60),
            ],
        )
        .expect("fixed retry");
    bridge
        .send_data(
            4,
            "A",
            "B",
            &mut [
                adapter("lan", Underlay::Lan, 4, 10)
                    .with_outcome(DataOutcome::Failed { emitted_tokens: 1 }),
                adapter("internet", Underlay::Internet, 4, 60),
            ],
        )
        .expect("fixed partial");
    bridge
        .send_data(
            5,
            "A",
            "B",
            &mut [
                adapter("lan", Underlay::Lan, 5, 10),
                adapter("internet", Underlay::Internet, 5, 60),
            ],
        )
        .expect("fixed breaker");
    bridge
        .send_data(6, "A", "B", &mut [adapter("lan", Underlay::Lan, 6, 10)])
        .expect("fixed recovery");
    bridge
        .send_data(7, "A", "B", &mut [])
        .expect("fixed outage");
    bridge
        .send_data(7, "A", "UNKNOWN", &mut links)
        .expect("fixed denial");
    let mut fresh = [adapter("lan", Underlay::Lan, 8, 10)];
    let board = Billboard {
        machine: "B".into(),
        kind: BillboardKind::Rule,
        fact: "Pause this application while its owner is away.".into(),
        since: 8,
        until: 10,
        receipt: "rule-1".into(),
    };
    bridge
        .send_billboard(8, &board, &mut fresh)
        .expect("fixed billboard");
    let future = Billboard {
        machine: "B".into(),
        kind: BillboardKind::Fact,
        fact: "Maintenance window starts at tick nine.".into(),
        since: 9,
        until: 11,
        receipt: "fact-1".into(),
    };
    bridge
        .send_billboard(8, &future, &mut fresh)
        .expect("fixed held billboard");
    bridge
        .send_billboard(8, &board, &mut fresh)
        .expect("fixed replay denial");
    bridge
        .reject_control_input(8, "START", &mut fresh)
        .expect("fixed START denial");
    let mut active = Vec::new();
    for tick in [8_i128, 9] {
        active.push((
            tick.to_string(),
            bridge
                .policy
                .active_billboards(tick, "B")
                .expect("fixed clock"),
        ));
    }
    bridge
        .send_billboard(10, &board, &mut [adapter("lan", Underlay::Lan, 10, 10)])
        .expect("fixed expiry denial");
    for tick in [10_i128, 11] {
        active.push((
            tick.to_string(),
            bridge
                .policy
                .active_billboards(tick, "B")
                .expect("fixed clock"),
        ));
    }
    AdapterScenario {
        run: ScenarioRun {
            rows: bridge.policy.rows().to_vec(),
            active,
        },
        audit: bridge.audit,
    }
}

pub fn artifacts() -> Artifacts {
    let result = run();
    Artifacts {
        csv: rpp_core::overlay::serialize_csv(&result.run.rows),
        markdown: scenarios::render_markdown(&result.run),
        json: scenarios::render_json(&result.run.active),
    }
}
