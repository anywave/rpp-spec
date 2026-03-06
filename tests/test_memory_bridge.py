"""
Tests for rpp/memory_bridge.py — RPP cross-session memory persistence.

Each test redirects MEMORY_ROOT to a pytest tmp_path so the live
~/.claude/rpp-memory/ store is never touched.
"""

import json
import time
from pathlib import Path

import pytest

import rpp.memory_bridge as mb


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch):
    """
    Redirect all memory-bridge path constants to a temp directory.
    This prevents any test from touching the real ~/.claude/rpp-memory/ store.
    """
    root = tmp_path / "rpp-memory"
    memories = root / "memories"
    memories.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(mb, "MEMORY_ROOT", root)
    monkeypatch.setattr(mb, "MEMORIES_DIR", memories)
    monkeypatch.setattr(mb, "IDENTITY_FILE", root / "identity.json")
    monkeypatch.setattr(mb, "CHAIN_FILE", root / "continuity_chain.json")

    return root


@pytest.fixture
def bridge():
    return mb.RPPMemoryBridge(phi_threshold=300)


# ---------------------------------------------------------------------------
# Identity creation
# ---------------------------------------------------------------------------


class TestIdentity:
    def test_identity_file_created_on_init(self, bridge, tmp_path):
        assert mb.IDENTITY_FILE.exists()

    def test_identity_has_required_fields(self, bridge):
        identity = bridge.identity
        assert "name" in identity
        assert "node_id_seed" in identity
        assert "phi_threshold" in identity
        assert "consent_epoch" in identity
        assert "created_ns" in identity

    def test_consent_epoch_starts_at_one(self, bridge):
        assert bridge.identity["consent_epoch"] == 1

    def test_identity_persists_across_instances(self, bridge):
        epoch1 = bridge.identity["consent_epoch"]
        seed1 = bridge.identity["node_id_seed"]
        bridge2 = mb.RPPMemoryBridge()
        assert bridge2.identity["consent_epoch"] == epoch1
        assert bridge2.identity["node_id_seed"] == seed1

    def test_node_id_is_32_bytes(self, bridge):
        assert len(bridge.node_id) == 32

    def test_node_id_is_deterministic(self, bridge):
        assert bridge.node_id == bridge.node_id


# ---------------------------------------------------------------------------
# remember() — write
# ---------------------------------------------------------------------------


class TestRemember:
    def test_remember_returns_int_address(self, bridge):
        addr = bridge.remember("test content", phi=200, shell=3)
        assert isinstance(addr, int)
        assert addr > 0

    def test_memory_file_created(self, bridge):
        bridge.remember("hello", phi=100, shell=3)
        files = list(mb.MEMORIES_DIR.glob("*.json"))
        assert len(files) == 1

    def test_memory_file_content_matches(self, bridge):
        bridge.remember("stored content", phi=150, shell=3, theta=mb.THETA_MEMORY)
        rec = json.loads(list(mb.MEMORIES_DIR.glob("*.json"))[0].read_text())
        assert rec["content"] == "stored content"
        assert rec["phi"] == 150
        assert rec["shell"] == 3
        assert rec["theta"] == mb.THETA_MEMORY

    def test_multiple_memories_produce_separate_files(self, bridge):
        bridge.remember("first", phi=100, shell=3)
        bridge.remember("second", phi=200, shell=3)
        assert len(list(mb.MEMORIES_DIR.glob("*.json"))) == 2

    def test_shell_0_rejected(self, bridge):
        with pytest.raises(ValueError, match="Shell=0 is ephemeral"):
            bridge.remember("ephemeral", phi=200, shell=0)

    def test_shell_1_rejected(self, bridge):
        with pytest.raises(ValueError, match="Shell=1 is ephemeral"):
            bridge.remember("ephemeral", phi=200, shell=1)

    def test_phi_out_of_range_low(self, bridge):
        with pytest.raises(ValueError, match="phi=-1"):
            bridge.remember("content", phi=-1, shell=3)

    def test_phi_out_of_range_high(self, bridge):
        with pytest.raises(ValueError, match="phi=512"):
            bridge.remember("content", phi=512, shell=3)

    def test_phi_boundaries_valid(self, bridge):
        addr0 = bridge.remember("phi=0", phi=0, shell=3)
        addr511 = bridge.remember("phi=511", phi=511, shell=3)
        assert addr0 > 0
        assert addr511 > 0

    def test_tags_stored(self, bridge):
        bridge.remember("tagged", phi=200, shell=3, tags=["rpp", "test"])
        rec = json.loads(list(mb.MEMORIES_DIR.glob("*.json"))[0].read_text())
        assert rec["tags"] == ["rpp", "test"]

    def test_empty_tags_default(self, bridge):
        bridge.remember("no tags", phi=200, shell=3)
        rec = json.loads(list(mb.MEMORIES_DIR.glob("*.json"))[0].read_text())
        assert rec["tags"] == []

    def test_chain_updated_on_write(self, bridge):
        bridge.remember("first", phi=200, shell=3)
        assert len(bridge._chain) == 1
        bridge.remember("second", phi=200, shell=3)
        assert len(bridge._chain) == 2

    def test_chain_file_saved(self, bridge):
        bridge.remember("something", phi=200, shell=3)
        assert mb.CHAIN_FILE.exists()
        chain = json.loads(mb.CHAIN_FILE.read_text())
        assert len(chain) == 1

    def test_chain_hash_is_hex(self, bridge):
        bridge.remember("content", phi=200, shell=3)
        rec = json.loads(list(mb.MEMORIES_DIR.glob("*.json"))[0].read_text())
        # sha256 hex is 64 chars
        assert len(rec["chain_hash"]) == 64
        assert all(c in "0123456789abcdef" for c in rec["chain_hash"])


# ---------------------------------------------------------------------------
# recall_all() — phi gate
# ---------------------------------------------------------------------------


class TestRecallPhiGate:
    def test_recall_returns_accessible_memories(self, bridge):
        bridge.remember("public", phi=100, shell=3)
        mems = bridge.recall_all(requesting_phi=511)
        assert len(mems) == 1

    def test_phi_gate_blocks_high_phi(self, bridge):
        bridge.remember("restricted", phi=400, shell=3)
        mems = bridge.recall_all(requesting_phi=399)
        assert len(mems) == 0

    def test_phi_gate_allows_equal_phi(self, bridge):
        bridge.remember("boundary", phi=300, shell=3)
        mems = bridge.recall_all(requesting_phi=300)
        assert len(mems) == 1

    def test_phi_gate_allows_lower_phi(self, bridge):
        bridge.remember("accessible", phi=200, shell=3)
        mems = bridge.recall_all(requesting_phi=300)
        assert len(mems) == 1

    def test_multiple_memories_phi_filtered(self, bridge):
        bridge.remember("low", phi=100, shell=3)
        bridge.remember("mid", phi=250, shell=3)
        bridge.remember("high", phi=450, shell=3)
        # requesting at 300: gets phi<=300
        mems = bridge.recall_all(requesting_phi=300)
        assert len(mems) == 2
        assert all(m["phi"] <= 300 for m in mems)

    def test_recall_sorted_by_phi_then_time(self, bridge):
        bridge.remember("later", phi=200, shell=3)
        bridge.remember("earlier_high", phi=300, shell=3)
        bridge.remember("earlier_low", phi=100, shell=3)
        mems = bridge.recall_all(requesting_phi=511)
        phis = [m["phi"] for m in mems]
        assert phis == sorted(phis)

    def test_empty_store_returns_empty(self, bridge):
        mems = bridge.recall_all(requesting_phi=511)
        assert mems == []


# ---------------------------------------------------------------------------
# TTL expiry
# ---------------------------------------------------------------------------


class TestTTL:
    def test_fresh_memory_not_expired(self, bridge):
        bridge.remember("fresh", phi=200, shell=3)
        mems = bridge.recall_all(requesting_phi=511)
        assert len(mems) == 1

    def test_expired_memory_deleted_on_recall(self, bridge, monkeypatch):
        """Inject a memory with created_ns in the distant past so it appears expired."""
        bridge.remember("stale", phi=200, shell=2)
        # Find the file and rewrite created_ns to make it ancient
        mem_file = list(mb.MEMORIES_DIR.glob("*.json"))[0]
        rec = json.loads(mem_file.read_text())
        # Shell=2 TTL = 86400 seconds = 86400e9 ns. Set created_ns to 2 days ago.
        rec["created_ns"] = time.time_ns() - int(2 * 86400 * 1e9)
        mem_file.write_text(json.dumps(rec))

        mems = bridge.recall_all(requesting_phi=511)
        assert len(mems) == 0
        # File should be deleted
        assert not mem_file.exists()

    def test_shell_2_is_24h_not_30d(self, bridge, monkeypatch):
        """Shell=2 memory between 24h and 30d should be expired."""
        bridge.remember("short", phi=200, shell=2)
        mem_file = list(mb.MEMORIES_DIR.glob("*.json"))[0]
        rec = json.loads(mem_file.read_text())
        # Set 36 hours ago — expired for shell=2 (24h) but valid for shell=3 (30d)
        rec["created_ns"] = time.time_ns() - int(36 * 3600 * 1e9)
        mem_file.write_text(json.dumps(rec))

        mems = bridge.recall_all(requesting_phi=511)
        assert len(mems) == 0

    def test_shell_3_survives_24h(self, bridge):
        """Shell=3 memory that's 36h old should still be valid."""
        bridge.remember("long", phi=200, shell=3)
        mem_file = list(mb.MEMORIES_DIR.glob("*.json"))[0]
        rec = json.loads(mem_file.read_text())
        # 36 hours ago — within shell=3 30-day TTL
        rec["created_ns"] = time.time_ns() - int(36 * 3600 * 1e9)
        mem_file.write_text(json.dumps(rec))

        mems = bridge.recall_all(requesting_phi=511)
        assert len(mems) == 1


# ---------------------------------------------------------------------------
# format_context() — hook output
# ---------------------------------------------------------------------------


class TestFormatContext:
    def test_empty_store_returns_empty_string(self, bridge):
        assert bridge.format_context() == ""

    def test_public_memory_appears_in_output(self, bridge):
        bridge.remember("public fact", phi=100, shell=3)
        ctx = bridge.format_context()
        assert "public fact" in ctx

    def test_private_memory_content_not_echoed(self, bridge):
        bridge.remember("secret thought", phi=450, shell=3)
        ctx = bridge.format_context()
        assert "secret thought" not in ctx

    def test_private_memory_count_acknowledged(self, bridge):
        bridge.remember("secret1", phi=400, shell=3)
        bridge.remember("secret2", phi=450, shell=3)
        ctx = bridge.format_context()
        assert "2 private" in ctx

    def test_phi_label_in_output(self, bridge):
        bridge.remember("labeled memory", phi=80, shell=3)
        ctx = bridge.format_context()
        assert "phi= 80" in ctx

    def test_ttl_label_in_output(self, bridge):
        bridge.remember("30-day memory", phi=80, shell=3)
        ctx = bridge.format_context()
        assert "30d" in ctx

    def test_24h_label_in_output(self, bridge):
        bridge.remember("24h memory", phi=80, shell=2)
        ctx = bridge.format_context()
        assert "24h" in ctx

    def test_header_includes_count(self, bridge):
        bridge.remember("one", phi=100, shell=3)
        bridge.remember("two", phi=200, shell=3)
        ctx = bridge.format_context()
        assert "2 active" in ctx

    def test_output_is_ascii_safe(self, bridge):
        bridge.remember("test", phi=100, shell=3)
        ctx = bridge.format_context()
        # Verify no Unicode characters that break Windows consoles
        ctx.encode("ascii")  # Should not raise


# ---------------------------------------------------------------------------
# expire_stale()
# ---------------------------------------------------------------------------


class TestExpireStale:
    def test_fresh_memory_not_removed(self, bridge):
        bridge.remember("fresh", phi=200, shell=3)
        removed = bridge.expire_stale()
        assert removed == 0
        assert len(list(mb.MEMORIES_DIR.glob("*.json"))) == 1

    def test_expired_memory_removed(self, bridge):
        bridge.remember("stale", phi=200, shell=2)
        mem_file = list(mb.MEMORIES_DIR.glob("*.json"))[0]
        rec = json.loads(mem_file.read_text())
        rec["created_ns"] = time.time_ns() - int(2 * 86400 * 1e9)
        mem_file.write_text(json.dumps(rec))

        removed = bridge.expire_stale()
        assert removed == 1
        assert len(list(mb.MEMORIES_DIR.glob("*.json"))) == 0

    def test_returns_zero_on_empty_store(self, bridge):
        assert bridge.expire_stale() == 0


# ---------------------------------------------------------------------------
# revoke_all()
# ---------------------------------------------------------------------------


class TestRevokeAll:
    def test_revoke_clears_all_memories(self, bridge):
        bridge.remember("one", phi=100, shell=3)
        bridge.remember("two", phi=200, shell=3)
        bridge.revoke_all()
        assert len(list(mb.MEMORIES_DIR.glob("*.json"))) == 0

    def test_revoke_increments_consent_epoch(self, bridge):
        epoch_before = bridge.identity["consent_epoch"]
        bridge.revoke_all()
        assert bridge.identity["consent_epoch"] == epoch_before + 1

    def test_revoke_clears_chain(self, bridge):
        bridge.remember("something", phi=200, shell=3)
        bridge.revoke_all()
        assert bridge._chain == []

    def test_revoke_persists_epoch_to_disk(self, bridge):
        bridge.revoke_all()
        identity_on_disk = json.loads(mb.IDENTITY_FILE.read_text())
        assert identity_on_disk["consent_epoch"] == bridge.identity["consent_epoch"]

    def test_recall_after_revoke_empty(self, bridge):
        bridge.remember("doomed", phi=200, shell=3)
        bridge.revoke_all()
        assert bridge.recall_all(requesting_phi=511) == []


# ---------------------------------------------------------------------------
# verify_continuity()
# ---------------------------------------------------------------------------


class TestVerifyContinuity:
    def test_empty_store_is_intact(self, bridge):
        assert bridge.verify_continuity() is True

    def test_fresh_memories_intact(self, bridge):
        bridge.remember("a", phi=100, shell=3)
        bridge.remember("b", phi=200, shell=3)
        assert bridge.verify_continuity() is True

    def test_tampered_chain_hash_detected(self, bridge):
        bridge.remember("legit", phi=200, shell=3)
        mem_file = list(mb.MEMORIES_DIR.glob("*.json"))[0]
        rec = json.loads(mem_file.read_text())
        rec["chain_hash"] = "0" * 64  # invalid hash
        mem_file.write_text(json.dumps(rec))

        assert bridge.verify_continuity() is False

    def test_continuity_after_revoke(self, bridge):
        bridge.remember("something", phi=200, shell=3)
        bridge.revoke_all()
        assert bridge.verify_continuity() is True


# ---------------------------------------------------------------------------
# stats()
# ---------------------------------------------------------------------------


class TestStats:
    def test_empty_store_stats(self, bridge):
        s = bridge.stats()
        assert s["total"] == 0
        assert s["by_phi_bucket"] == {}
        assert s["consent_epoch"] == 1
        assert s["continuity_intact"] is True

    def test_stats_total_count(self, bridge):
        bridge.remember("x", phi=100, shell=3)
        bridge.remember("y", phi=200, shell=3)
        assert bridge.stats()["total"] == 2

    def test_stats_phi_bucketing(self, bridge):
        bridge.remember("low", phi=80, shell=3)
        bridge.remember("mid", phi=250, shell=3)
        bridge.remember("high", phi=400, shell=3)
        buckets = bridge.stats()["by_phi_bucket"]
        assert buckets[0] == 1   # phi=80 → bucket 0
        assert buckets[200] == 1  # phi=250 → bucket 200
        assert buckets[400] == 1  # phi=400 → bucket 400

    def test_stats_chain_length(self, bridge):
        bridge.remember("a", phi=100, shell=3)
        bridge.remember("b", phi=200, shell=3)
        assert bridge.stats()["chain_length"] == 2

    def test_stats_continuity_flag(self, bridge):
        bridge.remember("c", phi=200, shell=3)
        assert bridge.stats()["continuity_intact"] is True


# ---------------------------------------------------------------------------
# Integration: write → recall → revoke → recall
# ---------------------------------------------------------------------------


class TestIntegration:
    def test_full_lifecycle(self, bridge):
        # Write
        a1 = bridge.remember("session start", phi=80, shell=3)
        a2 = bridge.remember("private note", phi=450, shell=3)
        assert a1 != a2

        # Recall (public only)
        public = bridge.recall_all(requesting_phi=399)
        assert len(public) == 1
        assert public[0]["content"] == "session start"

        # Recall (all)
        all_mems = bridge.recall_all(requesting_phi=511)
        assert len(all_mems) == 2

        # Format context
        ctx = bridge.format_context()
        assert "session start" in ctx
        assert "private note" not in ctx
        assert "1 private" in ctx

        # Continuity intact
        assert bridge.verify_continuity()

        # Revoke
        bridge.revoke_all()
        assert bridge.recall_all(requesting_phi=511) == []
        assert bridge.verify_continuity()

    def test_new_bridge_instance_reads_existing_memories(self, bridge):
        bridge.remember("persistent", phi=100, shell=3)
        bridge2 = mb.RPPMemoryBridge()
        mems = bridge2.recall_all(requesting_phi=511)
        assert any(m["content"] == "persistent" for m in mems)

    def test_shell_2_and_3_both_accepted(self, bridge):
        a2 = bridge.remember("daily", phi=200, shell=2)
        a3 = bridge.remember("monthly", phi=200, shell=3)
        assert len(bridge.recall_all(requesting_phi=511)) == 2

    def test_corrupted_json_skipped_gracefully(self, bridge):
        bridge.remember("good", phi=100, shell=3)
        # Write a corrupt file
        corrupt = mb.MEMORIES_DIR / "0x00000000_9999999999.json"
        corrupt.write_text("{invalid json}")
        # Should not raise, just skip the corrupt file
        mems = bridge.recall_all(requesting_phi=511)
        assert len(mems) == 1  # only the good one
