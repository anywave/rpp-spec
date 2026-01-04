"""
RPP Token Encoder - RPPv0.9-beta Protocol Implementation

Converts code signals into valid RPP tokens for PARL routing.

Token Format:
{
  "source_id": "node-473",
  "theta": 0.64,        # Normalized code complexity (0-1)
  "phi": 0.51,          # Normalized diff size (0-1)
  "coherence": 0.92,    # LLM confidence (0-1)
  "entropy_delta": 0.13, # Change in system entropy (-1 to 1)
  "role": "Ematician",
  "timestamp": "2026-01-02T12:00:00Z"
}

Ra-Canonical Mapping:
- theta (0-1) maps to Repitan 1-27
- phi (0-1) maps to RAC 1-6
- coherence maps to Omega tier 0-4
"""

import json
import uuid
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional, Literal
from enum import Enum


class Role(str, Enum):
    """Valid roles for RPP tokens."""
    EMATICIAN = "Ematician"
    MATHEMATICIAN = "Mathematician"
    MAGNETIC_FIELD_ENGINEER = "Magnetic Field Engineer"
    TIME_COMPRESSION_EXPERIMENTER = "Time Compression Experimenter"
    WITNESS = "Witness"
    GUARDIAN = "Guardian"
    BRIDGE = "Bridge"
    DREAM_NAVIGATOR = "Dream Navigator"


@dataclass
class RPPToken:
    """
    RPP Token - Semantic payload for phase-coherent routing.

    Attributes:
        source_id: Unique node identifier
        theta: Normalized code complexity (0.0-1.0)
        phi: Normalized diff size (0.0-1.0)
        coherence: LLM confidence / signal quality (0.0-1.0)
        entropy_delta: Change in system entropy (-1.0 to 1.0)
        role: Semantic role category
        timestamp: ISO 8601 timestamp
        field_hash: Content-addressable hash (optional)
        public_key: Sender's public key (optional)
    """
    source_id: str
    theta: float
    phi: float
    coherence: float
    role: str
    entropy_delta: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    field_hash: Optional[str] = None
    public_key: Optional[str] = None

    def __post_init__(self):
        # Validate ranges
        if not 0.0 <= self.theta <= 1.0:
            raise ValueError(f"theta must be 0-1, got {self.theta}")
        if not 0.0 <= self.phi <= 1.0:
            raise ValueError(f"phi must be 0-1, got {self.phi}")
        if not 0.0 <= self.coherence <= 1.0:
            raise ValueError(f"coherence must be 0-1, got {self.coherence}")
        if not -1.0 <= self.entropy_delta <= 1.0:
            raise ValueError(f"entropy_delta must be -1 to 1, got {self.entropy_delta}")

        # Compute field hash if not provided
        if self.field_hash is None:
            self.field_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        """Compute content-addressable hash."""
        data = f"{self.theta:.6f}:{self.phi:.6f}:{self.coherence:.6f}:{self.role}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(asdict(self), indent=2)

    def to_bytes(self) -> bytes:
        """Serialize to bytes for transmission."""
        return self.to_json().encode('utf-8')

    @classmethod
    def from_json(cls, json_str: str) -> 'RPPToken':
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        return cls(**data)

    @classmethod
    def from_bytes(cls, data: bytes) -> 'RPPToken':
        """Deserialize from bytes."""
        return cls.from_json(data.decode('utf-8'))

    def to_ra_canonical(self) -> dict:
        """
        Convert to Ra-Canonical address components.

        Returns:
            Dict with theta (1-27), phi (1-6), omega (0-4), radius (0-255)
        """
        # theta: 0-1 -> Repitan 1-27
        repitan = max(1, min(27, int(self.theta * 26) + 1))

        # phi: 0-1 -> RAC 1-6
        rac = max(1, min(6, int(self.phi * 5) + 1))

        # coherence: 0-1 -> Omega tier 0-4
        # Higher coherence = more stable = GREEN (tier 2)
        if self.coherence >= 0.9:
            omega = 2  # GREEN - stable
        elif self.coherence >= 0.7:
            omega = 1  # OMEGA_MAJOR
        elif self.coherence >= 0.5:
            omega = 3  # OMEGA_MINOR
        elif self.coherence >= 0.3:
            omega = 4  # BLUE
        else:
            omega = 0  # RED - alert

        # entropy_delta: -1 to 1 -> radius 0-255
        radius = int((self.entropy_delta + 1) * 127.5)

        return {
            "theta": repitan,
            "phi": rac,
            "omega": omega,
            "radius": radius,
            "reserved": 0
        }


class RPPTokenEncoder:
    """
    Encodes code signals into RPP tokens.

    Usage:
        encoder = RPPTokenEncoder("node-001")
        token = encoder.encode_from_code_signal(
            complexity=0.7,
            diff_size=500,
            llm_confidence=0.95,
            role="Ematician"
        )
    """

    def __init__(self, node_id: str):
        self.node_id = node_id

    def encode_from_code_signal(
        self,
        complexity: float,
        diff_size: int,
        llm_confidence: float,
        role: str,
        entropy_delta: float = 0.0,
        public_key: Optional[str] = None
    ) -> RPPToken:
        """
        Convert code signal metrics into RPP token.

        Args:
            complexity: Code complexity score (0-1)
            diff_size: Number of lines changed
            llm_confidence: Model confidence (0-1)
            role: Semantic role category
            entropy_delta: Change in system entropy
            public_key: Optional sender public key

        Returns:
            Encoded RPP token
        """
        # Normalize theta from complexity (already 0-1)
        theta = max(0.0, min(1.0, complexity))

        # Normalize phi from diff_size (log scale, capped at 10000 lines)
        import math
        if diff_size <= 0:
            phi = 0.0
        else:
            phi = min(1.0, math.log10(diff_size + 1) / 4.0)  # log10(10000) = 4

        # Coherence directly from LLM confidence
        coherence = max(0.0, min(1.0, llm_confidence))

        return RPPToken(
            source_id=self.node_id,
            theta=round(theta, 4),
            phi=round(phi, 4),
            coherence=round(coherence, 4),
            entropy_delta=round(entropy_delta, 4),
            role=role,
            public_key=public_key
        )

    def encode_from_raw(
        self,
        theta: float,
        phi: float,
        coherence: float,
        role: str,
        entropy_delta: float = 0.0
    ) -> RPPToken:
        """
        Create token from raw normalized values.

        Args:
            theta: Normalized complexity (0-1)
            phi: Normalized diff size (0-1)
            coherence: Signal quality (0-1)
            role: Semantic role
            entropy_delta: Entropy change (-1 to 1)

        Returns:
            RPP token
        """
        return RPPToken(
            source_id=self.node_id,
            theta=theta,
            phi=phi,
            coherence=coherence,
            entropy_delta=entropy_delta,
            role=role
        )


def generate_sample_tokens() -> list[dict]:
    """Generate 10 sample RPP tokens for testing."""
    encoder = RPPTokenEncoder("sample-node")

    samples = [
        # Ematician - high complexity, high coherence
        {"complexity": 0.85, "diff_size": 250, "llm_confidence": 0.95,
         "role": "Ematician", "entropy_delta": 0.15},

        # Mathematician - moderate complexity, very high coherence
        {"complexity": 0.72, "diff_size": 120, "llm_confidence": 0.98,
         "role": "Mathematician", "entropy_delta": 0.05},

        # Magnetic Field Engineer - low complexity, high diff
        {"complexity": 0.45, "diff_size": 800, "llm_confidence": 0.88,
         "role": "Magnetic Field Engineer", "entropy_delta": -0.1},

        # Time Compression Experimenter - high entropy delta
        {"complexity": 0.92, "diff_size": 50, "llm_confidence": 0.75,
         "role": "Time Compression Experimenter", "entropy_delta": 0.45},

        # Witness - observational, low entropy
        {"complexity": 0.30, "diff_size": 10, "llm_confidence": 0.99,
         "role": "Witness", "entropy_delta": 0.0},

        # Guardian - protective, stable
        {"complexity": 0.65, "diff_size": 300, "llm_confidence": 0.92,
         "role": "Guardian", "entropy_delta": -0.05},

        # Bridge - translation layer
        {"complexity": 0.55, "diff_size": 450, "llm_confidence": 0.85,
         "role": "Bridge", "entropy_delta": 0.12},

        # Dream Navigator - subconscious exploration
        {"complexity": 0.78, "diff_size": 180, "llm_confidence": 0.70,
         "role": "Dream Navigator", "entropy_delta": 0.25},

        # Low coherence edge case
        {"complexity": 0.40, "diff_size": 1500, "llm_confidence": 0.35,
         "role": "Ematician", "entropy_delta": -0.3},

        # Maximum values
        {"complexity": 0.99, "diff_size": 5000, "llm_confidence": 0.99,
         "role": "Mathematician", "entropy_delta": 0.8},
    ]

    tokens = []
    for i, params in enumerate(samples):
        token = encoder.encode_from_code_signal(**params)
        token.source_id = f"node-{100 + i}"
        tokens.append(asdict(token))

    return tokens


if __name__ == "__main__":
    print("RPP Token Encoder Test")
    print("=" * 50)

    # Create encoder
    encoder = RPPTokenEncoder("test-node-001")

    # Encode a sample signal
    token = encoder.encode_from_code_signal(
        complexity=0.75,
        diff_size=350,
        llm_confidence=0.92,
        role="Ematician",
        entropy_delta=0.15
    )

    print("\nEncoded Token:")
    print(token.to_json())

    print("\nRa-Canonical Mapping:")
    canonical = token.to_ra_canonical()
    print(f"  Repitan (theta): {canonical['theta']}")
    print(f"  RAC (phi): {canonical['phi']}")
    print(f"  Omega (tier): {canonical['omega']}")
    print(f"  Radius: {canonical['radius']}")

    print("\n" + "=" * 50)
    print("Sample Tokens:")
    samples = generate_sample_tokens()
    for i, sample in enumerate(samples[:3]):
        print(f"\n[{i+1}] {sample['role']}:")
        print(f"    theta={sample['theta']}, phi={sample['phi']}, coherence={sample['coherence']}")
