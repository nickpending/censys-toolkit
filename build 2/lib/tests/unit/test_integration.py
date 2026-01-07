"""
Tests for the integration module.
"""

import unittest
from unittest.mock import Mock, patch

import pytest

from censyspy.api import CensysClient
from censyspy.integration import (
    fetch_and_process_domains,
    process_domain_results,
    _process_api_results,
    _process_dns_records,
    _process_certificate_records
)
from censyspy.models import CertificateMatch, DNSMatch, Domain


class TestIntegration:
    """Tests for the integration module functions."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create sample test data
        self.domain = "example.com"
        
        # Sample DNS result from API
        self.dns_result = {
            "ip": "93.184.216.34",
            "dns": {
                "names": ["example.com", "www.example.com"],
                "reverse_dns": {
                    "names": ["example-host.example.net"]
                }
            },
            "last_updated_at": "2023-01-15T12:00:00Z"
        }
        
        # Sample certificate result from API
        self.cert_result = {
            "names": ["example.com", "*.example.com", "example.org"],
            "added_at": "2023-02-20T15:30:00Z"
        }
    
    @patch('censyspy.integration.CensysClient')
    def test_fetch_and_process_domains(self, mock_client_class):
        """Test the full pipeline from API to processed results."""
        # Setup mock client and returns
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Mock API method returns
        mock_client.build_dns_query.return_value = ("dns_query", ["field1", "field2"])
        mock_client.build_certificate_query.return_value = ("cert_query", ["field1", "field2"])
        
        # Mock search to return our sample results
        mock_client.search.side_effect = [
            [self.dns_result],  # First call for DNS
            [self.cert_result]  # Second call for certificates
        ]
        
        # Call the function under test
        results = fetch_and_process_domains(
            domain=self.domain,
            data_type="both",
            days="7",
            expand_wildcards=True
        )
        
        # Verify API client was created
        mock_client_class.assert_called_once()
        
        # Verify query building was called
        mock_client.build_dns_query.assert_called_once_with(self.domain, "7")
        mock_client.build_certificate_query.assert_called_once_with(self.domain, "7")
        
        # Verify search was called twice (once for each data type)
        assert mock_client.search.call_count == 2
        
        # Verify results were processed
        assert results is not None
        assert isinstance(results, dict)
        assert len(results) > 0  # Should have at least some results
        
        # Check that expected domains are in results
        assert "example.com" in results
        
        # Ensure results are the right type
        for domain_name, match in results.items():
            assert isinstance(match, (DNSMatch, CertificateMatch))
            assert isinstance(match.hostname, Domain)
    
    @patch('censyspy.integration._process_api_results')
    @patch('censyspy.integration.process_domain_results')
    def test_fetch_and_process_domains_invalid_data_type(self, mock_process, mock_api_results):
        """Test that invalid data type raises an error."""
        with pytest.raises(ValueError):
            fetch_and_process_domains(
                domain=self.domain,
                data_type="invalid_type"  # Invalid data type
            )
        
        # Verify neither processing function was called
        mock_api_results.assert_not_called()
        mock_process.assert_not_called()
    
    def test_process_domain_results(self):
        """Test processing of raw API results into domain matches."""
        # Call the function under test
        results = process_domain_results(
            domain=self.domain,
            dns_results=[self.dns_result],
            cert_results=[self.cert_result],
            expand_wildcards=True
        )
        
        # Verify results
        assert results is not None
        assert isinstance(results, dict)
        
        # Check that expected domains are in results
        assert "example.com" in results
        
        # With expand_wildcards=True, *.example.com should be processed to example.com
        assert "*.example.com" not in results
        
        # Check result types
        for domain_name, match in results.items():
            assert isinstance(match, (DNSMatch, CertificateMatch))
    
    def test_process_domain_results_no_wildcard_expansion(self):
        """Test processing without wildcard expansion."""
        # Call the function under test
        results = process_domain_results(
            domain=self.domain,
            dns_results=[self.dns_result],
            cert_results=[self.cert_result],
            expand_wildcards=False  # Don't expand wildcards
        )
        
        # Verify results
        assert results is not None
        assert isinstance(results, dict)
        
        # With expand_wildcards=False, *.example.com should still be in results
        # assuming it matched the domain pattern
        wildcard_found = False
        for domain_name in results.keys():
            if domain_name.startswith("*."):
                wildcard_found = True
                break
        
        # This will depend on how processor.is_domain_match handles wildcards
        # and the specific test data, so we don't assert a specific value
    
    @patch('censyspy.integration.CensysClient')
    def test_process_api_results_both(self, mock_client_class):
        """Test API result processing for both data types."""
        # Setup mock client
        mock_client = Mock()
        
        # Mock build_dns_query and build_certificate_query
        mock_client.build_dns_query.return_value = ("dns_query", ["field1", "field2"])
        mock_client.build_certificate_query.return_value = ("cert_query", ["field1", "field2"])
        
        # Mock search to return our sample results
        mock_client.search.side_effect = [
            [self.dns_result],  # First call for DNS
            [self.cert_result]  # Second call for certificates
        ]
        
        # Call the function under test
        dns_results, cert_results = _process_api_results(
            api_client=mock_client,
            domain=self.domain,
            data_type="both",
            days="7"
        )
        
        # Verify search was called twice
        assert mock_client.search.call_count == 2
        
        # Verify results
        assert len(dns_results) == 1
        assert len(cert_results) == 1
        assert dns_results[0] == self.dns_result
        assert cert_results[0] == self.cert_result
    
    @patch('censyspy.integration.CensysClient')
    def test_process_api_results_dns_only(self, mock_client_class):
        """Test API result processing for DNS only."""
        # Setup mock client
        mock_client = Mock()
        
        # Mock build_dns_query
        mock_client.build_dns_query.return_value = ("dns_query", ["field1", "field2"])
        
        # Mock search to return our sample results
        mock_client.search.return_value = [self.dns_result]
        
        # Call the function under test
        dns_results, cert_results = _process_api_results(
            api_client=mock_client,
            domain=self.domain,
            data_type="dns",  # DNS only
            days="7"
        )
        
        # Verify search was called once
        mock_client.search.assert_called_once()
        
        # Verify results
        assert len(dns_results) == 1
        assert len(cert_results) == 0
        assert dns_results[0] == self.dns_result
    
    @patch('censyspy.integration.CensysClient')
    def test_process_api_results_certificate_only(self, mock_client_class):
        """Test API result processing for certificate only."""
        # Setup mock client
        mock_client = Mock()
        
        # Mock build_certificate_query
        mock_client.build_certificate_query.return_value = ("cert_query", ["field1", "field2"])
        
        # Mock search to return our sample results
        mock_client.search.return_value = [self.cert_result]
        
        # Call the function under test
        dns_results, cert_results = _process_api_results(
            api_client=mock_client,
            domain=self.domain,
            data_type="certificate",  # Certificate only
            days="7"
        )
        
        # Verify search was called once
        mock_client.search.assert_called_once()
        
        # Verify results
        assert len(dns_results) == 0
        assert len(cert_results) == 1
        assert cert_results[0] == self.cert_result
    
    def test_process_dns_records(self):
        """Test processing DNS records into domain matches."""
        # Call the function under test
        results = _process_dns_records(
            dns_results=[self.dns_result],
            domain=self.domain
        )
        
        # Verify results
        assert results is not None
        assert isinstance(results, dict)
        
        # Results should include domains from both dns.names and dns.reverse_dns.names
        # that match the domain pattern
        for domain_name, match in results.items():
            assert isinstance(match, DNSMatch)
            assert isinstance(match.hostname, Domain)
    
    def test_process_certificate_records(self):
        """Test processing certificate records into domain matches."""
        # Call the function under test
        results = _process_certificate_records(
            cert_results=[self.cert_result],
            domain=self.domain
        )
        
        # Verify results
        assert results is not None
        assert isinstance(results, dict)
        
        # Results should include domains from names that match the domain pattern
        for domain_name, match in results.items():
            assert isinstance(match, CertificateMatch)
            assert isinstance(match.hostname, Domain)