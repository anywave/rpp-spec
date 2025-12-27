"""
Filesystem Backend Adapter

A local filesystem storage backend.
Uses pathlib for cross-platform compatibility (Windows, Linux, macOS).
"""

from pathlib import Path
from typing import Optional


class FilesystemAdapter:
    """
    Filesystem storage adapter.

    Suitable for:
    - Shell 1 (Warm tier)
    - Local development
    - Persistent storage

    Uses pathlib for Windows/Linux/macOS compatibility.
    """

    name: str = "filesystem"

    def __init__(self, base_path: Optional[str] = None) -> None:
        """
        Initialize filesystem adapter.

        Args:
            base_path: Base directory for storage. If None, uses temp directory.
        """
        if base_path is None:
            # Use a cross-platform temp location
            import tempfile
            self._base = Path(tempfile.gettempdir()) / "rpp_storage"
        else:
            self._base = Path(base_path)

        # Ensure base directory exists
        self._base.mkdir(parents=True, exist_ok=True)

    @property
    def base_path(self) -> Path:
        """Return the base storage path."""
        return self._base

    def _resolve_path(self, path: str) -> Path:
        """Resolve a path relative to base."""
        # Normalize path separators
        normalized = path.replace("\\", "/")
        # Remove leading slashes
        normalized = normalized.lstrip("/")
        return self._base / normalized

    def read(self, path: str) -> Optional[bytes]:
        """
        Read data from filesystem.

        Args:
            path: Storage path (relative to base)

        Returns:
            Data bytes if found, None otherwise
        """
        full_path = self._resolve_path(path)
        if not full_path.exists():
            return None
        try:
            return full_path.read_bytes()
        except (OSError, IOError):
            return None

    def write(self, path: str, data: bytes) -> bool:
        """
        Write data to filesystem.

        Args:
            path: Storage path (relative to base)
            data: Data to store

        Returns:
            True on success, False on failure
        """
        full_path = self._resolve_path(path)
        try:
            # Ensure parent directories exist
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_bytes(data)
            return True
        except (OSError, IOError):
            return False

    def delete(self, path: str) -> bool:
        """
        Delete data from filesystem.

        Args:
            path: Storage path (relative to base)

        Returns:
            True if deleted, False if not found or error
        """
        full_path = self._resolve_path(path)
        if not full_path.exists():
            return False
        try:
            full_path.unlink()
            return True
        except (OSError, IOError):
            return False

    def exists(self, path: str) -> bool:
        """
        Check if path exists.

        Args:
            path: Storage path (relative to base)

        Returns:
            True if exists
        """
        return self._resolve_path(path).exists()

    def is_available(self) -> bool:
        """Check if adapter is available (base path exists and is writable)."""
        try:
            return self._base.exists() and self._base.is_dir()
        except (OSError, IOError):
            return False

    def list_paths(self, pattern: str = "**/*") -> list:
        """
        List stored paths matching pattern.

        Args:
            pattern: Glob pattern (default: all files)

        Returns:
            List of relative path strings
        """
        try:
            paths = []
            for p in self._base.glob(pattern):
                if p.is_file():
                    # Return path relative to base
                    rel_path = p.relative_to(self._base)
                    paths.append(str(rel_path))
            return paths
        except (OSError, IOError):
            return []
