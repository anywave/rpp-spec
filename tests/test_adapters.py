"""
RPP Adapters Test Suite

Tests for the memory and filesystem adapters.
"""

import pytest
import tempfile
from pathlib import Path

from rpp.adapters.memory import MemoryAdapter
from rpp.adapters.filesystem import FilesystemAdapter


class TestMemoryAdapter:
    """Test the in-memory adapter."""

    def test_create_adapter(self):
        """Test creating adapter."""
        adapter = MemoryAdapter()
        assert adapter.name == "memory"

    def test_write_and_read(self):
        """Test writing and reading data."""
        adapter = MemoryAdapter()
        data = b"test data"

        assert adapter.write("test/path", data) is True
        assert adapter.read("test/path") == data

    def test_read_nonexistent(self):
        """Test reading nonexistent path."""
        adapter = MemoryAdapter()
        assert adapter.read("nonexistent") is None

    def test_exists(self):
        """Test exists check."""
        adapter = MemoryAdapter()
        adapter.write("test/path", b"data")

        assert adapter.exists("test/path") is True
        assert adapter.exists("nonexistent") is False

    def test_delete(self):
        """Test deleting data."""
        adapter = MemoryAdapter()
        adapter.write("test/path", b"data")

        assert adapter.delete("test/path") is True
        assert adapter.exists("test/path") is False
        assert adapter.delete("test/path") is False  # Already deleted

    def test_is_available(self):
        """Test availability check."""
        adapter = MemoryAdapter()
        assert adapter.is_available() is True

    def test_clear(self):
        """Test clearing all data."""
        adapter = MemoryAdapter()
        adapter.write("a", b"1")
        adapter.write("b", b"2")
        adapter.clear()

        assert adapter.size() == 0
        assert adapter.read("a") is None

    def test_list_paths(self):
        """Test listing paths."""
        adapter = MemoryAdapter()
        adapter.write("a/b", b"1")
        adapter.write("c/d", b"2")

        paths = adapter.list_paths()
        assert "a/b" in paths
        assert "c/d" in paths

    def test_size(self):
        """Test size count."""
        adapter = MemoryAdapter()
        assert adapter.size() == 0

        adapter.write("a", b"1")
        assert adapter.size() == 1

        adapter.write("b", b"2")
        assert adapter.size() == 2


class TestFilesystemAdapter:
    """Test the filesystem adapter."""

    def test_create_adapter_default_path(self):
        """Test creating adapter with default path."""
        adapter = FilesystemAdapter()
        assert adapter.name == "filesystem"
        assert adapter.base_path.exists()

    def test_create_adapter_custom_path(self):
        """Test creating adapter with custom path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            adapter = FilesystemAdapter(tmpdir)
            assert adapter.base_path == Path(tmpdir)

    def test_write_and_read(self):
        """Test writing and reading data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            adapter = FilesystemAdapter(tmpdir)
            data = b"test data"

            assert adapter.write("test/path.txt", data) is True
            assert adapter.read("test/path.txt") == data

    def test_read_nonexistent(self):
        """Test reading nonexistent path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            adapter = FilesystemAdapter(tmpdir)
            assert adapter.read("nonexistent") is None

    def test_exists(self):
        """Test exists check."""
        with tempfile.TemporaryDirectory() as tmpdir:
            adapter = FilesystemAdapter(tmpdir)
            adapter.write("test/path.txt", b"data")

            assert adapter.exists("test/path.txt") is True
            assert adapter.exists("nonexistent") is False

    def test_delete(self):
        """Test deleting data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            adapter = FilesystemAdapter(tmpdir)
            adapter.write("test/path.txt", b"data")

            assert adapter.delete("test/path.txt") is True
            assert adapter.exists("test/path.txt") is False
            assert adapter.delete("test/path.txt") is False

    def test_is_available(self):
        """Test availability check."""
        with tempfile.TemporaryDirectory() as tmpdir:
            adapter = FilesystemAdapter(tmpdir)
            assert adapter.is_available() is True

    def test_nested_paths(self):
        """Test nested directory creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            adapter = FilesystemAdapter(tmpdir)

            # Write to deeply nested path
            assert adapter.write("a/b/c/d/e/f.txt", b"data") is True
            assert adapter.read("a/b/c/d/e/f.txt") == b"data"

    def test_list_paths(self):
        """Test listing paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            adapter = FilesystemAdapter(tmpdir)
            adapter.write("a/1.txt", b"1")
            adapter.write("b/2.txt", b"2")
            adapter.write("c/d/3.txt", b"3")

            paths = adapter.list_paths()
            assert len(paths) == 3

    def test_path_normalization(self):
        """Test that paths are normalized (forward slashes)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            adapter = FilesystemAdapter(tmpdir)

            # Write with forward slashes
            adapter.write("a/b/c.txt", b"data")

            # Should be readable with same path
            assert adapter.read("a/b/c.txt") == b"data"


class TestAdapterInterface:
    """Test that adapters implement the same interface."""

    @pytest.fixture(params=["memory", "filesystem"])
    def adapter(self, request, tmp_path):
        """Create adapter based on parameter."""
        if request.param == "memory":
            return MemoryAdapter()
        else:
            return FilesystemAdapter(str(tmp_path))

    def test_interface_name(self, adapter):
        """Test that adapter has name attribute."""
        assert hasattr(adapter, "name")
        assert isinstance(adapter.name, str)

    def test_interface_read(self, adapter):
        """Test that adapter has read method."""
        assert callable(adapter.read)

    def test_interface_write(self, adapter):
        """Test that adapter has write method."""
        assert callable(adapter.write)

    def test_interface_delete(self, adapter):
        """Test that adapter has delete method."""
        assert callable(adapter.delete)

    def test_interface_exists(self, adapter):
        """Test that adapter has exists method."""
        assert callable(adapter.exists)

    def test_interface_is_available(self, adapter):
        """Test that adapter has is_available method."""
        assert callable(adapter.is_available)

    def test_interface_roundtrip(self, adapter):
        """Test that all adapters support roundtrip."""
        data = b"roundtrip test data"
        path = "roundtrip/test.bin"

        assert adapter.write(path, data) is True
        assert adapter.read(path) == data
        assert adapter.exists(path) is True
        assert adapter.delete(path) is True
        assert adapter.exists(path) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
