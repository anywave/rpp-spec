"""
RPP Backend Adapters

Adapters provide the bridge between RPP addresses and actual storage backends.
The resolver selects adapters based on shell value.
"""

from rpp.adapters.memory import MemoryAdapter
from rpp.adapters.filesystem import FilesystemAdapter

__all__ = [
    "MemoryAdapter",
    "FilesystemAdapter",
]
