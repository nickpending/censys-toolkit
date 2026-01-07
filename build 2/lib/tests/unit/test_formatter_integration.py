"""
Tests for the integration between processor and formatter.
"""

import json
from unittest.mock import patch

import pytest

from censyspy.integration import process_and_format
from censyspy.models import CertificateMatch, DNSMatch, Domain


class TestFormatterIntegration:
    """Tests for the formatter integration functions."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create sample domain and match objects
        self.domain1 = Domain("example.com")
        self.domain2 = Domain("sub.example.com")
        self.domain3 = Domain("other.org")
        
        # DNS matches
        self.dns_match1 = DNSMatch(
            hostname=self.domain1,
            types={"forward"},
            last_updated_at="2023-01-01T12:00:00Z",
            ip="192.0.2.1"
        )
        self.dns_match2 = DNSMatch(
            hostname=self.domain2,
            types={"reverse"},
            last_updated_at="2023-01-02T12:00:00Z",
            ip="192.0.2.2"
        )
        
        # Certificate match
        self.cert_match = CertificateMatch(
            hostname=self.domain3,
            types={"certificate"},
            added_at="2023-01-03T12:00:00Z"
        )
        
        # Create a dictionary of matches (simulating processor output)
        self.results = {
            str(self.domain1): self.dns_match1,
            str(self.domain2): self.dns_match2,
            str(self.domain3): self.cert_match
        }
    
    def test_process_and_format_json(self):
        """Test formatting processor results as JSON."""
        # Format the results as JSON
        formatted = process_and_format(self.results, "json")
        
        # Verify the output is valid JSON
        json_data = json.loads(formatted)
        
        # Check the structure and metadata
        assert "format" in json_data
        assert "total_matches" in json_data
        assert "dns_matches" in json_data
        assert "certificate_matches" in json_data
        assert "data" in json_data
        
        # Verify match counts
        assert json_data["dns_matches"] == 2
        assert json_data["certificate_matches"] == 1
        assert json_data["total_matches"] == 3
        
        # Check that all domains are present in the formatted output
        domain_names = [entry.get("domain") for entry in json_data["data"]]
        assert "example.com" in domain_names
        assert "sub.example.com" in domain_names
        assert "other.org" in domain_names
    
    def test_process_and_format_text(self):
        """Test formatting processor results as text."""
        # Format the results as text
        formatted = process_and_format(self.results, "text")
        
        # Split into lines and check content
        lines = formatted.strip().split("\n")
        
        # The text format should have a list of domains
        assert "example.com" in formatted
        assert "sub.example.com" in formatted
        assert "other.org" in formatted
    
    def test_process_and_format_with_options(self):
        """Test formatting with additional options."""
        # Format as text with metadata
        formatted = process_and_format(
            self.results, 
            "text", 
            include_metadata=True
        )
        
        # Check that metadata is included
        assert "[dns]" in formatted  # dns source instead of specific record types
        assert "[certificate]" in formatted
        
        # Check IP addresses included in output
        
        # IP addresses should be present
        assert "192.0.2.1" in formatted
        assert "192.0.2.2" in formatted
    
    def test_process_and_format_empty_results(self):
        """Test formatting empty results."""
        # Empty results
        empty_results = {}
        
        # Format empty results
        formatted_json = process_and_format(empty_results, "json")
        formatted_text = process_and_format(empty_results, "text")
        
        # Verify JSON output
        json_data = json.loads(formatted_json)
        assert json_data["total_matches"] == 0
        assert json_data["dns_matches"] == 0
        assert json_data["certificate_matches"] == 0
        assert len(json_data["data"]) == 0
        
        # Verify text output
        assert formatted_text.strip() == ""
    
    def test_process_and_format_invalid_format(self):
        """Test invalid format raises ValueError."""
        with pytest.raises(ValueError):
            process_and_format(self.results, "invalid_format")
    
    @patch('censyspy.integration.logger')
    def test_process_and_format_logging(self, mock_logger):
        """Test that logging occurs during formatting."""
        # Format the results
        process_and_format(self.results, "json")
        
        # Verify logging calls
        mock_logger.info.assert_called()
        mock_logger.debug.assert_called_with(
            "Formatting 2 DNS matches and 1 certificate matches"
        )