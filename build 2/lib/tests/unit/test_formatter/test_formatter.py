"""
Unit tests for the formatter module.

This module contains tests for output formatting functionality,
including JSON, text, and other format transformations.
"""

import json
import unittest
from enum import Enum
from typing import List

from censyspy.formatter import (
    BaseFormatter,
    FormatterProtocol,
    JSONFormatter,
    OutputFormat,
    TextFormatter,
    format_console_summary,
    format_results,
    get_formatter,
    is_valid_format,
    normalize_format_type,
)
from censyspy.models import CertificateMatch, DNSMatch, Domain, SerializationFormat


class TestOutputFormatEnum(unittest.TestCase):
    """Test the OutputFormat enum."""

    def test_output_format_values(self):
        """Test that OutputFormat enum contains expected values."""
        self.assertEqual(OutputFormat.JSON, "json")
        self.assertEqual(OutputFormat.TEXT, "text")
        self.assertTrue(issubclass(OutputFormat, str))
        self.assertTrue(issubclass(OutputFormat, Enum))


class TestFormatSelection(unittest.TestCase):
    """Test the format selection functionality."""

    def test_is_valid_format(self):
        """Test the is_valid_format function."""
        # Test valid formats
        self.assertTrue(is_valid_format("json"))
        self.assertTrue(is_valid_format("text"))
        
        # Test case insensitivity
        self.assertTrue(is_valid_format("JSON"))
        self.assertTrue(is_valid_format("Text"))
        
        # Test invalid formats
        self.assertFalse(is_valid_format("invalid"))
        self.assertFalse(is_valid_format(""))
        self.assertFalse(is_valid_format("xml"))

    def test_normalize_format_type(self):
        """Test the normalize_format_type function."""
        # Test with enum values
        self.assertEqual(normalize_format_type(OutputFormat.JSON), OutputFormat.JSON)
        self.assertEqual(normalize_format_type(OutputFormat.TEXT), OutputFormat.TEXT)
        
        # Test with string values
        self.assertEqual(normalize_format_type("json"), OutputFormat.JSON)
        self.assertEqual(normalize_format_type("text"), OutputFormat.TEXT)
        
        # Test case insensitivity
        self.assertEqual(normalize_format_type("JSON"), OutputFormat.JSON)
        self.assertEqual(normalize_format_type("Text"), OutputFormat.TEXT)
        
        # Test invalid format
        with self.assertRaises(ValueError):
            normalize_format_type("invalid")

    def test_get_formatter(self):
        """Test the get_formatter function."""
        # Test with enum values
        self.assertIsInstance(get_formatter(OutputFormat.JSON), JSONFormatter)
        self.assertIsInstance(get_formatter(OutputFormat.TEXT), TextFormatter)
        
        # Test with string values
        self.assertIsInstance(get_formatter("json"), JSONFormatter)
        self.assertIsInstance(get_formatter("text"), TextFormatter)
        
        # Test case insensitivity
        self.assertIsInstance(get_formatter("JSON"), JSONFormatter)
        self.assertIsInstance(get_formatter("Text"), TextFormatter)
        
        # Test invalid format
        with self.assertRaises(ValueError):
            get_formatter("invalid")
            
        # We can't directly check if an instance implements a Protocol,
        # but we can verify they have the expected format method
        json_formatter = get_formatter("json")
        text_formatter = get_formatter("text")
        self.assertTrue(hasattr(json_formatter, "format"))
        self.assertTrue(hasattr(text_formatter, "format"))
        
        # Test that returned formatters extend BaseFormatter
        self.assertTrue(isinstance(get_formatter("json"), BaseFormatter))
        self.assertTrue(isinstance(get_formatter("text"), BaseFormatter))


class TestJSONFormatter(unittest.TestCase):
    """Test the JSON formatter."""
    
    def setUp(self):
        """Set up test data."""
        self.domain1 = Domain("example.com")
        self.domain2 = Domain("test.org")
        
        self.dns_match1 = DNSMatch(
            hostname=self.domain1,
            types={"forward", "a"},
            last_updated_at="2023-05-20T10:00:00Z",
            ip="93.184.216.34"
        )
        
        self.dns_match2 = DNSMatch(
            hostname=self.domain2,
            types={"forward"},
            last_updated_at="2023-05-20T12:00:00Z"
        )
        
        self.cert_match = CertificateMatch(
            hostname=self.domain1,
            types={"certificate"},
            added_at="2023-04-15T08:30:00Z"
        )
        
        self.dns_matches = [self.dns_match1, self.dns_match2]
        self.cert_matches = [self.cert_match]
        
        self.formatter = JSONFormatter()

    def test_json_formatter_instance(self):
        """Test that JSONFormatter is properly instantiated."""
        self.assertIsInstance(self.formatter, JSONFormatter)
        self.assertIsInstance(self.formatter, BaseFormatter)
        self.assertTrue(hasattr(self.formatter, 'format'))

    def test_json_formatter_output(self):
        """Test that JSON formatter produces valid JSON output."""
        # Format the data
        result = self.formatter.format(
            self.dns_matches,
            self.cert_matches
        )
        
        # Verify it's a string
        self.assertIsInstance(result, str)
        
        # Verify it's valid JSON
        try:
            parsed = json.loads(result)
            self.assertIsInstance(parsed, dict)
        except json.JSONDecodeError:
            self.fail("JSONFormatter did not produce valid JSON")
            
        # Verify expected structure
        self.assertIn("format", parsed)
        self.assertIn("total_matches", parsed)
        self.assertIn("dns_matches", parsed)
        self.assertIn("certificate_matches", parsed)
        self.assertIn("data", parsed)
        
        # Verify counts
        self.assertEqual(parsed["dns_matches"], 2)
        self.assertEqual(parsed["certificate_matches"], 1)
        
        # Verify with both serialization formats
        for format_type in [SerializationFormat.FLAT, SerializationFormat.UNIFIED]:
            result = self.formatter.format(
                self.dns_matches,
                self.cert_matches,
                serialization_format=format_type
            )
            # Should be valid JSON
            self.assertIsInstance(json.loads(result), dict)
            
    def test_json_formatter_indentation(self):
        """Test that JSON formatter respects indentation settings."""
        # Default indentation
        default_result = self.formatter.format(
            self.dns_matches,
            self.cert_matches
        )
        
        # Custom indentation
        custom_result = self.formatter.format(
            self.dns_matches,
            self.cert_matches,
            indent=4
        )
        
        # No indentation
        no_indent_result = self.formatter.format(
            self.dns_matches,
            self.cert_matches,
            indent=None
        )
        
        # Verify they're all valid JSON
        for result in [default_result, custom_result, no_indent_result]:
            self.assertIsInstance(json.loads(result), dict)
            
        # The no-indent version should be shorter than the indented versions
        self.assertLess(len(no_indent_result), len(default_result))
        self.assertLess(len(no_indent_result), len(custom_result))
        
        # The custom indent (4) should produce different output than default (2)
        self.assertNotEqual(default_result, custom_result)


class TestTextFormatter(unittest.TestCase):
    """Test the text formatter."""
    
    def setUp(self):
        """Set up test data."""
        self.domain1 = Domain("example.com")
        self.domain2 = Domain("test.org")
        
        self.dns_match1 = DNSMatch(
            hostname=self.domain1,
            types={"forward", "a"},
            last_updated_at="2023-05-20T10:00:00Z",
            ip="93.184.216.34"
        )
        
        self.dns_match2 = DNSMatch(
            hostname=self.domain2,
            types={"forward"},
            last_updated_at="2023-05-20T12:00:00Z"
        )
        
        self.cert_match = CertificateMatch(
            hostname=self.domain1,
            types={"certificate"},
            added_at="2023-04-15T08:30:00Z"
        )
        
        self.dns_matches = [self.dns_match1, self.dns_match2]
        self.cert_matches = [self.cert_match]
        
        self.formatter = TextFormatter()
        
    def test_text_formatter_instance(self):
        """Test that TextFormatter is properly instantiated."""
        self.assertIsInstance(self.formatter, TextFormatter)
        self.assertIsInstance(self.formatter, BaseFormatter)
        self.assertTrue(hasattr(self.formatter, 'format'))
        
    def test_text_formatter_basic_output(self):
        """Test that text formatter produces correct plain text output."""
        # Default format (no metadata)
        result = self.formatter.format(
            self.dns_matches,
            self.cert_matches
        )
        
        # Verify it's a string
        self.assertIsInstance(result, str)
        
        # Verify it contains expected domains
        self.assertIn("example.com", result)
        self.assertIn("test.org", result)
        
        # Verify one domain per line
        lines = result.strip().split("\n")
        self.assertEqual(len(lines), 2)  # Two unique domains
        
        # Verify domains are sorted
        self.assertEqual(lines[0], "example.com")
        self.assertEqual(lines[1], "test.org")
        
    def test_text_formatter_with_metadata(self):
        """Test text formatter with metadata included."""
        # With metadata
        result = self.formatter.format(
            self.dns_matches,
            self.cert_matches,
            include_metadata=True
        )
        
        # Verify it's a string
        self.assertIsInstance(result, str)
        
        # Should contain more than just domain names
        self.assertIn("example.com", result)
        self.assertIn("test.org", result)
        
        # Should contain source information
        self.assertIn("dns", result.lower())
        self.assertIn("certificate", result.lower())
        
        # Should contain IP information
        self.assertIn("93.184.216.34", result)
        
        # Should contain timestamp information
        self.assertIn("2023-05-20", result)
        
        # Should have header section
        self.assertIn("DOMAINS DISCOVERED THROUGH CENSYS SEARCHES", result.upper())
        
    def test_text_formatter_empty_input(self):
        """Test text formatter with empty input."""
        result = self.formatter.format([], [])
        
        # Should be empty string or contain no domains message
        if result:
            self.assertIn("No matching domains", result)
        else:
            self.assertEqual(result, "")


class TestFormatResults(unittest.TestCase):
    """Test the format_results function."""
    
    def setUp(self):
        """Set up test data."""
        self.domain1 = Domain("example.com")
        self.domain2 = Domain("test.org")
        
        self.dns_match = DNSMatch(
            hostname=self.domain1,
            types={"forward", "a"},
            last_updated_at="2023-05-20T10:00:00Z",
            ip="93.184.216.34"
        )
        
        self.cert_match = CertificateMatch(
            hostname=self.domain2,
            types={"certificate"},
            added_at="2023-04-15T08:30:00Z"
        )
        
        self.dns_matches = [self.dns_match]
        self.cert_matches = [self.cert_match]
        
    def test_format_results_json(self):
        """Test format_results with JSON output."""
        # Default format is JSON
        result = format_results(
            self.dns_matches,
            self.cert_matches
        )
        
        # Verify it's valid JSON
        try:
            parsed = json.loads(result)
            self.assertIsInstance(parsed, dict)
        except json.JSONDecodeError:
            self.fail("format_results did not produce valid JSON")
            
    def test_format_results_text(self):
        """Test format_results with text output."""
        result = format_results(
            self.dns_matches,
            self.cert_matches,
            format_type="text"
        )
        
        # Should be a string with domain names
        self.assertIsInstance(result, str)
        self.assertIn("example.com", result)
        self.assertIn("test.org", result)
        
    def test_format_results_options(self):
        """Test format_results with options."""
        # JSON with custom indentation
        json_result = format_results(
            self.dns_matches,
            self.cert_matches,
            format_type="json",
            options={"indent": 4}
        )
        
        # Text with metadata
        text_result = format_results(
            self.dns_matches,
            self.cert_matches,
            format_type="text",
            options={"include_metadata": True}
        )
        
        # Verify results
        self.assertIsInstance(json_result, str)
        self.assertIsInstance(text_result, str)
        self.assertIn("example.com", text_result)
        self.assertIn("dns", text_result.lower())
        
    def test_format_results_enum(self):
        """Test format_results with enum format_type."""
        # With enum
        json_result = format_results(
            self.dns_matches,
            self.cert_matches,
            format_type=OutputFormat.JSON
        )
        
        text_result = format_results(
            self.dns_matches,
            self.cert_matches,
            format_type=OutputFormat.TEXT
        )
        
        # Verify results
        self.assertIsInstance(json_result, str)
        self.assertIsInstance(text_result, str)
        
        # JSON should be parseable
        self.assertIsInstance(json.loads(json_result), dict)
        
        # Text should contain domains
        self.assertIn("example.com", text_result)
        self.assertIn("test.org", text_result)
        
    def test_format_results_error(self):
        """Test format_results with invalid format."""
        with self.assertRaises(ValueError):
            format_results(
                self.dns_matches,
                self.cert_matches,
                format_type="invalid"
            )


class TestConsoleSummary(unittest.TestCase):
    """Test the console summary output."""
    
    def setUp(self):
        """Set up test data."""
        domains = [
            "example.com",
            "api.example.com",
            "test.org",
            "dev.test.org",
            "stage.test.org"
        ]
        
        self.dns_matches: List[DNSMatch] = []
        self.cert_matches: List[CertificateMatch] = []
        
        # Create DNS matches for all domains
        for domain_str in domains:
            domain = Domain(domain_str)
            self.dns_matches.append(
                DNSMatch(
                    hostname=domain,
                    types={"forward"},
                    last_updated_at="2023-05-20T10:00:00Z"
                )
            )
            
        # Create certificate matches for some domains
        for domain_str in domains[:2]:  # First two
            domain = Domain(domain_str)
            self.cert_matches.append(
                CertificateMatch(
                    hostname=domain,
                    types={"certificate"},
                    added_at="2023-04-15T08:30:00Z"
                )
            )
            
    def test_console_summary_structure(self):
        """Test that console summary contains expected components."""
        result = format_console_summary(
            self.dns_matches,
            self.cert_matches
        )
        
        # Verify it's a string
        self.assertIsInstance(result, str)
        
        # Check for expected sections
        self.assertIn("CENSYS SEARCH RESULTS SUMMARY", result)
        self.assertIn("STATISTICS", result)
        self.assertIn("SAMPLE DOMAINS", result)
        
        # Check for statistics
        self.assertIn("Total unique domains", result)
        self.assertIn("DNS records:", result)
        self.assertIn("Certificate records:", result)
        
        # Check for domain examples
        self.assertIn("example.com", result)
        
    def test_console_summary_counts(self):
        """Test that console summary shows correct counts."""
        result = format_console_summary(
            self.dns_matches,
            self.cert_matches
        )
        
        # There should be 5 unique domains
        self.assertIn("Total unique domains: 5", result)
        
        # There should be 5 DNS records
        self.assertIn("DNS records: 5", result)
        
        # There should be 2 certificate records
        self.assertIn("Certificate records: 2", result)
        
    def test_console_summary_sample_limit(self):
        """Test that console summary respects max_display."""
        # Default is 10, so all 5 domains should be shown
        default_result = format_console_summary(
            self.dns_matches,
            self.cert_matches
        )
        
        # Limit to 3 domains
        limited_result = format_console_summary(
            self.dns_matches,
            self.cert_matches,
            max_display=3
        )
        
        # Limit to all domains
        all_result = format_console_summary(
            self.dns_matches,
            self.cert_matches,
            max_display=10
        )
        
        # Default should show all 5 domains
        for domain in ["example.com", "api.example.com", "test.org", "dev.test.org", "stage.test.org"]:
            self.assertIn(domain, default_result)
            
        # Limited should only show 3 domains and "... and 2 more domains"
        limited_lines = limited_result.split("\n")
        domain_count = sum(1 for line in limited_lines if "1." in line or "2." in line or "3." in line)
        self.assertEqual(domain_count, 3)
        self.assertIn("... and 2 more domains", limited_result)
        
        # All should show all 5 domains and no "... and X more domains"
        self.assertNotIn("more domains", all_result)
        
    def test_console_summary_empty(self):
        """Test console summary with empty input."""
        result = format_console_summary([], [])
        
        # Should still have structure
        self.assertIn("CENSYS SEARCH RESULTS SUMMARY", result)
        self.assertIn("STATISTICS", result)
        
        # But show zero counts
        self.assertIn("Total unique domains: 0", result)
        self.assertIn("DNS records: 0", result)
        self.assertIn("Certificate records: 0", result)
        
        # And no domains found message
        self.assertIn("No matching domains", result)


if __name__ == '__main__':
    unittest.main()