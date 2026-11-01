//! Pure, deterministic port of the Python overlay policy simulator.
//!
//! Verification booleans are prior-verification fixtures, not signatures or
//! cryptography. This module performs no I/O, networking, enrollment or execution
//! of billboard facts. Rust enums/strings exclude Python's malformed dynamic
//! object types; absent verification/billboard fixtures fail closed explicitly.
//!
//! Port domain: readings/observations/tokens/sequences are `u64` (loss is a
//! validated `u32`); operation ticks are accepted only in the `u64` clock range,
//! and billboard intervals use `i128`. Path scores use checked `u128` sums. These
//! representability choices do not claim equivalence for arbitrary Python big
//! integers, malformed dynamic objects or invalid UTF-8.
//!
//! This policy model requires the `alloc` feature but never requires `std`.

use alloc::{
    borrow::ToOwned,
    collections::{BTreeMap, BTreeSet},
    format,
    string::{String, ToString},
    vec::Vec,
};

#[derive(Clone, Copy, Debug, Eq, PartialEq, Ord, PartialOrd)]
pub enum Underlay {
    Lan,
    Wifi,
    Internet,
    Bluetooth,
    Lora,
}

impl Underlay {
    pub fn parse(value: &str) -> Option<Self> {
        match value {
            "LAN" => Some(Self::Lan),
            "Wi-Fi" => Some(Self::Wifi),
            "internet" => Some(Self::Internet),
            "Bluetooth" => Some(Self::Bluetooth),
            "LoRa" => Some(Self::Lora),
            _ => None,
        }
    }

    pub fn supports_ip(self) -> bool {
        matches!(self, Self::Lan | Self::Wifi | Self::Internet)
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Ord, PartialOrd)]
pub struct Link {
    pub name: String,
    pub left: String,
    pub right: String,
    pub underlay: Underlay,
    pub latency: u64,
    pub loss_ppm: u32,
    pub jitter: u64,
    pub available: bool,
    pub observed: u64,
    pub failure_domain: String,
    pub tunnel_verified: bool,
    pub reviewed_adapter: bool,
    pub observation_verified: bool,
}

impl Link {
    /// Convenience fixture with the same default readings as Python's `link`.
    pub fn new(name: &str, left: &str, right: &str, underlay: Underlay) -> Self {
        Self {
            name: name.into(),
            left: left.into(),
            right: right.into(),
            underlay,
            latency: 10,
            loss_ppm: 0,
            jitter: 0,
            available: true,
            observed: 0,
            failure_domain: name.into(),
            tunnel_verified: true,
            reviewed_adapter: false,
            observation_verified: true,
        }
    }

    pub fn valid(&self) -> bool {
        [&self.name, &self.left, &self.right, &self.failure_domain]
            .iter()
            .all(|s| identifier(s))
            && self.left != self.right
            && self.loss_ppm <= 1_000_000
    }

    pub fn score(&self) -> u128 {
        1000 * (u128::from(self.latency) + 2 * u128::from(self.jitter)) + u128::from(self.loss_ppm)
    }

    pub fn supports_data(&self) -> bool {
        self.tunnel_verified && (self.underlay.supports_ip() || self.reviewed_adapter)
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Auth {
    pub issuer: String,
    pub signature_verified: bool,
}

impl Auth {
    pub fn fixture(issuer: &str, verified: bool) -> Self {
        Self {
            issuer: issuer.into(),
            signature_verified: verified,
        }
    }

    fn valid(&self) -> bool {
        identifier(&self.issuer) && self.signature_verified
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Ord, PartialOrd)]
pub enum BillboardKind {
    Fact,
    Rule,
}

impl BillboardKind {
    pub fn parse(value: &str) -> Option<Self> {
        match value {
            "fact" => Some(Self::Fact),
            "rule" => Some(Self::Rule),
            _ => None,
        }
    }

    pub fn as_str(self) -> &'static str {
        match self {
            Self::Fact => "fact",
            Self::Rule => "rule",
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Billboard {
    pub machine: String,
    pub kind: BillboardKind,
    pub fact: String,
    pub since: i128,
    pub until: i128,
    pub receipt: String,
}

impl Billboard {
    pub fn valid(&self) -> bool {
        identifier(&self.machine)
            && !self.fact.is_empty()
            && self.fact.len() <= 256
            && 0 <= self.since
            && self.since < self.until
            && !self.receipt.is_empty()
            && self.receipt.len() <= 64
            && self
                .receipt
                .bytes()
                .all(|c| c.is_ascii_alphanumeric() || b"-_.".contains(&c))
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ControlKind {
    Alive,
    MemberChanged,
    Stop,
    Pause,
    RouteAround,
    Resume,
}

impl ControlKind {
    pub fn parse(value: &str) -> Option<Self> {
        match value {
            "ALIVE" => Some(Self::Alive),
            "MEMBER-CHANGED" => Some(Self::MemberChanged),
            "STOP" => Some(Self::Stop),
            "PAUSE" => Some(Self::Pause),
            "ROUTE-AROUND" => Some(Self::RouteAround),
            "RESUME" => Some(Self::Resume),
            _ => None,
        }
    }

    pub fn as_str(self) -> &'static str {
        match self {
            Self::Alive => "ALIVE",
            Self::MemberChanged => "MEMBER-CHANGED",
            Self::Stop => "STOP",
            Self::Pause => "PAUSE",
            Self::RouteAround => "ROUTE-AROUND",
            Self::Resume => "RESUME",
        }
    }
}

/// A notice has a closed schema: no payload/grant/consent/key/model fields exist.
/// A decoder can retain endpoint accounting for a rejected incoming frame.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ControlFrame {
    Notice {
        source: String,
        target: String,
        kind: ControlKind,
        sequence: u64,
    },
    Rejected {
        source: String,
        target: String,
    },
}

impl ControlFrame {
    pub fn notice(source: &str, target: &str, kind: ControlKind, sequence: u64) -> Self {
        Self::Notice {
            source: source.into(),
            target: target.into(),
            kind,
            sequence,
        }
    }

    pub fn from_kind(source: &str, target: &str, kind: &str, sequence: u64) -> Self {
        match ControlKind::parse(kind) {
            Some(kind) => Self::notice(source, target, kind, sequence),
            None => Self::Rejected {
                source: source.into(),
                target: target.into(),
            },
        }
    }

    fn endpoints(&self) -> (&str, &str) {
        match self {
            Self::Notice { source, target, .. } | Self::Rejected { source, target } => {
                (source, target)
            }
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Traffic {
    Data,
    Control,
    Billboard,
}

impl Traffic {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Data => "data",
            Self::Control => "control",
            Self::Billboard => "billboard",
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Status {
    Ok,
    Failed,
    InvalidInput,
    Denied,
    DeniedSelfTarget,
    NoChannel,
    NoIndependentChannel,
    Delivered,
    HeldUntilSince,
}

impl Status {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Ok => "OK",
            Self::Failed => "FAILED",
            Self::InvalidInput => "INVALID_INPUT",
            Self::Denied => "DENIED",
            Self::DeniedSelfTarget => "DENIED_SELF_TARGET",
            Self::NoChannel => "NO_CHANNEL",
            Self::NoIndependentChannel => "NO_INDEPENDENT_CHANNEL",
            Self::Delivered => "DELIVERED",
            Self::HeldUntilSince => "HELD_UNTIL_SINCE",
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct MeterRow {
    pub row: u64,
    pub tick: i128,
    pub request: u64,
    pub traffic: Traffic,
    pub source: String,
    pub target: String,
    pub path: String,
    pub status: Status,
    pub tokens: u64,
    pub detail: String,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum PolicyError {
    InvalidLinks,
    UnknownRecipient,
    ClockRollback,
    Capacity,
}

/// A read-only policy decision. It does not reserve a request, sequence or time,
/// remember a data reference, emit a meter row or report physical delivery.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SelectionPreview {
    pub status: Status,
    pub path: Vec<Link>,
    pub detail: &'static str,
}

impl SelectionPreview {
    fn empty(status: Status, detail: &'static str) -> Self {
        Self {
            status,
            path: Vec::new(),
            detail,
        }
    }
}

#[derive(Clone, Debug)]
struct Operation {
    tick: i128,
    request: u64,
    traffic: Traffic,
    source: String,
    target: String,
}

impl Operation {
    fn new(tick: i128, request: u64, traffic: Traffic, source: &str, target: &str) -> Self {
        Self {
            tick,
            request,
            traffic,
            source: source.into(),
            target: target.into(),
        }
    }
}

struct RouteFilter<'a> {
    traffic: Traffic,
    excluded: &'a BTreeSet<String>,
    avoid_domains: &'a BTreeSet<String>,
}

#[derive(Clone, Debug, Eq, PartialEq, Ord, PartialOrd)]
struct KnownPath {
    source: String,
    target: String,
    selected: i128,
    path: Vec<Link>,
}

#[derive(Clone, Debug)]
pub struct Simulator {
    members: BTreeSet<String>,
    consents: BTreeSet<(String, String)>,
    scopes: BTreeSet<(String, String, BillboardKind)>,
    rows: Vec<MeterRow>,
    next_id: u64,
    next_row: u64,
    failures: BTreeMap<String, u8>,
    open_until: BTreeMap<String, u128>,
    billboards: BTreeMap<(String, String), Billboard>,
    receipts: BTreeSet<(String, String)>,
    control_sequences: BTreeMap<(String, String), u64>,
    clock: u64,
    known_data_paths: BTreeSet<KnownPath>,
}

impl Simulator {
    pub fn new(
        members: BTreeSet<String>,
        consents: BTreeSet<(String, String)>,
        scopes: BTreeSet<(String, String, BillboardKind)>,
    ) -> Self {
        Self {
            members,
            consents,
            scopes,
            rows: Vec::new(),
            next_id: 1,
            next_row: 1,
            failures: BTreeMap::new(),
            open_until: BTreeMap::new(),
            billboards: BTreeMap::new(),
            receipts: BTreeSet::new(),
            control_sequences: BTreeMap::new(),
            clock: 0,
            known_data_paths: BTreeSet::new(),
        }
    }

    pub fn rows(&self) -> &[MeterRow] {
        &self.rows
    }
    pub fn clock(&self) -> u64 {
        self.clock
    }
    pub fn members(&self) -> &BTreeSet<String> {
        &self.members
    }
    pub fn consents(&self) -> &BTreeSet<(String, String)> {
        &self.consents
    }

    /// Number of remembered data references. Legacy choose/send calls retain
    /// history; choose_latest instead keeps one successful selection per pair.
    pub fn known_data_path_count(&self) -> usize {
        self.known_data_paths.len()
    }

    /// Keep only the newest rows without renumbering any row or request.
    /// A host requiring a complete ledger must persist returned rows separately.
    /// No retention limit is imposed unless the caller opts into this method.
    pub fn retain_meter_rows(&mut self, limit: usize) {
        let remove = self.rows.len().saturating_sub(limit);
        self.rows.drain(..remove);
        // Release a previously large allocation, but avoid reallocating on each
        // push/trim when a continuously retained window briefly grows by one.
        if self.rows.capacity() > limit.saturating_mul(2) {
            self.rows.shrink_to(limit);
        }
    }

    fn begin(&mut self, tick: i128, traffic: Traffic, source: &str, target: &str) -> Operation {
        let request = self.next_id;
        // An in-memory vector cannot practically reach this count; saturation
        // prevents arithmetic panic even for an adversarially enormous run.
        self.next_id = self.next_id.saturating_add(1);
        Operation::new(tick, request, traffic, source, target)
    }

    fn meter(
        &mut self,
        op: &Operation,
        path: &[Link],
        status: Status,
        tokens: u64,
        detail: &str,
    ) -> MeterRow {
        let row = MeterRow {
            row: self.next_row,
            tick: op.tick,
            request: op.request,
            traffic: op.traffic,
            source: op.source.clone(),
            target: op.target.clone(),
            path: path
                .iter()
                .map(|x| x.name.as_str())
                .collect::<Vec<_>>()
                .join("/"),
            status,
            tokens,
            detail: detail.into(),
        };
        self.next_row = self.next_row.saturating_add(1);
        self.rows.push(row.clone());
        row
    }

    fn time_valid(&self, tick: i128) -> bool {
        u64::try_from(tick).is_ok_and(|value| value >= self.clock)
    }

    fn advance(&mut self, tick: i128) {
        // Only called after time_valid and acceptance, never for a denied call.
        self.clock = tick as u64;
    }

    fn links_valid(links: &[Link]) -> bool {
        links.iter().all(Link::valid)
            && links.iter().map(|x| &x.name).collect::<BTreeSet<_>>().len() == links.len()
    }

    fn authorized(&self, source: &str, target: &str) -> bool {
        identifier(source)
            && identifier(target)
            && source != target
            && self.members.contains(source)
            && self.members.contains(target)
            && self.consents.contains(&(source.into(), target.into()))
    }

    fn usable(
        &self,
        link: &Link,
        tick: i128,
        traffic: Traffic,
        excluded: &BTreeSet<String>,
    ) -> bool {
        let age = tick - i128::from(link.observed);
        !excluded.contains(&link.name)
            && link.available
            && link.observation_verified
            && (0..=5).contains(&age)
            && u128::try_from(tick)
                .is_ok_and(|value| value >= *self.open_until.get(&link.name).unwrap_or(&0))
            && self.members.contains(&link.left)
            && self.members.contains(&link.right)
            && link.tunnel_verified
            && (traffic == Traffic::Control || link.supports_data())
    }

    pub fn choose(
        &mut self,
        source: &str,
        target: &str,
        tick: i128,
        links: &[Link],
    ) -> Result<Vec<Link>, PolicyError> {
        let chosen = self.select_path(
            source,
            target,
            tick,
            links,
            RouteFilter {
                traffic: Traffic::Data,
                excluded: &BTreeSet::new(),
                avoid_domains: &BTreeSet::new(),
            },
        )?;
        self.remember_data_path(source, target, tick, &chosen);
        Ok(chosen)
    }

    /// The same selection query as choose, with one retained successful path
    /// per endpoint pair. An empty/no-channel selection preserves the old path;
    /// no expiry or extra clock rule is added to historical references.
    pub fn choose_latest(
        &mut self,
        source: &str,
        target: &str,
        tick: i128,
        links: &[Link],
    ) -> Result<Vec<Link>, PolicyError> {
        let chosen = self.select_path(
            source,
            target,
            tick,
            links,
            RouteFilter {
                traffic: Traffic::Data,
                excluded: &BTreeSet::new(),
                avoid_domains: &BTreeSet::new(),
            },
        )?;
        if !chosen.is_empty() {
            self.known_data_paths
                .retain(|path| path.source != source || path.target != target);
            self.remember_data_path(source, target, tick, &chosen);
        }
        Ok(chosen)
    }

    fn remember_data_path(&mut self, source: &str, target: &str, tick: i128, path: &[Link]) {
        if !path.is_empty() {
            self.known_data_paths.insert(KnownPath {
                source: source.into(),
                target: target.into(),
                selected: tick,
                path: path.into(),
            });
        }
    }

    fn select_path(
        &self,
        source: &str,
        target: &str,
        tick: i128,
        links: &[Link],
        filter: RouteFilter<'_>,
    ) -> Result<Vec<Link>, PolicyError> {
        if !self.authorized(source, target) || tick < 0 {
            return Ok(Vec::new());
        }
        if !Self::links_valid(links) {
            return Err(PolicyError::InvalidLinks);
        }
        let mut candidates: Vec<_> = links
            .iter()
            .filter(|x| {
                self.usable(x, tick, filter.traffic, filter.excluded)
                    && !filter.avoid_domains.contains(&x.failure_domain)
            })
            .cloned()
            .collect();
        candidates.sort_by(|a, b| a.name.cmp(&b.name));
        let mut paths = Vec::new();
        let mut seen = BTreeSet::from([source.to_owned()]);
        self.visit(
            source,
            target,
            &candidates,
            &mut seen,
            &mut Vec::new(),
            &mut paths,
        );
        let mut scored = Vec::new();
        for path in paths {
            let score = path
                .iter()
                .try_fold(0_u128, |sum, link| sum.checked_add(link.score()))
                .ok_or(PolicyError::Capacity)?;
            let names = path.iter().map(|x| x.name.clone()).collect::<Vec<_>>();
            scored.push(((score, path.len(), names), path));
        }
        scored.sort_by(|a, b| a.0.cmp(&b.0));
        Ok(scored.into_iter().next().map_or_else(Vec::new, |x| x.1))
    }

    /// Evaluate a data choice using the same checks as send_data, without
    /// copying simulator state or changing its ledger, references or clock.
    pub fn preview_data(
        &self,
        tick: i128,
        source: &str,
        target: &str,
        links: &[Link],
    ) -> SelectionPreview {
        self.evaluate_data(tick, source, target, links, &BTreeSet::new())
    }

    fn evaluate_data(
        &self,
        tick: i128,
        source: &str,
        target: &str,
        links: &[Link],
        excluded: &BTreeSet<String>,
    ) -> SelectionPreview {
        if !self.time_valid(tick) || !Self::links_valid(links) {
            return SelectionPreview::empty(Status::InvalidInput, "");
        }
        if source == target {
            return SelectionPreview::empty(Status::DeniedSelfTarget, "");
        }
        if !self.authorized(source, target) {
            return SelectionPreview::empty(Status::Denied, "");
        }
        match self.select_path(
            source,
            target,
            tick,
            links,
            RouteFilter {
                traffic: Traffic::Data,
                excluded,
                avoid_domains: &BTreeSet::new(),
            },
        ) {
            Err(_) => SelectionPreview::empty(Status::InvalidInput, ""),
            Ok(path) if path.is_empty() => SelectionPreview::empty(Status::NoChannel, ""),
            Ok(path) => {
                let detail = if path.len() > 1 { "relay" } else { "direct" };
                SelectionPreview {
                    status: Status::Ok,
                    path,
                    detail,
                }
            }
        }
    }

    fn visit(
        &self,
        node: &str,
        target: &str,
        candidates: &[Link],
        seen: &mut BTreeSet<String>,
        path: &mut Vec<Link>,
        paths: &mut Vec<Vec<Link>>,
    ) {
        if node == target {
            paths.push(path.clone());
            return;
        }
        for link in candidates {
            let other = if link.left == node {
                &link.right
            } else if link.right == node {
                &link.left
            } else {
                continue;
            };
            if !seen.contains(other) && self.consents.contains(&(node.into(), other.clone())) {
                seen.insert(other.clone());
                path.push(link.clone());
                self.visit(other, target, candidates, seen, path, paths);
                path.pop();
                seen.remove(other);
            }
        }
    }

    pub fn send_data(
        &mut self,
        tick: i128,
        source: &str,
        target: &str,
        links: &[Link],
        failures: &BTreeMap<String, i128>,
    ) {
        let op = self.begin(tick, Traffic::Data, source, target);
        if failures.values().any(|x| u64::try_from(*x).is_err()) {
            self.meter(&op, &[], Status::InvalidInput, 0, "");
            return;
        }
        let mut excluded = BTreeSet::new();
        loop {
            let selection = self.evaluate_data(tick, source, target, links, &excluded);
            if selection.status != Status::Ok {
                self.meter(&op, &selection.path, selection.status, 0, selection.detail);
                return;
            }
            let path = selection.path;
            self.remember_data_path(source, target, tick, &path);
            self.advance(tick);
            let failure = path.iter().find(|x| failures.contains_key(&x.name));
            let Some(failure) = failure else {
                for link in &path {
                    self.failures.insert(link.name.clone(), 0);
                }
                self.meter(
                    &op,
                    &path,
                    Status::Ok,
                    3,
                    if path.len() > 1 { "relay" } else { "direct" },
                );
                return;
            };
            let tokens = failures[&failure.name] as u64;
            let count = self.failures.entry(failure.name.clone()).or_default();
            *count += 1;
            if *count >= 2 {
                self.open_until
                    .insert(failure.name.clone(), tick as u128 + 2);
                *count = 0;
            }
            self.meter(
                &op,
                &path,
                Status::Failed,
                tokens,
                if tokens == 0 {
                    "retry-before-first-token"
                } else {
                    "terminal-after-first-token"
                },
            );
            // MUTATION_ANCHOR retry_after_first_token: deleting this boundary replays emitted data.
            if tokens > 0 {
                return;
            }
            excluded.insert(failure.name.clone());
        }
    }

    fn known_reference(&self, source: &str, target: &str, tick: i128, path: &[Link]) -> bool {
        !path.is_empty()
            && path.iter().all(Link::supports_data)
            && self.known_data_paths.iter().any(|p| {
                p.source == source && p.target == target && p.selected <= tick && p.path == path
            })
    }

    /// Evaluate the existing control policy without spending a sequence, clock
    /// transition, request ID or meter row. Historical-reference rules match
    /// send_control exactly; no extra expiry is introduced.
    pub fn preview_control(
        &self,
        tick: i128,
        frame: &ControlFrame,
        auth: Option<&Auth>,
        links: &[Link],
        data_path: &[Link],
    ) -> SelectionPreview {
        self.evaluate_control(tick, frame, auth, links, data_path).0
    }

    // The bool retains legacy endpoint redaction for malformed initial input;
    // later path-capacity errors retain the parsed endpoints as before.
    fn evaluate_control(
        &self,
        tick: i128,
        frame: &ControlFrame,
        auth: Option<&Auth>,
        links: &[Link],
        data_path: &[Link],
    ) -> (SelectionPreview, bool) {
        let (source, target) = frame.endpoints();
        if !self.time_valid(tick) || !Self::links_valid(links) {
            return (SelectionPreview::empty(Status::InvalidInput, ""), true);
        }
        if identifier(source) && identifier(target) && source == target {
            return (SelectionPreview::empty(Status::DeniedSelfTarget, ""), false);
        }
        let ControlFrame::Notice { kind, sequence, .. } = frame else {
            return (SelectionPreview::empty(Status::Denied, ""), false);
        };
        let good = auth.is_some_and(|a| a.valid() && a.issuer == source)
            && self.authorized(source, target)
            && self
                .control_sequences
                .get(&(source.into(), target.into()))
                .is_none_or(|old| sequence > old);
        if !good {
            return (SelectionPreview::empty(Status::Denied, ""), false);
        }
        if !self.known_reference(source, target, tick, data_path) {
            return (
                SelectionPreview::empty(Status::Denied, "unknown-data-path"),
                false,
            );
        }
        let domains = data_path.iter().map(|x| x.failure_domain.clone()).collect();
        let path = match self.select_path(
            source,
            target,
            tick,
            links,
            RouteFilter {
                traffic: Traffic::Control,
                excluded: &BTreeSet::new(),
                avoid_domains: &domains,
            },
        ) {
            Ok(path) => path,
            Err(_) => return (SelectionPreview::empty(Status::InvalidInput, ""), false),
        };
        if path.is_empty() {
            return (
                SelectionPreview::empty(Status::NoIndependentChannel, ""),
                false,
            );
        }
        (
            SelectionPreview {
                status: Status::Ok,
                path,
                detail: kind.as_str(),
            },
            false,
        )
    }

    pub fn send_control(
        &mut self,
        tick: i128,
        frame: &ControlFrame,
        auth: Option<&Auth>,
        links: &[Link],
        data_path: &[Link],
    ) -> MeterRow {
        let (source, target) = frame.endpoints();
        let mut op = self.begin(tick, Traffic::Control, source, target);
        let (selection, clear_endpoints) =
            self.evaluate_control(tick, frame, auth, links, data_path);
        if clear_endpoints {
            op.source.clear();
            op.target.clear();
        }
        if let (Status::Ok, ControlFrame::Notice { sequence, .. }) = (selection.status, frame) {
            self.advance(tick);
            self.control_sequences
                .insert((source.into(), target.into()), *sequence);
        }
        self.meter(&op, &selection.path, selection.status, 0, selection.detail)
    }

    pub fn deliver_billboard(
        &mut self,
        tick: i128,
        board: Option<&Billboard>,
        auth: Option<&Auth>,
        source: &str,
        target: &str,
        links: &[Link],
    ) -> MeterRow {
        let op = self.begin(tick, Traffic::Billboard, source, target);
        if !self.time_valid(tick) || !Self::links_valid(links) {
            return self.meter(&op, &[], Status::InvalidInput, 0, "");
        }
        if source == target {
            return self.meter(&op, &[], Status::DeniedSelfTarget, 0, "");
        }
        let Some((board, auth)) = board.zip(auth) else {
            return self.meter(&op, &[], Status::Denied, 0, "");
        };
        let key = (auth.issuer.clone(), board.receipt.clone());
        let good = board.valid()
            && auth.valid()
            && self.members.contains(&auth.issuer)
            && self
                .scopes
                .contains(&(auth.issuer.clone(), board.machine.clone(), board.kind))
            && board.machine == target
            && self.authorized(source, target)
            && !self.receipts.contains(&key)
            && tick < board.until;
        if !good {
            return self.meter(&op, &[], Status::Denied, 0, "");
        }
        let path = match self.choose(source, target, tick, links) {
            Ok(path) => path,
            Err(_) => return self.meter(&op, &[], Status::InvalidInput, 0, ""),
        };
        if path.is_empty() {
            return self.meter(&op, &[], Status::NoChannel, 0, "");
        }
        self.advance(tick);
        self.receipts.insert(key.clone());
        self.billboards.insert(key, board.clone());
        self.meter(
            &op,
            &path,
            if tick >= board.since {
                Status::Delivered
            } else {
                Status::HeldUntilSince
            },
            0,
            &board.receipt,
        )
    }

    pub fn active_billboards(
        &mut self,
        tick: i128,
        machine: &str,
    ) -> Result<Vec<Billboard>, PolicyError> {
        if !identifier(machine) || !self.members.contains(machine) {
            return Err(PolicyError::UnknownRecipient);
        }
        if !self.time_valid(tick) {
            return Err(PolicyError::ClockRollback);
        }
        self.advance(tick);
        Ok(self
            .billboards
            .values()
            .filter(|candidate| {
                candidate.machine == machine && candidate.since <= tick
                // MUTATION_ANCHOR expired_billboard_applied: removing until applies stale rules.
                && tick < candidate.until
            })
            .cloned()
            .collect())
    }
}

fn identifier(value: &str) -> bool {
    let len = value.chars().count();
    (1..=64).contains(&len)
}

pub fn serialize_csv(rows: &[MeterRow]) -> Vec<u8> {
    let mut output =
        String::from("row,tick,request,traffic,source,target,path,status,tokens,detail\n");
    for row in rows {
        let cells = [
            row.row.to_string(),
            row.tick.to_string(),
            row.request.to_string(),
            row.traffic.as_str().into(),
            row.source.clone(),
            row.target.clone(),
            row.path.clone(),
            row.status.as_str().into(),
            row.tokens.to_string(),
            row.detail.clone(),
        ];
        output.push_str(
            &cells
                .iter()
                .map(|cell| csv_cell(cell))
                .collect::<Vec<_>>()
                .join(","),
        );
        output.push('\n');
    }
    output.into_bytes()
}

fn csv_cell(value: &str) -> String {
    if value.contains([',', '"', '\r', '\n']) {
        format!("\"{}\"", value.replace('"', "\"\""))
    } else {
        value.into()
    }
}

pub(crate) fn json_string(value: &str) -> String {
    let mut out = String::from("\"");
    for ch in value.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            '\u{08}' => out.push_str("\\b"),
            '\u{0c}' => out.push_str("\\f"),
            c if c < '\u{20}' => out.push_str(&format!("\\u{:04x}", u32::from(c))),
            c => out.push(c),
        }
    }
    out.push('"');
    out
}
