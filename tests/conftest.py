"""Shared test fixtures for AEGIS."""

import os
from pathlib import Path

import pytest


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "slow: tests that need mesh data or take >10s")


@pytest.fixture
def data_dir():
    """Path to the data directory containing mesh files and databases."""
    env_path = os.environ.get("AEGIS_DATA_DIR")
    if env_path:
        return Path(env_path)
    # Default: two levels up from aegis/ into Geometric Dosimetry/data/
    default = Path(__file__).parent.parent.parent.parent / "data"
    return default


@pytest.fixture
def has_data(data_dir):
    """Whether the data directory exists and contains mesh files."""
    return data_dir.exists() and any(data_dir.glob("*.stl"))
