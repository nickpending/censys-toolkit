"""
Tests for the DNSMatch and CertificateMatch classes in the models module.
"""

import unittest
from datetime import datetime
from typing import Dict, Any, Set

import pytest
from censyspy.models import Domain, DNSMatch, CertificateMatch


class TestDNSMatch(unittest.TestCase):
    """Test the DNSMatch class functionality."""

    def test_init_valid(self):
        """Test valid DNSMatch initialization."""
        # Test basic initialization
        domain = Domain("example.com")
        match = DNSMatch(hostname=domain)
        self.assertEqual(match.hostname, domain)
        self.assertEqual(match.types, set())
        self.assertIsNone(match.last_updated_at)
        self.assertIsNone(match.ip)
        self.assertEqual(match.source, "censys")
        
        # Test initialization with all parameters
        types = {"forward", "reverse"}
        match = DNSMatch(
            hostname=domain,
            types=types,
            last_updated_at="2025-05-15T10:00:00Z",
            ip="192.168.1.1",
            source="test-source"
        )
        self.assertEqual(match.hostname, domain)
        self.assertEqual(match.types, types)
        self.assertEqual(match.last_updated_at, "2025-05-15T10:00:00Z")
        self.assertEqual(match.ip, "192.168.1.1")
        self.assertEqual(match.source, "test-source")

    def test_init_invalid(self):
        """Test initialization with invalid values."""
        domain = Domain("example.com")
        
        # Test with non-Domain hostname
        with self.assertRaises(ValueError):
            DNSMatch(hostname="not-a-domain-object")
            
        # Test with non-set types
        with self.assertRaises(ValueError):
            DNSMatch(hostname=domain, types=["forward", "reverse"])  # List instead of set
            
        # Test with non-string in types
        with self.assertRaises(ValueError):
            DNSMatch(hostname=domain, types={123, "forward"})  # Non-string in set
            
        # Test with non-string last_updated_at
        with self.assertRaises(ValueError):
            DNSMatch(hostname=domain, last_updated_at=datetime.now())  # Datetime object instead of string
            
        # Test with non-string IP - causes TypeError in re.match during validation
        with self.assertRaises((ValueError, TypeError)):
            DNSMatch(hostname=domain, ip=123)  # Int instead of string
            
        # Test with invalid IP format
        with self.assertRaises(ValueError):
            DNSMatch(hostname=domain, ip="invalid-ip")
            
        # Test with non-string source
        with self.assertRaises(ValueError):
            DNSMatch(hostname=domain, source=None)
            
        # Test with empty source
        with self.assertRaises(ValueError):
            DNSMatch(hostname=domain, source="")

    def test_to_dict(self):
        """Test DNSMatch serialization to dictionary."""
        domain = Domain("example.com")
        types = {"forward", "reverse"}
        match = DNSMatch(
            hostname=domain,
            types=types,
            last_updated_at="2025-05-15T10:00:00Z",
            ip="192.168.1.1",
            source="test-source"
        )
        
        expected_dict = {
            "hostname": {"name": "example.com"},
            "types": ["forward", "reverse"],  # Note: Set converted to list for serialization
            "last_updated_at": "2025-05-15T10:00:00Z",
            "ip": "192.168.1.1",
            "source": "test-source"
        }
        
        # Order of types in list doesn't matter, so we sort for comparison
        result_dict = match.to_dict()
        result_dict["types"] = sorted(result_dict["types"])
        expected_dict["types"] = sorted(expected_dict["types"])
        
        self.assertEqual(result_dict, expected_dict)
        
        # Test with default values
        minimal_match = DNSMatch(hostname=domain)
        minimal_dict = minimal_match.to_dict()
        self.assertEqual(minimal_dict["hostname"], {"name": "example.com"})
        self.assertEqual(minimal_dict["types"], [])
        self.assertIsNone(minimal_dict["last_updated_at"])
        self.assertIsNone(minimal_dict["ip"])
        self.assertEqual(minimal_dict["source"], "censys")

    def test_from_dict(self):
        """Test creating DNSMatch from dictionary."""
        # Test with full dictionary
        data: Dict[str, Any] = {
            "hostname": {"name": "example.com"},
            "types": ["forward", "reverse"],
            "last_updated_at": "2025-05-15T10:00:00Z",
            "ip": "192.168.1.1",
            "source": "test-source"
        }
        
        match = DNSMatch.from_dict(data)
        self.assertEqual(match.hostname.name, "example.com")
        self.assertEqual(match.types, {"forward", "reverse"})
        self.assertEqual(match.last_updated_at, "2025-05-15T10:00:00Z")
        self.assertEqual(match.ip, "192.168.1.1")
        self.assertEqual(match.source, "test-source")
        
        # Test with string hostname
        data = {
            "hostname": "example.org",
            "types": ["forward"]
        }
        
        match = DNSMatch.from_dict(data)
        self.assertEqual(match.hostname.name, "example.org")
        self.assertEqual(match.types, {"forward"})
        
        # Test with minimal data
        data = {
            "hostname": "example.net"
        }
        
        match = DNSMatch.from_dict(data)
        self.assertEqual(match.hostname.name, "example.net")
        self.assertEqual(match.types, set())
        self.assertIsNone(match.last_updated_at)
        self.assertIsNone(match.ip)
        self.assertEqual(match.source, "censys")
        
        # Test with invalid hostname format
        with self.assertRaises(ValueError):
            DNSMatch.from_dict({"hostname": 123})  # Int instead of dict or string

    def test_validation(self):
        """Test DNSMatch explicit validation."""
        domain = Domain("example.com")
        match = DNSMatch(hostname=domain)
        
        # Valid match should have no errors
        errors = match.validate()
        self.assertEqual(errors, [])
        
        # Test direct validation of invalid types
        # We need to set the attributes directly to bypass __post_init__ validation
        match_invalid = DNSMatch(hostname=domain)
        object.__setattr__(match_invalid, 'types', "not-a-set")
        
        errors = match_invalid.validate()
        self.assertTrue(len(errors) > 0)
        self.assertTrue(any("types" in err.lower() for err in errors))


class TestCertificateMatch(unittest.TestCase):
    """Test the CertificateMatch class functionality."""

    def test_init_valid(self):
        """Test valid CertificateMatch initialization."""
        # Test basic initialization
        domain = Domain("example.com")
        match = CertificateMatch(hostname=domain)
        self.assertEqual(match.hostname, domain)
        self.assertEqual(match.types, set())
        self.assertIsNone(match.added_at)
        self.assertEqual(match.source, "censys")
        
        # Test initialization with all parameters
        types = {"certificate", "ssl"}
        match = CertificateMatch(
            hostname=domain,
            types=types,
            added_at="2025-05-15T10:00:00Z",
            source="test-source"
        )
        self.assertEqual(match.hostname, domain)
        self.assertEqual(match.types, types)
        self.assertEqual(match.added_at, "2025-05-15T10:00:00Z")
        self.assertEqual(match.source, "test-source")

    def test_init_invalid(self):
        """Test initialization with invalid values."""
        domain = Domain("example.com")
        
        # Test with non-Domain hostname
        with self.assertRaises(ValueError):
            CertificateMatch(hostname="not-a-domain-object")
            
        # Test with non-set types
        with self.assertRaises(ValueError):
            CertificateMatch(hostname=domain, types=["certificate", "ssl"])  # List instead of set
            
        # Test with non-string in types
        with self.assertRaises(ValueError):
            CertificateMatch(hostname=domain, types={123, "certificate"})  # Non-string in set
            
        # Test with non-string added_at
        with self.assertRaises(ValueError):
            CertificateMatch(hostname=domain, added_at=datetime.now())  # Datetime object instead of string
            
        # Test with non-string source
        with self.assertRaises(ValueError):
            CertificateMatch(hostname=domain, source=None)
            
        # Test with empty source
        with self.assertRaises(ValueError):
            CertificateMatch(hostname=domain, source="")

    def test_to_dict(self):
        """Test CertificateMatch serialization to dictionary."""
        domain = Domain("example.com")
        types = {"certificate", "ssl"}
        match = CertificateMatch(
            hostname=domain,
            types=types,
            added_at="2025-05-15T10:00:00Z",
            source="test-source"
        )
        
        expected_dict = {
            "hostname": {"name": "example.com"},
            "types": ["certificate", "ssl"],  # Note: Set converted to list for serialization
            "added_at": "2025-05-15T10:00:00Z",
            "source": "test-source"
        }
        
        # Order of types in list doesn't matter, so we sort for comparison
        result_dict = match.to_dict()
        result_dict["types"] = sorted(result_dict["types"])
        expected_dict["types"] = sorted(expected_dict["types"])
        
        self.assertEqual(result_dict, expected_dict)
        
        # Test with default values
        minimal_match = CertificateMatch(hostname=domain)
        minimal_dict = minimal_match.to_dict()
        self.assertEqual(minimal_dict["hostname"], {"name": "example.com"})
        self.assertEqual(minimal_dict["types"], [])
        self.assertIsNone(minimal_dict["added_at"])
        self.assertEqual(minimal_dict["source"], "censys")

    def test_from_dict(self):
        """Test creating CertificateMatch from dictionary."""
        # Test with full dictionary
        data: Dict[str, Any] = {
            "hostname": {"name": "example.com"},
            "types": ["certificate", "ssl"],
            "added_at": "2025-05-15T10:00:00Z",
            "source": "test-source"
        }
        
        match = CertificateMatch.from_dict(data)
        self.assertEqual(match.hostname.name, "example.com")
        self.assertEqual(match.types, {"certificate", "ssl"})
        self.assertEqual(match.added_at, "2025-05-15T10:00:00Z")
        self.assertEqual(match.source, "test-source")
        
        # Test with string hostname
        data = {
            "hostname": "example.org",
            "types": ["certificate"]
        }
        
        match = CertificateMatch.from_dict(data)
        self.assertEqual(match.hostname.name, "example.org")
        self.assertEqual(match.types, {"certificate"})
        
        # Test with minimal data
        data = {
            "hostname": "example.net"
        }
        
        match = CertificateMatch.from_dict(data)
        self.assertEqual(match.hostname.name, "example.net")
        self.assertEqual(match.types, set())
        self.assertIsNone(match.added_at)
        self.assertEqual(match.source, "censys")
        
        # Test with invalid hostname format
        with self.assertRaises(ValueError):
            CertificateMatch.from_dict({"hostname": 123})  # Int instead of dict or string

    def test_validation(self):
        """Test CertificateMatch explicit validation."""
        domain = Domain("example.com")
        match = CertificateMatch(hostname=domain)
        
        # Valid match should have no errors
        errors = match.validate()
        self.assertEqual(errors, [])
        
        # Test direct validation of invalid types
        # We need to set the attributes directly to bypass __post_init__ validation
        match_invalid = CertificateMatch(hostname=domain)
        object.__setattr__(match_invalid, 'types', "not-a-set")
        
        errors = match_invalid.validate()
        self.assertTrue(len(errors) > 0)
        self.assertTrue(any("types" in err.lower() for err in errors))


class TestMatchFixtures:
    """Test the match classes using pytest fixtures."""
    
    def test_dns_match_with_fixtures(self, sample_domain, timestamp):
        """Test DNSMatch with pytest fixtures."""
        domain = Domain(sample_domain)
        match = DNSMatch(
            hostname=domain, 
            last_updated_at=timestamp,
            ip="192.168.1.1"
        )
        
        assert match.hostname.name == sample_domain
        assert match.last_updated_at == timestamp
        assert match.ip == "192.168.1.1"
    
    def test_certificate_match_with_fixtures(self, sample_domain, timestamp):
        """Test CertificateMatch with pytest fixtures."""
        domain = Domain(sample_domain)
        match = CertificateMatch(
            hostname=domain, 
            added_at=timestamp
        )
        
        assert match.hostname.name == sample_domain
        assert match.added_at == timestamp


if __name__ == '__main__':
    unittest.main()