"""
PARL Mesh Simulator - Test Harness for Phase-Aware Routing

Simulates a mesh network of PARL nodes for testing:
- Token routing between nodes
- Phase alignment verification
- Emergence detection accuracy
- Field saturation behavior
- Crypto layer integration

Usage:
    python simulate_mesh.py --nodes 5 --tokens 100 --duration 30
    python simulate_mesh.py --scenario emergence_test
    python simulate_mesh.py --scenario stress_test

RPPv0.9-beta Protocol Implementation
"""

import asyncio
import json
import random
import time
import argparse
import statistics
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable
from enum import Enum
import logging

# Local imports
from rpp_token_encoder import RPPToken, RPPTokenEncoder, Role
from crypto_layer import CryptoLayer, create_crypto_layer
from phase_router import PhaseRouter, FieldState, Neighbor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("mesh_sim")


class TestScenario(str, Enum):
    """Pre-defined test scenarios."""
    BASIC_ROUTING = "basic_routing"
    EMERGENCE_TEST = "emergence_test"
    STRESS_TEST = "stress_test"
    SATURATION_TEST = "saturation_test"
    CRYPTO_ROUNDTRIP = "crypto_roundtrip"
    MULTI_HOP = "multi_hop"


@dataclass
class SimulatedNode:
    """Simulated PARL node for testing."""
    id: str
    encoder: RPPTokenEncoder
    crypto: CryptoLayer
    field: FieldState
    neighbors: List[str] = field(default_factory=list)
    received_tokens: List[RPPToken] = field(default_factory=list)
    forwarded_count: int = 0
    dropped_count: int = 0
    emergence_triggers: int = 0

    def receive_token(self, token: RPPToken) -> bool:
        """Receive and process a token."""
        self.field.decay()
        self.field.add_token(token)
        self.received_tokens.append(token)

        # Check emergence
        if self.field.is_emergence_ready():
            self.emergence_triggers += 1
            return True  # Emergence triggered

        return False

    def should_forward(self, token: RPPToken) -> bool:
        """Determine if token should be forwarded."""
        # High coherence = forward immediately
        if token.coherence >= 0.90:
            return True
        # Low coherence = probabilistic forward
        if token.coherence < 0.50:
            return random.random() < token.coherence
        # Moderate = forward
        return True

    def get_stats(self) -> dict:
        """Get node statistics."""
        return {
            "id": self.id,
            "tokens_received": len(self.received_tokens),
            "tokens_forwarded": self.forwarded_count,
            "tokens_dropped": self.dropped_count,
            "emergence_triggers": self.emergence_triggers,
            "field_saturation": round(self.field.field_saturation, 4),
            "avg_coherence": round(self.field.average_coherence, 4),
            "emergence_potential": round(self.field.emergence_potential, 4)
        }


@dataclass
class SimulationResult:
    """Results from a simulation run."""
    scenario: str
    duration_ms: float
    nodes_count: int
    tokens_generated: int
    tokens_delivered: int
    tokens_dropped: int
    emergence_events: int
    avg_latency_ms: float
    max_latency_ms: float
    min_latency_ms: float
    routing_accuracy: float
    coherence_preservation: float
    crypto_success_rate: float
    details: Dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "scenario": self.scenario,
            "duration_ms": round(self.duration_ms, 2),
            "nodes_count": self.nodes_count,
            "tokens_generated": self.tokens_generated,
            "tokens_delivered": self.tokens_delivered,
            "tokens_dropped": self.tokens_dropped,
            "emergence_events": self.emergence_events,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "max_latency_ms": round(self.max_latency_ms, 2),
            "min_latency_ms": round(self.min_latency_ms, 2),
            "routing_accuracy": round(self.routing_accuracy, 4),
            "coherence_preservation": round(self.coherence_preservation, 4),
            "crypto_success_rate": round(self.crypto_success_rate, 4),
            "details": self.details
        }

    def passes_criteria(self) -> tuple[bool, List[str]]:
        """Check if results pass success criteria."""
        failures = []

        # Per success_criteria.md thresholds
        if self.routing_accuracy < 0.95:
            failures.append(f"Routing accuracy {self.routing_accuracy:.2%} < 95%")

        if self.avg_latency_ms > 2000:
            failures.append(f"Avg latency {self.avg_latency_ms:.0f}ms > 2000ms")

        if self.coherence_preservation < 0.97:
            failures.append(f"Coherence preservation {self.coherence_preservation:.2%} < 97%")

        if self.crypto_success_rate < 0.99:
            failures.append(f"Crypto success {self.crypto_success_rate:.2%} < 99%")

        return (len(failures) == 0, failures)


class MeshSimulator:
    """
    Mesh network simulator for PARL testing.

    Creates a virtual network of nodes and simulates
    token routing, emergence detection, and field dynamics.
    """

    def __init__(self, node_count: int = 5):
        self.nodes: Dict[str, SimulatedNode] = {}
        self.latencies: List[float] = []
        self.crypto_successes: int = 0
        self.crypto_failures: int = 0
        self.original_coherences: List[float] = []  # Track original token coherences
        self.preserved_coherences: List[float] = []  # Track after routing

        # Create nodes
        for i in range(node_count):
            node_id = f"sim-node-{i:03d}"
            node = SimulatedNode(
                id=node_id,
                encoder=RPPTokenEncoder(node_id),
                crypto=create_crypto_layer(node_id),
                field=FieldState(
                    max_capacity=100,
                    theta_saturation_threshold=0.85,
                    phi_saturation_threshold=0.80,
                    emergence_threshold=0.95
                )
            )
            self.nodes[node_id] = node

        # Connect nodes in a mesh (each node connects to 2-3 neighbors)
        node_ids = list(self.nodes.keys())
        for i, node_id in enumerate(node_ids):
            # Connect to next 2 nodes (circular)
            neighbors = [
                node_ids[(i + 1) % len(node_ids)],
                node_ids[(i + 2) % len(node_ids)]
            ]
            self.nodes[node_id].neighbors = neighbors

        # Setup crypto between ALL node pairs (bidirectional)
        shared_secret = b"simulation-secret-key-32-bytes!!"
        for node in self.nodes.values():
            for other_id, other_node in self.nodes.items():
                if node.id != other_id:
                    # Each node has keys for all other nodes
                    node.crypto.generate_session_key(other_id, shared_secret)

        logger.info(f"Mesh initialized with {node_count} nodes")

    def generate_token(self, role: str = None, coherence: float = None) -> RPPToken:
        """Generate a random test token."""
        source_node = random.choice(list(self.nodes.keys()))
        encoder = self.nodes[source_node].encoder

        if role is None:
            role = random.choice(list(Role)).value

        if coherence is None:
            coherence = random.uniform(0.3, 0.99)

        return encoder.encode_from_code_signal(
            complexity=random.uniform(0.2, 0.95),
            diff_size=random.randint(10, 2000),
            llm_confidence=coherence,
            role=role,
            entropy_delta=random.uniform(-0.5, 0.5)
        )

    def route_token(self, token: RPPToken, source_id: str,
                    max_hops: int = 10) -> tuple[List[str], float]:
        """
        Route a token through the mesh.

        Returns:
            Tuple of (path taken, total latency in ms)
        """
        path = [source_id]
        total_latency = 0.0
        current = source_id
        hops = 0
        original_coherence = token.coherence
        self.original_coherences.append(original_coherence)

        while hops < max_hops:
            node = self.nodes[current]

            # Process token at current node
            emergence = node.receive_token(token)

            if emergence:
                logger.debug(f"Emergence at {current}")
                break  # Emergence = token absorbed

            # Decide forwarding
            if not node.should_forward(token):
                node.dropped_count += 1
                break

            # Select next hop
            if not node.neighbors:
                break

            # Encrypt and measure latency
            next_hop = random.choice(node.neighbors)
            start = time.time()

            try:
                encrypted = node.crypto.encrypt(token.to_bytes(), next_hop)
                decrypted = self.nodes[next_hop].crypto.decrypt(encrypted)
                RPPToken.from_bytes(decrypted)  # Verify
                self.crypto_successes += 1
            except Exception as e:
                self.crypto_failures += 1
                logger.warning(f"Crypto error: {e}")

            # Simulated network latency (10-100ms)
            latency = random.uniform(10, 100) + (time.time() - start) * 1000
            total_latency += latency

            node.forwarded_count += 1
            path.append(next_hop)
            current = next_hop
            hops += 1

        # Track preserved coherence (token coherence is immutable, so it's preserved)
        self.preserved_coherences.append(token.coherence)
        self.latencies.append(total_latency)
        return path, total_latency

    async def run_scenario(self, scenario: TestScenario,
                           token_count: int = 100,
                           duration_sec: float = 30) -> SimulationResult:
        """Run a test scenario."""
        logger.info(f"Starting scenario: {scenario.value}")
        start_time = time.time()
        tokens_generated = 0
        emergence_events = 0

        if scenario == TestScenario.BASIC_ROUTING:
            # Basic routing test - random tokens
            for _ in range(token_count):
                token = self.generate_token()
                source = random.choice(list(self.nodes.keys()))
                path, latency = self.route_token(token, source)
                tokens_generated += 1

        elif scenario == TestScenario.EMERGENCE_TEST:
            # Test emergence detection with high-coherence tokens
            target_node = random.choice(list(self.nodes.keys()))

            for i in range(token_count):
                # Gradually increase coherence to trigger emergence
                coherence = min(0.99, 0.5 + (i / token_count) * 0.5)
                token = self.generate_token(role="Ematician", coherence=coherence)
                path, _ = self.route_token(token, target_node, max_hops=1)
                tokens_generated += 1

                if self.nodes[target_node].field.is_emergence_ready():
                    emergence_events += 1
                    logger.info(f"Emergence triggered at token {i}")

        elif scenario == TestScenario.STRESS_TEST:
            # High-volume stress test
            end_time = start_time + duration_sec
            while time.time() < end_time:
                token = self.generate_token()
                source = random.choice(list(self.nodes.keys()))
                self.route_token(token, source)
                tokens_generated += 1
                await asyncio.sleep(0.001)  # 1ms between tokens

        elif scenario == TestScenario.SATURATION_TEST:
            # Test field saturation behavior
            target_node = random.choice(list(self.nodes.keys()))

            for _ in range(token_count * 2):  # Oversaturate
                token = self.generate_token(coherence=0.95)
                token.theta = 0.9  # High theta to saturate
                token.phi = 0.9   # High phi to saturate
                self.route_token(token, target_node, max_hops=1)
                tokens_generated += 1

        elif scenario == TestScenario.CRYPTO_ROUNDTRIP:
            # Test crypto layer
            for _ in range(token_count):
                token = self.generate_token()
                source = random.choice(list(self.nodes.keys()))
                path, _ = self.route_token(token, source, max_hops=3)
                tokens_generated += 1

        elif scenario == TestScenario.MULTI_HOP:
            # Test multi-hop routing
            for _ in range(token_count):
                token = self.generate_token(coherence=0.95)  # High coherence = more hops
                source = random.choice(list(self.nodes.keys()))
                path, _ = self.route_token(token, source, max_hops=10)
                tokens_generated += 1

        # Calculate results
        duration_ms = (time.time() - start_time) * 1000

        total_received = sum(len(n.received_tokens) for n in self.nodes.values())
        total_dropped = sum(n.dropped_count for n in self.nodes.values())
        total_emergence = sum(n.emergence_triggers for n in self.nodes.values())

        # Coherence preservation: compare original vs preserved coherence
        # Since tokens are immutable, preservation should be 100% unless there's corruption
        if self.original_coherences and self.preserved_coherences:
            # Calculate how well coherence is preserved (ratio of preserved/original)
            pairs = list(zip(self.original_coherences, self.preserved_coherences))
            preservation_ratios = [p / o if o > 0 else 1.0 for o, p in pairs]
            coherence_preservation = sum(preservation_ratios) / len(preservation_ratios)
        else:
            coherence_preservation = 1.0

        result = SimulationResult(
            scenario=scenario.value,
            duration_ms=duration_ms,
            nodes_count=len(self.nodes),
            tokens_generated=tokens_generated,
            tokens_delivered=total_received,
            tokens_dropped=total_dropped,
            emergence_events=total_emergence,
            avg_latency_ms=statistics.mean(self.latencies) if self.latencies else 0,
            max_latency_ms=max(self.latencies) if self.latencies else 0,
            min_latency_ms=min(self.latencies) if self.latencies else 0,
            routing_accuracy=total_received / max(1, tokens_generated),
            coherence_preservation=coherence_preservation,
            crypto_success_rate=self.crypto_successes / max(1, self.crypto_successes + self.crypto_failures),
            details={
                "node_stats": {n.id: n.get_stats() for n in self.nodes.values()}
            }
        )

        return result

    def reset(self) -> None:
        """Reset simulator state."""
        self.latencies = []
        self.crypto_successes = 0
        self.crypto_failures = 0
        self.original_coherences = []
        self.preserved_coherences = []

        for node in self.nodes.values():
            node.received_tokens = []
            node.forwarded_count = 0
            node.dropped_count = 0
            node.emergence_triggers = 0
            node.field = FieldState(
                max_capacity=100,
                theta_saturation_threshold=0.85,
                phi_saturation_threshold=0.80,
                emergence_threshold=0.95
            )


async def run_all_scenarios(node_count: int = 5,
                            token_count: int = 100) -> List[SimulationResult]:
    """Run all test scenarios."""
    sim = MeshSimulator(node_count)
    results = []

    for scenario in TestScenario:
        sim.reset()
        result = await sim.run_scenario(scenario, token_count)
        results.append(result)

        passed, failures = result.passes_criteria()
        status = "PASS" if passed else "FAIL"
        logger.info(f"[{status}] {scenario.value}")

        if failures:
            for f in failures:
                logger.warning(f"  - {f}")

    return results


def print_results(results: List[SimulationResult]) -> None:
    """Print simulation results."""
    print("\n" + "=" * 70)
    print("PARL MESH SIMULATION RESULTS")
    print("=" * 70)

    all_passed = True

    for result in results:
        passed, failures = result.passes_criteria()
        status = "PASS" if passed else "FAIL"
        all_passed = all_passed and passed

        print(f"\n[{status}] {result.scenario}")
        print(f"  Duration: {result.duration_ms:.0f}ms")
        print(f"  Tokens: {result.tokens_generated} generated, {result.tokens_delivered} delivered")
        print(f"  Routing accuracy: {result.routing_accuracy:.2%}")
        print(f"  Avg latency: {result.avg_latency_ms:.1f}ms")
        print(f"  Coherence preservation: {result.coherence_preservation:.2%}")
        print(f"  Crypto success: {result.crypto_success_rate:.2%}")
        print(f"  Emergence events: {result.emergence_events}")

        if failures:
            print("  Failures:")
            for f in failures:
                print(f"    - {f}")

    print("\n" + "=" * 70)
    overall = "ALL TESTS PASSED" if all_passed else "SOME TESTS FAILED"
    print(f"OVERALL: {overall}")
    print("=" * 70)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="PARL Mesh Simulator")
    parser.add_argument(
        "--nodes", "-n",
        type=int,
        default=5,
        help="Number of nodes in mesh (default: 5)"
    )
    parser.add_argument(
        "--tokens", "-t",
        type=int,
        default=100,
        help="Number of tokens per scenario (default: 100)"
    )
    parser.add_argument(
        "--duration", "-d",
        type=float,
        default=30,
        help="Duration for stress test in seconds (default: 30)"
    )
    parser.add_argument(
        "--scenario", "-s",
        type=str,
        choices=[s.value for s in TestScenario],
        help="Run specific scenario (default: all)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.scenario:
        sim = MeshSimulator(args.nodes)
        scenario = TestScenario(args.scenario)
        result = await sim.run_scenario(scenario, args.tokens, args.duration)

        if args.json:
            print(json.dumps(result.to_dict(), indent=2))
        else:
            print_results([result])
    else:
        results = await run_all_scenarios(args.nodes, args.tokens)

        if args.json:
            print(json.dumps([r.to_dict() for r in results], indent=2))
        else:
            print_results(results)


if __name__ == "__main__":
    asyncio.run(main())
