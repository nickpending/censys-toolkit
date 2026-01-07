"""
Unit tests for the utils module.

This module contains tests for utility functions,
including logging, file operations, and helper functions.
"""

import os
import tempfile
from pathlib import Path

import pytest

from censyspy.utils import is_valid_domain, is_valid_file_path


class TestValidation:
    """Tests for validation utility functions."""

    def test_is_valid_domain(self):
        """Test domain validation function."""
        # Valid domains
        assert is_valid_domain("example.com") is True
        assert is_valid_domain("sub.domain.example.co.uk") is True
        assert is_valid_domain("valid-with-hyphen.com") is True
        assert is_valid_domain("example.com.") is True  # Trailing dot is valid in DNS
        
        # Invalid domains
        assert is_valid_domain("") is False
        assert is_valid_domain("invalid") is False  # No dots
        assert is_valid_domain(".example.com") is False  # Starts with dot
        assert is_valid_domain("example..com") is False  # Consecutive dots
        assert is_valid_domain("-example.com") is False  # Starts with hyphen
        assert is_valid_domain("example-.com") is False  # Part ends with hyphen
        assert is_valid_domain("exam@ple.com") is False  # Invalid character
        
    def test_is_valid_file_path(self):
        """Test file path validation function."""
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Valid paths
            valid_path = os.path.join(temp_dir, "valid.txt")
            assert is_valid_file_path(valid_path) is True
            
            # Valid subdirectory path
            subdir_path = os.path.join(temp_dir, "subdir")
            os.makedirs(subdir_path, exist_ok=True)
            assert is_valid_file_path(os.path.join(subdir_path, "valid.txt")) is True
            
            # Invalid paths
            assert is_valid_file_path("") is False
            assert is_valid_file_path("/path/does/not/exist/file.txt") is False
            
            # Current directory
            assert is_valid_file_path("file.txt") is True  # Should work in current dir