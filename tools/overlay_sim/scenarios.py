"""Scripted multi-channel examples; run with python -m tools.overlay_sim.scenarios."""

import argparse
from hashlib import sha256
from pathlib import Path

from .model import Auth, Billboard, Link, Simulator, canonical_json, serialize


def link(name, underlay="LAN", left="A", right="B", tick=0, latency=10,
         available=True, loss_ppm=0, jitter=0, domain=None, **kwargs):
    return Link(name, left, right, underlay, latency, loss_ppm, jitter, available,
                tick, domain or name, **kwargs)


def simulator():
    # Pre-existing membership and per-pair consent; no channel can modify these.
    return Simulator({"A", "B", "R"}, {(a, b) for a in "ABR" for b in "ABR" if a != b},
                     {("A", "B", "rule"), ("A", "B", "fact")})


def run():
    sim = simulator()
    links = [link("lan", domain="local-ip"), link("wifi", "Wi-Fi", latency=20, domain="local-ip"),
             link("internet", "internet", latency=160), link("bt", "Bluetooth", latency=90),
             link("lora", "LoRa", latency=400)]
    data = sim.choose("A", "B", 0, links)
    sim.send_data(0, "A", "B", links)
    sim.send_control(0, dict(source="A", target="B", kind="ALIVE", sequence=0), Auth("A", True), links, data)
    sim.send_control(0, dict(source="A", target="B", kind="ROUTE-AROUND", sequence=1),
                     Auth("A", True), [link("lora", "LoRa", latency=400)], data)
    degraded = [link("lan", tick=1, latency=100, loss_ppm=200_000, jitter=50),
                link("wifi", "Wi-Fi", tick=1, latency=20), link("internet", "internet", tick=1, latency=60)]
    sim.send_data(1, "A", "B", degraded)
    relay = [link("a-r", "internet", right="R", tick=2, latency=30),
             link("r-b", "internet", left="R", tick=2, latency=30)]
    sim.send_data(2, "A", "B", relay)
    attempts = [link("lan", tick=3), link("internet", "internet", tick=3, latency=60)]
    sim.send_data(3, "A", "B", attempts, {"lan": 0})
    # Second failure opens LAN's breaker through ticks 4 and 5; no token retry occurs.
    attempts = [link("lan", tick=4), link("internet", "internet", tick=4, latency=60)]
    sim.send_data(4, "A", "B", attempts, {"lan": 1})
    sim.send_data(5, "A", "B", [link("lan", tick=5), link("internet", "internet", tick=5, latency=60)])
    sim.send_data(6, "A", "B", [link("lan", tick=6)])
    sim.send_data(7, "A", "B", [])
    sim.send_data(7, "A", "UNKNOWN", links)
    fresh = [link("lan", tick=8)]
    board = Billboard("B", "rule", "Pause this application while its owner is away.", 8, 10, "rule-1")
    sim.deliver_billboard(8, board, Auth("A", True), "A", "B", fresh)
    future = Billboard("B", "fact", "Maintenance window starts at tick nine.", 9, 11, "fact-1")
    sim.deliver_billboard(8, future, Auth("A", True), "A", "B", fresh)
    sim.deliver_billboard(8, board, Auth("A", True), "A", "B", fresh)
    sim.send_control(8, dict(source="A", target="B", kind="START", sequence=1), Auth("A", True), fresh)
    active = {str(t): sim.active_billboards(t, "B") for t in (8, 9)}
    sim.deliver_billboard(10, board, Auth("A", True), "A", "B", [link("lan", tick=10)])
    active.update({str(t): sim.active_billboards(t, "B") for t in (10, 11)})
    return sim.rows, active


def render(rows, active):
    lines = ["# Scripted overlay scenarios", "", "All measurements, prior verification outcomes and times are fixtures.",
             "No network or cryptographic operation occurs.", "", "| Tick | Request | Class | Path | Status | Tokens | Detail |",
             "|---:|---:|---|---|---|---:|---|"]
    for row in rows:
        lines.append("| {tick} | {request} | {traffic} | {path} | {status} | {tokens} | {detail} |".format(**row))
    lines += ["", "Billboards are inert structured statements. Application policy would interpret authorized facts/rules;",
              "the simulator only reports the active set, never executes a rule or supplies model instructions.", "",
              "| Tick | Active receipts |", "|---:|---|"]
    for tick, boards in active.items():
        lines.append(f"| {tick} | {', '.join(x['receipt'] for x in boards) or '(none)'} |")
    return ("\n".join(lines) + "\n").encode("utf-8")


def artifacts():
    rows, active = run()
    return {"scenarios.csv": serialize(rows), "SCENARIOS.md": render(rows, active),
            "billboards.json": canonical_json(active)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True, help="explicit destination for generated artifacts")
    args = parser.parse_args()
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"output_dir={output_dir}")
    result = artifacts()
    for name, data in result.items():
        (output_dir / name).write_bytes(data)
    rows, _ = run()
    print(f"meter_rows={len(rows)} requests={len({r['request'] for r in rows})} artifacts={len(result)}")
    for name, data in result.items():
        print(f"{name} sha256={sha256(data).hexdigest()}")


if __name__ == "__main__":
    main()
