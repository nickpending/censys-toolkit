"""
Framework validation tests.

This module contains tests to verify that the testing framework is correctly configured.
"""
import pytest


def test_pytest_configuration():
    """Verify that pytest is correctly configured."""
    assert True, "Basic test assertion works"


def test_fixtures(sample_domain, sample_domains, timestamp):
    """Verify that fixtures are correctly loaded."""
    assert sample_domain == "example.com", "Domain fixture loaded correctly"
    assert len(sample_domains) == 5, "Domains fixture has correct length"
    assert timestamp.startswith("2025"), "Timestamp fixture loaded correctly"


@pytest.mark.parametrize(
    "domain,expected",
    [
        ("example.com", "example.com"),
        ("WWW.EXAMPLE.COM", "www.example.com"),
        ("sub.domain.example.com", "sub.domain.example.com"),
    ],
)
def test_parameterization(domain, expected):
    """Verify that test parameterization works."""
    assert domain.lower() == expected, f"Expected {expected}, got {domain.lower()}"


@pytest.mark.xfail(reason="This test is expected to fail as a demo")
def test_expected_failure():
    """Demonstrate that xfail marking works correctly."""
    assert False, "This test is marked to fail"