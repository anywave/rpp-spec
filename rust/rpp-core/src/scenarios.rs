//! In-memory equivalent of `tools.overlay_sim.scenarios.artifacts()`.
//! All inputs are scripted fixtures; no verification, transport or file I/O occurs.

use std::collections::{BTreeMap, BTreeSet};

use crate::overlay::{
    json_string, serialize_csv, Auth, Billboard, BillboardKind, ControlFrame, Link, MeterRow,
    Simulator, Underlay,
};

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Artifacts {
    pub csv: Vec<u8>,
    pub markdown: Vec<u8>,
    pub json: Vec<u8>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ScenarioRun {
    pub rows: Vec<MeterRow>,
    /// Script order is retained for Markdown; JSON renders keys lexicographically.
    pub active: Vec<(String, Vec<Billboard>)>,
}

pub fn simulator() -> Simulator {
    let members = ["A", "B", "R"].into_iter().map(str::to_owned).collect();
    let mut consents = BTreeSet::new();
    for a in ["A", "B", "R"] {
        for b in ["A", "B", "R"] {
            if a != b {
                consents.insert((a.into(), b.into()));
            }
        }
    }
    let scopes = BTreeSet::from([
        ("A".into(), "B".into(), BillboardKind::Rule),
        ("A".into(), "B".into(), BillboardKind::Fact),
    ]);
    Simulator::new(members, consents, scopes)
}

fn link(name: &str, underlay: Underlay, tick: u64, latency: u64) -> Link {
    let mut value = Link::new(name, "A", "B", underlay);
    value.observed = tick;
    value.latency = latency;
    value
}

pub fn run() -> ScenarioRun {
    let mut sim = simulator();
    let mut lan = link("lan", Underlay::Lan, 0, 10);
    lan.failure_domain = "local-ip".into();
    let mut wifi = link("wifi", Underlay::Wifi, 0, 20);
    wifi.failure_domain = "local-ip".into();
    let links = vec![
        lan,
        wifi,
        link("internet", Underlay::Internet, 0, 160),
        link("bt", Underlay::Bluetooth, 0, 90),
        link("lora", Underlay::Lora, 0, 400),
    ];
    let data = sim
        .choose("A", "B", 0, &links)
        .expect("valid fixed fixture");
    sim.send_data(0, "A", "B", &links, &BTreeMap::new());
    sim.send_control(
        0,
        &ControlFrame::from_kind("A", "B", "ALIVE", 0),
        Some(&Auth::fixture("A", true)),
        &links,
        &data,
    );
    sim.send_control(
        0,
        &ControlFrame::from_kind("A", "B", "ROUTE-AROUND", 1),
        Some(&Auth::fixture("A", true)),
        &[link("lora", Underlay::Lora, 0, 400)],
        &data,
    );
    let mut degraded_lan = link("lan", Underlay::Lan, 1, 100);
    degraded_lan.loss_ppm = 200_000;
    degraded_lan.jitter = 50;
    sim.send_data(
        1,
        "A",
        "B",
        &[
            degraded_lan,
            link("wifi", Underlay::Wifi, 1, 20),
            link("internet", Underlay::Internet, 1, 60),
        ],
        &BTreeMap::new(),
    );
    let mut ar = link("a-r", Underlay::Internet, 2, 30);
    ar.right = "R".into();
    let mut rb = link("r-b", Underlay::Internet, 2, 30);
    rb.left = "R".into();
    sim.send_data(2, "A", "B", &[ar, rb], &BTreeMap::new());
    sim.send_data(
        3,
        "A",
        "B",
        &[
            link("lan", Underlay::Lan, 3, 10),
            link("internet", Underlay::Internet, 3, 60),
        ],
        &BTreeMap::from([("lan".into(), 0)]),
    );
    sim.send_data(
        4,
        "A",
        "B",
        &[
            link("lan", Underlay::Lan, 4, 10),
            link("internet", Underlay::Internet, 4, 60),
        ],
        &BTreeMap::from([("lan".into(), 1)]),
    );
    sim.send_data(
        5,
        "A",
        "B",
        &[
            link("lan", Underlay::Lan, 5, 10),
            link("internet", Underlay::Internet, 5, 60),
        ],
        &BTreeMap::new(),
    );
    sim.send_data(
        6,
        "A",
        "B",
        &[link("lan", Underlay::Lan, 6, 10)],
        &BTreeMap::new(),
    );
    sim.send_data(7, "A", "B", &[], &BTreeMap::new());
    sim.send_data(7, "A", "UNKNOWN", &links, &BTreeMap::new());
    let fresh = [link("lan", Underlay::Lan, 8, 10)];
    let board = Billboard {
        machine: "B".into(),
        kind: BillboardKind::Rule,
        fact: "Pause this application while its owner is away.".into(),
        since: 8,
        until: 10,
        receipt: "rule-1".into(),
    };
    sim.deliver_billboard(
        8,
        Some(&board),
        Some(&Auth::fixture("A", true)),
        "A",
        "B",
        &fresh,
    );
    let future = Billboard {
        machine: "B".into(),
        kind: BillboardKind::Fact,
        fact: "Maintenance window starts at tick nine.".into(),
        since: 9,
        until: 11,
        receipt: "fact-1".into(),
    };
    sim.deliver_billboard(
        8,
        Some(&future),
        Some(&Auth::fixture("A", true)),
        "A",
        "B",
        &fresh,
    );
    sim.deliver_billboard(
        8,
        Some(&board),
        Some(&Auth::fixture("A", true)),
        "A",
        "B",
        &fresh,
    );
    sim.send_control(
        8,
        &ControlFrame::from_kind("A", "B", "START", 1),
        Some(&Auth::fixture("A", true)),
        &fresh,
        &[],
    );
    let mut active = Vec::new();
    for tick in [8_i128, 9] {
        active.push((
            tick.to_string(),
            sim.active_billboards(tick, "B").expect("monotonic fixture"),
        ));
    }
    sim.deliver_billboard(
        10,
        Some(&board),
        Some(&Auth::fixture("A", true)),
        "A",
        "B",
        &[link("lan", Underlay::Lan, 10, 10)],
    );
    for tick in [10_i128, 11] {
        active.push((
            tick.to_string(),
            sim.active_billboards(tick, "B").expect("monotonic fixture"),
        ));
    }
    ScenarioRun {
        rows: sim.rows().to_vec(),
        active,
    }
}

pub fn artifacts() -> Artifacts {
    let run = run();
    Artifacts {
        csv: serialize_csv(&run.rows),
        markdown: render_markdown(&run),
        json: render_json(&run.active),
    }
}

pub fn render_markdown(run: &ScenarioRun) -> Vec<u8> {
    let mut output = String::from("# Scripted overlay scenarios\n\nAll measurements, prior verification outcomes and times are fixtures.\nNo network or cryptographic operation occurs.\n\n| Tick | Request | Class | Path | Status | Tokens | Detail |\n|---:|---:|---|---|---|---:|---|\n");
    for row in &run.rows {
        output.push_str(&format!(
            "| {} | {} | {} | {} | {} | {} | {} |\n",
            row.tick,
            row.request,
            row.traffic.as_str(),
            row.path,
            row.status.as_str(),
            row.tokens,
            row.detail
        ));
    }
    output.push_str("\nBillboards are inert structured statements. Application policy would interpret authorized facts/rules;\nthe simulator only reports the active set, never executes a rule or supplies model instructions.\n\n| Tick | Active receipts |\n|---:|---|\n");
    for (tick, boards) in &run.active {
        let receipts = if boards.is_empty() {
            "(none)".into()
        } else {
            boards
                .iter()
                .map(|b| b.receipt.as_str())
                .collect::<Vec<_>>()
                .join(", ")
        };
        output.push_str(&format!("| {tick} | {receipts} |\n"));
    }
    output.into_bytes()
}

pub fn render_json(active: &[(String, Vec<Billboard>)]) -> Vec<u8> {
    let sorted: BTreeMap<_, _> = active.iter().map(|(tick, boards)| (tick, boards)).collect();
    let mut output = String::from("{\n");
    for (index, (tick, boards)) in sorted.iter().enumerate() {
        output.push_str(&format!("  {}: [", json_string(tick)));
        if !boards.is_empty() {
            output.push('\n');
        }
        for (i, b) in boards.iter().enumerate() {
            output.push_str(&format!("    {{\n      \"fact\": {},\n      \"kind\": {},\n      \"machine\": {},\n      \"receipt\": {},\n      \"since\": {},\n      \"until\": {}\n    }}{}\n",
                json_string(&b.fact), json_string(b.kind.as_str()), json_string(&b.machine), json_string(&b.receipt),
                b.since, b.until, if i + 1 < boards.len() { "," } else { "" }));
        }
        if !boards.is_empty() {
            output.push_str("  ");
        }
        output.push(']');
        if index + 1 < sorted.len() {
            output.push(',');
        }
        output.push('\n');
    }
    output.push_str("}\n");
    output.into_bytes()
}
