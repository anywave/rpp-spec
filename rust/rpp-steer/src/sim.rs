//! Scripted measurements only: no network, radios, framing or consent grant.
use crate::{Candidate, CostClass, Error, Hysteresis, MessageClass, Selector};
use rpp_link::{LinkKind, LinkReading};
use std::{
    fmt::Write,
    string::{String, ToString},
};

#[derive(Clone, Copy)]
pub struct Step {
    pub scenario: &'static str,
    pub tick: u64,
    pub wire_bytes: usize,
    pub links: [Candidate; 3],
}
fn step(scenario: &'static str, tick: u64, lan_up: bool, wifi_up: bool, wire_bytes: usize) -> Step {
    let mut links = [
        Candidate {
            id: 1,
            kind: LinkKind::Lan,
            reading: LinkReading {
                latency_ms: 4,
                loss_ppm: 100,
                jitter_ms: 0,
                available: lan_up,
                observed: tick,
            },
            mtu: 1200,
            throughput_kbps: 1000,
            cost: CostClass::Unmetered,
        },
        Candidate {
            id: 2,
            kind: LinkKind::Wifi,
            reading: LinkReading {
                latency_ms: 10,
                loss_ppm: 0,
                jitter_ms: 0,
                available: wifi_up,
                observed: tick,
            },
            mtu: 1200,
            throughput_kbps: 5000,
            cost: CostClass::Unmetered,
        },
        Candidate {
            id: 3,
            kind: LinkKind::Ble,
            reading: LinkReading {
                latency_ms: 3,
                loss_ppm: 0,
                jitter_ms: 0,
                available: true,
                observed: tick,
            },
            mtu: 20,
            throughput_kbps: 0,
            cost: CostClass::ControlOnly,
        },
    ];
    if scenario == "lan-flap" {
        links[0].reading.loss_ppm = 0;
        links[1].reading.loss_ppm = 100;
        links[1].throughput_kbps = 900;
        links[2].reading.available = false;
    }
    Step {
        scenario,
        tick,
        wire_bytes,
        links,
    }
}
pub fn steps() -> [Step; 12] {
    [
        step("wifi-drop", 0, true, true, 20),
        step("wifi-drop", 1, true, false, 20),
        step("wifi-drop", 2, true, true, 20),
        step("wifi-drop", 4, true, true, 20),
        step("lan-flap", 0, true, true, 20),
        step("lan-flap", 1, false, true, 20),
        step("lan-flap", 2, true, true, 20),
        step("lan-flap", 4, false, true, 20),
        step("lan-flap", 5, true, true, 20),
        step("ble-only", 0, false, false, 20),
        step("ble-only", 1, false, false, 112),
        step("ble-only", 2, false, false, 20),
    ]
}
pub const HEADER: &str = "scenario,tick,wire_bytes,lan_up,wifi_up,ble_up,lan_loss,wifi_loss,lan_kbps,wifi_kbps,class,chosen,reason\n";
pub fn parameters() -> Hysteresis {
    Hysteresis {
        hold_ticks: 3,
        control_margin_ppm: 10,
        bulk_margin_kbps: 500,
        billboard_margin_ppm: 10,
    }
}
pub fn trace_log() -> Result<String, Error> {
    let mut output = String::from(HEADER);
    let mut previous = "";
    let mut selector = Selector::new(parameters())?;
    for step in steps() {
        if previous != step.scenario {
            selector = Selector::new(parameters())?;
            previous = step.scenario;
        }
        for (class, label) in [
            (MessageClass::Control, "control"),
            (MessageClass::Bulk, "bulk"),
            (MessageClass::Billboard, "billboard"),
        ] {
            let decision = selector.choose(step.tick, class, step.wire_bytes, &step.links)?;
            let id = decision
                .link_id
                .map_or(String::from("none"), |id| id.to_string());
            let [lan, wifi, ble] = step.links;
            writeln!(
                output,
                "{},{},{},{},{},{},{},{},{},{},{},{},{}",
                step.scenario,
                step.tick,
                step.wire_bytes,
                u8::from(lan.reading.available),
                u8::from(wifi.reading.available),
                u8::from(ble.reading.available),
                lan.reading.loss_ppm,
                wifi.reading.loss_ppm,
                lan.throughput_kbps,
                wifi.throughput_kbps,
                label,
                id,
                decision.reason.as_str()
            )
            .expect("String formatting");
        }
    }
    Ok(output)
}
