# AVACHATTER Deployment Configuration
# deployment_config.py

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional

class DeploymentMode(Enum):
    """Available deployment modes for AVACHATTER fragment routing."""
    DIRECT = "direct"          # HTTPS/WSS direct to Portal Hosts
    VPN = "vpn"                # Standard VPN tunnel (WireGuard/Tailscale)
    RPP_MESH = "rpp_mesh"      # Consent-aware overlay network


@dataclass
class DirectConfig:
    """Configuration for direct deployment mode."""
    portal_hosts: List[str] = field(default_factory=lambda: [
        "portal-1.avachatter.net:443",
        "portal-2.avachatter.net:443",
    ])
    use_tls: bool = True
    retry_attempts: int = 3
    timeout_seconds: float = 30.0


@dataclass
class VPNConfig:
    """Configuration for VPN deployment mode."""
    provider: str = "wireguard"  # wireguard, tailscale, openvpn
    config_path: str = "/etc/wireguard/avachatter.conf"
    portal_hosts: List[str] = field(default_factory=lambda: [
        "10.100.0.10:443",  # VPN-internal IPs
        "10.100.0.11:443",
    ])
    fallback_to_direct: bool = True


@dataclass
class RPPMeshConfig:
    """Configuration for RPP Mesh consent-aware overlay."""
    
    # Ingress nodes (entry points to mesh)
    ingress_nodes: List[str] = field(default_factory=lambda: [
        "mesh-ingress-1.avachatter.net:7700",
        "mesh-ingress-2.avachatter.net:7700",
    ])
    
    # HNC consent state stream
    consent_update_endpoint: str = "wss://hnc.avachatter.net/consent-stream"
    
    # Soul identity
    soul_key_path: str = "/etc/avachatter/soul.key"
    soul_id_truncate_bits: int = 16
    
    # Mesh behavior
    consent_cache_ttl_seconds: int = 30
    max_hop_count: int = 8
    sector_ttl: int = 4  # Max sector boundary crossings
    
    # Packet settings
    encrypt_payload: bool = True
    compress_payload: bool = False
    
    # Fallback
    fallback_mode: str = "direct"  # direct, vpn, or fail
    fallback_on_mesh_timeout_seconds: float = 5.0
    
    # Observability
    log_routing_decisions: bool = True
    scl_endpoint: Optional[str] = "https://scl.avachatter.net/log"


@dataclass 
class DeploymentConfig:
    """Master deployment configuration."""
    
    mode: DeploymentMode = DeploymentMode.DIRECT
    
    direct: DirectConfig = field(default_factory=DirectConfig)
    vpn: VPNConfig = field(default_factory=VPNConfig)
    rpp_mesh: RPPMeshConfig = field(default_factory=RPPMeshConfig)
    
    # Common settings
    fragment_timeout_seconds: float = 60.0
    max_payload_bytes: int = 1024 * 1024  # 1MB
    
    def get_active_config(self):
        """Return config for current deployment mode."""
        if self.mode == DeploymentMode.DIRECT:
            return self.direct
        elif self.mode == DeploymentMode.VPN:
            return self.vpn
        elif self.mode == DeploymentMode.RPP_MESH:
            return self.rpp_mesh
        raise ValueError(f"Unknown deployment mode: {self.mode}")


# Default configurations for different environments

DEVELOPMENT_CONFIG = DeploymentConfig(
    mode=DeploymentMode.DIRECT,
    direct=DirectConfig(
        portal_hosts=["localhost:8080"],
        use_tls=False,
    )
)

STAGING_CONFIG = DeploymentConfig(
    mode=DeploymentMode.VPN,
    vpn=VPNConfig(
        provider="tailscale",
        config_path="",  # Tailscale manages this
        portal_hosts=["staging-portal.tail1234.ts.net:443"],
    )
)

PRODUCTION_CONFIG = DeploymentConfig(
    mode=DeploymentMode.RPP_MESH,
    rpp_mesh=RPPMeshConfig(
        ingress_nodes=[
            "mesh-us-east.avachatter.net:7700",
            "mesh-us-west.avachatter.net:7700",
            "mesh-eu-west.avachatter.net:7700",
        ],
        consent_update_endpoint="wss://hnc.avachatter.net/consent-stream",
        fallback_mode="vpn",
    ),
    vpn=VPNConfig(
        provider="wireguard",
        portal_hosts=["10.100.0.10:443", "10.100.0.11:443"],
    )
)


# Environment loader
def load_config(environment: str = "development") -> DeploymentConfig:
    """Load deployment config for environment."""
    configs = {
        "development": DEVELOPMENT_CONFIG,
        "staging": STAGING_CONFIG,
        "production": PRODUCTION_CONFIG,
    }
    return configs.get(environment, DEVELOPMENT_CONFIG)
