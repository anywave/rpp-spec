"""
RPP Backend Adapters

Adapters provide the bridge between RPP addresses and actual storage backends
or network transport substrates. The resolver selects storage adapters based
on shell value; transport adapters are chosen by the application layer.

Storage adapters implement: read(path), write(path, data), delete(path),
                            exists(path), is_available()

Transport adapters implement a distinct send/receive interface appropriate
to their underlying network substrate. They do NOT share the storage interface.
"""

# Storage adapters
from rpp.adapters.memory import MemoryAdapter
from rpp.adapters.filesystem import FilesystemAdapter

# Transport adapters (send/receive RPP packets over network substrates)
from rpp.adapters.udp import UDPTransport
from rpp.adapters.lora import LoRaTransport
from rpp.adapters.ipfs import IPFSTransport
from rpp.adapters.hedera import HederaTransport

__all__ = [
    "MemoryAdapter",
    "FilesystemAdapter",
    "UDPTransport",
    "LoRaTransport",
    "IPFSTransport",
    "HederaTransport",
]
