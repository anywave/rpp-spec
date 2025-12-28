"""
RPP Mesh - Consent-Aware Overlay Network for RPP

An optional extension to RPP that provides consent-aware routing
at the network level. Mesh nodes inspect RPP headers and enforce
ACSP consent states before packets reach their destination.

Features:
- Geometric routing by theta/phi sectors
- Consent enforcement at relay nodes
- Coherence-aware prioritization
- Fragment quarantine support

RPP Mesh IS:
- An overlay network extension to RPP
- A consent gate implementation
- A transport layer for AVACHATTER

RPP Mesh IS NOT:
- Required for basic RPP usage
- A replacement for the core RPP protocol
- A standalone networking solution
"""

__version__ = "0.1.0"

from rpp_mesh.transport import (
    ConsentState,
    MeshFlags,
    RPPMeshHeader,
    RPPMeshPacket,
    RPPMeshTransport,
    ConsentGate,
)

from rpp_mesh.config import (
    DeploymentMode,
    DirectConfig,
    VPNConfig,
    RPPMeshConfig,
    DeploymentConfig,
    load_config,
    DEVELOPMENT_CONFIG,
    STAGING_CONFIG,
    PRODUCTION_CONFIG,
)

__all__ = [
    # Version
    "__version__",
    # Transport
    "ConsentState",
    "MeshFlags",
    "RPPMeshHeader",
    "RPPMeshPacket",
    "RPPMeshTransport",
    "ConsentGate",
    # Config
    "DeploymentMode",
    "DirectConfig",
    "VPNConfig",
    "RPPMeshConfig",
    "DeploymentConfig",
    "load_config",
    "DEVELOPMENT_CONFIG",
    "STAGING_CONFIG",
    "PRODUCTION_CONFIG",
]
