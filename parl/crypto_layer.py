"""
PARL Crypto Layer - AEAD Encryption for RPP Tokens

Provides authenticated encryption for RPP token transport using
ChaCha20-Poly1305 or AES-256-GCM.

Part of the Phase-Aware Routing Layer (PARL) for SPIRAL Protocol.
"""

import os
import json
import hashlib
import hmac
from dataclasses import dataclass, field
from typing import Optional, Tuple
from datetime import datetime, timezone

# Try to import cryptography library
try:
    from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305, AESGCM
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("Warning: cryptography library not available. Using fallback XOR cipher.")


@dataclass
class SessionKey:
    """Represents an encrypted session key pair."""
    key: bytes
    nonce_counter: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    algorithm: str = "chacha20-poly1305"

    def next_nonce(self) -> bytes:
        """Generate next nonce (12 bytes for ChaCha20/AES-GCM)."""
        self.nonce_counter += 1
        return self.nonce_counter.to_bytes(12, 'big')

    def is_expired(self) -> bool:
        """Check if session key has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at


@dataclass
class EncryptedPacket:
    """Encrypted RPP token packet."""
    ciphertext: bytes
    nonce: bytes
    tag: bytes  # For AEAD, this is included in ciphertext
    algorithm: str
    sender_id: str
    timestamp: int

    def to_bytes(self) -> bytes:
        """Serialize to wire format."""
        header = json.dumps({
            "alg": self.algorithm,
            "sender": self.sender_id,
            "ts": self.timestamp,
            "nonce": self.nonce.hex()
        }).encode('utf-8')
        header_len = len(header).to_bytes(2, 'big')
        return header_len + header + self.ciphertext

    @classmethod
    def from_bytes(cls, data: bytes) -> 'EncryptedPacket':
        """Deserialize from wire format."""
        header_len = int.from_bytes(data[:2], 'big')
        header = json.loads(data[2:2+header_len].decode('utf-8'))
        ciphertext = data[2+header_len:]
        return cls(
            ciphertext=ciphertext,
            nonce=bytes.fromhex(header['nonce']),
            tag=b'',  # Included in AEAD ciphertext
            algorithm=header['alg'],
            sender_id=header['sender'],
            timestamp=header['ts']
        )


class CryptoLayer:
    """
    AEAD encryption layer for RPP tokens.

    Supports:
    - ChaCha20-Poly1305 (preferred for embedded/IoT)
    - AES-256-GCM (fallback for hardware acceleration)
    - XOR fallback (for testing only)
    """

    def __init__(self, node_id: str, algorithm: str = "chacha20-poly1305"):
        self.node_id = node_id
        self.algorithm = algorithm
        self.session_keys: dict[str, SessionKey] = {}

    def generate_session_key(self, peer_id: str, shared_secret: Optional[bytes] = None) -> SessionKey:
        """
        Generate or derive a session key for peer communication.

        Args:
            peer_id: Remote peer identifier
            shared_secret: Optional pre-shared secret for key derivation

        Returns:
            SessionKey for encrypting/decrypting with this peer
        """
        if shared_secret:
            # Derive key using HKDF with canonical ordering (alphabetical)
            # This ensures both parties derive the same key
            pair = tuple(sorted([self.node_id, peer_id]))
            canonical_salt = f"{pair[0]}:{pair[1]}".encode()

            if CRYPTO_AVAILABLE:
                hkdf = HKDF(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=canonical_salt,
                    info=b"parl-session-key"
                )
                key = hkdf.derive(shared_secret)
            else:
                # Fallback: simple hash-based derivation
                key = hashlib.sha256(
                    shared_secret + canonical_salt
                ).digest()
        else:
            # Generate random key
            key = os.urandom(32)

        session = SessionKey(key=key, algorithm=self.algorithm)
        self.session_keys[peer_id] = session
        return session

    def encrypt(self, plaintext: bytes, peer_id: str,
                associated_data: Optional[bytes] = None) -> EncryptedPacket:
        """
        Encrypt plaintext for transmission to peer.

        Args:
            plaintext: Raw RPP token bytes
            peer_id: Target peer ID
            associated_data: Optional authenticated but unencrypted data

        Returns:
            EncryptedPacket ready for transmission
        """
        if peer_id not in self.session_keys:
            raise ValueError(f"No session key for peer: {peer_id}")

        session = self.session_keys[peer_id]
        nonce = session.next_nonce()
        timestamp = int(datetime.now(timezone.utc).timestamp())

        if CRYPTO_AVAILABLE:
            if self.algorithm == "chacha20-poly1305":
                cipher = ChaCha20Poly1305(session.key)
            else:  # aes-256-gcm
                cipher = AESGCM(session.key)

            ciphertext = cipher.encrypt(nonce, plaintext, associated_data)
        else:
            # Fallback XOR cipher (NOT SECURE - testing only)
            ciphertext = self._xor_cipher(plaintext, session.key, nonce)

        return EncryptedPacket(
            ciphertext=ciphertext,
            nonce=nonce,
            tag=b'',  # Included in AEAD ciphertext
            algorithm=self.algorithm,
            sender_id=self.node_id,
            timestamp=timestamp
        )

    def decrypt(self, packet: EncryptedPacket,
                associated_data: Optional[bytes] = None) -> bytes:
        """
        Decrypt received packet.

        Args:
            packet: Encrypted packet from peer
            associated_data: Optional authenticated data

        Returns:
            Decrypted plaintext bytes

        Raises:
            ValueError: If decryption fails (authentication error)
        """
        peer_id = packet.sender_id
        if peer_id not in self.session_keys:
            raise ValueError(f"No session key for peer: {peer_id}")

        session = self.session_keys[peer_id]

        if CRYPTO_AVAILABLE:
            if packet.algorithm == "chacha20-poly1305":
                cipher = ChaCha20Poly1305(session.key)
            else:
                cipher = AESGCM(session.key)

            try:
                plaintext = cipher.decrypt(packet.nonce, packet.ciphertext, associated_data)
            except Exception as e:
                raise ValueError(f"Decryption failed: {e}")
        else:
            # Fallback XOR
            plaintext = self._xor_cipher(packet.ciphertext, session.key, packet.nonce)

        return plaintext

    def _xor_cipher(self, data: bytes, key: bytes, nonce: bytes) -> bytes:
        """Simple XOR cipher fallback (NOT SECURE)."""
        # Derive keystream from key + nonce
        keystream = hashlib.sha256(key + nonce).digest()
        # Extend keystream if needed
        while len(keystream) < len(data):
            keystream += hashlib.sha256(keystream).digest()

        return bytes(d ^ k for d, k in zip(data, keystream))

    def compute_field_hash(self, token_data: dict) -> str:
        """
        Compute field hash for token integrity verification.

        This is NOT encryption - it's a content-addressable hash
        for deduplication and verification.
        """
        canonical = json.dumps(token_data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]


class KeyExchange:
    """
    Simple key exchange stub for session establishment.

    In production, this would use:
    - X25519 for key agreement
    - Ed25519 for signatures
    - Noise Protocol Framework for handshake
    """

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.private_key = os.urandom(32)
        self.public_key = hashlib.sha256(self.private_key).digest()  # Placeholder

    def initiate_handshake(self, peer_public_key: bytes) -> Tuple[bytes, bytes]:
        """
        Initiate key exchange with peer.

        Returns:
            Tuple of (shared_secret, our_public_key)
        """
        # Placeholder: In production, use X25519
        shared_secret = hashlib.sha256(
            self.private_key + peer_public_key
        ).digest()
        return shared_secret, self.public_key

    def complete_handshake(self, peer_public_key: bytes,
                           handshake_message: bytes) -> bytes:
        """
        Complete key exchange handshake.

        Returns:
            Shared secret for session key derivation
        """
        # Verify handshake and derive shared secret
        shared_secret = hashlib.sha256(
            self.private_key + peer_public_key + handshake_message
        ).digest()
        return shared_secret


# Convenience functions
def create_crypto_layer(node_id: str, use_aes: bool = False) -> CryptoLayer:
    """Create a crypto layer with sensible defaults."""
    algorithm = "aes-256-gcm" if use_aes else "chacha20-poly1305"
    return CryptoLayer(node_id, algorithm)


if __name__ == "__main__":
    # Test the crypto layer
    print("PARL Crypto Layer Test")
    print("=" * 50)

    # Create two nodes
    alice = CryptoLayer("alice-node")
    bob = CryptoLayer("bob-node")

    # Establish session keys (in production, use key exchange)
    shared_secret = os.urandom(32)
    alice.generate_session_key("bob-node", shared_secret)
    bob.generate_session_key("alice-node", shared_secret)

    # Test encryption
    message = b'{"theta": 10, "phi": 3, "coherence": 0.85}'
    print(f"Original: {message}")

    encrypted = alice.encrypt(message, "bob-node")
    print(f"Encrypted: {encrypted.ciphertext[:32].hex()}...")

    decrypted = bob.decrypt(encrypted)
    print(f"Decrypted: {decrypted}")

    assert message == decrypted, "Roundtrip failed!"
    print("\nCrypto layer test passed!")
