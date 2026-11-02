use rpp_link::{LinkKind, LinkReading};
use rpp_steer::{Candidate, CostClass, Hysteresis, MessageClass, Selector};
use std::fmt::Write;
const GOLDEN: &[u8] = include_bytes!("data/steer-decisions.csv");

#[test]
fn golden_decisions_replay_identically_through_bare_or_std_core() {
    // Mutations changed-steering/hold/reason/row-loss change exact replay bytes.
    // These are Rust regression snapshots, not an independent Python oracle.
    let text = std::str::from_utf8(GOLDEN).unwrap();
    let mut lines = text.lines();
    let header = lines.next().unwrap();
    assert_eq!(header, "scenario,tick,wire_bytes,lan_up,wifi_up,ble_up,lan_loss,wifi_loss,lan_kbps,wifi_kbps,class,chosen,reason");
    let mut replay = format!("{header}\n");
    let params = Hysteresis {
        hold_ticks: 3,
        control_margin_ppm: 10,
        bulk_margin_kbps: 500,
        billboard_margin_ppm: 10,
    };
    let mut selector = Selector::new(params).unwrap();
    let mut previous = "";
    let mut rows = 0;
    for line in lines {
        let cells: Vec<_> = line.split(',').collect();
        assert_eq!(cells.len(), 13);
        if previous != cells[0] {
            selector = Selector::new(params).unwrap();
            previous = cells[0];
        }
        let n = |index: usize| cells[index].parse::<u64>().unwrap();
        let tick = n(1);
        let mut links = [Candidate {
            id: 1,
            kind: LinkKind::Lan,
            reading: LinkReading {
                latency_ms: 4,
                loss_ppm: n(6) as u32,
                jitter_ms: 0,
                available: n(3) == 1,
                observed: tick,
            },
            mtu: 1200,
            throughput_kbps: n(8),
            cost: CostClass::Unmetered,
        }; 3];
        links[1] = Candidate {
            id: 2,
            kind: LinkKind::Wifi,
            reading: LinkReading {
                latency_ms: 10,
                loss_ppm: n(7) as u32,
                jitter_ms: 0,
                available: n(4) == 1,
                observed: tick,
            },
            throughput_kbps: n(9),
            ..links[0]
        };
        links[2] = Candidate {
            id: 3,
            kind: LinkKind::Ble,
            reading: LinkReading {
                latency_ms: 3,
                loss_ppm: 0,
                jitter_ms: 0,
                available: n(5) == 1,
                observed: tick,
            },
            mtu: 20,
            throughput_kbps: 0,
            cost: CostClass::ControlOnly,
        };
        let class = match cells[10] {
            "control" => MessageClass::Control,
            "bulk" => MessageClass::Bulk,
            "billboard" => MessageClass::Billboard,
            _ => panic!("unknown fixed class"),
        };
        let decision = selector.choose(tick, class, n(2) as usize, &links).unwrap();
        let id = decision
            .link_id
            .map_or(String::from("none"), |id| id.to_string());
        writeln!(
            replay,
            "{},{},{}",
            cells[..11].join(","),
            id,
            decision.reason.as_str()
        )
        .unwrap();
        rows += 1;
    }
    assert_eq!(rows, 36);
    assert_eq!(replay.as_bytes(), GOLDEN);
}
#[cfg(feature = "std")]
#[test]
fn scripted_std_simulator_repeats_exact_snapshot_bytes() {
    // Mutations nondeterministic-output or omitted-scenario change the golden/repeat.
    let first = rpp_steer::sim::trace_log().unwrap();
    assert_eq!(first.as_bytes(), GOLDEN);
    assert_eq!(first, rpp_steer::sim::trace_log().unwrap());
}
