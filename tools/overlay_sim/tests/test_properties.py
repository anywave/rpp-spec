"""Bounded policy properties. Each test states its failing mutation in the docstring."""

from dataclasses import replace
import os
from pathlib import Path
import subprocess
import sys

import pytest

from tools.overlay_sim import model
from tools.overlay_sim.mutation_check import is_assertion_failure
from tools.overlay_sim.model import Auth, Billboard, CONTROL_KINDS, Link, Simulator, serialize
from tools.overlay_sim.scenarios import artifacts, link, run, simulator


@pytest.fixture(autouse=True)
def in_memory_mutation(monkeypatch):
    mutation = os.environ.get("OVERLAY_MUTATION")
    if mutation == "unavailable":
        original = Simulator._usable
        monkeypatch.setattr(Simulator, "_usable", lambda self, item, *args: original(self, replace(item, available=True), *args))
    elif mutation == "start":
        monkeypatch.setattr(model, "CONTROL_KINDS", model.CONTROL_KINDS | {"START"})
    elif mutation == "expiry":
        monkeypatch.setattr(Simulator, "active_billboards", lambda self, tick, machine: tuple(
            model.asdict(b) for _, b in sorted(self._billboards.items()) if b.machine == machine and b.since <= tick))
    elif mutation == "after_token":
        original = Simulator.send_data
        monkeypatch.setattr(Simulator, "send_data", lambda self, tick, source, target, links, scripted_failures=None:
                            original(self, tick, source, target, links, {k: 0 for k in (scripted_failures or {})}))
    elif mutation == "meter":
        original = Simulator._meter
        def success_only(self, *args, **kwargs):
            status = args[6] if len(args) > 6 else kwargs.get("status", "OK")
            return original(self, *args, **kwargs) if status != "FAILED" else None
        monkeypatch.setattr(Simulator, "_meter", success_only)
    elif mutation == "unstable":
        original = model.serialize
        counter = iter(range(1000))
        monkeypatch.setattr(model, "serialize", lambda rows: original(rows) + str(next(counter)).encode())
    elif mutation == "independence":
        original = Simulator.choose
        def shared_domains(self, source, target, tick, links, traffic="data", excluded=frozenset(), avoid_domains=frozenset()):
            return original(self, source, target, tick, links, traffic, excluded,
                            frozenset() if traffic == "control" else avoid_domains)
        monkeypatch.setattr(Simulator, "choose", shared_domains)
    elif mutation == "known_path":
        monkeypatch.setattr(Simulator, "_known_independent_reference", lambda *_: True)
    elif mutation == "issuer_replay":
        original = Simulator.deliver_billboard
        def global_receipt(self, tick, board, auth, source, target, links):
            if isinstance(board, Billboard) and any(receipt == board.receipt for _, receipt in self._receipts):
                return self._meter(tick, next(self._ids), "billboard", source, target, status="DENIED")
            return original(self, tick, board, auth, source, target, links)
        monkeypatch.setattr(Simulator, "deliver_billboard", global_receipt)
    elif mutation == "delivery_expiry":
        monkeypatch.setattr(Simulator, "_delivery_current", staticmethod(lambda *_: True))
    elif mutation == "tunnel_bypass":
        original = Simulator._usable
        monkeypatch.setattr(Simulator, "_usable", lambda self, item, tick, traffic, excluded:
                            original(self, replace(item, tunnel_verified=True) if traffic == "control" else item,
                                     tick, traffic, excluded))
    elif mutation == "premature_clock":
        original = Simulator._time_valid
        def advance_during_validation(self, tick):
            valid = original(self, tick)
            if valid:
                self._clock = tick
            return valid
        monkeypatch.setattr(Simulator, "_time_valid", advance_during_validation)



def test_available_channel_all_masks_and_live_measurements():
    """Mutation unavailable: selecting a link marked down violates every-mask property."""
    for mask in range(8):
        links = [link(f"link-{i}", available=bool(mask & (1 << i)), latency=i + 1) for i in range(3)]
        path = simulator().choose("A", "B", 0, links)
        available = [x for x in links if x.available]
        assert bool(path) == bool(available)
        if path:
            assert all(x.available for x in path)
            assert path == (min(available, key=lambda x: x.score),)
    sim = simulator()
    assert sim.choose("A", "B", 0, [link("slow", jitter=40), link("lossy", loss_ppm=100_000), link("fast", latency=20)])[0].name == "fast"


def test_available_control_clean():
    """Clean mutation control: available trusted status path remains selectable."""
    assert simulator().choose("A", "B", 0, [link("up")])[0].name == "up"


def test_control_start_forbidden_even_when_signed():
    """Mutation start: adding START to the allowlist improperly permits an operation."""
    sim = simulator()
    links = [link("lan"), link("bt", "Bluetooth", latency=20)]
    data = sim.choose("A", "B", 0, links)
    row = sim.send_control(0, dict(source="A", target="B", kind="START", sequence=0), Auth("A", True), links, data)
    assert row["status"] == "DENIED"


def test_control_allowlist_and_independent_channel_clean():
    """Mutation same-path: allowing shared failure domains defeats independent control."""
    sim = simulator()
    links = [link("lan", domain="local"), link("wifi", "Wi-Fi", latency=11, domain="local"), link("bt", "Bluetooth", latency=90)]
    data = sim.choose("A", "B", 0, links)
    original_members, original_consents = sim.members, sim.consents
    for sequence, kind in enumerate(sorted(CONTROL_KINDS)):
        row = sim.send_control(0, dict(source="A", target="B", kind=kind, sequence=sequence), Auth("A", True), links, data)
        assert row["status"] == "OK" and row["path"] == "bt"
    assert sim.members == original_members and sim.consents == original_consents
    assert not any(r["traffic"] == "data" for r in sim.rows)
    assert sim.send_control(0, dict(source="A", target="B", kind="ALIVE", sequence=6), Auth("A", True), [links[0]], data)["status"] == "NO_INDEPENDENT_CHANNEL"


@pytest.mark.parametrize("forbidden", ["grant", "consent", "key", "model", "prompt", "answer", "payload"])
def test_no_payload_fields_on_control(forbidden):
    """Mutation unknown-fields: removing exact field-set check allows content smuggling."""
    message = dict(source="A", target="B", kind="ALIVE", sequence=0)
    message[forbidden] = "forbidden-content"
    sim = simulator()
    links = [link("lan"), link("bt", "Bluetooth", latency=20)]
    data = sim.choose("A", "B", 0, links)
    assert sim.send_control(0, message, Auth("A", True), links, data)["status"] == "DENIED"


def test_control_auth_consent_sequence_and_member_rejection():
    """Mutation trust-bypass: accepting failed signatures/replays or nonmembers fails."""
    sim = simulator()
    links = [link("lan"), link("bt", "Bluetooth", latency=20)]
    data = sim.choose("A", "B", 0, links)
    message = dict(source="A", target="B", kind="ALIVE", sequence=0)
    assert sim.send_control(0, message, Auth("A", False), links, data)["status"] == "DENIED"
    assert sim.send_control(0, message, Auth("A", "unverified"), links, data)["status"] == "DENIED"
    assert sim.send_control(0, dict(message, kind=["ALIVE"]), Auth("A", True), links, data)["status"] == "DENIED"
    assert sim.send_control(0, dict(message, source=["A"]), Auth("A", True), links, data)["status"] == "DENIED"
    assert sim.send_control(0, dict(message, sequence=2**64), Auth("A", True), links, data)["status"] == "DENIED"
    assert sim.send_control(0, message, Auth("R", True), links, data)["status"] == "DENIED"
    assert sim.send_control(0, message, Auth("A", True), links, data)["status"] == "OK"
    assert sim.send_control(0, message, Auth("A", True), links, data)["status"] == "DENIED"
    message.update(target="UNKNOWN", sequence=1)
    assert sim.send_control(0, message, Auth("A", True), links, data)["status"] == "DENIED"
    assert Simulator({"A", "B"}, set()).send_control(0, dict(source="A", target="B", kind="STOP", sequence=0), Auth("A", True), links, data)["status"] == "DENIED"


def test_billboard_half_open_expiry_and_future_hold():
    """Mutation expiry: omitting until check applies an expired rule."""
    sim = simulator()
    board = Billboard("B", "rule", "Pause the application.", 2, 4, "r1")
    assert sim.deliver_billboard(0, board, Auth("A", True), "A", "B", [link("lan")])["status"] == "HELD_UNTIL_SINCE"
    assert sim.active_billboards(1, "B") == ()
    assert len(sim.active_billboards(2, "B")) == 1
    assert len(sim.active_billboards(3, "B")) == 1
    assert sim.active_billboards(4, "B") == ()
    with pytest.raises(ValueError, match="backwards"):
        sim.active_billboards(3, "B")
    assert sim.active_billboards(100, "B") == ()
    with pytest.raises(ValueError, match="backwards"):
        sim.active_billboards(1, "B")


def test_billboard_unexpired_clean():
    """Clean mutation control: a verified current rule is present before expiry."""
    sim = simulator()
    board = Billboard("B", "rule", "Pause the application.", 0, 2, "r1")
    assert sim.deliver_billboard(0, board, Auth("A", True), "A", "B", [link("lan")])["status"] == "DELIVERED"
    assert sim.active_billboards(1, "B")[0]["receipt"] == "r1"


def test_billboard_auth_scope_shape_replay_and_expired_delivery():
    """Mutation authorization: skipping receipt, issuer scope or shape checks fails."""
    sim = simulator()
    board = Billboard("B", "rule", "Pause the application.", 0, 2, "r1")
    links = [link("lan")]
    assert sim.deliver_billboard(0, board, Auth("A", False), "A", "B", links)["status"] == "DENIED"
    assert sim.deliver_billboard(0, board, Auth("R", True), "A", "B", links)["status"] == "DENIED"
    assert sim.deliver_billboard(0, replace(board, machine="R"), Auth("A", True), "A", "B", links)["status"] == "DENIED"
    assert sim.deliver_billboard(0, replace(board, since=2), Auth("A", True), "A", "B", links)["status"] == "DENIED"
    assert sim.deliver_billboard(0, replace(board, receipt=""), Auth("A", True), "A", "B", links)["status"] == "DENIED"
    assert sim.deliver_billboard(0, board, Auth("A", True), "A", "B", links)["status"] == "DELIVERED"
    assert sim.deliver_billboard(0, board, Auth("A", True), "A", "B", links)["status"] == "DENIED"
    assert simulator().deliver_billboard(2, board, Auth("A", True), "A", "B", links)["status"] == "DENIED"
    assert simulator().deliver_billboard(0, board, Auth("A", True), "A", "B", [])["status"] == "NO_CHANNEL"


def test_before_token_retry_preserves_every_meter_row():
    """Mutation meter: dropping failed attempts loses the first row of retry accounting."""
    sim = simulator()
    sim.send_data(0, "A", "B", [link("lan"), link("internet", "internet", latency=30)], {"lan": 0})
    assert len(sim.rows) == 2
    assert [r["status"] for r in sim.rows] == ["FAILED", "OK"]
    assert [r["path"] for r in sim.rows] == ["lan", "internet"]
    assert sim.rows[0]["request"] == sim.rows[1]["request"]
    assert sim.rows[0]["tokens"] == 0


def test_success_meter_clean():
    """Clean mutation control: successful attempts still have one row."""
    sim = simulator()
    sim.send_data(0, "A", "B", [link("lan")])
    assert len(sim.rows) == 1 and sim.rows[0]["status"] == "OK"


def test_after_first_token_never_retries():
    """Mutation after_token: treating nonzero token failure as zero creates a retry."""
    for emitted in range(1, 5):
        sim = simulator()
        sim.send_data(0, "A", "B", [link("lan"), link("internet", "internet", latency=30)], {"lan": emitted})
        assert len(sim.rows) == 1
        assert sim.rows[0]["status"] == "FAILED" and sim.rows[0]["tokens"] == emitted


def test_relay_breaker_staleness_adapter_and_outage():
    """Mutation breaker/relay: ignoring open_until or removing relay forwarding fails."""
    sim = simulator()
    relay = [link("ar", right="R"), link("rb", left="R")]
    assert tuple(x.name for x in sim.choose("A", "B", 0, relay)) == ("ar", "rb")
    denied_hop = Simulator({"A", "B", "R"}, {("A", "B"), ("A", "R")})
    assert denied_hop.choose("A", "B", 0, relay) == ()
    for tick in (0, 1):
        sim.send_data(tick, "A", "B", [link("lan", tick=tick)], {"lan": 0})
    assert sim.choose("A", "B", 2, [link("lan", tick=2)]) == ()
    assert sim.choose("A", "B", 3, [link("lan", tick=3)])[0].name == "lan"
    assert sim.choose("A", "B", 10, [link("stale")]) == ()
    assert sim.choose("A", "B", 0, [link("future", tick=1)]) == ()
    assert sim.choose("A", "B", 0, [link("untrusted", observation_verified=False)]) == ()
    assert sim.choose("A", "B", 0, [link("bt", "Bluetooth"), link("lora", "LoRa")]) == ()
    assert sim.choose("A", "B", 0, [link("adapter", "Bluetooth", reviewed_adapter=True)])[0].name == "adapter"
    assert sim.choose("A", "B", 0, [link("unverified", tunnel_verified=False)]) == ()
    sim.send_data(3, "A", "B", [])
    sim.send_data(3, "A", "UNKNOWN", [])
    assert [r["status"] for r in sim.rows[-2:]] == ["NO_CHANNEL", "DENIED"]


def test_byte_identical_reruns_and_stable_tiebreak():
    """Mutation unstable: appending a per-call counter produces different output bytes."""
    assert artifacts() == artifacts()
    rows, _ = run()
    assert model.serialize(rows) == model.serialize(rows)
    assert serialize(rows).endswith(b"\n")
    assert simulator().choose("A", "B", 0, [link("z"), link("a")])[0].name == "a"
    assert simulator().choose("A", "B", 0, [link("a"), link("z")])[0].name == "a"


def test_invalid_readings_and_duplicate_ids_rejected():
    """Mutation input-validation: accepting negative/unknown/duplicate readings fails."""
    for kwargs in ({"latency": -1}, {"loss_ppm": 1_000_001}, {"jitter": -1}, {"tick": -1}, {"underlay": "unknown"},
                   {"available": "false"}, {"tunnel_verified": "false"}, {"reviewed_adapter": 1}, {"observation_verified": "false"}):
        with pytest.raises(ValueError):
            link("bad", **kwargs)
    with pytest.raises(ValueError):
        simulator().choose("A", "B", 0, [link("same"), link("same")])
    with pytest.raises(ValueError):
        Link("same", "A", "A", "LAN", 1, 0, 0, True, 0, "d")


def test_invalid_operations_metered_and_time_cannot_rollback():
    """Mutation error-skip: invalid inputs/clock rollback must retain a denial row."""
    sim = simulator()
    sim.send_data(0, "A", "B", [link("lan")], {"lan": -1})
    sim.send_data(0, "A", "B", [link("lan"), link("lan")])
    sim.send_control(0, {}, Auth("A", True), [link("lan"), link("lan")])
    board = Billboard("B", "rule", "Pause.", 0, 10, "r1")
    sim.deliver_billboard(0, board, Auth("A", True), "A", "B", [link("lan"), link("lan")])
    assert [row["status"] for row in sim.rows] == ["INVALID_INPUT"] * 4
    sim.send_data(2, "A", "B", [link("lan", tick=2)])
    sim.send_data(1, "A", "B", [link("lan", tick=1)])
    assert [row["status"] for row in sim.rows[-2:]] == ["OK", "INVALID_INPUT"]
    assert [row["request"] for row in sim.rows] == list(range(1, 7))


def test_control_requires_known_path_and_disjoint_verified_tunnel():
    """Mutation independence/known_path/tunnel_bypass: reference, separate domain and verified tunnel are all required."""
    sim = simulator()
    message = dict(source="A", target="B", kind="ALIVE", sequence=0)
    lan, bt = link("lan"), link("bt", "Bluetooth", latency=20)
    assert sim.send_control(0, message, Auth("A", True), [bt])["status"] == "DENIED"
    assert sim.send_control(0, message, Auth("A", True), [bt], (lan,))["status"] == "DENIED"
    data = sim.choose("A", "B", 0, [lan])
    assert sim.send_control(0, message, Auth("A", True), [lan], data)["status"] == "NO_INDEPENDENT_CHANNEL"
    assert sim.send_control(0, message, Auth("A", True), [replace(bt, tunnel_verified=False)], data)["status"] == "NO_INDEPENDENT_CHANNEL"
    assert sim.send_control(0, message, Auth("A", True), [bt], data)["status"] == "OK"


def test_control_valid_independent_fixture_clean():
    """Clean independence control: known LAN reference and verified Bluetooth path succeed."""
    sim = simulator()
    data = sim.choose("A", "B", 0, [link("lan")])
    assert sim.send_control(0, dict(source="A", target="B", kind="ALIVE", sequence=0),
                            Auth("A", True), [link("bt", "Bluetooth")], data)["status"] == "OK"


def test_billboard_receipts_are_per_issuer_and_cannot_burn_another_id():
    """Mutation issuer_replay: global receipt suppression lets one issuer burn another's ID."""
    sim = Simulator({"A", "B", "R"}, {("A", "B"), ("R", "B")},
                    {("A", "B", "rule"), ("R", "B", "rule")})
    board = Billboard("B", "rule", "Pause.", 0, 2, "shared-id")
    assert sim.deliver_billboard(0, board, Auth("A", True), "A", "B", [link("lan")])["status"] == "DELIVERED"
    assert sim.deliver_billboard(0, board, Auth("R", True), "R", "B", [link("r-b", left="R")])["status"] == "DELIVERED"
    assert len(sim.active_billboards(0, "B")) == 2
    assert sim.deliver_billboard(0, board, Auth("A", True), "A", "B", [link("lan")])["status"] == "DENIED"


def test_billboard_delivery_rejects_expired_before_storage():
    """Mutation delivery_expiry: accepting an already-expired delivery incorrectly stores its receipt."""
    sim = simulator()
    board = Billboard("B", "rule", "Pause.", 0, 2, "expired")
    assert sim.deliver_billboard(2, board, Auth("A", True), "A", "B", [link("lan", tick=2)])["status"] == "DENIED"
    assert ("A", "expired") not in sim._receipts
    assert sim._billboards == {}


def test_invalid_far_future_calls_do_not_lock_out_later_valid_work():
    """Mutation premature-clock: denied/invalid/no-channel future calls must not advance accepted time."""
    sim = simulator()
    board = Billboard("B", "rule", "Pause.", 0, 2, "r1")
    message = dict(source="A", target="B", kind="ALIVE", sequence=0)
    sim.send_data(10000, "A", "B", [link("lan", tick=10000)], {"lan": -1})
    sim.send_data(10000, "UNKNOWN", "B", [link("lan", tick=10000)])
    sim.send_data(10000, "A", "B", [])
    sim.send_control(10000, message, None, [link("bt", "Bluetooth", tick=10000)])
    sim.send_control(10000, message, Auth("A", True), [link("bt", "Bluetooth", tick=10000)])
    known = sim.choose("A", "B", 0, [link("lan")])
    sim.send_control(10000, message, Auth("A", True), [link("lan", tick=10000)], known)
    sim.deliver_billboard(10000, board, Auth("A", True), "A", "B", [link("lan", tick=10000)])
    sim.deliver_billboard(10000, replace(board, until=20000), Auth("A", True), "A", "B", [])
    with pytest.raises(ValueError, match="recipient"):
        sim.active_billboards(10000, "UNKNOWN")
    with pytest.raises(ValueError, match="recipient"):
        sim.active_billboards(10000, [])
    if sim._clock != 0:
        raise AssertionError("Rejected future calls advanced accepted time")
    sim.send_data(1, "A", "B", [link("lan", tick=1)])
    assert sim.rows[-1]["status"] == "OK" and sim._clock == 1


def test_malformed_auth_billboards_and_same_node_fail_closed_without_exceptions():
    """Mutation shape-guard: non-Auth/non-Billboard and malformed issuer fields must be metered."""
    sim = simulator()
    links = [link("lan"), link("bt", "Bluetooth", latency=20)]
    data = sim.choose("A", "B", 0, links)
    message = dict(source="A", target="B", kind="ALIVE", sequence=0)
    board = Billboard("B", "rule", "Pause.", 0, 2, "r1")
    for auth in (None, {}, Auth([], True)):
        assert sim.send_control(1000, message, auth, links, data)["status"] == "DENIED"
        assert sim.deliver_billboard(1000, board, auth, "A", "B", links)["status"] == "DENIED"
    for bad in (None, {}, replace(board, kind=[]), replace(board, fact="\ud800"), replace(board, machine=[])):
        assert sim.deliver_billboard(1000, bad, Auth("A", True), "A", "B", links)["status"] == "DENIED"
    sim.send_data(0, "A", "A", links)
    assert sim.rows[-1]["status"] == "DENIED_SELF_TARGET"
    assert sim.send_control(0, dict(message, target="A"), Auth("A", True), links, data)["status"] == "DENIED_SELF_TARGET"
    assert sim.deliver_billboard(0, board, Auth("A", True), "A", "A", links)["status"] == "DENIED_SELF_TARGET"
    assert sim._clock == 0 and len(sim.rows) == 14


def test_scenario_requires_explicit_output_directory_and_snapshots_normalize_crlf(tmp_path):
    """Mutation in-tree-default: omitted output directory must never rewrite committed artifacts."""
    root = Path(__file__).resolve().parents[3]
    generated = artifacts()
    before = {name: (root / "tools" / "overlay_sim" / "results" / name).read_bytes() for name in generated}
    command = [sys.executable, "-m", "tools.overlay_sim.scenarios"]
    result = subprocess.run(command, cwd=root, capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 2 and "--output-dir" in result.stderr
    for name, raw in before.items():
        assert (root / "tools" / "overlay_sim" / "results" / name).read_bytes() == raw
    subprocess.run(command + ["--output-dir", str(tmp_path)], cwd=root, check=True, capture_output=True)
    for name, expected in generated.items():
        assert (tmp_path / name).read_bytes() == expected
        assert before[name].replace(b"\r\n", b"\n") == expected


def test_mutation_runner_rejects_runtime_collection_and_missing_assertion_results():
    """Mutation count-any-failure: runtime/collection failures must never count as killed mutants."""
    def result(code, output):
        return subprocess.CompletedProcess([], code, output, "")
    assert is_assertion_failure(result(1, "E       AssertionError: intended mutation caught\n1 failed\n"))
    for code, output in (
        (1, "E       TypeError: bad fixture\n1 failed\n"),
        (2, "E       AssertionError: collection error\n1 failed\n"),
        (0, "E       AssertionError: ordinary stdout\n1 passed\n"),
        (1, "quoted AssertionError in test source\nE       RuntimeError: oops\n1 failed\n"),
        (1, "E       AssertionError: no test summary\n"),
    ):
        assert not is_assertion_failure(result(code, output))
