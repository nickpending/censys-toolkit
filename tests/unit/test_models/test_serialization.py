"""
Tests for the serialization functions in the models module.
"""

import unittest
from censyspy.models import (
    Domain,
    DNSMatch,
    CertificateMatch,
    SerializationFormat,
    serialize_flat,
    serialize_unified,
    serialize
)


class TestSerialization(unittest.TestCase):
    """Test the serialization functions in the models module."""

    def setUp(self):
        """Set up test data."""
        # Create test domains
        self.domain1 = Domain("example.com")
        self.domain2 = Domain("api.example.com")
        self.domain3 = Domain("mail.example.com")
        
        # Create DNS matches
        self.dns_match1 = DNSMatch(
            hostname=self.domain1,
            types={"forward"},
            last_updated_at="2023-01-01T00:00:00Z",
            ip="192.0.2.1"
        )
        self.dns_match2 = DNSMatch(
            hostname=self.domain3,
            types={"forward"},
            last_updated_at="2023-01-02T00:00:00Z",
            ip="192.0.2.3"
        )
        
        # Create certificate matches
        self.cert_match1 = CertificateMatch(
            hostname=self.domain1,
            types={"certificate"},
            added_at="2023-02-01T00:00:00Z"
        )
        self.cert_match2 = CertificateMatch(
            hostname=self.domain2,
            types={"certificate"},
            added_at="2023-02-02T00:00:00Z"
        )
        
        # Create test collections
        self.dns_matches = [self.dns_match1, self.dns_match2]
        self.cert_matches = [self.cert_match1, self.cert_match2]

    def test_serialize_flat(self):
        """Test flat serialization format."""
        result = serialize_flat(self.dns_matches, self.cert_matches)
        
        # Expected: sorted list of unique domain names
        expected = ["api.example.com", "example.com", "mail.example.com"]
        
        self.assertEqual(result, expected)
        
        # Test with empty inputs
        self.assertEqual(serialize_flat([], []), [])
        
        # Test with single source
        dns_only = serialize_flat(self.dns_matches, [])
        self.assertEqual(dns_only, ["example.com", "mail.example.com"])
        
        cert_only = serialize_flat([], self.cert_matches)
        self.assertEqual(cert_only, ["api.example.com", "example.com"])

    def test_serialize_unified(self):
        """Test unified serialization format."""
        result = serialize_unified(self.dns_matches, self.cert_matches)
        
        # Verify result structure
        self.assertEqual(len(result), 3)  # Should have 3 unique domains
        
        # Convert to dictionary for easier testing
        result_dict = {item["domain"]: item for item in result}
        
        # Check example.com which should have both DNS and certificate data
        example_data = result_dict["example.com"]
        self.assertEqual(set(example_data["sources"]), {"dns", "certificate"})
        self.assertEqual(example_data["last_updated_at"], "2023-01-01T00:00:00Z")
        self.assertEqual(example_data["added_at"], "2023-02-01T00:00:00Z")
        self.assertEqual(example_data["ip"], "192.0.2.1")
        
        # Check api.example.com which should only have certificate data
        api_data = result_dict["api.example.com"]
        self.assertEqual(api_data["sources"], ["certificate"])
        self.assertEqual(api_data["added_at"], "2023-02-02T00:00:00Z")
        self.assertNotIn("last_updated_at", api_data)
        self.assertNotIn("ip", api_data)
        
        # Check mail.example.com which should only have DNS data
        mail_data = result_dict["mail.example.com"]
        self.assertEqual(mail_data["sources"], ["dns"])
        self.assertEqual(mail_data["last_updated_at"], "2023-01-02T00:00:00Z")
        self.assertEqual(mail_data["ip"], "192.0.2.3")
        self.assertNotIn("added_at", mail_data)
        
        # Test with empty inputs
        self.assertEqual(serialize_unified([], []), [])

    def test_serialize_entry_point(self):
        """Test the main serialize function."""
        # Test FLAT format
        flat_result = serialize(self.dns_matches, self.cert_matches, SerializationFormat.FLAT)
        self.assertEqual(flat_result, ["api.example.com", "example.com", "mail.example.com"])
        
        # Test UNIFIED format
        unified_result = serialize(self.dns_matches, self.cert_matches, SerializationFormat.UNIFIED)
        self.assertEqual(len(unified_result), 3)
        
        # Test default format (should be UNIFIED)
        default_result = serialize(self.dns_matches, self.cert_matches)
        self.assertEqual(len(default_result), 3)
        
        # Test invalid format
        with self.assertRaises(ValueError):
            serialize(self.dns_matches, self.cert_matches, "invalid_format")


if __name__ == '__main__':
    unittest.main()