"""
Test file I/O utilities in censyspy.utils module.
"""

import json
import os
import tempfile
from pathlib import Path
from typing import List

import pytest

from censyspy.utils import (
    ensure_directory_exists,
    read_json_file,
    read_text_file,
    write_json_file,
    write_text_file,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for file operations."""
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield tmpdirname


class TestFileIO:
    """Tests for file I/O utilities."""
    
    def test_ensure_directory_exists_creates_directory(self, temp_dir):
        """Test that ensure_directory_exists creates a directory when it doesn't exist."""
        # Create a path to a file in a nonexistent subdirectory
        new_dir = os.path.join(temp_dir, "new_dir")
        file_path = os.path.join(new_dir, "test.txt")
        
        # The directory should not exist yet
        assert not os.path.exists(new_dir)
        
        # After calling ensure_directory_exists, the directory should exist
        ensure_directory_exists(file_path)
        assert os.path.exists(new_dir)
    
    def test_ensure_directory_exists_with_existing_directory(self, temp_dir):
        """Test that ensure_directory_exists works with an existing directory."""
        # Using an existing directory should not raise an error
        ensure_directory_exists(os.path.join(temp_dir, "test.txt"))
        assert os.path.exists(temp_dir)
    
    def test_write_and_read_json_file(self, temp_dir):
        """Test writing and reading a JSON file."""
        file_path = os.path.join(temp_dir, "test.json")
        test_data = {"key1": "value1", "key2": [1, 2, 3], "key3": {"nested": True}}
        
        # Write the JSON file
        write_json_file(test_data, file_path)
        
        # Verify the file exists
        assert os.path.exists(file_path)
        
        # Read the file and verify the content
        read_data = read_json_file(file_path)
        assert read_data == test_data
    
    def test_read_json_file_not_found(self, temp_dir):
        """Test that read_json_file raises FileNotFoundError for nonexistent files."""
        nonexistent_path = os.path.join(temp_dir, "nonexistent.json")
        with pytest.raises(FileNotFoundError):
            read_json_file(nonexistent_path)
    
    def test_read_json_file_invalid_json(self, temp_dir):
        """Test that read_json_file raises JSONDecodeError for invalid JSON."""
        file_path = os.path.join(temp_dir, "invalid.json")
        
        # Create a file with invalid JSON
        with open(file_path, 'w') as f:
            f.write("{invalid json")
        
        with pytest.raises(json.JSONDecodeError):
            read_json_file(file_path)
    
    def test_write_and_read_text_file(self, temp_dir):
        """Test writing and reading a text file."""
        file_path = os.path.join(temp_dir, "test.txt")
        test_lines = ["Line 1", "Line 2", "Line 3"]
        
        # Write the text file
        write_text_file(test_lines, file_path)
        
        # Verify the file exists
        assert os.path.exists(file_path)
        
        # Read the file and verify the content
        read_lines = read_text_file(file_path)
        assert read_lines == test_lines
    
    def test_read_text_file_with_comments(self, temp_dir):
        """Test reading a text file with comments."""
        file_path = os.path.join(temp_dir, "comments.txt")
        
        # Create a file with comments and empty lines
        with open(file_path, 'w') as f:
            f.write("# This is a comment\nLine 1\n\n# Another comment\nLine 2\n")
        
        # Read with comments included
        lines_with_comments = read_text_file(file_path, ignore_comments=False)
        assert "# This is a comment" in lines_with_comments
        assert "# Another comment" in lines_with_comments
        assert len(lines_with_comments) == 4  # Two comments, two content lines
        
        # Read with comments ignored
        lines_without_comments = read_text_file(file_path, ignore_comments=True)
        assert "# This is a comment" not in lines_without_comments
        assert "# Another comment" not in lines_without_comments
        assert len(lines_without_comments) == 2  # Just the two content lines
    
    def test_read_text_file_not_found(self, temp_dir):
        """Test that read_text_file raises FileNotFoundError for nonexistent files."""
        nonexistent_path = os.path.join(temp_dir, "nonexistent.txt")
        with pytest.raises(FileNotFoundError):
            read_text_file(nonexistent_path)
    
    def test_write_text_file_with_newlines(self, temp_dir):
        """Test writing a text file with and without newlines."""
        file_path = os.path.join(temp_dir, "newlines.txt")
        test_lines = ["Line 1", "Line 2", "Line 3"]
        
        # Write with newlines added
        write_text_file(test_lines, file_path, add_newlines=True)
        
        # Read the raw file content to check newlines
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Should have newlines after each entry
        assert content == "Line 1\nLine 2\nLine 3\n"
        
        # Write without adding newlines
        write_text_file(test_lines, file_path, add_newlines=False)
        
        # Read the raw file content to check no newlines
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Should be concatenated without newlines
        assert content == "Line 1Line 2Line 3"
    
    def test_write_text_file_deep_directory(self, temp_dir):
        """Test writing to a file in a deep directory structure."""
        # Create a deep directory path
        deep_path = os.path.join(temp_dir, "level1", "level2", "level3", "test.txt")
        test_lines = ["This is a test"]
        
        # Write to the file - all directories should be created
        write_text_file(test_lines, deep_path)
        
        # Verify the file exists
        assert os.path.exists(deep_path)
        
        # Read the file and verify the content
        read_lines = read_text_file(deep_path)
        assert read_lines == test_lines