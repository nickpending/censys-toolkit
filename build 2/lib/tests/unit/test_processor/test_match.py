"""
Tests for domain matching functionality in the processor module.

This module tests the is_domain_match function to ensure it
correctly identifies when hostnames match a given domain pattern.
"""

import unittest
from typing import Optional

from censyspy.processor import is_domain_match


class TestDomainMatching(unittest.TestCase):
    """Test domain matching functionality."""

    def test_exact_match(self):
        """Test exact domain matching."""
        # Exact matches should return the matched domain
        self.assertEqual(is_domain_match("example.com", "example.com"), "example.com")
        self.assertEqual(is_domain_match("sub.example.com", "sub.example.com"), "sub.example.com")
        
        # Case-insensitive matching
        self.assertEqual(is_domain_match("ExAmPlE.cOm", "example.com"), "example.com")
        self.assertEqual(is_domain_match("example.com", "EXAMPLE.COM"), "example.com")
        
        # Trailing dot normalization
        self.assertEqual(is_domain_match("example.com.", "example.com"), "example.com")
        self.assertEqual(is_domain_match("example.com", "example.com."), "example.com")

    def test_subdomain_match(self):
        """Test subdomain matching."""
        # Subdomains should match against their parent domain
        self.assertEqual(is_domain_match("sub.example.com", "example.com"), "sub.example.com")
        self.assertEqual(is_domain_match("deep.sub.example.com", "example.com"), "deep.sub.example.com")
        self.assertEqual(is_domain_match("deep.sub.example.com", "sub.example.com"), "deep.sub.example.com")
        
        # Different domains should not match even with similar strings
        self.assertIsNone(is_domain_match("example.org", "example.com"))
        self.assertIsNone(is_domain_match("anexample.com", "example.com"))
        self.assertIsNone(is_domain_match("example.commercial", "example.com"))

    def test_wildcard_match(self):
        """Test wildcard domain matching."""
        # Wildcard matches
        self.assertEqual(is_domain_match("sub.example.com", "*.example.com"), "sub.example.com")
        self.assertEqual(is_domain_match("deep.sub.example.com", "*.example.com"), "deep.sub.example.com")
        
        # Wildcard should not match parent domain
        self.assertIsNone(is_domain_match("example.com", "*.example.com"))
        
        # Specific wildcard matches
        self.assertEqual(is_domain_match("test.example.com", "*.example.com"), "test.example.com")
        self.assertIsNone(is_domain_match("test.sub.example.com", "*.example.com"))
        self.assertEqual(is_domain_match("test.sub.example.com", "*.sub.example.com"), "test.sub.example.com")

    def test_edge_cases(self):
        """Test edge cases for domain matching."""
        # Empty inputs
        self.assertIsNone(is_domain_match("", "example.com"))
        self.assertIsNone(is_domain_match("example.com", ""))
        self.assertIsNone(is_domain_match("", ""))
        
        # None inputs
        self.assertIsNone(is_domain_match(None, "example.com"))  # type: ignore
        self.assertIsNone(is_domain_match("example.com", None))  # type: ignore
        self.assertIsNone(is_domain_match(None, None))  # type: ignore
        
        # Malformed domains
        self.assertIsNone(is_domain_match("not a domain", "example.com"))
        self.assertIsNone(is_domain_match("example.com", "not a domain"))
        
        # IP addresses (should not match any domain)
        self.assertIsNone(is_domain_match("192.168.1.1", "example.com"))
        self.assertIsNone(is_domain_match("example.com", "192.168.1.1"))
        
        # Double wildcards (current implementation would treat this as a regular domain)
        self.assertIsNone(is_domain_match("sub.example.com", "*.*.example.com"))
        
        # Domain with just TLD
        self.assertIsNone(is_domain_match("com", "example.com"))
        self.assertIsNone(is_domain_match("example.com", "com"))

    def test_match_with_special_domains(self):
        """Test matching with special domain formats."""
        # Localhost
        self.assertEqual(is_domain_match("localhost", "localhost"), "localhost")
        self.assertIsNone(is_domain_match("test.localhost", "localhost"))
        
        # Special TLDs
        self.assertEqual(is_domain_match("test.local", "test.local"), "test.local")
        self.assertEqual(is_domain_match("sub.test.local", "test.local"), "sub.test.local")
        
        # International domains
        self.assertEqual(is_domain_match("例子.com", "例子.com"), "例子.com")
        self.assertEqual(is_domain_match("sub.例子.com", "例子.com"), "sub.例子.com")
        
        # Punycode
        self.assertEqual(is_domain_match("xn--fsqu00a.com", "xn--fsqu00a.com"), "xn--fsqu00a.com")
        self.assertEqual(is_domain_match("sub.xn--fsqu00a.com", "xn--fsqu00a.com"), "sub.xn--fsqu00a.com")

    def test_partial_matches(self):
        """Test cases that should not match due to partial matching."""
        # Partial string matches that should not be domain matches
        self.assertIsNone(is_domain_match("myexample.com", "example.com"))
        self.assertIsNone(is_domain_match("example.commercial", "example.com"))
        self.assertIsNone(is_domain_match("company.example", "example.com"))
        
        # Similar TLDs
        self.assertIsNone(is_domain_match("example.co", "example.com"))
        self.assertIsNone(is_domain_match("example.commm", "example.com"))
        
        # Domain as part of hostname but not subdomain
        self.assertIsNone(is_domain_match("notsubexample.com", "example.com"))