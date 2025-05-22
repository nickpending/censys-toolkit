"""
Tests for the Domain class in the models module.
"""

import unittest
from censyspy.models import Domain


class TestDomain(unittest.TestCase):
    """Test the Domain class functionality."""

    def test_domain_initialization(self):
        """Test basic domain initialization."""
        # Test basic initialization
        domain = Domain("example.com")
        self.assertEqual(domain.name, "example.com")
        
        # Test empty domain (should raise ValueError)
        with self.assertRaises(ValueError):
            Domain("")
            
        # Test None domain (will raise ValueError since None is falsy)
        # In the implementation, it first checks if the name exists,
        # so it raises ValueError instead of TypeError
        with self.assertRaises(ValueError):
            Domain(None)

    def test_domain_normalization(self):
        """Test domain name normalization."""
        # Test lowercase conversion
        domain = Domain("EXAMPLE.COM")
        self.assertEqual(domain.name, "example.com")
        
        # Test trailing dot removal
        domain = Domain("example.com.")
        self.assertEqual(domain.name, "example.com")
        
        # Test multiple trailing dots
        domain = Domain("example.com...")
        self.assertEqual(domain.name, "example.com")
        
        # Test mixed case with trailing dot
        domain = Domain("ExAmPlE.CoM.")
        self.assertEqual(domain.name, "example.com")
        
        # Test normalization via static method
        self.assertEqual(Domain.normalize_domain("EXAMPLE.COM."), "example.com")
        self.assertEqual(Domain.normalize_domain("example.com"), "example.com")

    def test_domain_validation(self):
        """Test domain validation."""
        # Test valid domains (updated for more permissive validation)
        valid_domains = [
            "example.com",
            "sub.example.com", 
            "sub-domain.example.com",
            "xn--fsqu00a.example.com",  # IDN
            "123.example.com",
            "example-1.com",
            "under_score.example.com",  # Underscores now allowed
            "_service._tcp.example.com",  # SRV record format
            "esb-ivr_mc.mx.att.com",  # Real-world example with underscore
            "localhost"  # Special case
        ]
        
        for domain_str in valid_domains:
            # Should not raise any exception
            domain = Domain(domain_str)
            # Validation should return empty list
            self.assertEqual(domain.validate(), [])
            # Static validation should also pass
            self.assertEqual(Domain.validate_str(domain_str), [])
        
        # Test invalid domains (updated for more permissive validation)
        invalid_domains = [
            "a" * 254 + ".com",  # Too long
            "exam ple.com",  # Space (unsafe character)
            "example.com/path",  # Path (unsafe character)
            "example.com:8080",  # Port (unsafe character) 
            "http://example.com",  # Protocol (unsafe character)
            "example@example.com",  # Email (unsafe character)
            '"quoted.domain.com"',  # Quoted (unsafe character)
            "domain\x00null.com",  # Null byte
            "domain\nnewline.com",  # Newline
            "nodot",  # Missing dot (except localhost)
        ]
        
        for domain_str in invalid_domains:
            # Static validation should fail with errors
            errors = Domain.validate_str(domain_str)
            self.assertTrue(len(errors) > 0, f"Expected validation to fail for '{domain_str}'")
            
            # Creating a Domain object should raise ValueError
            with self.assertRaises(ValueError):
                Domain(domain_str)

    def test_wildcard_domain_handling(self):
        """Test wildcard domain handling."""
        # Test wildcard detection
        wildcard = Domain("*.example.com")
        self.assertTrue(wildcard.is_wildcard)
        
        # Test non-wildcard detection
        normal = Domain("example.com")
        self.assertFalse(normal.is_wildcard)
        
        # Test base domain extraction
        self.assertEqual(wildcard.base_domain.name, "example.com")
        self.assertIsNone(normal.base_domain)
        
        # Test wildcard normalization
        self.assertEqual(Domain.normalize_wildcard("*.example.com"), "*.example.com")
        self.assertEqual(Domain.normalize_wildcard(".example.com"), "*.example.com")
        self.assertEqual(Domain.normalize_wildcard("%example.com"), "*.example.com")
        self.assertEqual(Domain.normalize_wildcard("example.com"), "example.com")
        
        # Test factory method
        from_wildcard = Domain.from_wildcard(".example.com")
        self.assertEqual(from_wildcard.name, "*.example.com")
        self.assertTrue(from_wildcard.is_wildcard)
        
        # Note: Current implementation actually allows *.*.example.com patterns
        # and handles them as valid wildcard domains
        double_wildcard = Domain("*.*.example.com")
        self.assertTrue(double_wildcard.is_wildcard)

    def test_domain_properties(self):
        """Test domain properties."""
        # Test is_wildcard property
        self.assertTrue(Domain("*.example.com").is_wildcard)
        self.assertFalse(Domain("example.com").is_wildcard)
        
        # Test base_domain property
        wildcard = Domain("*.example.com")
        base = wildcard.base_domain
        self.assertIsNotNone(base)
        self.assertEqual(base.name, "example.com")
        self.assertFalse(base.is_wildcard)
        
        # Test base_domain returns None for invalid wildcard
        invalid_wildcard = "*.."
        with self.assertRaises(ValueError):
            Domain(invalid_wildcard)

    def test_domain_serialization(self):
        """Test domain serialization."""
        # Test to_dict method
        domain = Domain("example.com")
        expected_dict = {"name": "example.com"}
        self.assertEqual(domain.to_dict(), expected_dict)
        
        # Test from_dict method
        deserialized = Domain.from_dict({"name": "example.org"})
        self.assertEqual(deserialized.name, "example.org")
        
        # Test from_dict with empty dict
        with self.assertRaises(ValueError):
            Domain.from_dict({})
            
        # Test round-trip serialization
        original = Domain("sub.example.com")
        serialized = original.to_dict()
        deserialized = Domain.from_dict(serialized)
        self.assertEqual(original.name, deserialized.name)

    def test_domain_factory_methods(self):
        """Test domain factory methods."""
        # Test from_str method
        domain = Domain.from_str("example.com")
        self.assertEqual(domain.name, "example.com")
        
        # Test from_str with normalization
        domain = Domain.from_str("EXAMPLE.COM.")
        self.assertEqual(domain.name, "example.com")
        
        # Test from_wildcard method
        domain = Domain.from_wildcard(".example.com")
        self.assertEqual(domain.name, "*.example.com")
        self.assertTrue(domain.is_wildcard)
        
        # Test from_dict method
        domain = Domain.from_dict({"name": "example.org"})
        self.assertEqual(domain.name, "example.org")
        
        # Test from_str with invalid input
        with self.assertRaises(ValueError):
            Domain.from_str("")

    def test_domain_string_representation(self):
        """Test domain string representation."""
        domain = Domain("example.com")
        self.assertEqual(str(domain), "example.com")
        
        wildcard = Domain("*.example.com")
        self.assertEqual(str(wildcard), "*.example.com")

    def test_domain_edge_cases(self):
        """Test domain edge cases."""
        # Special case: 'localhost' is explicitly allowed in the implementation
        localhost = Domain("localhost")
        self.assertEqual(localhost.name, "localhost")
            
        # Test special domains
        for special in ["test.local", "example.test", "example.example", "example.invalid"]:
            domain = Domain(special)  # Should not raise exceptions
            self.assertEqual(domain.name, special)
            
        # IP addresses don't match the domain pattern and should fail validation
        with self.assertRaises(ValueError):
            Domain("192.168.1.1")
            
        # Test extremely long domain parts (63 chars is max for each part)
        long_label = "a" * 63
        valid_long = Domain(f"{long_label}.example.com")
        self.assertEqual(valid_long.name, f"{long_label}.example.com")
        
        # Test overall domain length (limited to 253 chars)
        very_long = Domain(f"{long_label}.{long_label}.{long_label}.example.com")
        self.assertEqual(very_long.name, f"{long_label}.{long_label}.{long_label}.example.com")
        
        # Test domain that exceeds max length (253 chars)
        too_long = "a" * 254
        with self.assertRaises(ValueError):
            Domain(too_long)

    def test_domain_error_cases(self):
        """Test domain error cases."""
        # Test error message for empty domain
        try:
            Domain("")
            self.fail("Empty domain should raise ValueError")
        except ValueError as e:
            self.assertIn("cannot be empty", str(e))
            
        # Test error message for invalid format (use something actually invalid)
        try:
            Domain("domain with spaces.com")
            self.fail("Invalid domain should raise ValueError")
        except ValueError as e:
            self.assertIn("unsafe characters", str(e).lower())
            
        # Test error for domain that's too long
        too_long = "a" * 254
        try:
            Domain(too_long)
            self.fail("Too long domain should raise ValueError")
        except ValueError as e:
            self.assertIn("too long", str(e).lower())
            
        # Test validation failure with direct validation
        errors = Domain.validate_str("invalid..domain")
        self.assertTrue(len(errors) > 0)
        self.assertIn("invalid dot placement", errors[0].lower())


if __name__ == '__main__':
    unittest.main()