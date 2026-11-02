"""Fleet endpoint tables from the existing merged Python overlay policy.

This scaffold uses actual tools.overlay_sim.model selection. It is not an
independent identity derivation oracle, transport implementation or verifier.
Fourteen rows use core routing/status results; three explicitly named rows
describe the fleet boundary contract, not independent Python core parity.
No cost formula, randomness, network or cryptography is introduced.
"""

import argparse
import csv
from dataclasses import replace
import hashlib
import io
import json
from pathlib import Path

from tools.overlay_sim.model import Auth, Link, Simulator


FIELDS = ("scenario", "traffic", "status", "endpoint", "kind", "uri", "failover")
URIS = {1: "ipv4://192.0.2.10:9000/rpp", 2: "ipv4://192.0.2.20:9000/rpp",
        3: "ipv4://198.51.100.10:9000/rpp", 4: "bt://voice-device/control",
        6: "ws://voice-gateway.lan/xiaozhi"}
KINDS = {1: "LAN", 2: "Wi-Fi", 3: "internet", 4: "BLE", 6: "WebSocketGateway"}
UNDERLAYS = {1: "LAN", 2: "Wi-Fi", 3: "internet", 4: "Bluetooth", 6: "LAN"}
BOUNDARY_ROWS = ("invalid-latency-u64max-update", "invalid-loss-ppm-update", "clock-rollback")
PROVENANCE = "Fourteen core-derived rows; three fleet-boundary contract rows are not independent core parity."


def model():
    return Simulator({"A", "B"}, {("A", "B"), ("B", "A")})


def link(endpoint, latency, *, tick=0, available=True, loss=0, jitter=0, reviewed=False):
    return Link(f"ep{endpoint:08x}", "A", "B", UNDERLAYS[endpoint], latency, loss, jitter,
                available, tick, "ble" if endpoint == 4 else "ip", True, reviewed, True)


def endpoint_id(selected):
    return int(selected.name[2:], 16)


def row(name, traffic, ids, *, status=None):
    selected = ids[0] if ids else None
    return {"scenario": name, "traffic": traffic, "status": status or ("OK" if ids else "NO_CHANNEL"),
            "endpoint": str(selected) if selected is not None else "-",
            "kind": KINDS[selected] if selected is not None else "-",
            "uri": URIS[selected] if selected is not None else "-",
            "failover": ",".join(map(str, ids)) or "-"}


def data_case(name, links, *, tick=0):
    policy = model()
    excluded = frozenset()
    order = []
    while chosen := policy.choose("A", "B", tick, links, excluded=excluded):
        if len(chosen) != 1:
            raise ValueError("these endpoint fixtures contain direct links only")
        order.append(endpoint_id(chosen[0]))
        excluded |= frozenset(item.name for item in chosen)
    return row(name, "data", order)


def control_case(name, links):
    policy = model()
    known_data = policy.choose("A", "B", 0, [link(1, 10)])
    result = policy.send_control(1, {"source": "A", "target": "B", "kind": "STOP", "sequence": 1},
                                 Auth("A", True), links, known_data)
    chosen = [int(name[2:], 16) for name in result["path"].split("/") if name]
    if result["status"] not in {"OK", "NO_INDEPENDENT_CHANNEL"}:
        raise ValueError("unexpected authorization failure in the known control fixture")
    # Fleet-level NO_CHANNEL includes the core's independent-control no-path result.
    return row(name, "control", chosen)


class FleetReadingFixture:
    """Tiny host fixture for the two numeric update contracts, not a new validator API."""

    def __init__(self, current):
        self.current = current

    def update(self, *, latency=None, loss=None):
        latency = self.current.latency if latency is None else latency
        loss = self.current.loss_ppm if loss is None else loss
        if not 0 <= latency < 2**64 - 1 or not 0 <= loss <= 1_000_000:
            return "INVALID_READING"
        self.current = replace(self.current, latency=latency, loss_ppm=loss)
        return "OK"


def rejected_update_case(name, **replacement):
    fixture = FleetReadingFixture(link(1, 10))
    before = fixture.current
    status = fixture.update(**replacement)
    assert fixture.current == before
    assert data_case("after-rejection", [fixture.current, link(2, 40)])["failover"] == "1,2"
    return row(name, "fleet-update", [], status=status)


def sequenced_control_case(name, *, rollback=False):
    policy = model()
    known = policy.choose("A", "B", 0, [link(1, 10)])
    tick = 2 if rollback else 1
    links = [link(4, 1, tick=tick)]
    notice = {"source": "A", "target": "B", "kind": "STOP", "sequence": 1}
    assert policy.send_control(tick, notice, Auth("A", True), links, known)["status"] == "OK"
    if rollback:
        notice["sequence"] = 2
    result = policy.send_control(1, notice, Auth("A", True), links, known)
    # The fleet facade rejects rollback before calling core. Core itself meters
    # INVALID_INPUT; this explicit fixture mapping is not a core status alias.
    status = result["status"]
    if rollback:
        assert status == "INVALID_INPUT"
        status = "CLOCK_ROLLBACK"
    notice["sequence"] = 2
    assert policy.send_control(tick, notice, Auth("A", True), links, known)["status"] == "OK"
    return row(name, "control", [], status=status)


def rows():
    return [
        data_case("lan-up", [link(2, 40), link(1, 10), link(3, 100), link(4, 1)]),
        data_case("wifi-before-spike", [link(2, 5), link(1, 50), link(3, 100), link(4, 1)]),
        data_case("wifi-spike", [link(2, 600, tick=1, loss=500_000, jitter=90),
                                 link(1, 50, tick=1), link(3, 100, tick=1), link(4, 1, tick=1)], tick=1),
        data_case("ble-control-only-data", [link(4, 1, tick=1)], tick=1),
        control_case("ble-control-only-control", [link(4, 1, tick=1)]),
        data_case("ble-reviewed-data", [link(4, 1, reviewed=True)]),
        data_case("partition-data", [link(1, 10, tick=1, available=False), link(2, 5, tick=1, available=False),
                                      link(4, 1, tick=1, available=False)], tick=1),
        control_case("partition-control", [link(4, 1, tick=1, available=False)]),
        data_case("xiaozhi-websocket-lan-gateway", [link(6, 15)]),
        data_case("equal-score-tie", [link(2, 10), link(1, 10)]),
        rejected_update_case("invalid-latency-u64max-update", latency=2**64 - 1),
        rejected_update_case("invalid-loss-ppm-update", loss=1_000_001),
        sequenced_control_case("control-replay"),
        sequenced_control_case("clock-rollback", rollback=True),
        data_case("xiaozhi-ws-lost", [link(6, 15, tick=1, available=False)], tick=1),
        data_case("xiaozhi-ws-lost-lan-fallback", [link(6, 15, tick=1, available=False),
                                               link(1, 50, tick=1)], tick=1),
        data_case("empty-endpoints-no-channel", []),
    ]


def artifacts():
    result = rows()
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(result)
    table = ["# Scripted fleet endpoint selection", "",
             "The existing merged overlay policy chooses paths from these supplied readings.",
             "Identity assignments and prior verification are fixtures; no radio, discovery or cryptography runs.", "",
             PROVENANCE, "",
             "| Scenario | Traffic | Status | Endpoint | Kind | URI | Failover order |",
             "|---|---|---|---:|---|---|---|"]
    table.extend("| " + " | ".join(record[field] for field in FIELDS) + " |" for record in result)
    return {"fleet-scenarios.tsv": stream.getvalue().encode("utf-8"),
            "fleet-scenarios.md": ("\n".join(table) + "\n").encode("utf-8")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True, help="explicit artifact destination")
    args = parser.parse_args()
    outputs = artifacts()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in outputs.items():
        (args.output_dir / name).write_bytes(payload)
    repo = Path(__file__).resolve().parents[2]
    source = repo / "tools/overlay_sim/model.py"
    manifest = {"evidence": "14 actual Python core-derived rows; 3 explicitly labeled fleet-boundary contract fixtures",
                "identity_scope": "explicit fixture assignments; not an identity derivation oracle",
                "rows": len(rows()),
                "fleet_boundary_rows": list(BOUNDARY_ROWS),
                "boundary_core_status": {"clock-rollback": "INVALID_INPUT"},
                "fleet_contract_source_sha256_lf": {path: hashlib.sha256((repo / path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
                    for path in ("rust/rpp-fleet/src/endpoint.rs", "rust/rpp-fleet/src/resolver.rs")},
                "fixture_source_sha256_lf": hashlib.sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
                "policy_source_sha256_lf": hashlib.sha256(source.read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
                "sha256": {name: hashlib.sha256(value).hexdigest() for name, value in outputs.items()},
                "bytes": {name: len(value) for name, value in outputs.items()}}
    (args.output_dir / "fleet-manifest.json").write_bytes((json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    print(json.dumps(manifest, sort_keys=True))


if __name__ == "__main__":
    main()
