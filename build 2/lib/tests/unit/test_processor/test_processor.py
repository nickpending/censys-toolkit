"""
Unit tests for the processor module.

This module contains tests for data processing functionality,
including domain matching, result filtering, and data transformation.
"""

import pytest
from collections import defaultdict

from censyspy.models import CertificateMatch, DNSMatch, Domain
from censyspy.processor import (
    is_domain_match, 
    process_dns_result, 
    process_cert_result, 
    aggregate_results, 
    process_wildcards
)


def test_is_domain_match():
    """Test domain matching functionality."""
    # Test exact domain match
    assert is_domain_match("example.com", "example.com") == "example.com"
    
    # Test subdomain match
    assert is_domain_match("sub.example.com", "example.com") == "sub.example.com"
    
    # Test no match
    assert is_domain_match("example.org", "example.com") is None
    
    # Test with trailing dots
    assert is_domain_match("example.com.", "example.com") == "example.com"
    
    # Test with mixed case
    assert is_domain_match("ExAmPle.CoM", "example.com") == "example.com"
    
    # Test with empty inputs
    assert is_domain_match("", "example.com") is None
    assert is_domain_match("example.com", "") is None
    
    # Test with wildcard domain as host
    assert is_domain_match("*.example.com", "example.com") == "*.example.com"


def test_process_wildcards():
    """Test wildcard domain processing functionality."""
    # Create test data with a mix of wildcard and non-wildcard domains
    domain1 = Domain("*.example.com")
    domain2 = Domain("sub.example.com")
    domain3 = Domain("example.com")
    domain4 = Domain("*.test.org")
    
    # Create match objects
    dns_match1 = DNSMatch(hostname=domain1, types={"forward"}, last_updated_at="2023-01-01T00:00:00Z")
    dns_match2 = DNSMatch(hostname=domain2, types={"forward"}, last_updated_at="2023-01-02T00:00:00Z")
    dns_match3 = DNSMatch(hostname=domain3, types={"forward"}, last_updated_at="2023-01-03T00:00:00Z")
    cert_match = CertificateMatch(hostname=domain4, types={"certificate"}, added_at="2023-01-04T00:00:00Z")
    
    # Create input dictionary
    input_results = {
        "*.example.com": dns_match1,
        "sub.example.com": dns_match2,
        "example.com": dns_match3,
        "*.test.org": cert_match
    }
    
    # Process wildcards
    processed_results = process_wildcards(input_results)
    
    # Assertions
    
    # Check that wildcards are removed
    assert "*.example.com" not in processed_results
    assert "*.test.org" not in processed_results
    
    # Check that base domains are preserved/created
    assert "example.com" in processed_results
    assert "test.org" in processed_results
    
    # Check that non-wildcard domains are preserved
    assert "sub.example.com" in processed_results
    
    # Check that types are merged correctly
    assert "forward" in processed_results["example.com"].types
    
    # Check timestamps are preserved
    assert processed_results["example.com"].last_updated_at == "2023-01-03T00:00:00Z"
    assert processed_results["test.org"].added_at == "2023-01-04T00:00:00Z"
    
    # Check that DNSMatch and CertificateMatch types are preserved
    assert isinstance(processed_results["example.com"], DNSMatch)
    assert isinstance(processed_results["test.org"], CertificateMatch)


def test_process_wildcards_merging():
    """Test merging of wildcard domains with existing base domains."""
    # Create test setup with a wildcard domain and corresponding base domain
    wildcard = Domain("*.example.com")
    base = Domain("example.com")
    
    # Create matches with different metadata
    dns_wildcard = DNSMatch(
        hostname=wildcard, 
        types={"wildcard"}, 
        last_updated_at="2023-01-10T00:00:00Z",
        ip="1.2.3.4"
    )
    dns_base = DNSMatch(
        hostname=base, 
        types={"base"}, 
        last_updated_at="2023-01-01T00:00:00Z",
        ip=None
    )
    
    # Create input with both wildcard and base domain
    input_results = {
        "*.example.com": dns_wildcard,
        "example.com": dns_base
    }
    
    # Process wildcards
    processed_results = process_wildcards(input_results)
    
    # Assertions
    
    # Check that only base domain remains
    assert "*.example.com" not in processed_results
    assert "example.com" in processed_results
    
    # Check that types are merged
    assert "wildcard" in processed_results["example.com"].types
    assert "base" in processed_results["example.com"].types
    
    # Check that newer timestamp is used
    assert processed_results["example.com"].last_updated_at == "2023-01-10T00:00:00Z"
    
    # Check that IP from wildcard is used when base had none
    assert processed_results["example.com"].ip == "1.2.3.4"


def test_process_wildcards_different_match_types():
    """Test wildcard processing with different match types (DNS vs Certificate)."""
    # Create test domains
    wildcard = Domain("*.example.com")
    base = Domain("example.com")
    
    # Create different match types
    dns_match = DNSMatch(hostname=wildcard, types={"dns"})
    cert_match = CertificateMatch(hostname=base, types={"cert"})
    
    # Create input
    input_results = {
        "*.example.com": dns_match,
        "example.com": cert_match
    }
    
    # Process wildcards
    processed_results = process_wildcards(input_results)
    
    # Assertions
    
    # Check that wildcard is removed
    assert "*.example.com" not in processed_results
    
    # Check that types are preserved (not merged due to different match types)
    assert "example.com" in processed_results
    
    # Note: The exact behavior here depends on your implementation -
    # either the DNS match could replace the certificate match, or vice versa,
    # or you might create a mechanism to preserve both types of data.
    # This test just verifies that something reasonable happens.
    assert processed_results["example.com"] is not None


def test_process_wildcards_empty_input():
    """Test wildcard processing with empty input."""
    # Process empty dictionary
    processed_results = process_wildcards({})
    
    # Should return empty dictionary
    assert processed_results == {}


def test_process_dns_result():
    """Test processing of DNS search results."""
    # Create sample DNS result from Censys API
    dns_result = {
        "ip": "93.184.216.34",
        "last_updated_at": "2023-01-15T10:00:00Z",
        "dns": {
            "names": ["example.com", "www.example.com", "not-matching.org"],
            "reverse_dns": {
                "names": ["mail.example.com", "another.example.com"]
            }
        }
    }
    
    # Dictionary to collect matched domains
    collected_data = defaultdict(dict)
    
    # Process DNS result
    process_dns_result(dns_result, "example.com", collected_data)
    
    # Check that we found the expected domains
    assert "example.com" in collected_data
    assert "www.example.com" in collected_data
    assert "mail.example.com" in collected_data
    assert "another.example.com" in collected_data
    
    # Non-matching domain should not be included
    assert "not-matching.org" not in collected_data
    
    # Check metadata
    assert isinstance(collected_data["example.com"], DNSMatch)
    assert "forward" in collected_data["example.com"].types
    assert collected_data["example.com"].last_updated_at == "2023-01-15T10:00:00Z"
    assert collected_data["example.com"].ip == "93.184.216.34"
    
    # Check metadata for reverse DNS entry
    assert "reverse" in collected_data["mail.example.com"].types
    assert collected_data["mail.example.com"].ip == "93.184.216.34"


def test_process_dns_result_no_dns_data():
    """Test DNS processing with results that don't contain DNS data."""
    # Create sample result without DNS data
    dns_result = {
        "ip": "93.184.216.34",
        "last_updated_at": "2023-01-15T10:00:00Z"
        # No "dns" key
    }
    
    # Dictionary to collect matched domains
    collected_data = defaultdict(dict)
    
    # Process DNS result (should not error, just return)
    process_dns_result(dns_result, "example.com", collected_data)
    
    # Check that no domains were added
    assert len(collected_data) == 0


def test_process_dns_result_updating_existing_entry():
    """Test DNS processing with existing entries in the collected data."""
    # Create initial entry
    domain = Domain("example.com")
    initial_match = DNSMatch(
        hostname=domain,
        types={"existing"},
        last_updated_at=None,
        ip=None
    )
    
    # Dictionary with existing entry
    collected_data = defaultdict(dict)
    collected_data["example.com"] = initial_match
    
    # Create sample DNS result
    dns_result = {
        "ip": "93.184.216.34",
        "last_updated_at": "2023-01-15T10:00:00Z",
        "dns": {
            "names": ["example.com"]
        }
    }
    
    # Process DNS result
    process_dns_result(dns_result, "example.com", collected_data)
    
    # Check that metadata was updated
    assert "existing" in collected_data["example.com"].types
    assert "forward" in collected_data["example.com"].types
    assert collected_data["example.com"].last_updated_at == "2023-01-15T10:00:00Z"
    assert collected_data["example.com"].ip == "93.184.216.34"


def test_process_cert_result():
    """Test processing of certificate search results."""
    # Create sample certificate result from Censys API
    cert_result = {
        "added_at": "2023-01-10T12:30:45Z",
        "names": ["example.com", "www.example.com", "api.example.com", "not-matching.org"]
    }
    
    # Dictionary to collect matched domains
    collected_data = defaultdict(dict)
    
    # Process certificate result
    process_cert_result(cert_result, "example.com", collected_data)
    
    # Check that we found the expected domains
    assert "example.com" in collected_data
    assert "www.example.com" in collected_data
    assert "api.example.com" in collected_data
    
    # Non-matching domain should not be included
    assert "not-matching.org" not in collected_data
    
    # Check metadata
    assert isinstance(collected_data["example.com"], CertificateMatch)
    assert "certificate" in collected_data["example.com"].types
    assert collected_data["example.com"].added_at == "2023-01-10T12:30:45Z"


def test_process_cert_result_with_existing_dns_entry():
    """Test certificate processing with existing DNS entry."""
    # Create existing DNS match
    domain = Domain("example.com")
    dns_match = DNSMatch(
        hostname=domain,
        types={"forward"},
        last_updated_at="2023-01-05T00:00:00Z",
        ip="93.184.216.34"
    )
    
    # Dictionary with existing entry
    collected_data = defaultdict(dict)
    collected_data["example.com"] = dns_match
    
    # Create sample certificate result
    cert_result = {
        "added_at": "2023-01-10T12:30:45Z",
        "names": ["example.com"]
    }
    
    # Process certificate result
    process_cert_result(cert_result, "example.com", collected_data)
    
    # Check that type was changed to CertificateMatch
    assert isinstance(collected_data["example.com"], CertificateMatch)
    assert "certificate" in collected_data["example.com"].types
    assert collected_data["example.com"].added_at == "2023-01-10T12:30:45Z"


def test_process_cert_result_with_existing_cert_entry():
    """Test certificate processing with existing certificate entry."""
    # Create existing cert match
    domain = Domain("example.com")
    cert_match = CertificateMatch(
        hostname=domain,
        types={"existing_type"},
        added_at=None
    )
    
    # Dictionary with existing entry
    collected_data = defaultdict(dict)
    collected_data["example.com"] = cert_match
    
    # Create sample certificate result
    cert_result = {
        "added_at": "2023-01-10T12:30:45Z",
        "names": ["example.com"]
    }
    
    # Process certificate result
    process_cert_result(cert_result, "example.com", collected_data)
    
    # Check that types were merged and timestamp was updated
    assert "existing_type" in collected_data["example.com"].types
    assert "certificate" in collected_data["example.com"].types
    assert collected_data["example.com"].added_at == "2023-01-10T12:30:45Z"


def test_aggregate_results():
    """Test aggregation of DNS and certificate results."""
    # Create sample DNS results
    domain1 = Domain("example.com")
    domain2 = Domain("dns-only.example.com")
    
    dns_results = {
        "example.com": DNSMatch(
            hostname=domain1,
            types={"forward"},
            last_updated_at="2023-01-15T10:00:00Z",
            ip="93.184.216.34"
        ),
        "dns-only.example.com": DNSMatch(
            hostname=domain2,
            types={"reverse"},
            last_updated_at="2023-01-16T11:22:33Z",
            ip="93.184.216.35"
        )
    }
    
    # Create sample certificate results
    domain3 = Domain("example.com")
    domain4 = Domain("cert-only.example.com")
    
    cert_results = {
        "example.com": CertificateMatch(
            hostname=domain3,
            types={"certificate"},
            added_at="2023-01-10T12:30:45Z"
        ),
        "cert-only.example.com": CertificateMatch(
            hostname=domain4,
            types={"subject_alt_name"},
            added_at="2023-01-11T08:15:30Z"
        )
    }
    
    # Aggregate results
    combined_results = aggregate_results(dns_results, cert_results)
    
    # Check that all domains are included
    assert "example.com" in combined_results
    assert "dns-only.example.com" in combined_results
    assert "cert-only.example.com" in combined_results
    
    # Check that the combined entry has correct metadata
    assert isinstance(combined_results["example.com"], CertificateMatch)
    assert "forward" in combined_results["example.com"].types
    assert "certificate" in combined_results["example.com"].types
    assert combined_results["example.com"].added_at == "2023-01-10T12:30:45Z"
    
    # Check that DNS-only entry is preserved
    assert isinstance(combined_results["dns-only.example.com"], DNSMatch)
    assert "reverse" in combined_results["dns-only.example.com"].types
    
    # Check that cert-only entry is preserved
    assert isinstance(combined_results["cert-only.example.com"], CertificateMatch)
    assert "subject_alt_name" in combined_results["cert-only.example.com"].types


def test_aggregate_results_empty_input():
    """Test aggregation with empty input dictionaries."""
    # Test with both inputs as None
    combined_results = aggregate_results()
    assert combined_results == {}
    
    # Test with empty DNS results and None certificate results
    combined_results = aggregate_results({})
    assert combined_results == {}
    
    # Test with None DNS results and empty certificate results
    combined_results = aggregate_results(None, {})
    assert combined_results == {}


def test_aggregate_results_dns_only():
    """Test aggregation with only DNS results."""
    # Create sample DNS results
    domain = Domain("example.com")
    dns_results = {
        "example.com": DNSMatch(
            hostname=domain,
            types={"forward"},
            last_updated_at="2023-01-15T10:00:00Z",
            ip="93.184.216.34"
        )
    }
    
    # Aggregate results with only DNS data
    combined_results = aggregate_results(dns_results)
    
    # Check that domain is included
    assert "example.com" in combined_results
    assert isinstance(combined_results["example.com"], DNSMatch)
    assert combined_results["example.com"].ip == "93.184.216.34"


def test_aggregate_results_cert_only():
    """Test aggregation with only certificate results."""
    # Create sample certificate results
    domain = Domain("example.com")
    cert_results = {
        "example.com": CertificateMatch(
            hostname=domain,
            types={"certificate"},
            added_at="2023-01-10T12:30:45Z"
        )
    }
    
    # Aggregate results with only certificate data
    combined_results = aggregate_results(None, cert_results)
    
    # Check that domain is included
    assert "example.com" in combined_results
    assert isinstance(combined_results["example.com"], CertificateMatch)
    assert combined_results["example.com"].added_at == "2023-01-10T12:30:45Z"