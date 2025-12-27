"""
In-Memory Backend Adapter

A simple in-memory storage backend for testing and hot-tier data.
No external dependencies.
"""

from typing import Dict, Optional


class MemoryAdapter:
    """
    In-memory storage adapter.

    Suitable for:
    - Shell 0 (Hot tier)
    - Testing
    - Ephemeral data

    Thread-safety: NOT thread-safe. Use external locking if needed.
    """

    name: str = "memory"

    def __init__(self) -> None:
        self._storage: Dict[str, bytes] = {}

    def read(self, path: str) -> Optional[bytes]:
        """
        Read data from memory.

        Args:
            path: Storage path

        Returns:
            Data bytes if found, None otherwise
        """
        return self._storage.get(path)

    def write(self, path: str, data: bytes) -> bool:
        """
        Write data to memory.

        Args:
            path: Storage path
            data: Data to store

        Returns:
            True on success
        """
        self._storage[path] = data
        return True

    def delete(self, path: str) -> bool:
        """
        Delete data from memory.

        Args:
            path: Storage path

        Returns:
            True if deleted, False if not found
        """
        if path in self._storage:
            del self._storage[path]
            return True
        return False

    def exists(self, path: str) -> bool:
        """
        Check if path exists.

        Args:
            path: Storage path

        Returns:
            True if exists
        """
        return path in self._storage

    def is_available(self) -> bool:
        """Check if adapter is available. Always True for memory."""
        return True

    def clear(self) -> None:
        """Clear all stored data."""
        self._storage.clear()

    def list_paths(self) -> list:
        """List all stored paths."""
        return list(self._storage.keys())

    def size(self) -> int:
        """Return number of stored items."""
        return len(self._storage)
