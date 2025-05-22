"""
Test date manipulation helper functions in utils module.
"""

from datetime import datetime, timedelta
from unittest import mock

import pytest

from censyspy.utils import (
    calculate_past_date,
    format_date,
    format_date_for_api_query,
    get_date_filter,
    is_valid_date_string,
    parse_date_string,
)


class TestDateHelpers:
    """Tests for date manipulation utility functions."""

    def test_get_date_filter_none(self):
        """Test get_date_filter returns None for None or 'all'."""
        assert get_date_filter(None) is None
        assert get_date_filter("all") is None

    def test_get_date_filter_valid_days(self):
        """Test get_date_filter with valid days parameter."""
        # Mock datetime.now() to return a fixed date for testing
        with mock.patch("censyspy.utils.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 1, 15)
            # The timedelta function is called from inside calculate_past_date
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            # Test with a few valid inputs
            result = get_date_filter("7")
            assert result == "[2023-01-08 TO *]"
            
            result = get_date_filter("1")
            assert result == "[2023-01-14 TO *]"
            
            result = get_date_filter("30")
            assert result == "[2022-12-16 TO *]"

    def test_get_date_filter_invalid_days(self):
        """Test get_date_filter raises ValueError for invalid days."""
        with pytest.raises(ValueError):
            get_date_filter("-1")  # Negative days
            
        with pytest.raises(ValueError):
            get_date_filter("0")  # Zero days
            
        with pytest.raises(ValueError):
            get_date_filter("abc")  # Non-numeric

    def test_calculate_past_date(self):
        """Test calculate_past_date function."""
        # Mock datetime.now() to return a fixed date for testing
        with mock.patch("censyspy.utils.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 1, 15)
            # The timedelta function is called from inside calculate_past_date
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            # Test with valid inputs
            result = calculate_past_date(7)
            assert result == datetime(2023, 1, 8)
            
            result = calculate_past_date(0)
            assert result == datetime(2023, 1, 15)  # Same as now
            
            result = calculate_past_date(365)
            assert result == datetime(2022, 1, 15)  # One year ago
            
            # Test with invalid input
            with pytest.raises(ValueError):
                calculate_past_date(-1)  # Negative days

    def test_format_date_for_api_query(self):
        """Test format_date_for_api_query function."""
        # Test with start date only
        start_date = datetime(2023, 1, 15)
        result = format_date_for_api_query(start_date)
        assert result == "[2023-01-15 TO *]"
        
        # Test with start and end dates
        start_date = datetime(2023, 1, 15)
        end_date = datetime(2023, 1, 30)
        result = format_date_for_api_query(start_date, end_date)
        assert result == "[2023-01-15 TO 2023-01-30]"

    def test_format_date(self):
        """Test format_date function."""
        test_date = datetime(2023, 1, 15, 14, 30, 45)
        
        # Default format (YYYY-MM-DD)
        result = format_date(test_date)
        assert result == "2023-01-15"
        
        # Custom formats
        result = format_date(test_date, "%Y%m%d")
        assert result == "20230115"
        
        result = format_date(test_date, "%d/%m/%Y")
        assert result == "15/01/2023"
        
        result = format_date(test_date, "%Y-%m-%dT%H:%M:%S")
        assert result == "2023-01-15T14:30:45"

    def test_parse_date_string(self):
        """Test parse_date_string function."""
        # Test with default formats
        assert parse_date_string("2023-01-15") == datetime(2023, 1, 15)
        assert parse_date_string("2023-01-15T14:30:45") == datetime(2023, 1, 15, 14, 30, 45)
        assert parse_date_string("20230115") == datetime(2023, 1, 15)
        assert parse_date_string("15/01/2023") == datetime(2023, 1, 15)
        
        # Test with custom format
        custom_formats = ["%d-%b-%Y"]
        assert parse_date_string("15-Jan-2023", custom_formats) == datetime(2023, 1, 15)
        
        # Test with invalid format
        assert parse_date_string("invalid-date") is None
        
        # Test with empty input
        assert parse_date_string("") is None
        assert parse_date_string(None) is None

    def test_is_valid_date_string(self):
        """Test is_valid_date_string function."""
        # Test with valid dates
        assert is_valid_date_string("2023-01-15") is True
        assert is_valid_date_string("15/01/2023") is True
        assert is_valid_date_string("2023-01-15T14:30:45Z") is True
        
        # Test with custom format
        custom_formats = ["%d-%b-%Y"]
        assert is_valid_date_string("15-Jan-2023", custom_formats) is True
        
        # Test with invalid formats
        assert is_valid_date_string("invalid-date") is False
        assert is_valid_date_string("2023/13/32") is False  # Invalid date
        assert is_valid_date_string("") is False
        assert is_valid_date_string(None) is False