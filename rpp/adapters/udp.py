"""
UDP/IPv4 Transport Adapter for RPP

Sends RPP packets as 4-byte big-endian integers over UDP sockets.
The transport does not interpret the RPP address — it delivers the raw bytes.

This is a real implementation using stdlib socket module only.
No external dependencies.
"""

import socket
import struct
from typing import Tuple


class UDPTransport:
    """
    UDP/IPv4 transport adapter.

    Sends and receives RPP packets as UDP datagrams. The wire format is:
        [4 bytes big-endian address int] [N bytes payload]

    The transport is address-agnostic — it does not decode phi/theta/shell;
    it simply delivers the raw 32-bit integer and any trailing payload bytes.

    Usage (real network):
        t = UDPTransport("127.0.0.1", 9000)
        t.send(0x01234567, b"hello")
        addr_int, payload = t.receive()
        t.close()

    Usage (loopback test):
        sender   = UDPTransport("127.0.0.1", 9001)
        receiver = UDPTransport("0.0.0.0",   9001)
        receiver._sock.bind(("0.0.0.0", 9001))
        sender.send(0xABCD, b"data")
        print(receiver.receive())
    """

    name: str = "UDP/IPv4"

    def __init__(self, host: str, port: int, timeout: float = 1.0) -> None:
        """
        Initialize UDP transport.

        Args:
            host: Remote host for send(), or bind address for receive().
            port: UDP port number.
            timeout: Default socket timeout in seconds.
        """
        self._host = host
        self._port = port
        self._timeout = timeout
        self._sock: socket.socket = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM
        )
        self._sock.settimeout(timeout)

    # ------------------------------------------------------------------
    # Core transport interface
    # ------------------------------------------------------------------

    def send(self, address_int: int, payload: bytes = b"") -> bool:
        """
        Serialize and transmit an RPP address + payload as a UDP datagram.

        Wire format: struct.pack(">I", address_int) + payload
        The 4-byte big-endian address integer is always present;
        the payload is optional and may be empty.

        Args:
            address_int: 28-bit RPP address as an unsigned integer.
            payload:     Optional payload bytes to append.

        Returns:
            True on successful send, False on any socket error.
        """
        datagram = struct.pack(">I", address_int) + payload
        try:
            self._sock.sendto(datagram, (self._host, self._port))
            return True
        except (OSError, socket.error):
            return False

    def receive(self, timeout: float = 1.0) -> Tuple[int, bytes]:
        """
        Block waiting for a UDP datagram and unpack the RPP address.

        The first 4 bytes are interpreted as a big-endian unsigned int
        (the RPP address). Any remaining bytes are the payload.

        Args:
            timeout: How long to wait for a datagram (seconds).

        Returns:
            Tuple of (address_int, payload_bytes).
            Returns (0, b"") on timeout or socket error.

        Raises:
            Nothing — errors are absorbed and return the empty sentinel.
        """
        self._sock.settimeout(timeout)
        try:
            data, _addr = self._sock.recvfrom(65535)
        except (OSError, socket.timeout, socket.error):
            return (0, b"")

        if len(data) < 4:
            # Datagram too short to contain a valid address
            return (0, data)

        address_int = struct.unpack(">I", data[:4])[0]
        payload = data[4:]
        return (address_int, payload)

    def is_available(self) -> bool:
        """
        Check whether UDP networking is available on this host.

        Creates a temporary probe socket; returns False if the OS denies it.

        Returns:
            True if the network stack is accessible, False otherwise.
        """
        try:
            probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            probe.close()
            return True
        except (OSError, socket.error):
            return False

    def close(self) -> None:
        """
        Close the underlying UDP socket and release OS resources.

        Safe to call multiple times.
        """
        try:
            self._sock.close()
        except (OSError, socket.error):
            pass

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> "UDPTransport":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"UDPTransport(host={self._host!r}, port={self._port})"
