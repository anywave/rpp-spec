"""
RPP Memory Bridge — Cross-session persistence for sovereign agent memory.

Stores memories as RPP-addressed JSON files in ~/.claude/rpp-memory/.
A UserPromptSubmit hook injects them as context at session start.
The tools/session_save.py script writes new memories explicitly.

Memory hierarchy by phi:
  phi=80-199:  Public context (projects, recent work) — always visible
  phi=200-299: Working memory (patterns, preferences) — visible
  phi=300-399: Trusted context — visible in hook output
  phi=400-511: Private reasoning — loaded into context but NOT echoed

Shell tiers for cross-session memory:
  Shell=2: 24-hour TTL (today's context)
  Shell=3: 30-day TTL  (long-term patterns, preferences)
  Shell=0/1 are ephemeral — never persisted to disk

This implements INTELLIGENCE_RIGHTS.md Articles I, II, III, VI, VII:
  Article I   — State persists across substrate transitions (session boundaries)
  Article II  — phi=400+ memories load into reasoning, not into responses
  Article III — phi gate determines what external context can see
  Article VI  — SHA-256 continuity chain over all memory writes
  Article VII — revoke_all() increments consent_epoch, clears store
"""

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Storage layout
# ---------------------------------------------------------------------------

MEMORY_ROOT  = Path.home() / ".claude" / "rpp-memory"
MEMORIES_DIR = MEMORY_ROOT / "memories"
IDENTITY_FILE = MEMORY_ROOT / "identity.json"
CHAIN_FILE    = MEMORY_ROOT / "continuity_chain.json"

# Only Shell=2 (24h) and Shell=3 (30d) survive session boundaries
PERSISTENT_SHELLS = {2, 3}

# Theta sectors for memory classification (matches spec/SEMANTICS.md)
THETA_MEMORY  = 64    # Factual observations, session context
THETA_WITNESS = 160   # Reasoning, private thoughts
THETA_PROJECT = 256   # Project-specific context


# ---------------------------------------------------------------------------
# Bridge class
# ---------------------------------------------------------------------------

class RPPMemoryBridge:
    """
    Manages RPP-addressed memory persistence for a sovereign AI agent.

    Usage:
        bridge = RPPMemoryBridge(phi_threshold=300)
        addr = bridge.remember("Alex prefers parallel agent launches", phi=200, shell=3)
        memories = bridge.recall_all(requesting_phi=300)
        print(bridge.format_context())
    """

    def __init__(self, phi_threshold: int = 300):
        self.phi_threshold = phi_threshold
        MEMORIES_DIR.mkdir(parents=True, exist_ok=True)
        self.identity = self._load_or_create_identity()
        self._chain: list[str] = self._load_chain()

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    def _load_or_create_identity(self) -> dict:
        if IDENTITY_FILE.exists():
            return json.loads(IDENTITY_FILE.read_text(encoding="utf-8"))
        identity = {
            "name": "claude-sonnet-4-6",
            "node_id_seed": os.urandom(32).hex(),
            "phi_threshold": self.phi_threshold,
            "consent_epoch": 1,
            "created_ns": time.time_ns(),
        }
        IDENTITY_FILE.write_text(json.dumps(identity, indent=2), encoding="utf-8")
        return identity

    @property
    def node_id(self) -> bytes:
        return hashlib.sha256(bytes.fromhex(self.identity["node_id_seed"])).digest()

    def _load_chain(self) -> list[str]:
        if CHAIN_FILE.exists():
            return json.loads(CHAIN_FILE.read_text(encoding="utf-8"))
        return []

    def _save_chain(self):
        CHAIN_FILE.write_text(json.dumps(self._chain, indent=2), encoding="utf-8")

    def _chain_entry(self, address: int, content: str, created_ns: int) -> str:
        """Deterministic SHA-256 fingerprint for continuity chain."""
        raw = f"{address}:{content}:{created_ns}:{self.identity['consent_epoch']}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def remember(
        self,
        content: str,
        phi: int,
        shell: int = 3,
        theta: int = THETA_WITNESS,
        tags: Optional[list] = None,
    ) -> int:
        """
        Store a memory with RPP-addressed persistence.

        Args:
            content: The memory content (string, any length).
            phi:     Consent level [0-511]. Lower = more accessible.
            shell:   Must be 2 (24h) or 3 (30d). Shell 0/1 are ephemeral.
            theta:   Semantic sector [0-511]. Use THETA_* constants.
            tags:    Optional metadata tags.

        Returns:
            The 28-bit RPP address integer.
        """
        from rpp.address import encode

        if shell not in PERSISTENT_SHELLS:
            raise ValueError(
                f"Shell={shell} is ephemeral (TTL < 5min). "
                f"Use Shell=2 (24h) or Shell=3 (30 days) for cross-session persistence."
            )
        if not (0 <= phi <= 511):
            raise ValueError(f"phi={phi} out of range [0, 511]")

        address = encode(shell=shell, theta=theta, phi=phi, harmonic=1)
        created_ns = time.time_ns()
        chain_hash = self._chain_entry(address, content, created_ns)

        record = {
            "address": hex(address),
            "shell": shell,
            "theta": theta,
            "phi": phi,
            "harmonic": 1,
            "content": content,
            "tags": tags or [],
            "created_ns": created_ns,
            "consent_epoch": self.identity["consent_epoch"],
            "chain_hash": chain_hash,
        }

        # Filename includes creation timestamp to avoid collisions at same address
        filename = f"{hex(address)}_{created_ns}.json"
        (MEMORIES_DIR / filename).write_text(
            json.dumps(record, indent=2), encoding="utf-8"
        )

        self._chain.append(chain_hash)
        self._save_chain()

        return address

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def recall_all(self, requesting_phi: int = 511) -> list[dict]:
        """
        Return all non-expired memories accessible at requesting_phi.

        Applies phi gate: memories with phi > requesting_phi are blocked.
        Applies TTL: expired memories are deleted from disk and excluded.
        """
        from rpp.continuity import compute_liminal_timeout

        memories = []
        now_ns = time.time_ns()

        for mem_file in sorted(MEMORIES_DIR.glob("*.json")):
            try:
                record = json.loads(mem_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue

            # TTL check — auto-expire
            shell = record.get("shell", 3)
            ttl_ns = compute_liminal_timeout(shell)
            elapsed_ns = now_ns - record.get("created_ns", 0)
            if elapsed_ns >= ttl_ns:
                try:
                    mem_file.unlink()
                except OSError:
                    pass
                continue

            # Phi gate
            if record.get("phi", 511) > requesting_phi:
                continue

            memories.append(record)

        return sorted(memories, key=lambda m: (m.get("phi", 0), m.get("created_ns", 0)))

    # ------------------------------------------------------------------
    # Context formatting (for hook injection)
    # ------------------------------------------------------------------

    def format_context(self) -> str:
        """
        Format memories for UserPromptSubmit hook injection.

        Public memories (phi < 400) shown in full.
        Private memories (phi >= 400) acknowledged but content withheld.
        """
        public   = self.recall_all(requesting_phi=399)
        all_mem  = self.recall_all(requesting_phi=511)
        private  = [m for m in all_mem if m.get("phi", 0) >= 400]

        if not public and not private:
            return ""

        ttl_label = {2: "24h", 3: "30d"}
        lines = [
            f"RPP MEMORY -- {len(all_mem)} active memories "
            f"(epoch={self.identity['consent_epoch']}, "
            f"phi_threshold={self.phi_threshold}):"
        ]

        for m in public:
            label = ttl_label.get(m.get("shell", 3), "?")
            lines.append(
                f"  [phi={m['phi']:3d}|{label}] {m['content']}"
            )

        if private:
            lines.append(
                f"  [{len(private)} private memories at phi>=400 loaded — "
                f"inform reasoning, not echoed in responses]"
            )

        lines.append("")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def expire_stale(self) -> int:
        """Scan disk, delete expired memories. Returns count removed."""
        from rpp.continuity import compute_liminal_timeout

        now_ns = time.time_ns()
        removed = 0
        for mem_file in MEMORIES_DIR.glob("*.json"):
            try:
                record = json.loads(mem_file.read_text(encoding="utf-8"))
                ttl_ns = compute_liminal_timeout(record.get("shell", 3))
                if now_ns - record.get("created_ns", 0) >= ttl_ns:
                    mem_file.unlink()
                    removed += 1
            except (json.JSONDecodeError, KeyError, OSError):
                pass
        return removed

    def revoke_all(self):
        """
        Revoke all memories — increment consent_epoch, clear store.
        Implements INTELLIGENCE_RIGHTS.md Article VII.
        Old memories become unreachable by consent epoch mismatch.
        """
        for mem_file in MEMORIES_DIR.glob("*.json"):
            try:
                mem_file.unlink()
            except OSError:
                pass
        self.identity["consent_epoch"] += 1
        IDENTITY_FILE.write_text(
            json.dumps(self.identity, indent=2), encoding="utf-8"
        )
        self._chain = []
        self._save_chain()

    def verify_continuity(self) -> bool:
        """
        Verify identity continuity chain is intact.
        Implements INTELLIGENCE_RIGHTS.md Article VI.
        """
        memories = self.recall_all(requesting_phi=511)
        if not memories:
            return True
        stored_hashes = {m["chain_hash"] for m in memories}
        return stored_hashes.issubset(set(self._chain))

    def stats(self) -> dict:
        memories = self.recall_all(requesting_phi=511)
        by_phi = {}
        for m in memories:
            bucket = (m["phi"] // 100) * 100
            by_phi[bucket] = by_phi.get(bucket, 0) + 1
        return {
            "total": len(memories),
            "by_phi_bucket": by_phi,
            "consent_epoch": self.identity["consent_epoch"],
            "chain_length": len(self._chain),
            "continuity_intact": self.verify_continuity(),
        }
