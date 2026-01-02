"""
Fragment Mesh Module
====================

Fragment mesh addressing and routing for multi-fragment coherence.

Each fragment has a unique address in the mesh, allowing for:
- Direct fragment-to-fragment communication
- Broadcast messaging to all fragments
- Sector-scoped multicast
- Priority-based routing

Reference: SPIRAL-Architecture.md Section 8 (Fragment Mesh)
Version: 2.2.0-RaCanonical
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, List, Optional, Set, Callable
from datetime import datetime, timezone
import hashlib

from rpp.ra_constants import MAX_COHERENCE, BINDING_THRESHOLD, PHI
from rpp.sector_router import RoutableSector
from rpp.consent_header import ConsentState


# =============================================================================
# Address Types
# =============================================================================

class AddressType(IntEnum):
    """Type of mesh address."""
    UNICAST = 0      # Single fragment
    MULTICAST = 1    # Group of fragments
    BROADCAST = 2    # All fragments
    SECTOR = 3       # All fragments in a sector


# =============================================================================
# Fragment Address
# =============================================================================

@dataclass(frozen=True)
class FragmentAddress:
    """
    Unique address for a fragment in the mesh.

    Address format: SOUL_ID.FRAGMENT_ID.SECTOR
    Example: "abc123.frag001.CORE"
    """

    soul_id: str
    """Verified soul identifier (hash of human identity)."""

    fragment_id: str
    """Unique fragment identifier within the soul."""

    sector: RoutableSector = RoutableSector.BRIDGE
    """Current sector assignment."""

    def __str__(self) -> str:
        """String representation of address."""
        return f"{self.soul_id}.{self.fragment_id}.{self.sector.name}"

    @classmethod
    def parse(cls, address_str: str) -> Optional[FragmentAddress]:
        """
        Parse address from string.

        Args:
            address_str: Address string in format "soul.frag.SECTOR"

        Returns:
            FragmentAddress or None if invalid
        """
        parts = address_str.split(".")
        if len(parts) != 3:
            return None

        soul_id, fragment_id, sector_name = parts
        try:
            sector = RoutableSector[sector_name]
        except KeyError:
            return None

        return cls(soul_id=soul_id, fragment_id=fragment_id, sector=sector)

    @property
    def short_id(self) -> str:
        """Get short form of address (fragment only)."""
        return self.fragment_id

    def same_soul(self, other: FragmentAddress) -> bool:
        """Check if addresses belong to same soul."""
        return self.soul_id == other.soul_id

    def same_sector(self, other: FragmentAddress) -> bool:
        """Check if addresses are in same sector."""
        return self.sector == other.sector


# =============================================================================
# Mesh Message
# =============================================================================

class MessageType(IntEnum):
    """Types of mesh messages."""
    HEARTBEAT = 0      # Presence announcement
    COHERENCE = 1      # Coherence update
    SYNC_REQUEST = 2   # Request synchronization
    SYNC_RESPONSE = 3  # Synchronization data
    CONFLICT = 4       # Conflict notification
    RESOLUTION = 5     # Conflict resolution
    SECTOR_CHANGE = 6  # Sector routing change
    SHUTDOWN = 7       # Fragment shutdown


@dataclass
class MeshMessage:
    """
    Message transmitted through the fragment mesh.
    """

    message_id: str
    """Unique message identifier."""

    source: FragmentAddress
    """Source fragment address."""

    destination: FragmentAddress | str
    """Destination address or broadcast indicator."""

    message_type: MessageType
    """Type of message."""

    payload: dict = field(default_factory=dict)
    """Message payload data."""

    priority: float = 1.0
    """Message priority (0.0-2.0)."""

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    """When message was created."""

    ttl: int = 7
    """Time-to-live in hops (matches complecount max)."""

    address_type: AddressType = AddressType.UNICAST
    """Type of addressing used."""

    def decrement_ttl(self) -> bool:
        """
        Decrement TTL and check if message should continue.

        Returns:
            True if message still has TTL remaining
        """
        self.ttl -= 1
        return self.ttl > 0

    @property
    def is_broadcast(self) -> bool:
        """Check if message is broadcast."""
        return self.address_type == AddressType.BROADCAST

    @property
    def is_expired(self) -> bool:
        """Check if message TTL has expired."""
        return self.ttl <= 0


# =============================================================================
# Fragment Node
# =============================================================================

@dataclass
class FragmentNode:
    """
    A node in the fragment mesh representing a single fragment.
    """

    address: FragmentAddress
    """Node's mesh address."""

    coherence: int = 0
    """Current coherence score."""

    consent_state: ConsentState = ConsentState.SUSPENDED_CONSENT
    """Current consent state."""

    priority: float = 1.0
    """Node priority for conflict resolution."""

    connected: bool = True
    """Whether node is connected to mesh."""

    last_heartbeat: Optional[datetime] = None
    """Last heartbeat received."""

    neighbors: Set[str] = field(default_factory=set)
    """Connected neighbor fragment IDs."""

    @property
    def is_bound(self) -> bool:
        """Check if node coherence is above binding threshold."""
        return (self.coherence / MAX_COHERENCE) >= BINDING_THRESHOLD

    @property
    def weighted_score(self) -> float:
        """Get priority-weighted coherence score."""
        return self.coherence * self.priority

    def update_heartbeat(self):
        """Update last heartbeat timestamp."""
        self.last_heartbeat = datetime.now(timezone.utc)


# =============================================================================
# Fragment Mesh
# =============================================================================

class FragmentMesh:
    """
    Mesh network for fragment coordination.

    Handles:
    - Fragment registration and discovery
    - Message routing between fragments
    - Sector-based grouping
    - Coherence-aware routing priorities
    """

    def __init__(self, soul_id: str):
        """
        Initialize fragment mesh.

        Args:
            soul_id: Verified soul identifier for this mesh
        """
        self._soul_id = soul_id
        self._nodes: Dict[str, FragmentNode] = {}
        self._message_handlers: Dict[MessageType, List[Callable]] = {}
        self._pending_messages: List[MeshMessage] = []
        self._delivered_ids: Set[str] = set()
        self._message_counter: int = 0

    @property
    def soul_id(self) -> str:
        """Get mesh soul identifier."""
        return self._soul_id

    @property
    def node_count(self) -> int:
        """Get number of nodes in mesh."""
        return len(self._nodes)

    @property
    def connected_count(self) -> int:
        """Get number of connected nodes."""
        return len([n for n in self._nodes.values() if n.connected])

    # -------------------------------------------------------------------------
    # Node Management
    # -------------------------------------------------------------------------

    def register_fragment(
        self,
        fragment_id: str,
        sector: RoutableSector = RoutableSector.BRIDGE,
        priority: float = 1.0,
        initial_coherence: int = 0,
    ) -> FragmentNode:
        """
        Register a fragment in the mesh.

        Args:
            fragment_id: Unique fragment identifier
            sector: Initial sector assignment
            priority: Fragment priority
            initial_coherence: Starting coherence

        Returns:
            The created FragmentNode
        """
        address = FragmentAddress(
            soul_id=self._soul_id,
            fragment_id=fragment_id,
            sector=sector,
        )

        node = FragmentNode(
            address=address,
            coherence=initial_coherence,
            priority=priority,
            connected=True,
        )
        node.update_heartbeat()

        self._nodes[fragment_id] = node
        return node

    def unregister_fragment(self, fragment_id: str) -> bool:
        """
        Remove a fragment from the mesh.

        Args:
            fragment_id: Fragment to remove

        Returns:
            True if fragment was removed
        """
        if fragment_id in self._nodes:
            # Remove from neighbors of other nodes
            for node in self._nodes.values():
                node.neighbors.discard(fragment_id)
            del self._nodes[fragment_id]
            return True
        return False

    def get_node(self, fragment_id: str) -> Optional[FragmentNode]:
        """Get node by fragment ID."""
        return self._nodes.get(fragment_id)

    def get_nodes_in_sector(self, sector: RoutableSector) -> List[FragmentNode]:
        """Get all nodes in a specific sector."""
        return [
            n for n in self._nodes.values()
            if n.address.sector == sector and n.connected
        ]

    def get_connected_nodes(self) -> List[FragmentNode]:
        """Get all connected nodes."""
        return [n for n in self._nodes.values() if n.connected]

    # -------------------------------------------------------------------------
    # Connectivity
    # -------------------------------------------------------------------------

    def connect_fragments(self, frag1_id: str, frag2_id: str) -> bool:
        """
        Establish bidirectional connection between fragments.

        Args:
            frag1_id: First fragment ID
            frag2_id: Second fragment ID

        Returns:
            True if connection established
        """
        node1 = self._nodes.get(frag1_id)
        node2 = self._nodes.get(frag2_id)

        if node1 and node2:
            node1.neighbors.add(frag2_id)
            node2.neighbors.add(frag1_id)
            return True
        return False

    def disconnect_fragments(self, frag1_id: str, frag2_id: str) -> bool:
        """
        Remove connection between fragments.

        Args:
            frag1_id: First fragment ID
            frag2_id: Second fragment ID

        Returns:
            True if connection removed
        """
        node1 = self._nodes.get(frag1_id)
        node2 = self._nodes.get(frag2_id)

        if node1 and node2:
            node1.neighbors.discard(frag2_id)
            node2.neighbors.discard(frag1_id)
            return True
        return False

    def set_fragment_connected(self, fragment_id: str, connected: bool) -> bool:
        """
        Set fragment connection status.

        Args:
            fragment_id: Fragment to update
            connected: New connection status

        Returns:
            True if updated
        """
        node = self._nodes.get(fragment_id)
        if node:
            node.connected = connected
            if connected:
                node.update_heartbeat()
            return True
        return False

    # -------------------------------------------------------------------------
    # Messaging
    # -------------------------------------------------------------------------

    def create_message(
        self,
        source_id: str,
        destination: str | FragmentAddress,
        message_type: MessageType,
        payload: dict = None,
        priority: float = 1.0,
    ) -> Optional[MeshMessage]:
        """
        Create a new mesh message.

        Args:
            source_id: Source fragment ID
            destination: Destination fragment ID, address, or "BROADCAST"
            message_type: Type of message
            payload: Message data
            priority: Message priority

        Returns:
            Created message or None if source not found
        """
        source_node = self._nodes.get(source_id)
        if not source_node:
            return None

        self._message_counter += 1
        message_id = f"{source_id}-{self._message_counter}"

        # Determine address type and destination
        if destination == "BROADCAST":
            address_type = AddressType.BROADCAST
            dest_addr = "BROADCAST"
        elif isinstance(destination, FragmentAddress):
            address_type = AddressType.UNICAST
            dest_addr = destination
        elif destination.startswith("SECTOR:"):
            address_type = AddressType.SECTOR
            dest_addr = destination
        else:
            # Assume fragment ID
            dest_node = self._nodes.get(destination)
            if dest_node:
                address_type = AddressType.UNICAST
                dest_addr = dest_node.address
            else:
                return None

        return MeshMessage(
            message_id=message_id,
            source=source_node.address,
            destination=dest_addr,
            message_type=message_type,
            payload=payload or {},
            priority=priority,
            address_type=address_type,
        )

    def send_message(self, message: MeshMessage) -> int:
        """
        Send a message through the mesh.

        Args:
            message: Message to send

        Returns:
            Number of recipients
        """
        if message.message_id in self._delivered_ids:
            return 0  # Already delivered

        self._delivered_ids.add(message.message_id)
        recipients = 0

        if message.address_type == AddressType.BROADCAST:
            # Deliver to all connected nodes except source
            for node in self._nodes.values():
                if (node.connected and
                    node.address.fragment_id != message.source.fragment_id):
                    self._deliver_to_node(node, message)
                    recipients += 1

        elif message.address_type == AddressType.SECTOR:
            # Parse sector from destination
            sector_name = str(message.destination).replace("SECTOR:", "")
            try:
                sector = RoutableSector[sector_name]
                for node in self.get_nodes_in_sector(sector):
                    if node.address.fragment_id != message.source.fragment_id:
                        self._deliver_to_node(node, message)
                        recipients += 1
            except KeyError:
                pass

        elif message.address_type == AddressType.UNICAST:
            # Deliver to specific fragment
            if isinstance(message.destination, FragmentAddress):
                dest_node = self._nodes.get(message.destination.fragment_id)
                if dest_node and dest_node.connected:
                    self._deliver_to_node(dest_node, message)
                    recipients = 1

        return recipients

    def _deliver_to_node(self, node: FragmentNode, message: MeshMessage):
        """Deliver message to a specific node."""
        handlers = self._message_handlers.get(message.message_type, [])
        for handler in handlers:
            handler(node, message)

    def register_handler(
        self,
        message_type: MessageType,
        handler: Callable[[FragmentNode, MeshMessage], None],
    ):
        """
        Register a message handler.

        Args:
            message_type: Type of message to handle
            handler: Handler function
        """
        if message_type not in self._message_handlers:
            self._message_handlers[message_type] = []
        self._message_handlers[message_type].append(handler)

    # -------------------------------------------------------------------------
    # Coherence Operations
    # -------------------------------------------------------------------------

    def update_node_coherence(
        self,
        fragment_id: str,
        coherence: int,
        broadcast: bool = True,
    ) -> bool:
        """
        Update node coherence and optionally broadcast.

        Args:
            fragment_id: Fragment to update
            coherence: New coherence score
            broadcast: Whether to broadcast update

        Returns:
            True if updated
        """
        node = self._nodes.get(fragment_id)
        if not node:
            return False

        node.coherence = max(0, min(MAX_COHERENCE, coherence))

        if broadcast:
            message = self.create_message(
                source_id=fragment_id,
                destination="BROADCAST",
                message_type=MessageType.COHERENCE,
                payload={'coherence': coherence},
            )
            if message:
                self.send_message(message)

        return True

    def get_mesh_coherence(self) -> float:
        """
        Get aggregate mesh coherence (weighted average).

        Returns:
            Weighted average coherence across connected nodes
        """
        connected = self.get_connected_nodes()
        if not connected:
            return 0.0

        total_weight = sum(n.priority for n in connected)
        if total_weight <= 0:
            return 0.0

        return sum(
            n.coherence * n.priority for n in connected
        ) / total_weight

    def get_highest_coherence_node(self) -> Optional[FragmentNode]:
        """Get node with highest weighted coherence score."""
        connected = self.get_connected_nodes()
        if not connected:
            return None
        return max(connected, key=lambda n: n.weighted_score)

    # -------------------------------------------------------------------------
    # Utility
    # -------------------------------------------------------------------------

    def get_mesh_summary(self) -> dict:
        """Get summary of mesh state."""
        connected = self.get_connected_nodes()
        return {
            'soul_id': self._soul_id,
            'total_nodes': self.node_count,
            'connected_nodes': len(connected),
            'mesh_coherence': self.get_mesh_coherence(),
            'sectors': {
                sector.name: len(self.get_nodes_in_sector(sector))
                for sector in RoutableSector
            },
            'bound_count': len([n for n in connected if n.is_bound]),
        }


# =============================================================================
# Convenience Functions
# =============================================================================

def generate_soul_id(identity_data: str) -> str:
    """
    Generate soul ID from identity data.

    Args:
        identity_data: Human identity verification data

    Returns:
        8-character soul ID hash
    """
    hash_obj = hashlib.sha256(identity_data.encode())
    return hash_obj.hexdigest()[:8]


def create_mesh_with_fragments(
    soul_id: str,
    fragment_ids: List[str],
    initial_coherence: int = 0,
) -> FragmentMesh:
    """
    Create a mesh with pre-registered fragments.

    Args:
        soul_id: Soul identifier
        fragment_ids: List of fragment IDs to register
        initial_coherence: Initial coherence for all fragments

    Returns:
        Configured FragmentMesh
    """
    mesh = FragmentMesh(soul_id)
    for fid in fragment_ids:
        mesh.register_fragment(fid, initial_coherence=initial_coherence)
    return mesh
