"""Tests for data models."""

import pytest
from censyspy.models import Domain, DNSMatch


class TestDomain:
    """Test suite for the Domain class."""

    def test_domain_initialization(self):
        """Test basic domain initialization."""
        domain = Domain(name="example.com")
        assert domain.name == "example.com"

    def test_domain_normalization(self):
        """Test that domains are properly normalized."""
        # Test lowercase conversion
        domain = Domain(name="EXAMPLE.COM")
        assert domain.name == "example.com"

        # Test trailing dot removal
        domain = Domain(name="example.com.")
        assert domain.name == "example.com"

        # Test both lowercase and trailing dot
        domain = Domain(name="EXAMPLE.COM.")
        assert domain.name == "example.com"

    def test_empty_domain_validation(self):
        """Test validation for empty domains."""
        with pytest.raises(ValueError):
            Domain(name="")

    def test_invalid_domain_validation(self):
        """Test validation for invalid domain formats."""
        invalid_domains = [
            "example",  # No TLD
            "-example.com",  # Starting with hyphen
            "example-.com",  # Ending with hyphen
            "exam ple.com",  # Contains space
            "exam_ple.com",  # Contains underscore
            "a" * 300 + ".com",  # Too long
        ]
        
        for domain in invalid_domains:
            with pytest.raises(ValueError):
                Domain(name=domain)

    def test_valid_domains(self):
        """Test validation for valid domain formats."""
        valid_domains = [
            "example.com",
            "sub.example.com",
            "sub-domain.example.com",
            "123.example.com",
            "example.co.uk",
            "localhost",  # Special case
            "test.local",  # Special TLD
            "test.example",  # Special TLD
            "test.test",  # Special TLD
            "test.invalid",  # Special TLD
        ]
        
        for domain in valid_domains:
            # Should not raise an exception
            assert Domain(name=domain).name == domain.lower()

    def test_normalize_domain(self):
        """Test domain normalization."""
        # Basic normalization
        assert Domain.normalize_domain("EXAMPLE.COM.") == "example.com"
        
        # Empty domain
        assert Domain.normalize_domain("") == ""

    def test_validate_str(self):
        """Test string validation without object creation."""
        # Valid domain
        assert Domain.validate_str("example.com") == []
        
        # Invalid domain
        errors = Domain.validate_str("invalid..domain")
        assert len(errors) > 0
        
        # Empty domain
        errors = Domain.validate_str("")
        assert "empty" in errors[0]

    def test_to_dict(self):
        """Test conversion to dictionary."""
        domain = Domain(name="example.com")
        result = domain.to_dict()
        assert result == {"name": "example.com"}

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {"name": "example.com"}
        domain = Domain.from_dict(data)
        assert domain.name == "example.com"
        
        # Empty dictionary should raise ValueError
        with pytest.raises(ValueError):
            Domain.from_dict({})
        
    def test_from_str(self):
        """Test creation from string."""
        domain = Domain.from_str("example.com")
        assert domain.name == "example.com"
        
        # With normalization
        domain = Domain.from_str("EXAMPLE.COM.")
        assert domain.name == "example.com"

    def test_string_representation(self):
        """Test string representation."""
        domain = Domain(name="example.com")
        assert str(domain) == "example.com"
        
    def test_is_wildcard(self):
        """Test wildcard domain detection."""
        # Wildcard domain
        domain = Domain(name="*.example.com")
        assert domain.is_wildcard is True
        
        # Non-wildcard domain
        domain = Domain(name="example.com")
        assert domain.is_wildcard is False
        
    def test_base_domain(self):
        """Test extracting base domain from wildcard."""
        # Wildcard domain
        domain = Domain(name="*.example.com")
        base = domain.base_domain
        assert base is not None
        assert base.name == "example.com"
        
        # Non-wildcard domain
        domain = Domain(name="example.com")
        assert domain.base_domain is None
        
        # Invalid wildcard (no domain after prefix)
        with pytest.raises(ValueError):
            Domain(name="*.")
            
    def test_normalize_wildcard(self):
        """Test wildcard domain normalization."""
        # Standard wildcard format
        assert Domain.normalize_wildcard("*.example.com") == "*.example.com"
        
        # Leading dot format
        assert Domain.normalize_wildcard(".example.com") == "*.example.com"
        
        # SQL-like wildcard
        assert Domain.normalize_wildcard("%example.com") == "*.example.com"
        
        # Case normalization
        assert Domain.normalize_wildcard("*.EXAMPLE.COM") == "*.example.com"
        
        # Trailing dot removal
        assert Domain.normalize_wildcard("*.example.com.") == "*.example.com"
        
        # Non-wildcard
        assert Domain.normalize_wildcard("example.com") == "example.com"
        
    def test_from_wildcard(self):
        """Test creating Domain from wildcard string."""
        # Standard wildcard format
        domain = Domain.from_wildcard("*.example.com")
        assert domain.name == "*.example.com"
        assert domain.is_wildcard is True
        
        # Leading dot format
        domain = Domain.from_wildcard(".example.com")
        assert domain.name == "*.example.com"
        assert domain.is_wildcard is True
        
        # SQL-like wildcard
        domain = Domain.from_wildcard("%example.com")
        assert domain.name == "*.example.com"
        assert domain.is_wildcard is True
        
        # Non-wildcard input
        domain = Domain.from_wildcard("example.com")
        assert domain.name == "example.com"
        assert domain.is_wildcard is False
        
    def test_wildcard_validation(self):
        """Test that wildcard domains are properly validated."""
        # Valid wildcard domain
        domain = Domain(name="*.example.com")
        assert domain.name == "*.example.com"
        
        # Invalid base domain in wildcard
        with pytest.raises(ValueError):
            Domain(name="*.invalid..com")


class TestDNSMatch:
    """Test suite for the DNSMatch class."""

    def test_dns_match_initialization(self):
        """Test basic DNSMatch initialization."""
        domain = Domain(name="example.com")
        dns_match = DNSMatch(hostname=domain)
        
        assert dns_match.hostname == domain
        assert dns_match.types == set()
        assert dns_match.last_updated_at is None
        assert dns_match.ip is None
        assert dns_match.source == "censys"
        
    def test_dns_match_with_all_fields(self):
        """Test DNSMatch initialization with all fields provided."""
        domain = Domain(name="example.com")
        dns_match = DNSMatch(
            hostname=domain,
            types={"forward", "reverse"},
            last_updated_at="2023-05-15T12:30:45Z",
            ip="192.168.1.1",
            source="test"
        )
        
        assert dns_match.hostname == domain
        assert dns_match.types == {"forward", "reverse"}
        assert dns_match.last_updated_at == "2023-05-15T12:30:45Z"
        assert dns_match.ip == "192.168.1.1"
        assert dns_match.source == "test"
        
    def test_dns_match_validation(self):
        """Test DNSMatch validation."""
        domain = Domain(name="example.com")
        
        # Valid DNS match
        dns_match = DNSMatch(hostname=domain)
        assert dns_match.validate() == []
        
        # Invalid hostname (not a Domain object)
        with pytest.raises(ValueError):
            DNSMatch(hostname="example.com")
            
        # Invalid types (not a set)
        with pytest.raises(ValueError):
            DNSMatch(hostname=domain, types=["forward", "reverse"])
            
        # Invalid IP format
        with pytest.raises(ValueError):
            DNSMatch(hostname=domain, ip="invalid-ip")
            
    def test_dns_match_to_dict(self):
        """Test conversion to dictionary."""
        domain = Domain(name="example.com")
        dns_match = DNSMatch(
            hostname=domain,
            types={"forward"},
            last_updated_at="2023-05-15T12:30:45Z",
            ip="192.168.1.1"
        )
        
        result = dns_match.to_dict()
        expected = {
            'hostname': {'name': 'example.com'},
            'types': ['forward'],  # Set converted to list
            'last_updated_at': "2023-05-15T12:30:45Z",
            'ip': "192.168.1.1",
            'source': "censys"
        }
        
        assert result == expected
        
    def test_dns_match_from_dict(self):
        """Test creation from dictionary."""
        # From dict with hostname as dict
        data = {
            'hostname': {'name': 'example.com'},
            'types': ['forward', 'reverse'],
            'last_updated_at': "2023-05-15T12:30:45Z",
            'ip': "192.168.1.1",
            'source': "test"
        }
        
        dns_match = DNSMatch.from_dict(data)
        assert dns_match.hostname.name == "example.com"
        assert dns_match.types == {"forward", "reverse"}
        assert dns_match.last_updated_at == "2023-05-15T12:30:45Z"
        assert dns_match.ip == "192.168.1.1"
        assert dns_match.source == "test"
        
        # From dict with hostname as string
        data = {
            'hostname': 'example.com',
            'types': ['forward'],
            'ip': "192.168.1.1"
        }
        
        dns_match = DNSMatch.from_dict(data)
        assert dns_match.hostname.name == "example.com"
        assert dns_match.types == {"forward"}
        assert dns_match.ip == "192.168.1.1"
        assert dns_match.source == "censys"  # Default value
        
        # With minimal data
        data = {
            'hostname': 'example.com'
        }
        
        dns_match = DNSMatch.from_dict(data)
        assert dns_match.hostname.name == "example.com"
        assert dns_match.types == set()
        assert dns_match.last_updated_at is None
        assert dns_match.ip is None
        assert dns_match.source == "censys"
        
        # Invalid hostname format
        with pytest.raises(ValueError):
            DNSMatch.from_dict({'hostname': 123})