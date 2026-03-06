"""
IPFS Content-Addressed Transport Adapter for RPP

Stores RPP packets as IPFS objects using the HTTP API.
The RPP address maps to an IPFS CID — content-addressed by the data,
routed by the RPP phi/theta/shell semantics.

In mock mode (no IPFS daemon): uses an in-memory dict keyed by simulated CID.
In real mode: requires running IPFS daemon at http://127.0.0.1:5001.
"""

import base64
import struct
from typing import Dict, Optional


class IPFSTransport:
    """
    IPFS content-addressed transport adapter for RPP.

    In mock mode (mock=True, the default):
    - No IPFS daemon or network access is required.
    - Data is stored in an in-memory dict (_store) keyed by deterministic CIDs.
    - is_available() always returns True.

    In real mode (mock=False):
    - Requires a running IPFS daemon at the configured api_url.
    - Uses the IPFS HTTP API v0: /api/v0/add and /api/v0/cat.
    - Requires urllib (stdlib) — no third-party libraries needed.

    CID derivation (mock):
        cid = "bafyrei" + base32(struct.pack(">I", address_int)).lower().rstrip("=")

    This produces a deterministic, unique-per-address identifier that is
    structurally similar to real IPFS CIDv1 strings (bafyrei... prefix).

    Usage:
        ipfs = IPFSTransport()                    # mock mode
        cid  = ipfs.add(0x01234567, b"payload")
        data = ipfs.cat(cid)
        cid2 = ipfs.resolve_address(0x01234567)   # same as cid
    """

    name: str = "IPFS"

    def __init__(
        self,
        api_url: str = "http://127.0.0.1:5001",
        mock: bool = True,
    ) -> None:
        """
        Initialize IPFS transport.

        Args:
            api_url: Base URL of the IPFS HTTP API daemon.
                     Only used when mock=False.
            mock:    If True (default), operate entirely in-memory without
                     a real IPFS daemon.
        """
        self._api_url = api_url.rstrip("/")
        self._mock = mock

        # In-memory content store for mock mode: {cid: bytes}
        self._store: Dict[str, bytes] = {}

    # ------------------------------------------------------------------
    # CID derivation
    # ------------------------------------------------------------------

    @staticmethod
    def _rpp_to_cid(address_int: int) -> str:
        """
        Derive a deterministic mock CID from a 28-bit RPP address.

        Format:
            "bafyrei" + base32(4-byte big-endian address).lower().rstrip("=")

        This mirrors the CIDv1 bafyrei... prefix used by real IPFS for
        raw-leaf sha2-256 content identifiers, making mock CIDs easy to
        recognize while remaining structurally plausible.

        Args:
            address_int: 28-bit RPP address as unsigned integer.

        Returns:
            Deterministic CID string.
        """
        packed = struct.pack(">I", address_int)
        b32 = base64.b32encode(packed).decode().lower().rstrip("=")
        return "bafyrei" + b32

    # ------------------------------------------------------------------
    # Core transport interface
    # ------------------------------------------------------------------

    def add(self, address_int: int, data: bytes) -> str:
        """
        Store data under the CID derived from the RPP address.

        In mock mode: stores data in self._store[cid] and returns the CID.
        In real mode: POSTs data to /api/v0/add and returns the IPFS CID.

        Args:
            address_int: 28-bit RPP address used to derive the CID.
            data:        Raw bytes to store.

        Returns:
            CID string (mock: deterministic; real: sha2-256 content hash).
        """
        if self._mock:
            cid = self._rpp_to_cid(address_int)
            self._store[cid] = data
            return cid

        return self._real_add(address_int, data)

    def cat(self, cid: str) -> Optional[bytes]:
        """
        Retrieve data by CID.

        In mock mode: looks up self._store[cid], returns None if missing.
        In real mode: POSTs to /api/v0/cat?arg=<cid>.

        Args:
            cid: IPFS content identifier string.

        Returns:
            Stored bytes, or None if not found / on error.
        """
        if self._mock:
            return self._store.get(cid)

        return self._real_cat(cid)

    def resolve_address(self, address_int: int) -> Optional[str]:
        """
        Look up whether the given RPP address has data stored in IPFS.

        Derives the deterministic CID from the address and checks whether
        it exists in the store.

        Args:
            address_int: 28-bit RPP address as unsigned integer.

        Returns:
            The CID string if data exists for this address, None otherwise.
        """
        cid = self._rpp_to_cid(address_int)
        if self._mock:
            return cid if cid in self._store else None

        # In real mode, attempt to retrieve; if it returns data, address is resolved
        data = self._real_cat(cid)
        return cid if data is not None else None

    def is_available(self) -> bool:
        """
        Check whether the IPFS transport is available.

        In mock mode: always True.
        In real mode: GETs /api/v0/version and checks for a 200 response.

        Returns:
            True if available, False otherwise.
        """
        if self._mock:
            return True

        return self._real_check_version()

    # ------------------------------------------------------------------
    # Real-mode HTTP helpers (stdlib urllib only)
    # ------------------------------------------------------------------

    def _real_add(self, address_int: int, data: bytes) -> str:
        """
        POST data to IPFS daemon /api/v0/add and return the resulting CID.

        Uses multipart/form-data encoding (stdlib urllib.request).
        Falls back to the mock CID on any error.
        """
        import urllib.request
        import urllib.error
        import json

        boundary = "rpp_ipfs_boundary"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="rpp"\r\n'
            f"Content-Type: application/octet-stream\r\n\r\n"
        ).encode() + data + f"\r\n--{boundary}--\r\n".encode()

        url = f"{self._api_url}/api/v0/add"
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}"
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode())
                return result.get("Hash", self._rpp_to_cid(address_int))
        except Exception:
            # Daemon unavailable — fall back to deterministic mock CID
            return self._rpp_to_cid(address_int)

    def _real_cat(self, cid: str) -> Optional[bytes]:
        """
        POST to IPFS daemon /api/v0/cat?arg=<cid> and return raw bytes.

        Returns None on any error.
        """
        import urllib.request
        import urllib.error

        url = f"{self._api_url}/api/v0/cat?arg={cid}"
        req = urllib.request.Request(url, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.read()
        except Exception:
            return None

    def _real_check_version(self) -> bool:
        """
        GET /api/v0/version to verify IPFS daemon is reachable.

        Returns True if daemon responds with HTTP 200, False otherwise.
        """
        import urllib.request
        import urllib.error

        url = f"{self._api_url}/api/v0/version"
        req = urllib.request.Request(url, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=3) as resp:
                return resp.status == 200
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> "IPFSTransport":
        return self

    def __exit__(self, *_) -> None:
        pass  # No persistent connections to close

    def __repr__(self) -> str:
        mode = "mock" if self._mock else f"api={self._api_url!r}"
        return f"IPFSTransport({mode}, store_size={len(self._store)})"
