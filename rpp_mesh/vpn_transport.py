# RPP VPN Transport
# Secure fallback transport through VPN tunnel

import asyncio
import struct
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class VPNTransport:
    """
    VPN-based transport.

    Routes traffic through a secure VPN tunnel when mesh
    is unavailable but enhanced security is required.
    """

    def __init__(self, config):
        self.config = config
        self.vpn_gateway = getattr(config, 'vpn_gateway', None)
        self.vpn_credentials = getattr(config, 'vpn_credentials', None)
        self._connection: Optional[tuple] = None
        self._tunnel_established = False

    async def connect(self):
        """Establish VPN tunnel and connection."""
        if not self.vpn_gateway:
            raise ConnectionError("VPN gateway not configured")

        # VPN tunnel establishment would happen here
        # For now, we connect directly to the gateway
        host, port = self.vpn_gateway.rsplit(":", 1)

        try:
            reader, writer = await asyncio.open_connection(host, int(port))
            self._connection = (reader, writer)

            # Perform VPN handshake
            await self._establish_tunnel(writer, reader)
            self._tunnel_established = True

            logger.info(f"VPN tunnel established to {self.vpn_gateway}")

        except Exception as e:
            logger.error(f"VPN connection failed: {e}")
            raise ConnectionError(f"VPN tunnel failed: {e}")

    async def _establish_tunnel(self, writer, reader):
        """Perform VPN handshake protocol."""
        # Simplified handshake - real implementation would use proper VPN protocol
        handshake = b"RPP-VPN-HANDSHAKE-v1"
        writer.write(struct.pack(">I", len(handshake)) + handshake)
        await writer.drain()

        # Expect acknowledgment
        response_len = struct.unpack(">I", await reader.readexactly(4))[0]
        response = await reader.readexactly(response_len)

        if not response.startswith(b"RPP-VPN-ACK"):
            raise ConnectionError("VPN handshake failed")

    async def disconnect(self):
        """Close VPN tunnel."""
        if self._connection:
            _, writer = self._connection
            writer.close()
            await writer.wait_closed()
            self._connection = None
            self._tunnel_established = False
            logger.info("VPN tunnel closed")

    async def send(self, rpp_address: int, payload: bytes, timeout: float = 30.0) -> bytes:
        """
        Send payload through VPN tunnel.

        Args:
            rpp_address: Target RPP address
            payload: Data to send
            timeout: Response timeout in seconds

        Returns:
            Response payload bytes
        """
        if not self._tunnel_established:
            await self.connect()

        reader, writer = self._connection

        # Frame message with VPN header
        # [4-byte length][1-byte type][4-byte address][payload]
        message_type = 0x01  # Data message
        message = struct.pack(">BII", message_type, rpp_address, len(payload)) + payload

        writer.write(struct.pack(">I", len(message)) + message)
        await writer.drain()

        try:
            response_length = struct.unpack(
                ">I",
                await asyncio.wait_for(reader.readexactly(4), timeout)
            )[0]
            response = await asyncio.wait_for(
                reader.readexactly(response_length),
                timeout
            )

            # Strip VPN header from response
            if len(response) > 1:
                return response[1:]  # Skip type byte
            return response

        except asyncio.TimeoutError:
            logger.warning("VPN transport timeout")
            raise
