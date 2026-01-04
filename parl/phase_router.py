"""
PARL Phase Router - Phase-Aware Routing Layer Daemon

Main daemon for routing RPP tokens through a phase-coherent mesh network.
Implements the SPIRAL protocol routing logic with:
- Socket-based token reception
- AEAD encryption for transport security
- Phase alignment routing (theta, phi, coherence)
- Field saturation management
- Emergence detection and broadcast

RPPv0.9-beta Protocol Implementation
"""

import asyncio
import json
import logging
import socket
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Callable, List, Dict, Any
from enum import Enum
from pathlib import Path

# Local imports
from rpp_token_encoder import RPPToken, RPPTokenEncoder, Role
from crypto_layer import CryptoLayer, EncryptedPacket, SessionKey

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("phase_router")


class DropPolicy(str, Enum):
    """How to handle dropped packets."""
    LOG_AND_SKIP = "log_and_skip"
    SILENT_DROP = "silent_drop"
    RETURN_ERROR = "return_error"


class ForwardMode(str, Enum):
    """Forwarding strategy."""
    BEST_MATCH = "best_match"        # Forward to best phase-aligned neighbor
    BROADCAST = "broadcast"          # Forward to all neighbors
    ROUND_ROBIN = "round_robin"      # Cycle through neighbors


@dataclass
class FieldState:
    """
    Local field state for phase-aware routing.

    Tracks saturation levels and coherence metrics to determine
    routing decisions and emergence triggers.
    """
    theta_sum: float = 0.0
    phi_sum: float = 0.0
    coherence_sum: float = 0.0
    token_count: int = 0
    max_capacity: int = 100
    theta_saturation_threshold: float = 0.85
    phi_saturation_threshold: float = 0.80
    coherence_minimum: float = 0.30
    emergence_threshold: float = 0.95
    decay_rate: float = 0.01
    last_update: float = field(default_factory=time.time)

    @property
    def theta_saturation(self) -> float:
        """Current theta saturation level (0-1)."""
        if self.token_count == 0:
            return 0.0
        return min(1.0, self.theta_sum / self.max_capacity)

    @property
    def phi_saturation(self) -> float:
        """Current phi saturation level (0-1)."""
        if self.token_count == 0:
            return 0.0
        return min(1.0, self.phi_sum / self.max_capacity)

    @property
    def average_coherence(self) -> float:
        """Average coherence of tokens in field."""
        if self.token_count == 0:
            return 0.0
        return self.coherence_sum / self.token_count

    @property
    def field_saturation(self) -> float:
        """Combined field saturation metric."""
        return (self.theta_saturation + self.phi_saturation) / 2

    @property
    def emergence_potential(self) -> float:
        """Emergence potential based on coherence and saturation."""
        if self.average_coherence < self.coherence_minimum:
            return 0.0
        return self.average_coherence * self.field_saturation

    def add_token(self, token: RPPToken) -> None:
        """Add token to field state."""
        self.theta_sum += token.theta
        self.phi_sum += token.phi
        self.coherence_sum += token.coherence
        self.token_count += 1
        self.last_update = time.time()

    def decay(self) -> None:
        """Apply decay to field state."""
        elapsed = time.time() - self.last_update
        decay_factor = max(0, 1 - (self.decay_rate * elapsed))

        self.theta_sum *= decay_factor
        self.phi_sum *= decay_factor
        self.coherence_sum *= decay_factor
        self.token_count = int(self.token_count * decay_factor)
        self.last_update = time.time()

    def is_theta_saturated(self) -> bool:
        return self.theta_saturation >= self.theta_saturation_threshold

    def is_phi_saturated(self) -> bool:
        return self.phi_saturation >= self.phi_saturation_threshold

    def is_emergence_ready(self) -> bool:
        return self.emergence_potential >= self.emergence_threshold


@dataclass
class Neighbor:
    """Neighbor node configuration."""
    id: str
    host: str
    port: int
    priority: int = 1
    shared_secret: Optional[bytes] = None
    last_seen: float = 0.0
    latency_ms: float = 0.0

    def update_latency(self, latency: float) -> None:
        """Update latency measurement."""
        # Exponential moving average
        alpha = 0.3
        self.latency_ms = alpha * latency + (1 - alpha) * self.latency_ms
        self.last_seen = time.time()


@dataclass
class CoherenceFilter:
    """Filter rule for coherence-based routing."""
    name: str
    condition: str  # Simple expression like "coherence >= 0.90"
    action: str     # "forward_immediate", "delay_100ms", "drop_with_log"
    priority: int

    def matches(self, token: RPPToken, field: FieldState) -> bool:
        """Check if token matches this filter condition."""
        # Simple expression parser
        expr = self.condition.replace("coherence", str(token.coherence))
        expr = expr.replace("field_saturation", str(field.field_saturation))
        expr = expr.replace("theta", str(token.theta))
        expr = expr.replace("phi", str(token.phi))

        try:
            return eval(expr)
        except Exception:
            return False


class PhaseRouter:
    """
    Main Phase-Aware Router daemon.

    Handles:
    - Token reception via TCP socket
    - AEAD encryption/decryption
    - Phase alignment routing decisions
    - Field saturation management
    - Emergence detection and broadcast
    """

    def __init__(self, config_path: str = "router_config.json"):
        self.config = self._load_config(config_path)
        self.node_id = self.config["node"]["id"]
        self.node_name = self.config["node"]["name"]

        # Initialize components
        self.encoder = RPPTokenEncoder(self.node_id)
        self.crypto = CryptoLayer(
            self.node_id,
            self.config["security"]["encryption_algorithm"]
        )

        # Field state
        self.field = FieldState(
            max_capacity=self.config["field"]["max_capacity"],
            theta_saturation_threshold=self.config["field"]["theta_saturation_threshold"],
            phi_saturation_threshold=self.config["field"]["phi_saturation_threshold"],
            coherence_minimum=self.config["field"]["coherence_minimum"],
            emergence_threshold=self.config["field"]["emergence_threshold"],
            decay_rate=self.config["field"]["decay_rate"]
        )

        # Neighbors
        self.neighbors: Dict[str, Neighbor] = {}
        for nb in self.config.get("neighbors", []):
            neighbor = Neighbor(
                id=nb["id"],
                host=nb["host"],
                port=nb["port"],
                priority=nb.get("priority", 1),
                shared_secret=nb.get("shared_secret", "").encode() if nb.get("shared_secret") else None
            )
            self.neighbors[nb["id"]] = neighbor

            # Initialize crypto session
            if neighbor.shared_secret:
                self.crypto.generate_session_key(neighbor.id, neighbor.shared_secret)

        # Coherence filters
        self.filters: List[CoherenceFilter] = []
        for f in self.config.get("coherence_filters", []):
            self.filters.append(CoherenceFilter(
                name=f["name"],
                condition=f["condition"],
                action=f["action"],
                priority=f["priority"]
            ))
        self.filters.sort(key=lambda x: x.priority)

        # Routing config
        self.max_hops = self.config["routing"]["max_hops"]
        self.hop_timeout_ms = self.config["routing"]["hop_timeout_ms"]
        self.retry_count = self.config["routing"]["retry_count"]
        self.drop_policy = DropPolicy(self.config["routing"]["drop_policy"])
        self.forward_mode = ForwardMode(self.config["routing"]["forward_mode"])
        self.phase_tolerance = self.config["routing"]["phase_tolerance"]

        # Emergence config
        self.emergence_enabled = self.config["emergence"]["enabled"]
        self.emergence_cooldown_ms = self.config["emergence"]["trigger_cooldown_ms"]
        self.last_emergence_time = 0.0

        # Statistics
        self.stats = {
            "tokens_received": 0,
            "tokens_forwarded": 0,
            "tokens_dropped": 0,
            "emergence_triggers": 0,
            "crypto_errors": 0
        }

        # Server state
        self.server = None
        self.running = False

        logger.info(f"PhaseRouter initialized: {self.node_id} ({self.node_name})")

    def _load_config(self, path: str) -> dict:
        """Load configuration from JSON file."""
        config_path = Path(path)
        if not config_path.exists():
            # Use default config path relative to this file
            config_path = Path(__file__).parent / "router_config.json"

        with open(config_path) as f:
            return json.load(f)

    async def start(self) -> None:
        """Start the router daemon."""
        host = self.config["network"]["listen_host"]
        port = self.config["network"]["listen_port"]

        self.server = await asyncio.start_server(
            self._handle_connection,
            host,
            port
        )
        self.running = True

        logger.info(f"Router listening on {host}:{port}")

        # Start background tasks
        asyncio.create_task(self._decay_loop())
        asyncio.create_task(self._emergence_check_loop())

        async with self.server:
            await self.server.serve_forever()

    async def stop(self) -> None:
        """Stop the router daemon."""
        self.running = False
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        logger.info("Router stopped")

    async def _handle_connection(self, reader: asyncio.StreamReader,
                                  writer: asyncio.StreamWriter) -> None:
        """Handle incoming connection."""
        addr = writer.get_extra_info('peername')
        logger.debug(f"Connection from {addr}")

        try:
            while True:
                # Read packet length (4 bytes)
                length_data = await asyncio.wait_for(
                    reader.read(4),
                    timeout=self.config["network"]["socket_timeout"]
                )

                if not length_data:
                    break

                packet_len = int.from_bytes(length_data, 'big')

                # Read packet data
                packet_data = await asyncio.wait_for(
                    reader.read(packet_len),
                    timeout=self.config["network"]["socket_timeout"]
                )

                # Process packet
                response = await self._process_packet(packet_data)

                # Send response
                if response:
                    response_bytes = response.encode() if isinstance(response, str) else response
                    writer.write(len(response_bytes).to_bytes(4, 'big'))
                    writer.write(response_bytes)
                    await writer.drain()

        except asyncio.TimeoutError:
            logger.debug(f"Connection timeout from {addr}")
        except Exception as e:
            logger.error(f"Connection error from {addr}: {e}")
        finally:
            writer.close()
            await writer.wait_closed()

    async def _process_packet(self, data: bytes) -> Optional[str]:
        """Process incoming packet."""
        self.stats["tokens_received"] += 1

        try:
            # Try to decrypt if encrypted
            try:
                encrypted = EncryptedPacket.from_bytes(data)
                plaintext = self.crypto.decrypt(encrypted)
                token = RPPToken.from_bytes(plaintext)
            except Exception:
                # Assume unencrypted token
                token = RPPToken.from_bytes(data)

            # Apply decay before processing
            self.field.decay()

            # Check coherence filters
            action = self._apply_filters(token)

            if action == "drop_with_log":
                self.stats["tokens_dropped"] += 1
                logger.warning(f"Dropped token: {token.source_id} (filter match)")
                return json.dumps({"status": "dropped", "reason": "filter"})

            if action.startswith("delay_"):
                delay_ms = int(action.split("_")[1].replace("ms", ""))
                await asyncio.sleep(delay_ms / 1000)

            # Add to field state
            self.field.add_token(token)

            # Check for emergence
            if self.emergence_enabled and self.field.is_emergence_ready():
                await self._trigger_emergence(token)

            # Route to next hop
            await self._route_token(token)

            return json.dumps({
                "status": "accepted",
                "field_saturation": round(self.field.field_saturation, 4),
                "emergence_potential": round(self.field.emergence_potential, 4)
            })

        except Exception as e:
            self.stats["crypto_errors"] += 1
            logger.error(f"Packet processing error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def _apply_filters(self, token: RPPToken) -> str:
        """Apply coherence filters and return action."""
        for f in self.filters:
            if f.matches(token, self.field):
                logger.debug(f"Filter matched: {f.name}")
                return f.action
        return "forward_immediate"

    async def _route_token(self, token: RPPToken) -> None:
        """Route token to appropriate neighbor(s)."""
        if not self.neighbors:
            logger.debug("No neighbors configured, token stored locally")
            return

        if self.forward_mode == ForwardMode.BROADCAST:
            # Send to all neighbors
            for neighbor in self.neighbors.values():
                await self._send_to_neighbor(token, neighbor)

        elif self.forward_mode == ForwardMode.BEST_MATCH:
            # Find best phase-aligned neighbor
            best = self._find_best_neighbor(token)
            if best:
                await self._send_to_neighbor(token, best)

        elif self.forward_mode == ForwardMode.ROUND_ROBIN:
            # Simple round-robin (use token hash for consistency)
            neighbors = list(self.neighbors.values())
            idx = hash(token.field_hash) % len(neighbors)
            await self._send_to_neighbor(token, neighbors[idx])

    def _find_best_neighbor(self, token: RPPToken) -> Optional[Neighbor]:
        """Find best neighbor based on phase alignment."""
        best = None
        best_score = -1

        for neighbor in self.neighbors.values():
            # Score based on priority and latency
            score = neighbor.priority / (1 + neighbor.latency_ms / 1000)

            if score > best_score:
                best_score = score
                best = neighbor

        return best

    async def _send_to_neighbor(self, token: RPPToken, neighbor: Neighbor) -> bool:
        """Send token to neighbor node."""
        try:
            start_time = time.time()

            # Encrypt if we have a session key
            if neighbor.id in self.crypto.session_keys:
                encrypted = self.crypto.encrypt(token.to_bytes(), neighbor.id)
                data = encrypted.to_bytes()
            else:
                data = token.to_bytes()

            # Connect and send
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(neighbor.host, neighbor.port),
                timeout=self.hop_timeout_ms / 1000
            )

            writer.write(len(data).to_bytes(4, 'big'))
            writer.write(data)
            await writer.drain()

            # Wait for ack
            ack_len = await reader.read(4)
            if ack_len:
                ack_data = await reader.read(int.from_bytes(ack_len, 'big'))

            writer.close()
            await writer.wait_closed()

            # Update latency
            latency = (time.time() - start_time) * 1000
            neighbor.update_latency(latency)

            self.stats["tokens_forwarded"] += 1
            logger.debug(f"Token forwarded to {neighbor.id} ({latency:.1f}ms)")
            return True

        except Exception as e:
            logger.warning(f"Failed to send to {neighbor.id}: {e}")
            return False

    async def _trigger_emergence(self, trigger_token: RPPToken) -> None:
        """Trigger emergence event."""
        now = time.time()

        # Check cooldown
        if (now - self.last_emergence_time) * 1000 < self.emergence_cooldown_ms:
            return

        self.last_emergence_time = now
        self.stats["emergence_triggers"] += 1

        logger.info(f"EMERGENCE TRIGGERED! Potential: {self.field.emergence_potential:.4f}")

        # Broadcast emergence signal if configured
        if self.config["emergence"]["broadcast_on_trigger"]:
            emergence_token = self.encoder.encode_from_raw(
                theta=0.99,
                phi=0.99,
                coherence=0.99,
                role="Guardian",
                entropy_delta=0.5
            )

            for neighbor in self.neighbors.values():
                await self._send_to_neighbor(emergence_token, neighbor)

    async def _decay_loop(self) -> None:
        """Background task for field decay."""
        interval = self.config["field"]["sample_interval_ms"] / 1000

        while self.running:
            await asyncio.sleep(interval)
            self.field.decay()

    async def _emergence_check_loop(self) -> None:
        """Background task for emergence checking."""
        interval = self.config["field"]["sample_interval_ms"] / 1000

        while self.running:
            await asyncio.sleep(interval)

            if self.emergence_enabled and self.field.is_emergence_ready():
                # Create synthetic trigger token
                trigger = self.encoder.encode_from_raw(
                    theta=self.field.theta_saturation,
                    phi=self.field.phi_saturation,
                    coherence=self.field.average_coherence,
                    role="Witness"
                )
                await self._trigger_emergence(trigger)

    def get_stats(self) -> dict:
        """Get router statistics."""
        return {
            **self.stats,
            "field_state": {
                "theta_saturation": round(self.field.theta_saturation, 4),
                "phi_saturation": round(self.field.phi_saturation, 4),
                "average_coherence": round(self.field.average_coherence, 4),
                "emergence_potential": round(self.field.emergence_potential, 4),
                "token_count": self.field.token_count
            },
            "neighbors": {
                n.id: {
                    "last_seen": n.last_seen,
                    "latency_ms": round(n.latency_ms, 2)
                }
                for n in self.neighbors.values()
            }
        }


# CLI interface
async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="PARL Phase Router Daemon")
    parser.add_argument(
        "--config", "-c",
        default="router_config.json",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="Enable debug logging"
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    router = PhaseRouter(args.config)

    try:
        await router.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        await router.stop()


if __name__ == "__main__":
    asyncio.run(main())
