"""Fleet endpoint tables from the existing merged Python overlay policy.

This scaffold uses actual tools.overlay_sim.model selection. It is not an
independent identity derivation oracle, transport implementation or verifier.
Endpoint records/readings/authorization are fixed fixtures. No cost formula is
reimplemented here and no randomness, network or cryptography is used.
"""

import argparse
import csv
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


def model():
    return Simulator({"A", "B"}, {("A", "B"), ("B", "A")})


def link(endpoint, latency, *, tick=0, available=True, loss=0, jitter=0, reviewed=False):
    return Link(f"ep{endpoint:08x}", "A", "B", UNDERLAYS[endpoint], latency, loss, jitter,
                available, tick, "ble" if endpoint == 4 else "ip", True, reviewed, True)


def endpoint_id(selected):
    return int(selected.name[2:], 16)


def row(name, traffic, ids):
    selected = ids[0] if ids else None
    return {"scenario": name, "traffic": traffic, "status": "OK" if ids else "NO_CHANNEL",
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
    source = Path(__file__).resolve().parents[2] / "tools/overlay_sim/model.py"
    manifest = {"evidence": "actual merged Python overlay policy applied to fixed fleet endpoint scenarios",
                "identity_scope": "explicit fixture assignments; not an identity derivation oracle",
                "rows": len(rows()),
                "policy_source_sha256_lf": hashlib.sha256(source.read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
                "sha256": {name: hashlib.sha256(value).hexdigest() for name, value in outputs.items()},
                "bytes": {name: len(value) for name, value in outputs.items()}}
    (args.output_dir / "fleet-manifest.json").write_bytes((json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    print(json.dumps(manifest, sort_keys=True))


if __name__ == "__main__":
    main()
