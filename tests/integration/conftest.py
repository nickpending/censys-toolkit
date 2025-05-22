"""
Fixtures for integration tests.

This module provides fixtures specifically for integration testing,
including mock API responses, CLI runners, and temporary files.
"""

import json
import tempfile
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from censyspy.models import Domain


@pytest.fixture
def cli_runner():
    """Provide a Click CLI runner for testing CLI commands."""
    return CliRunner()


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def sample_dns_api_response():
    """Sample DNS API response data for testing."""
    return [
        {
            "services": [
                {
                    "dns": {
                        "reverse_dns": {
                            "names": ["test.example.com", "api.example.com"]
                        }
                    }
                }
            ],
            "location": {
                "country": "US"
            },
            "last_updated_at": "2024-05-21T12:00:00.000Z"
        },
        {
            "services": [
                {
                    "dns": {
                        "reverse_dns": {
                            "names": ["prod.example.com", "www.example.com"]
                        }
                    }
                }
            ],
            "location": {
                "country": "US"
            },
            "last_updated_at": "2024-05-21T11:00:00.000Z"
        }
    ]


@pytest.fixture
def sample_cert_api_response():
    """Sample certificate API response data for testing."""
    return [
        {
            "parsed": {
                "names": ["example.com", "*.example.com", "test.example.com"],
                "subject": {
                    "common_name": ["example.com"]
                },
                "issuer": {
                    "common_name": ["Let's Encrypt Authority X3"]
                }
            },
            "metadata": {
                "added_at": "2024-05-21T10:00:00.000Z",
                "updated_at": "2024-05-21T12:00:00.000Z"
            }
        },
        {
            "parsed": {
                "names": ["dev.example.com", "staging.example.com"],
                "subject": {
                    "common_name": ["dev.example.com"]
                },
                "issuer": {
                    "common_name": ["DigiCert Inc"]
                }
            },
            "metadata": {
                "added_at": "2024-05-21T09:00:00.000Z",
                "updated_at": "2024-05-21T11:00:00.000Z"
            }
        }
    ]


@pytest.fixture
def mock_api_client(sample_dns_api_response, sample_cert_api_response):
    """Mock API client that returns predefined responses."""
    mock_client = MagicMock()
    
    # Mock the search method to return appropriate responses
    def mock_search(data_type, query, fields, page_size=100, max_pages=-1):
        if data_type == "dns":
            return iter(sample_dns_api_response)
        elif data_type == "certificate":
            return iter(sample_cert_api_response)
        else:
            return iter([])
    
    mock_client.search.side_effect = mock_search
    
    # Mock query builders
    mock_client.build_dns_query.return_value = ("services.dns.reverse_dns.names: example.com", ["services.dns.reverse_dns.names", "location.country", "last_updated_at"])
    mock_client.build_certificate_query.return_value = ("parsed.names: example.com", ["parsed.names", "parsed.subject.common_name", "parsed.issuer.common_name", "metadata.added_at", "metadata.updated_at"])
    
    return mock_client


@pytest.fixture
def sample_json_output_file(temp_dir):
    """Create a sample JSON output file for testing."""
    output_file = temp_dir / "test_results.json"
    sample_data = {
        "example.com": {
            "source": "dns",
            "matched_at": "2024-05-21T12:00:00Z"
        },
        "test.example.com": {
            "source": "certificate", 
            "matched_at": "2024-05-21T12:00:00Z"
        },
        "api.example.com": {
            "source": "dns",
            "matched_at": "2024-05-21T12:00:00Z"
        }
    }
    
    with open(output_file, 'w') as f:
        json.dump(sample_data, f, indent=2)
    
    return output_file


@pytest.fixture
def sample_text_output_file(temp_dir):
    """Create a sample text output file for testing."""
    output_file = temp_dir / "test_domains.txt"
    domains = [
        "example.com",
        "test.example.com", 
        "api.example.com",
        "www.example.com"
    ]
    
    with open(output_file, 'w') as f:
        for domain in domains:
            f.write(f"{domain}\n")
    
    return output_file


@pytest.fixture
def sample_master_list_file(temp_dir):
    """Create a sample master list file for testing."""
    master_file = temp_dir / "master_domains.txt"
    domains = [
        "# Existing master list",
        "example.com",
        "existing.example.com",
        "old.example.com"
    ]
    
    with open(master_file, 'w') as f:
        for line in domains:
            f.write(f"{line}\n")
    
    return master_file


@pytest.fixture
def expected_domains():
    """Expected domains for testing."""
    return [
        Domain("example.com"),
        Domain("test.example.com"),
        Domain("api.example.com"),
        Domain("prod.example.com"),
        Domain("www.example.com"),
        Domain("dev.example.com"),
        Domain("staging.example.com")
    ]


@pytest.fixture 
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing."""
    monkeypatch.setenv("CENSYS_API_ID", "test_api_id")
    monkeypatch.setenv("CENSYS_API_SECRET", "test_api_secret")


