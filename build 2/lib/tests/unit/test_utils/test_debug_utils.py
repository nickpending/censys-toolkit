"""
Tests for the debugging utilities in the utils module.
"""

import json
import logging
from io import StringIO
from unittest import mock

import pytest

from censyspy.utils import debug_object


class TestDebugObject:
    """Tests for the debug_object function."""

    def setup_method(self):
        """Set up test environment before each test."""
        # Create a StringIO object to capture log output
        self.log_stream = StringIO()
        
        # Configure a handler that writes to our StringIO object
        self.handler = logging.StreamHandler(self.log_stream)
        self.handler.setLevel(logging.DEBUG)
        
        # Configure root logger
        self.logger = logging.getLogger()
        self.original_level = self.logger.level
        self.original_handlers = self.logger.handlers.copy()
        
        # Remove existing handlers to avoid polluting test output
        for handler in self.logger.handlers:
            self.logger.removeHandler(handler)
            
        self.logger.addHandler(self.handler)
        self.logger.setLevel(logging.DEBUG)

    def teardown_method(self):
        """Clean up after each test."""
        # Restore original logger configuration
        self.logger.removeHandler(self.handler)
        self.logger.setLevel(self.original_level)
        
        for handler in self.original_handlers:
            self.logger.addHandler(handler)

    def get_log_output(self):
        """Get the captured log output as a string."""
        self.log_stream.seek(0)
        return self.log_stream.getvalue()

    def test_debug_string(self):
        """Test debugging a simple string."""
        debug_object("test string", "String Test")
        log_output = self.get_log_output()
        
        assert "String Test: Object of type str: 'test string'" in log_output

    def test_debug_dict(self):
        """Test debugging a dictionary with special formatting."""
        test_dict = {"name": "test", "value": 42, "nested": {"a": 1, "b": 2}}
        debug_object(test_dict, "Dict Test")
        log_output = self.get_log_output()
        
        # The dictionary should be formatted as JSON with indentation
        assert "Dict Test: Object of type dict:" in log_output
        # Check for formatting indicators like line breaks and indentation
        assert '"name": "test"' in log_output
        assert '"value": 42' in log_output

    def test_debug_list(self):
        """Test debugging a list with special formatting for longer lists."""
        # Short list - should use regular repr
        short_list = [1, 2, 3]
        debug_object(short_list, "Short List")
        
        # Long list - should use custom formatting with line breaks
        long_list = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        debug_object(long_list, "Long List")
        
        log_output = self.get_log_output()
        
        assert "Short List: Object of type list:" in log_output
        assert "Long List: Object of type list:" in log_output
        
        # For longer lists, check if items are numbered and on separate lines
        assert "0: 1" in log_output

    def test_debug_exception(self):
        """Test debugging an exception."""
        try:
            # Generate an exception
            1 / 0
        except Exception as e:
            debug_object(e, "Exception Test")
        
        log_output = self.get_log_output()
        
        assert "Exception Test: Object of type ZeroDivisionError:" in log_output
        assert "division by zero" in log_output

    def test_skip_if_not_debug_level(self):
        """Test that processing is skipped if logger level > DEBUG."""
        self.logger.setLevel(logging.INFO)
        
        # Create a mock for json.dumps to verify it's not called
        with mock.patch('json.dumps') as mock_dumps:
            debug_object({"test": "data"})
            
            # Verify json.dumps was not called, indicating the function returned early
            mock_dumps.assert_not_called()
        
        # The log should be empty since we're at INFO level
        log_output = self.get_log_output()
        assert log_output == ""

    def test_handles_unserializable_object(self):
        """Test handling objects that can't be properly serialized."""
        # Create an object with a custom __repr__ that raises an exception
        class BrokenRepr:
            def __repr__(self):
                raise ValueError("Cannot represent this object")
        
        broken_obj = BrokenRepr()
        debug_object(broken_obj, "Broken Object")
        
        log_output = self.get_log_output()
        
        assert "Broken Object: Object of type BrokenRepr:" in log_output
        assert "error during representation" in log_output