# RPP Mesh Transport Layer
# rpp_mesh_transport.py

import asyncio
import hashlib
import struct
import logging
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional, Callable, Awaitable

logger = logging.getLogger(__name__)


class ConsentState(IntEnum):
    """ACSP consent states encoded in mesh header."""
    FULL_CONSENT = 0x00
    DIMINISHED_CONSENT = 0x01
    SUSPENDED_CONSENT = 0x02
    EMERGENCY_OVERRIDE = 0xFF


class MeshFlags(IntEnum):
    """Mesh packet flags."""
    ENCRYPTED = 0x01
    COMPRESSED = 0x02
    PRIORITY = 0x04


@dataclass
class RPPMeshHeader:
    """16-byte mesh header prepended to RPP packets."""
    version: int = 1                    # 4 bits
    flags: int = 0                       # 4 bits
    consent_state: ConsentState = ConsentState.FULL_CONSENT  # 8 bits
    soul_id: int = 0                     # 16 bits (truncated)
    hop_count: int = 0                   # 8 bits
    ttl: int = 4                         # 8 bits (sector TTL)
    coherence_hash: int = 0              # 16 bits
    reserved: int = 0                    # 16 bits
    
    def pack(self) -> bytes:
        """Serialize header to 16 bytes."""
        # Byte 0: version (4 bits) | flags (4 bits)
        byte0 = ((self.version & 0x0F) << 4) | (self.flags & 0x0F)

        # Pack to 16 bytes: 1+1+2+1+1+2+2+6(padding) = 16
        return struct.pack(
            ">BBHBBHHBBBBBB",
            byte0,                    # 1
            self.consent_state,       # 1
            self.soul_id,             # 2
            self.hop_count,           # 1
            self.ttl,                 # 1
            self.coherence_hash,      # 2
            self.reserved,            # 2
            0, 0, 0, 0, 0, 0          # 6 padding to reach 16
        )
    
    @classmethod
    def unpack(cls, data: bytes) -> "RPPMeshHeader":
        """Deserialize header from bytes."""
        if len(data) < 16:
            raise ValueError(f"Header too short: {len(data)} bytes")
        
        byte0, consent, soul_id, hop, ttl, coherence, reserved, _, _, _, _, _, _ = \
            struct.unpack(">BBHBBHHBBBBBB", data[:16])
        
        return cls(
            version=(byte0 >> 4) & 0x0F,
            flags=byte0 & 0x0F,
            consent_state=ConsentState(consent),
            soul_id=soul_id,
            hop_count=hop,
            ttl=ttl,
            coherence_hash=coherence,
            reserved=reserved
        )


@dataclass
class RPPMeshPacket:
    """Complete mesh packet: header + RPP address + payload."""
    header: RPPMeshHeader
    rpp_address: int          # 28-bit RPP address (stored in 32-bit)
    payload: bytes
    
    def pack(self) -> bytes:
        """Serialize complete packet."""
        return (
            self.header.pack() +
            struct.pack(">I", self.rpp_address) +
            self.payload
        )
    
    @classmethod
    def unpack(cls, data: bytes) -> "RPPMeshPacket":
        """Deserialize packet from bytes."""
        header = RPPMeshHeader.unpack(data[:16])
        rpp_address = struct.unpack(">I", data[16:20])[0]
        payload = data[20:]
        return cls(header=header, rpp_address=rpp_address, payload=payload)


class RPPMeshTransport:
    """Transport layer for RPP Mesh overlay network."""
    
    def __init__(self, config):
        self.config = config
        self.ingress_nodes = config.ingress_nodes
        self.soul_key = self._load_soul_key(config.soul_key_path)
        self.soul_id_truncated = self._truncate_soul_id()
        
        self._consent_state = ConsentState.FULL_CONSENT
        self._consent_stream_task: Optional[asyncio.Task] = None
        self._connections: dict = {}
    
    def _load_soul_key(self, path: str) -> bytes:
        """Load soul private key for signing."""
        try:
            with open(path, "rb") as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(f"Soul key not found at {path}, using ephemeral key")
            return hashlib.sha256(b"ephemeral-dev-key").digest()
    
    def _truncate_soul_id(self) -> int:
        """Generate truncated 16-bit soul ID for routing."""
        full_hash = hashlib.sha256(self.soul_key).digest()
        return struct.unpack(">H", full_hash[:2])[0]
    
    def _compute_coherence_hash(self, payload: bytes) -> int:
        """Compute 16-bit coherence proof."""
        h = hashlib.sha256(self.soul_key + payload).digest()
        return struct.unpack(">H", h[:2])[0]
    
    async def connect(self):
        """Establish connections to ingress nodes."""
        for node in self.ingress_nodes:
            try:
                host, port = node.rsplit(":", 1)
                reader, writer = await asyncio.open_connection(host, int(port))
                self._connections[node] = (reader, writer)
                logger.info(f"Connected to mesh ingress: {node}")
            except Exception as e:
                logger.warning(f"Failed to connect to {node}: {e}")
        
        if not self._connections:
            raise ConnectionError("Could not connect to any mesh ingress node")
        
        # Start consent state stream
        self._consent_stream_task = asyncio.create_task(
            self._consent_stream_listener()
        )
    
    async def disconnect(self):
        """Close all mesh connections."""
        if self._consent_stream_task:
            self._consent_stream_task.cancel()
        
        for node, (reader, writer) in self._connections.items():
            writer.close()
            await writer.wait_closed()
        
        self._connections.clear()
    
    async def _consent_stream_listener(self):
        """Listen for consent state updates from HNC."""
        import websockets
        
        while True:
            try:
                async with websockets.connect(
                    self.config.consent_update_endpoint
                ) as ws:
                    logger.info("Connected to HNC consent stream")
                    async for message in ws:
                        self._handle_consent_update(message)
            except Exception as e:
                logger.warning(f"Consent stream error: {e}, reconnecting...")
                await asyncio.sleep(5)
    
    def _handle_consent_update(self, message: bytes):
        """Process consent state update from HNC."""
        # Expected format: 1 byte consent state + signature
        if len(message) < 1:
            return
        
        new_state = ConsentState(message[0])
        # TODO: Verify HNC signature
        
        if new_state != self._consent_state:
            logger.info(f"Consent state changed: {self._consent_state.name} -> {new_state.name}")
            self._consent_state = new_state
    
    def _select_ingress(self) -> tuple:
        """Select best available ingress node."""
        # Simple round-robin for now
        # TODO: Add latency-based selection
        for node, conn in self._connections.items():
            return conn
        raise ConnectionError("No ingress nodes available")
    
    async def send(self, rpp_address: int, payload: bytes) -> bytes:
        """Send packet through mesh and await response."""
        
        # Build mesh header
        flags = 0
        if self.config.encrypt_payload:
            flags |= MeshFlags.ENCRYPTED
            # TODO: Actually encrypt payload
        if self.config.compress_payload:
            flags |= MeshFlags.COMPRESSED
            # TODO: Actually compress payload
        
        header = RPPMeshHeader(
            version=1,
            flags=flags,
            consent_state=self._consent_state,
            soul_id=self.soul_id_truncated,
            hop_count=0,
            ttl=self.config.sector_ttl,
            coherence_hash=self._compute_coherence_hash(payload),
        )
        
        packet = RPPMeshPacket(
            header=header,
            rpp_address=rpp_address,
            payload=payload
        )
        
        # Send through mesh
        reader, writer = self._select_ingress()
        
        packed = packet.pack()
        length_prefix = struct.pack(">I", len(packed))
        
        writer.write(length_prefix + packed)
        await writer.drain()
        
        # Await response
        try:
            response_length = struct.unpack(">I", await reader.readexactly(4))[0]
            response_data = await reader.readexactly(response_length)
            
            response_packet = RPPMeshPacket.unpack(response_data)
            
            # Log routing decision if enabled
            if self.config.log_routing_decisions:
                logger.debug(
                    f"Mesh response: hops={response_packet.header.hop_count}, "
                    f"consent={response_packet.header.consent_state.name}"
                )
            
            return response_packet.payload
            
        except asyncio.TimeoutError:
            logger.warning("Mesh response timeout, attempting fallback")
            return await self._fallback_send(rpp_address, payload)
    
    async def _fallback_send(self, rpp_address: int, payload: bytes) -> bytes:
        """Fallback to direct/VPN mode if mesh fails."""
        if self.config.fallback_mode == "fail":
            raise ConnectionError("Mesh unavailable and fallback disabled")
        
        logger.info(f"Falling back to {self.config.fallback_mode} mode")
        
        # Import here to avoid circular dependency
        from .direct_transport import DirectTransport
        from .vpn_transport import VPNTransport
        
        if self.config.fallback_mode == "direct":
            transport = DirectTransport(self.config)
        else:
            transport = VPNTransport(self.config)
        
        return await transport.send(rpp_address, payload)


class ConsentGate:
    """
    Consent gate node implementation.
    Runs on mesh relay nodes to enforce ACSP state.
    """
    
    def __init__(self, hnc_public_key: bytes):
        self.hnc_public_key = hnc_public_key
        self.consent_cache: dict[int, tuple[ConsentState, float]] = {}
        self.cache_ttl = 30.0
    
    async def process_packet(
        self, 
        packet: RPPMeshPacket,
        forward: Callable[[RPPMeshPacket], Awaitable[bytes]]
    ) -> Optional[bytes]:
        """
        Process packet through consent gate.
        Returns response payload or None if dropped.
        """
        consent = packet.header.consent_state
        soul_id = packet.header.soul_id
        
        # Verify consent state signature (TODO)
        # if not self._verify_consent_signature(packet):
        #     logger.warning(f"Invalid consent signature for soul {soul_id}")
        #     return None
        
        # Apply consent policy
        if consent == ConsentState.FULL_CONSENT:
            # Pass through
            return await forward(packet)
        
        elif consent == ConsentState.DIMINISHED_CONSENT:
            # Delay and re-check
            await asyncio.sleep(2.0)
            # Re-query HNC for current state
            current = await self._query_consent(soul_id)
            if current == ConsentState.FULL_CONSENT:
                return await forward(packet)
            else:
                logger.info(f"Packet delayed, consent still {current.name}, dropping")
                return None
        
        elif consent == ConsentState.SUSPENDED_CONSENT:
            # Drop immediately
            logger.info(f"Dropping packet for soul {soul_id}: SUSPENDED_CONSENT")
            await self._log_to_scl("DROP", packet)
            return None
        
        elif consent == ConsentState.EMERGENCY_OVERRIDE:
            # Freeze and alert
            logger.critical(f"EMERGENCY_OVERRIDE for soul {soul_id}")
            await self._log_to_scl("EMERGENCY", packet)
            await self._alert_hnc(packet)
            return None
        
        return None
    
    async def _query_consent(self, soul_id: int) -> ConsentState:
        """Query HNC for current consent state."""
        # TODO: Implement HNC query
        return ConsentState.FULL_CONSENT
    
    async def _log_to_scl(self, action: str, packet: RPPMeshPacket):
        """Log routing decision to Semantic Consent Ledger."""
        # TODO: Implement SCL logging
        pass
    
    async def _alert_hnc(self, packet: RPPMeshPacket):
        """Send emergency alert to HNC."""
        # TODO: Implement HNC alerting
        pass
