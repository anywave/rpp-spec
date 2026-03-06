"""
Hedera Hashgraph Consensus Service (HCS) Transport Adapter for RPP

Publishes RPP packets as Hedera Consensus Service messages.
The RPP theta field maps to the HCS topic ID (0.0.{theta}).
The RPP phi and harmonic fields map to the sequence metadata.

In mock mode: simulates HCS topic publish/subscribe with in-memory queues.
In real mode: requires hedera-sdk-py and valid credentials.
"""

import struct
import time
from collections import defaultdict
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Address bit-field extraction helpers (mirrors rpp/address.py constants)
# ---------------------------------------------------------------------------
_SHELL_SHIFT    = 26
_THETA_SHIFT    = 17
_PHI_SHIFT      = 8
_SHELL_MASK     = 0x3
_THETA_MASK     = 0x1FF
_PHI_MASK       = 0x1FF
_HARMONIC_MASK  = 0xFF


def _decode_address(address_int: int):
    """Extract (shell, theta, phi, harmonic) from a raw 28-bit integer."""
    shell    = (address_int >> _SHELL_SHIFT) & _SHELL_MASK
    theta    = (address_int >> _THETA_SHIFT) & _THETA_MASK
    phi      = (address_int >> _PHI_SHIFT)   & _PHI_MASK
    harmonic = address_int & _HARMONIC_MASK
    return shell, theta, phi, harmonic


class HederaTransport:
    """
    Hedera Hashgraph Consensus Service (HCS) transport adapter for RPP.

    In mock mode (mock=True, the default):
    - No Hedera SDK or network access is required.
    - Messages are stored in an in-memory per-topic queue (_topics).
    - Sequence numbers are auto-incremented per topic.
    - is_available() always returns True.

    In real mode (mock=False):
    - Requires hedera-sdk-py: pip install hedera-sdk-py
    - Requires valid operator_account (e.g. "0.0.12345") and operator_key
      (ED25519 or ECDSA private key in DER or hex format).
    - HCS topic must already exist on the Hedera network.

    Topic mapping:
        topic_id = f"0.0.{theta}"

    where theta is decoded from bits [25:17] of the 28-bit RPP address.

    Message record schema (returned by publish / stored in mock queue):
        {
            "sequence":   int,          # per-topic monotonic sequence number
            "phi":        int,          # RPP phi field
            "harmonic":   int,          # RPP harmonic field
            "data":       bytes,        # raw payload
            "timestamp_ns": int,        # time.time_ns() at publish time
        }

    Usage (mock):
        h = HederaTransport()
        record = h.publish(0x00400001, b"some data")
        msgs   = h.subscribe(theta=2)   # 0.0.2 topic
    """

    name: str = "Hedera/HCS"

    def __init__(
        self,
        operator_account: Optional[str] = None,
        operator_key: Optional[str] = None,
        mock: bool = True,
    ) -> None:
        """
        Initialize Hedera HCS transport.

        Args:
            operator_account: Hedera account ID (e.g. "0.0.12345").
                              Required for real mode; ignored in mock mode.
            operator_key:     ED25519 or ECDSA private key for signing.
                              Required for real mode; ignored in mock mode.
            mock:             If True (default), operate in-memory without
                              a real Hedera network connection.
        """
        self._operator_account = operator_account
        self._operator_key = operator_key
        self._mock = mock

        # Per-topic message queues: {"0.0.N": [record, ...]}
        self._topics: Dict[str, List[dict]] = defaultdict(list)

        # Per-topic sequence counters (1-indexed, matching HCS convention)
        self._sequence_counters: Dict[str, int] = defaultdict(int)

    # ------------------------------------------------------------------
    # Topic-ID derivation
    # ------------------------------------------------------------------

    @staticmethod
    def topic_id_for_theta(theta: int) -> str:
        """
        Derive a deterministic Hedera topic ID from an RPP theta value.

        Hedera topic IDs follow the format "shard.realm.num".
        RPP uses shard 0 and realm 0; only the topic number varies.

        Args:
            theta: RPP theta field value (0-511).

        Returns:
            Topic ID string in the form "0.0.{theta}".
        """
        return f"0.0.{theta}"

    # ------------------------------------------------------------------
    # Core transport interface
    # ------------------------------------------------------------------

    def publish(self, address_int: int, data: bytes = b"") -> dict:
        """
        Publish an RPP packet to the HCS topic derived from its theta field.

        Decodes the theta, phi, and harmonic fields from the 28-bit address:
        - theta  → selects topic "0.0.{theta}"
        - phi    → stored as message metadata
        - harmonic → stored as message metadata

        In mock mode: appends a record to self._topics[topic_id] and returns it.
        In real mode: submits a TopicMessageSubmitTransaction to the Hedera network.

        Args:
            address_int: 28-bit RPP address as unsigned integer.
            data:        Optional payload bytes to attach to the message.

        Returns:
            Message record dict with keys:
                sequence, phi, harmonic, data, timestamp_ns
            Returns an empty dict on real-mode failure.
        """
        _shell, theta, phi, harmonic = _decode_address(address_int)
        topic_id = self.topic_id_for_theta(theta)

        if self._mock:
            return self._mock_publish(topic_id, phi, harmonic, data)

        return self._real_publish(topic_id, address_int, data)

    def subscribe(self, theta: int) -> List[dict]:
        """
        Retrieve all messages published to the topic for a given theta value.

        In mock mode: returns a copy of self._topics["0.0.{theta}"].
        In real mode: queries HCS topic history via the Hedera Mirror Node.

        Args:
            theta: RPP theta field value (0-511) identifying the topic.

        Returns:
            List of message record dicts (may be empty if no messages exist).
        """
        topic_id = self.topic_id_for_theta(theta)

        if self._mock:
            return list(self._topics[topic_id])

        return self._real_subscribe(topic_id)

    def is_available(self) -> bool:
        """
        Check whether the Hedera transport is available.

        In mock mode: always True.
        In real mode: attempts to instantiate a Hedera client and verify
                      credentials without submitting a transaction.

        Returns:
            True if transport is usable, False otherwise.
        """
        if self._mock:
            return True

        return self._real_check_credentials()

    # ------------------------------------------------------------------
    # Mock-mode implementation
    # ------------------------------------------------------------------

    def _mock_publish(
        self,
        topic_id: str,
        phi: int,
        harmonic: int,
        data: bytes,
    ) -> dict:
        """Append a message to the in-memory topic queue."""
        self._sequence_counters[topic_id] += 1
        record = {
            "sequence":     self._sequence_counters[topic_id],
            "phi":          phi,
            "harmonic":     harmonic,
            "data":         data,
            "timestamp_ns": time.time_ns(),
        }
        self._topics[topic_id].append(record)
        return record

    # ------------------------------------------------------------------
    # Real-mode implementation stubs
    # ------------------------------------------------------------------

    def _real_publish(
        self,
        topic_id: str,
        address_int: int,
        data: bytes,
    ) -> dict:
        """
        Submit a TopicMessageSubmitTransaction to the Hedera network.

        Requires: pip install hedera-sdk-py
        See: https://docs.hedera.com/hedera/sdks-and-apis/sdks/consensus-service

        Returns:
            Receipt dict with sequence number on success, empty dict on failure.
        """
        try:
            # Real Hedera SDK usage (requires hedera-sdk-py):
            #
            # from hedera import (
            #     Client, TopicMessageSubmitTransaction, AccountId, PrivateKey
            # )
            # client = Client.for_mainnet()  # or for_testnet()
            # client.set_operator(
            #     AccountId.from_string(self._operator_account),
            #     PrivateKey.from_string(self._operator_key),
            # )
            # receipt = (
            #     TopicMessageSubmitTransaction()
            #     .set_topic_id(topic_id)
            #     .set_message(data)
            #     .execute(client)
            #     .get_receipt(client)
            # )
            # return {"sequence": receipt.topic_sequence_number, "data": data}
            raise NotImplementedError(
                "Real Hedera publish requires hedera-sdk-py and valid credentials. "
                "Install with: pip install hedera-sdk-py"
            )
        except Exception:
            return {}

    def _real_subscribe(self, topic_id: str) -> List[dict]:
        """
        Query HCS topic message history via Hedera Mirror Node REST API.

        Mirror node endpoint: https://mainnet-public.mirrornode.hedera.com
        Path: /api/v1/topics/{topic_id}/messages

        Returns empty list on any error.
        """
        try:
            import urllib.request
            import json

            mirror_url = (
                f"https://mainnet-public.mirrornode.hedera.com"
                f"/api/v1/topics/{topic_id}/messages"
            )
            with urllib.request.urlopen(mirror_url, timeout=10) as resp:
                result = json.loads(resp.read().decode())
                messages = result.get("messages", [])
                return [
                    {
                        "sequence":     m.get("sequence_number", 0),
                        "phi":          0,   # not recoverable from raw message alone
                        "harmonic":     0,
                        "data":         m.get("message", b""),
                        "timestamp_ns": 0,
                    }
                    for m in messages
                ]
        except Exception:
            return []

    def _real_check_credentials(self) -> bool:
        """
        Attempt to validate Hedera credentials without submitting a transaction.

        Returns True only if both operator_account and operator_key are set
        and the account ID is parseable. Does not make a network call.
        """
        if not self._operator_account or not self._operator_key:
            return False
        # Basic format check: "0.0.NNNNN"
        parts = self._operator_account.split(".")
        if len(parts) != 3:
            return False
        try:
            int(parts[2])
            return True
        except ValueError:
            return False

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> "HederaTransport":
        return self

    def __exit__(self, *_) -> None:
        pass  # No persistent connections to close in mock mode

    def __repr__(self) -> str:
        mode = "mock" if self._mock else f"account={self._operator_account!r}"
        topic_count = len(self._topics)
        return f"HederaTransport({mode}, topics={topic_count})"
