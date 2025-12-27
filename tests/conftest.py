"""
Pytest configuration for RPP tests.
"""

import pytest
import sys
from pathlib import Path


# Ensure rpp package is importable
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def memory_adapter():
    """Provide a fresh memory adapter."""
    from rpp.adapters.memory import MemoryAdapter
    return MemoryAdapter()


@pytest.fixture
def filesystem_adapter(tmp_path):
    """Provide a filesystem adapter with temp directory."""
    from rpp.adapters.filesystem import FilesystemAdapter
    return FilesystemAdapter(str(tmp_path))


@pytest.fixture
def resolver():
    """Provide a fresh resolver."""
    from rpp.resolver import RPPResolver
    return RPPResolver()


@pytest.fixture
def sample_addresses():
    """Provide sample addresses for testing."""
    from rpp.address import from_components
    return [
        from_components(0, 0, 0, 0),  # Minimum
        from_components(3, 511, 511, 255),  # Maximum
        from_components(0, 12, 40, 1),  # Scenario 1: allowed read
        from_components(0, 100, 450, 64),  # Scenario 2: denied write
        from_components(2, 200, 128, 32),  # Scenario 3: archive route
    ]
