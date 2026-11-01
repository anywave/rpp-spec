"""Bounded policy properties. Each test states its failing mutation in the docstring."""

from dataclasses import replace
import os

import pytest

from tools.overlay_sim import model
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
    row = sim.send_control(0, dict(source="A", target="B", kind="START", sequence=0), Auth("A", True), [link("bt", "Bluetooth")])
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
    assert simulator().send_control(0, message, Auth("A", True), [link("bt", "Bluetooth")])["status"] == "DENIED"


def test_control_auth_consent_sequence_and_member_rejection():
    """Mutation trust-bypass: accepting failed signatures/replays or nonmembers fails."""
    sim = simulator()
    links = [link("bt", "Bluetooth")]
    message = dict(source="A", target="B", kind="ALIVE", sequence=0)
    assert sim.send_control(0, message, Auth("A", False), links)["status"] == "DENIED"
    assert sim.send_control(0, message, Auth("A", "unverified"), links)["status"] == "DENIED"
    assert sim.send_control(0, dict(message, kind=["ALIVE"]), Auth("A", True), links)["status"] == "DENIED"
    assert sim.send_control(0, dict(message, source=["A"]), Auth("A", True), links)["status"] == "DENIED"
    assert sim.send_control(0, dict(message, sequence=2**64), Auth("A", True), links)["status"] == "DENIED"
    assert sim.send_control(0, message, Auth("R", True), links)["status"] == "DENIED"
    assert sim.send_control(0, message, Auth("A", True), links)["status"] == "OK"
    assert sim.send_control(0, message, Auth("A", True), links)["status"] == "DENIED"
    message.update(target="UNKNOWN", sequence=1)
    assert sim.send_control(0, message, Auth("A", True), links)["status"] == "DENIED"
    assert Simulator({"A", "B"}, set()).send_control(0, dict(source="A", target="B", kind="STOP", sequence=0), Auth("A", True), links)["status"] == "DENIED"


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
