"""
Global pytest configuration and shared fixtures.

This file provides configuration settings and fixtures for all test modules.
"""
import pytest
from datetime import datetime


@pytest.fixture
def sample_domain() -> str:
    """Return a sample domain for testing."""
    return "example.com"


@pytest.fixture
def sample_domains() -> list:
    """Return a list of sample domains for testing."""
    return [
        "example.com",
        "api.example.com",
        "www.example.com",
        "test.example.com",
        "dev.example.com",
    ]


@pytest.fixture
def timestamp() -> str:
    """Return a fixed timestamp for testing."""
    return "2025-05-15T10:00:00Z"