# RPP Direct Transport
# Fallback transport for when mesh is unavailable

import asyncio
import struct
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class DirectTransport:
    """
    Direct point-to-point transport.

    Used as fallback when mesh is unavailable.
    Connects directly to known endpoints.
    """

    def __init__(self, config):
        self.config = config
        self.direct_endpoints = getattr(config, 'direct_endpoints', [])
        self._connection: Optional[tuple] = None

    async def connect(self, endpoint: Optional[str] = None):
        """Establish direct connection to endpoint."""
        target = endpoint or (self.direct_endpoints[0] if self.direct_endpoints else None)

        if not target:
            raise ConnectionError("No direct endpoint available")

        host, port = target.rsplit(":", 1)
        reader, writer = await asyncio.open_connection(host, int(port))
        self._connection = (reader, writer)
        logger.info(f"Direct connection established to {target}")

    async def disconnect(self):
        """Close direct connection."""
        if self._connection:
            _, writer = self._connection
            writer.close()
            await writer.wait_closed()
            self._connection = None

    async def send(self, rpp_address: int, payload: bytes, timeout: float = 30.0) -> bytes:
        """
        Send payload directly to endpoint.

        Args:
            rpp_address: Target RPP address
            payload: Data to send
            timeout: Response timeout in seconds

        Returns:
            Response payload bytes
        """
        if not self._connection:
            await self.connect()

        reader, writer = self._connection

        # Simple framing: [4-byte length][4-byte address][payload]
        message = struct.pack(">II", rpp_address, len(payload)) + payload

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
            return response
        except asyncio.TimeoutError:
            logger.warning("Direct transport timeout")
            raise
