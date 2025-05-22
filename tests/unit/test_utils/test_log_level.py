"""
Test the log level management functions in censyspy.utils.
"""

import logging
import os
from unittest import mock

import pytest

from censyspy.utils import LOG_LEVELS, parse_log_level


def test_parse_log_level_defaults_to_info():
    """Test that parse_log_level defaults to INFO when no level is provided."""
    assert parse_log_level() == logging.INFO


def test_parse_log_level_with_string_names():
    """Test that parse_log_level correctly converts string level names."""
    for name, level in LOG_LEVELS.items():
        assert parse_log_level(name) == level
        # Test with uppercase too
        assert parse_log_level(name.upper()) == level


def test_parse_log_level_with_integer_constants():
    """Test that parse_log_level accepts integer level constants."""
    level_values = [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL]
    for level in level_values:
        assert parse_log_level(level) == level


def test_parse_log_level_with_invalid_string():
    """Test that parse_log_level defaults to INFO for invalid string levels."""
    assert parse_log_level("not_a_valid_level") == logging.INFO


@mock.patch.dict(os.environ, {"CENSYS_LOG_LEVEL": "debug"})
def test_parse_log_level_from_environment():
    """Test that parse_log_level reads from environment variables."""
    assert parse_log_level() == logging.DEBUG


@mock.patch.dict(os.environ, {"CENSYS_LOG_LEVEL": "warning"})
def test_parse_log_level_explicit_overrides_env():
    """Test that explicit level overrides environment variable."""
    assert parse_log_level("debug") == logging.DEBUG


@mock.patch.dict(os.environ, {"CENSYS_LOG_LEVEL": "invalid"})
def test_parse_log_level_invalid_env():
    """Test that invalid environment level defaults to INFO."""
    assert parse_log_level() == logging.INFO


@mock.patch.dict(os.environ, {"CUSTOM_ENV_VAR": "critical"})
def test_parse_log_level_custom_env_var():
    """Test that parse_log_level uses custom environment variable name."""
    assert parse_log_level(env_var="CUSTOM_ENV_VAR") == logging.CRITICAL