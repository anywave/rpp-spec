"""
PARL - Phase-Aware Routing Layer

A decentralized mesh routing system for RPP (Rotational Phase Protocol) tokens
implementing the SPIRAL protocol's phase-coherent networking layer.

Components:
- phase_router: Main routing daemon
- rpp_token_encoder: RPP token encoding/decoding
- crypto_layer: AEAD encryption (ChaCha20-Poly1305 / AES-256-GCM)
- simulate_mesh: Test harness for mesh simulation

RPPv0.9-beta Protocol Implementation
"""

__version__ = "0.9.0-beta"
__protocol__ = "RPPv0.9-beta"

from .rpp_token_encoder import RPPToken, RPPTokenEncoder, Role
from .crypto_layer import CryptoLayer, EncryptedPacket, SessionKey, create_crypto_layer
from .phase_router import PhaseRouter, FieldState, Neighbor, DropPolicy, ForwardMode

__all__ = [
    # Token encoding
    "RPPToken",
    "RPPTokenEncoder",
    "Role",
    # Crypto
    "CryptoLayer",
    "EncryptedPacket",
    "SessionKey",
    "create_crypto_layer",
    # Router
    "PhaseRouter",
    "FieldState",
    "Neighbor",
    "DropPolicy",
    "ForwardMode",
]
