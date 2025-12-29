# RPP Mesh Crypto Utilities
# Encryption and compression for mesh payloads

import hashlib
import struct
import zlib
from typing import Tuple


# Simple XOR-based encryption (placeholder for real crypto)
# In production, use NaCl/libsodium or similar

def derive_key(soul_key: bytes, salt: bytes = b"rpp-mesh") -> bytes:
    """Derive 32-byte encryption key from soul key."""
    return hashlib.pbkdf2_hmac('sha256', soul_key, salt, 10000)


def encrypt_payload(payload: bytes, key: bytes) -> bytes:
    """
    Encrypt payload with key.

    Format: [8-byte nonce][encrypted data]
    """
    import secrets
    nonce = secrets.token_bytes(8)

    # Simple ChaCha20-like stream cipher (placeholder)
    # In production, use nacl.secret.SecretBox
    stream = _generate_stream(key, nonce, len(payload))
    encrypted = bytes(p ^ s for p, s in zip(payload, stream))

    return nonce + encrypted


def decrypt_payload(encrypted: bytes, key: bytes) -> bytes:
    """
    Decrypt payload with key.

    Expects: [8-byte nonce][encrypted data]
    """
    if len(encrypted) < 8:
        raise ValueError("Encrypted data too short")

    nonce = encrypted[:8]
    ciphertext = encrypted[8:]

    stream = _generate_stream(key, nonce, len(ciphertext))
    decrypted = bytes(c ^ s for c, s in zip(ciphertext, stream))

    return decrypted


def _generate_stream(key: bytes, nonce: bytes, length: int) -> bytes:
    """Generate keystream for encryption."""
    stream = b""
    counter = 0

    while len(stream) < length:
        block_input = key + nonce + struct.pack(">Q", counter)
        block = hashlib.sha256(block_input).digest()
        stream += block
        counter += 1

    return stream[:length]


def compress_payload(payload: bytes) -> bytes:
    """
    Compress payload using zlib.

    Format: [4-byte original length][compressed data]
    """
    compressed = zlib.compress(payload, level=6)

    # Only use compression if it actually reduces size
    if len(compressed) + 4 >= len(payload):
        # Return original with length=0 to indicate no compression
        return struct.pack(">I", 0) + payload

    return struct.pack(">I", len(payload)) + compressed


def decompress_payload(data: bytes) -> bytes:
    """
    Decompress payload.

    Expects: [4-byte original length][compressed data]
    Original length of 0 means data is not compressed.
    """
    if len(data) < 4:
        raise ValueError("Compressed data too short")

    original_length = struct.unpack(">I", data[:4])[0]

    if original_length == 0:
        # Data was not compressed
        return data[4:]

    return zlib.decompress(data[4:])


def compute_hmac(key: bytes, data: bytes) -> bytes:
    """Compute 16-byte HMAC for integrity verification."""
    import hmac
    h = hmac.new(key, data, hashlib.sha256)
    return h.digest()[:16]


def verify_hmac(key: bytes, data: bytes, expected: bytes) -> bool:
    """Verify HMAC tag."""
    import hmac
    computed = compute_hmac(key, data)
    return hmac.compare_digest(computed, expected)
