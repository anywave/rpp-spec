"""
RPP Packet - Rotational Packet Envelope

Implements the packet format from PACKET.md:
- 4-byte address (28-bit RPP address in big-endian)
- Optional payload (0 to N bytes)

Packet types:
- Empty: Address only (routing, query)
- Pointer: 8-byte reference
- Hash: 32-byte SHA-256
- Inline: Variable-length data
- Framed: Length-prefixed content
"""

from dataclasses import dataclass
from typing import Optional, Union
from enum import IntEnum
import hashlib

from rpp.address import from_raw, RPPAddress, is_valid_address, MAX_ADDRESS


class PayloadType(IntEnum):
    """Payload type identifiers for the flags byte."""
    EMPTY = 0x00
    POINTER = 0x01
    HASH = 0x02
    INLINE = 0x03
    FRAMED = 0x04


@dataclass(frozen=True)
class RPPPacket:
    """
    Immutable rotational packet.

    Attributes:
        address: Decoded RPP address
        payload: Raw payload bytes (may be empty)
        payload_type: Type of payload content
    """

    address: RPPAddress
    payload: bytes
    payload_type: PayloadType

    def __post_init__(self) -> None:
        """Validate packet structure."""
        if not isinstance(self.payload, bytes):
            raise TypeError("Payload must be bytes")

    def __len__(self) -> int:
        """Return total packet size in bytes."""
        return 4 + len(self.payload)

    def to_bytes(self) -> bytes:
        """
        Serialize packet to wire format.

        Returns:
            Bytes: 4-byte address (big-endian) + payload
        """
        addr_bytes = self.address.raw.to_bytes(4, byteorder='big')
        return addr_bytes + self.payload

    def to_framed_bytes(self) -> bytes:
        """
        Serialize packet with flags byte (extended wire format).

        Returns:
            Bytes: 1-byte flags + 4-byte address + payload
        """
        flags = self.payload_type & 0x0F
        addr_bytes = self.address.raw.to_bytes(4, byteorder='big')
        return bytes([flags]) + addr_bytes + self.payload

    @property
    def is_empty(self) -> bool:
        """True if packet has no payload."""
        return len(self.payload) == 0

    @property
    def content_hash(self) -> bytes:
        """SHA-256 hash of the entire packet."""
        return hashlib.sha256(self.to_bytes()).digest()

    def to_dict(self) -> dict:
        """Return packet as JSON-serializable dictionary."""
        return {
            "address": self.address.to_dict(),
            "payload_size": len(self.payload),
            "payload_type": self.payload_type.name,
            "total_size": len(self),
        }


def create_packet(
    address: int,
    payload: bytes = b"",
    payload_type: Optional[PayloadType] = None,
) -> RPPPacket:
    """
    Create a rotational packet from address and optional payload.

    Args:
        address: 28-bit RPP address
        payload: Optional payload bytes
        payload_type: Optional type hint (auto-detected if not provided)

    Returns:
        RPPPacket instance

    Raises:
        ValueError: If address is invalid
    """
    if not is_valid_address(address):
        raise ValueError(f"Address must be 0-{hex(MAX_ADDRESS)}, got {hex(address)}")

    # Auto-detect payload type if not specified
    if payload_type is None:
        if len(payload) == 0:
            payload_type = PayloadType.EMPTY
        elif len(payload) == 8:
            payload_type = PayloadType.POINTER
        elif len(payload) == 32:
            payload_type = PayloadType.HASH
        else:
            payload_type = PayloadType.INLINE

    addr = from_raw(address)
    return RPPPacket(address=addr, payload=payload, payload_type=payload_type)


def parse_packet(data: bytes) -> RPPPacket:
    """
    Parse a rotational packet from bytes.

    Args:
        data: Packet bytes (minimum 4 bytes)

    Returns:
        RPPPacket with decoded address and payload

    Raises:
        ValueError: If packet is too short or address is invalid
    """
    if len(data) < 4:
        raise ValueError(f"Packet too short: {len(data)} bytes (minimum 4)")

    # Extract address (first 4 bytes, big-endian)
    address = int.from_bytes(data[:4], byteorder='big')

    # Validate reserved bits
    if address > MAX_ADDRESS:
        raise ValueError(f"Reserved bits must be zero, got {hex(address)}")

    # Extract payload (remaining bytes)
    payload = data[4:]

    return create_packet(address, payload)


def parse_framed_packet(data: bytes) -> RPPPacket:
    """
    Parse a packet with flags byte (extended wire format).

    Args:
        data: Packet bytes with flags (minimum 5 bytes)

    Returns:
        RPPPacket with decoded address, payload, and type

    Raises:
        ValueError: If packet is invalid
    """
    if len(data) < 5:
        raise ValueError(f"Framed packet too short: {len(data)} bytes (minimum 5)")

    flags = data[0]
    payload_type = PayloadType(flags & 0x0F)

    # Extract address (bytes 1-4, big-endian)
    address = int.from_bytes(data[1:5], byteorder='big')

    if address > MAX_ADDRESS:
        raise ValueError(f"Reserved bits must be zero, got {hex(address)}")

    payload = data[5:]

    addr = from_raw(address)
    return RPPPacket(address=addr, payload=payload, payload_type=payload_type)


def is_valid_packet(data: bytes) -> bool:
    """
    Check if bytes form a valid rotational packet.

    Args:
        data: Bytes to validate

    Returns:
        True if valid packet, False otherwise
    """
    if len(data) < 4:
        return False

    address = int.from_bytes(data[:4], byteorder='big')
    return address <= MAX_ADDRESS


def create_hash_packet(address: int, content: bytes) -> RPPPacket:
    """
    Create a packet with SHA-256 hash of content.

    Args:
        address: 28-bit RPP address
        content: Content to hash (stored elsewhere)

    Returns:
        RPPPacket with 32-byte hash payload
    """
    content_hash = hashlib.sha256(content).digest()
    return create_packet(address, content_hash, PayloadType.HASH)


def create_pointer_packet(address: int, pointer: int) -> RPPPacket:
    """
    Create a packet with 8-byte pointer payload.

    Args:
        address: 28-bit RPP address
        pointer: 64-bit pointer value

    Returns:
        RPPPacket with 8-byte pointer payload
    """
    pointer_bytes = pointer.to_bytes(8, byteorder='big')
    return create_packet(address, pointer_bytes, PayloadType.POINTER)


def create_framed_packet(address: int, content: bytes) -> RPPPacket:
    """
    Create a length-prefixed framed packet.

    Args:
        address: 28-bit RPP address
        content: Content bytes

    Returns:
        RPPPacket with 4-byte length prefix + content
    """
    length_prefix = len(content).to_bytes(4, byteorder='big')
    payload = length_prefix + content
    return create_packet(address, payload, PayloadType.FRAMED)


def extract_framed_content(packet: RPPPacket) -> bytes:
    """
    Extract content from a framed packet.

    Args:
        packet: Framed packet

    Returns:
        Content bytes (without length prefix)

    Raises:
        ValueError: If packet is not framed or malformed
    """
    if packet.payload_type != PayloadType.FRAMED:
        raise ValueError("Packet is not framed")

    if len(packet.payload) < 4:
        raise ValueError("Framed payload too short for length prefix")

    length = int.from_bytes(packet.payload[:4], byteorder='big')
    content = packet.payload[4:]

    if len(content) != length:
        raise ValueError(f"Length mismatch: declared {length}, actual {len(content)}")

    return content
