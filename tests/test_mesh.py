"""
Tests for Fragment Mesh Module
==============================

Tests for fragment mesh addressing and routing.
"""

import pytest

from rpp.mesh import (
    AddressType,
    FragmentAddress,
    MessageType,
    MeshMessage,
    FragmentNode,
    FragmentMesh,
    generate_soul_id,
    create_mesh_with_fragments,
)
from rpp.sector_router import RoutableSector
from rpp.consent_header import ConsentState
from rpp.ra_constants import MAX_COHERENCE, BINDING_THRESHOLD


# =============================================================================
# Test AddressType
# =============================================================================

class TestAddressType:
    """Tests for AddressType enum."""

    def test_address_type_values(self):
        """Address types should have correct values."""
        assert AddressType.UNICAST == 0
        assert AddressType.MULTICAST == 1
        assert AddressType.BROADCAST == 2
        assert AddressType.SECTOR == 3


# =============================================================================
# Test FragmentAddress
# =============================================================================

class TestFragmentAddress:
    """Tests for FragmentAddress."""

    def test_address_creation(self):
        """Should create address with components."""
        addr = FragmentAddress(
            soul_id="abc123",
            fragment_id="frag001",
            sector=RoutableSector.CORE,
        )
        assert addr.soul_id == "abc123"
        assert addr.fragment_id == "frag001"
        assert addr.sector == RoutableSector.CORE

    def test_address_string(self):
        """String representation should be formatted correctly."""
        addr = FragmentAddress(
            soul_id="abc123",
            fragment_id="frag001",
            sector=RoutableSector.CORE,
        )
        assert str(addr) == "abc123.frag001.CORE"

    def test_address_parse_valid(self):
        """Should parse valid address string."""
        addr = FragmentAddress.parse("abc123.frag001.CORE")
        assert addr is not None
        assert addr.soul_id == "abc123"
        assert addr.fragment_id == "frag001"
        assert addr.sector == RoutableSector.CORE

    def test_address_parse_invalid_format(self):
        """Should return None for invalid format."""
        assert FragmentAddress.parse("invalid") is None
        assert FragmentAddress.parse("a.b") is None
        assert FragmentAddress.parse("a.b.c.d") is None

    def test_address_parse_invalid_sector(self):
        """Should return None for invalid sector."""
        assert FragmentAddress.parse("abc.frag.INVALID") is None

    def test_short_id(self):
        """Short ID should return fragment ID."""
        addr = FragmentAddress(
            soul_id="abc123",
            fragment_id="frag001",
            sector=RoutableSector.CORE,
        )
        assert addr.short_id == "frag001"

    def test_same_soul(self):
        """Should detect same soul."""
        addr1 = FragmentAddress("soul1", "frag1", RoutableSector.CORE)
        addr2 = FragmentAddress("soul1", "frag2", RoutableSector.MEMORY)
        addr3 = FragmentAddress("soul2", "frag3", RoutableSector.CORE)

        assert addr1.same_soul(addr2)
        assert not addr1.same_soul(addr3)

    def test_same_sector(self):
        """Should detect same sector."""
        addr1 = FragmentAddress("soul1", "frag1", RoutableSector.CORE)
        addr2 = FragmentAddress("soul2", "frag2", RoutableSector.CORE)
        addr3 = FragmentAddress("soul1", "frag3", RoutableSector.MEMORY)

        assert addr1.same_sector(addr2)
        assert not addr1.same_sector(addr3)


# =============================================================================
# Test MessageType
# =============================================================================

class TestMessageType:
    """Tests for MessageType enum."""

    def test_message_type_values(self):
        """Message types should have correct values."""
        assert MessageType.HEARTBEAT == 0
        assert MessageType.COHERENCE == 1
        assert MessageType.SYNC_REQUEST == 2
        assert MessageType.SYNC_RESPONSE == 3
        assert MessageType.CONFLICT == 4
        assert MessageType.RESOLUTION == 5
        assert MessageType.SECTOR_CHANGE == 6
        assert MessageType.SHUTDOWN == 7


# =============================================================================
# Test MeshMessage
# =============================================================================

class TestMeshMessage:
    """Tests for MeshMessage."""

    def test_message_creation(self):
        """Should create message with required fields."""
        source = FragmentAddress("soul", "frag1", RoutableSector.CORE)
        dest = FragmentAddress("soul", "frag2", RoutableSector.MEMORY)

        msg = MeshMessage(
            message_id="msg001",
            source=source,
            destination=dest,
            message_type=MessageType.COHERENCE,
        )

        assert msg.message_id == "msg001"
        assert msg.source == source
        assert msg.destination == dest
        assert msg.message_type == MessageType.COHERENCE

    def test_message_defaults(self):
        """Should have correct default values."""
        source = FragmentAddress("soul", "frag1", RoutableSector.CORE)

        msg = MeshMessage(
            message_id="msg001",
            source=source,
            destination="BROADCAST",
            message_type=MessageType.HEARTBEAT,
        )

        assert msg.priority == 1.0
        assert msg.ttl == 7
        assert msg.address_type == AddressType.UNICAST
        assert msg.payload == {}

    def test_message_ttl_decrement(self):
        """TTL should decrement correctly."""
        source = FragmentAddress("soul", "frag1", RoutableSector.CORE)

        msg = MeshMessage(
            message_id="msg001",
            source=source,
            destination="BROADCAST",
            message_type=MessageType.HEARTBEAT,
            ttl=3,
        )

        assert msg.decrement_ttl() is True
        assert msg.ttl == 2
        assert msg.decrement_ttl() is True
        assert msg.ttl == 1
        assert msg.decrement_ttl() is False
        assert msg.ttl == 0

    def test_message_is_expired(self):
        """Should detect expired messages."""
        source = FragmentAddress("soul", "frag1", RoutableSector.CORE)

        msg = MeshMessage(
            message_id="msg001",
            source=source,
            destination="BROADCAST",
            message_type=MessageType.HEARTBEAT,
            ttl=1,
        )

        assert not msg.is_expired
        msg.decrement_ttl()
        assert msg.is_expired


# =============================================================================
# Test FragmentNode
# =============================================================================

class TestFragmentNode:
    """Tests for FragmentNode."""

    def test_node_creation(self):
        """Should create node with address."""
        addr = FragmentAddress("soul", "frag1", RoutableSector.CORE)
        node = FragmentNode(address=addr)

        assert node.address == addr
        assert node.coherence == 0
        assert node.connected is True

    def test_node_is_bound(self):
        """Should check binding threshold."""
        addr = FragmentAddress("soul", "frag1", RoutableSector.CORE)

        node = FragmentNode(address=addr, coherence=100)
        assert not node.is_bound

        node = FragmentNode(address=addr, coherence=200)
        assert node.is_bound

    def test_node_weighted_score(self):
        """Should calculate weighted score."""
        addr = FragmentAddress("soul", "frag1", RoutableSector.CORE)
        node = FragmentNode(address=addr, coherence=500, priority=1.5)

        assert node.weighted_score == 750.0

    def test_node_heartbeat_update(self):
        """Should update heartbeat timestamp."""
        addr = FragmentAddress("soul", "frag1", RoutableSector.CORE)
        node = FragmentNode(address=addr)

        assert node.last_heartbeat is None
        node.update_heartbeat()
        assert node.last_heartbeat is not None


# =============================================================================
# Test FragmentMesh Registration
# =============================================================================

class TestMeshRegistration:
    """Tests for fragment registration."""

    def test_mesh_creation(self):
        """Should create mesh with soul ID."""
        mesh = FragmentMesh("soul123")
        assert mesh.soul_id == "soul123"
        assert mesh.node_count == 0

    def test_register_fragment(self):
        """Should register fragment and create node."""
        mesh = FragmentMesh("soul123")
        node = mesh.register_fragment("frag1")

        assert mesh.node_count == 1
        assert node.address.fragment_id == "frag1"
        assert node.address.soul_id == "soul123"

    def test_register_with_options(self):
        """Should register with custom options."""
        mesh = FragmentMesh("soul123")
        node = mesh.register_fragment(
            "frag1",
            sector=RoutableSector.CORE,
            priority=1.5,
            initial_coherence=500,
        )

        assert node.address.sector == RoutableSector.CORE
        assert node.priority == 1.5
        assert node.coherence == 500

    def test_unregister_fragment(self):
        """Should remove fragment from mesh."""
        mesh = FragmentMesh("soul123")
        mesh.register_fragment("frag1")
        assert mesh.node_count == 1

        result = mesh.unregister_fragment("frag1")
        assert result is True
        assert mesh.node_count == 0

    def test_unregister_nonexistent(self):
        """Should return False for nonexistent fragment."""
        mesh = FragmentMesh("soul123")
        result = mesh.unregister_fragment("nonexistent")
        assert result is False

    def test_get_node(self):
        """Should retrieve node by ID."""
        mesh = FragmentMesh("soul123")
        mesh.register_fragment("frag1", initial_coherence=500)

        node = mesh.get_node("frag1")
        assert node is not None
        assert node.coherence == 500


# =============================================================================
# Test Mesh Sector Queries
# =============================================================================

class TestMeshSectorQueries:
    """Tests for sector-based queries."""

    def test_get_nodes_in_sector(self):
        """Should return nodes in specific sector."""
        mesh = FragmentMesh("soul123")
        mesh.register_fragment("frag1", sector=RoutableSector.CORE)
        mesh.register_fragment("frag2", sector=RoutableSector.CORE)
        mesh.register_fragment("frag3", sector=RoutableSector.MEMORY)

        core_nodes = mesh.get_nodes_in_sector(RoutableSector.CORE)
        assert len(core_nodes) == 2

        memory_nodes = mesh.get_nodes_in_sector(RoutableSector.MEMORY)
        assert len(memory_nodes) == 1

    def test_get_connected_nodes(self):
        """Should return only connected nodes."""
        mesh = FragmentMesh("soul123")
        mesh.register_fragment("frag1")
        mesh.register_fragment("frag2")
        mesh.set_fragment_connected("frag2", False)

        connected = mesh.get_connected_nodes()
        assert len(connected) == 1
        assert connected[0].address.fragment_id == "frag1"


# =============================================================================
# Test Mesh Connectivity
# =============================================================================

class TestMeshConnectivity:
    """Tests for fragment connectivity."""

    def test_connect_fragments(self):
        """Should establish bidirectional connection."""
        mesh = FragmentMesh("soul123")
        mesh.register_fragment("frag1")
        mesh.register_fragment("frag2")

        result = mesh.connect_fragments("frag1", "frag2")
        assert result is True

        node1 = mesh.get_node("frag1")
        node2 = mesh.get_node("frag2")

        assert "frag2" in node1.neighbors
        assert "frag1" in node2.neighbors

    def test_disconnect_fragments(self):
        """Should remove bidirectional connection."""
        mesh = FragmentMesh("soul123")
        mesh.register_fragment("frag1")
        mesh.register_fragment("frag2")
        mesh.connect_fragments("frag1", "frag2")

        result = mesh.disconnect_fragments("frag1", "frag2")
        assert result is True

        node1 = mesh.get_node("frag1")
        node2 = mesh.get_node("frag2")

        assert "frag2" not in node1.neighbors
        assert "frag1" not in node2.neighbors

    def test_set_fragment_connected(self):
        """Should update connection status."""
        mesh = FragmentMesh("soul123")
        mesh.register_fragment("frag1")

        mesh.set_fragment_connected("frag1", False)
        assert not mesh.get_node("frag1").connected

        mesh.set_fragment_connected("frag1", True)
        assert mesh.get_node("frag1").connected


# =============================================================================
# Test Mesh Messaging
# =============================================================================

class TestMeshMessaging:
    """Tests for mesh messaging."""

    def test_create_message(self):
        """Should create message from fragment."""
        mesh = FragmentMesh("soul123")
        mesh.register_fragment("frag1")
        mesh.register_fragment("frag2")

        msg = mesh.create_message(
            source_id="frag1",
            destination="frag2",
            message_type=MessageType.COHERENCE,
            payload={'coherence': 500},
        )

        assert msg is not None
        assert msg.source.fragment_id == "frag1"
        assert msg.message_type == MessageType.COHERENCE

    def test_create_broadcast_message(self):
        """Should create broadcast message."""
        mesh = FragmentMesh("soul123")
        mesh.register_fragment("frag1")

        msg = mesh.create_message(
            source_id="frag1",
            destination="BROADCAST",
            message_type=MessageType.HEARTBEAT,
        )

        assert msg is not None
        assert msg.address_type == AddressType.BROADCAST

    def test_send_broadcast_message(self):
        """Should send to all connected nodes."""
        mesh = FragmentMesh("soul123")
        mesh.register_fragment("frag1")
        mesh.register_fragment("frag2")
        mesh.register_fragment("frag3")

        msg = mesh.create_message(
            source_id="frag1",
            destination="BROADCAST",
            message_type=MessageType.HEARTBEAT,
        )

        recipients = mesh.send_message(msg)
        assert recipients == 2  # Excludes source

    def test_message_handler(self):
        """Should call registered handlers."""
        mesh = FragmentMesh("soul123")
        mesh.register_fragment("frag1")
        mesh.register_fragment("frag2")

        received = []

        def handler(node, msg):
            received.append((node.address.fragment_id, msg.message_type))

        mesh.register_handler(MessageType.COHERENCE, handler)

        msg = mesh.create_message(
            source_id="frag1",
            destination="frag2",
            message_type=MessageType.COHERENCE,
        )
        mesh.send_message(msg)

        assert len(received) == 1
        assert received[0][0] == "frag2"


# =============================================================================
# Test Mesh Coherence
# =============================================================================

class TestMeshCoherence:
    """Tests for mesh coherence operations."""

    def test_update_node_coherence(self):
        """Should update node coherence."""
        mesh = FragmentMesh("soul123")
        mesh.register_fragment("frag1")

        result = mesh.update_node_coherence("frag1", 500, broadcast=False)
        assert result is True
        assert mesh.get_node("frag1").coherence == 500

    def test_get_mesh_coherence(self):
        """Should calculate weighted average coherence."""
        mesh = FragmentMesh("soul123")
        mesh.register_fragment("frag1", priority=1.0, initial_coherence=200)
        mesh.register_fragment("frag2", priority=1.0, initial_coherence=400)

        # (200*1 + 400*1) / (1+1) = 300
        assert mesh.get_mesh_coherence() == 300.0

    def test_get_mesh_coherence_weighted(self):
        """Should weight by priority."""
        mesh = FragmentMesh("soul123")
        mesh.register_fragment("frag1", priority=1.0, initial_coherence=200)
        mesh.register_fragment("frag2", priority=2.0, initial_coherence=400)

        # (200*1 + 400*2) / (1+2) = 1000/3 ≈ 333.3
        assert abs(mesh.get_mesh_coherence() - 333.33) < 1

    def test_get_highest_coherence_node(self):
        """Should return node with highest weighted score."""
        mesh = FragmentMesh("soul123")
        mesh.register_fragment("frag1", priority=1.0, initial_coherence=300)
        mesh.register_fragment("frag2", priority=1.0, initial_coherence=500)
        mesh.register_fragment("frag3", priority=2.0, initial_coherence=300)  # 600 weighted

        highest = mesh.get_highest_coherence_node()
        assert highest.address.fragment_id == "frag3"


# =============================================================================
# Test Mesh Summary
# =============================================================================

class TestMeshSummary:
    """Tests for mesh summary."""

    def test_mesh_summary_structure(self):
        """Should return summary with expected fields."""
        mesh = FragmentMesh("soul123")
        mesh.register_fragment("frag1", initial_coherence=500)

        summary = mesh.get_mesh_summary()

        assert 'soul_id' in summary
        assert 'total_nodes' in summary
        assert 'connected_nodes' in summary
        assert 'mesh_coherence' in summary
        assert 'sectors' in summary
        assert 'bound_count' in summary

    def test_mesh_summary_values(self):
        """Should return correct summary values."""
        mesh = FragmentMesh("soul123")
        mesh.register_fragment("frag1", initial_coherence=500)
        mesh.register_fragment("frag2", initial_coherence=100)  # Below binding threshold (137)

        summary = mesh.get_mesh_summary()

        assert summary['soul_id'] == "soul123"
        assert summary['total_nodes'] == 2
        assert summary['connected_nodes'] == 2
        assert summary['bound_count'] == 1  # Only frag1 is bound (coherence 500 > 137)


# =============================================================================
# Test Convenience Functions
# =============================================================================

class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_generate_soul_id(self):
        """Should generate 8-char hash."""
        soul_id = generate_soul_id("test_identity_data")
        assert len(soul_id) == 8
        assert soul_id.isalnum()

    def test_generate_soul_id_deterministic(self):
        """Same input should produce same output."""
        id1 = generate_soul_id("identity_data")
        id2 = generate_soul_id("identity_data")
        assert id1 == id2

    def test_generate_soul_id_unique(self):
        """Different input should produce different output."""
        id1 = generate_soul_id("identity_1")
        id2 = generate_soul_id("identity_2")
        assert id1 != id2

    def test_create_mesh_with_fragments(self):
        """Should create mesh with pre-registered fragments."""
        mesh = create_mesh_with_fragments(
            soul_id="soul123",
            fragment_ids=["f1", "f2", "f3"],
            initial_coherence=300,
        )

        assert mesh.node_count == 3
        assert mesh.get_node("f1").coherence == 300
        assert mesh.get_node("f2").coherence == 300
        assert mesh.get_node("f3").coherence == 300
