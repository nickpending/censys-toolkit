"""
Unit tests for the API client module.

This module contains tests for the Censys API client functionality,
including authentication, request handling, and error processing.
"""

import logging
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, Mock

from censys.common.exceptions import (
    CensysException,
    CensysRateLimitExceededException,
    CensysNotFoundException,
    CensysUnauthorizedException,
    CensysInvalidRequestException,
    CensysInternalServerException,
    CensysSearchException,
)

from censyspy.api import CensysClient


@pytest.fixture
def mock_env_credentials(monkeypatch):
    """Set up mock environment variables for testing."""
    monkeypatch.setenv("CENSYS_API_ID", "test_api_id")
    monkeypatch.setenv("CENSYS_API_SECRET", "test_api_secret")


@pytest.fixture
def mock_censys_hosts():
    """Create a mock for the CensysHosts client."""
    with patch("censyspy.api.CensysHosts") as mock:
        # Configure the mock to return a mock account method
        instance = mock.return_value
        instance.account.return_value = {"quota": {"used": 0, "allowance": 100}}
        yield instance


@pytest.fixture
def mock_censys_certs():
    """Create a mock for the CensysCerts client."""
    with patch("censyspy.api.CensysCerts") as mock:
        yield mock.return_value


@pytest.fixture
def api_client(mock_env_credentials, monkeypatch):
    """Create a CensysClient instance for testing."""
    # Create a patcher for _validate_credentials to always return True
    # This avoids the API call in the constructor
    with patch.object(CensysClient, '_validate_credentials', return_value=True):
        return CensysClient()


def test_client_initialization(api_client):
    """Test that the client initializes correctly with credentials."""
    assert api_client.api_id == "test_api_id"
    assert api_client.api_secret == "test_api_secret"
    assert api_client.timeout == 300
    assert api_client.max_retries == 3


def test_client_initialization_with_parameters():
    """Test that the client initializes correctly with provided parameters."""
    with patch.object(CensysClient, '_validate_credentials', return_value=True):
        client = CensysClient(
            api_id="custom_id",
            api_secret="custom_secret",
            timeout=500,
            max_retries=5
        )
        assert client.api_id == "custom_id"
        assert client.api_secret == "custom_secret"
        assert client.timeout == 500
        assert client.max_retries == 5


@patch("censyspy.api.CensysHosts")
def test_authentication_error(mock_hosts, mock_env_credentials):
    """Test that authentication errors are handled correctly."""
    # Configure the mock to raise an auth error
    instance = mock_hosts.return_value
    instance.account.side_effect = CensysUnauthorizedException(401, "Invalid credentials")
    
    with pytest.raises(ValueError, match="Invalid Censys API credentials"):
        CensysClient()


def test_lazy_client_initialization(api_client, mock_censys_hosts, mock_censys_certs):
    """Test that API clients are lazily initialized."""
    # Initially, client instances should be None
    assert api_client._hosts_client is None
    assert api_client._certs_client is None
    
    # Access the clients to trigger initialization
    hosts_client = api_client.hosts_client
    certs_client = api_client.certs_client
    
    # Clients should now be set
    assert api_client._hosts_client is not None
    assert api_client._certs_client is not None


def test_execute_with_retry_success(api_client):
    """Test that execute_with_retry successfully calls the function."""
    mock_func = MagicMock()
    mock_func.return_value = "success"
    
    result = api_client.execute_with_retry(mock_func, "arg1", kwarg1="value1")
    
    assert result == "success"
    mock_func.assert_called_once_with("arg1", kwarg1="value1")


def test_execute_with_retry_rate_limit(api_client, caplog):
    """Test that execute_with_retry handles rate limit errors correctly."""
    caplog.set_level(logging.WARNING)
    
    mock_func = MagicMock()
    mock_func.side_effect = [
        CensysRateLimitExceededException(429, "Rate limit exceeded"),
        "success"
    ]
    
    with patch("time.sleep") as mock_sleep:
        result = api_client.execute_with_retry(mock_func)
        
    assert result == "success"
    assert mock_func.call_count == 2
    assert "Rate limit exceeded" in caplog.text
    mock_sleep.assert_called_once()


def test_execute_with_retry_server_error(api_client, caplog):
    """Test that execute_with_retry handles server errors correctly."""
    caplog.set_level(logging.WARNING)
    
    mock_func = MagicMock()
    mock_func.side_effect = [
        CensysInternalServerException(500, "Server error"),
        "success"
    ]
    
    with patch("time.sleep") as mock_sleep:
        result = api_client.execute_with_retry(mock_func)
        
    assert result == "success"
    assert mock_func.call_count == 2
    assert "Server error" in caplog.text
    mock_sleep.assert_called_once()


def test_execute_with_retry_connection_error(api_client, caplog):
    """Test that execute_with_retry handles connection errors correctly."""
    caplog.set_level(logging.WARNING)
    
    mock_func = MagicMock()
    mock_func.side_effect = [
        ConnectionError("Connection failed"),
        "success"
    ]
    
    with patch("time.sleep") as mock_sleep:
        result = api_client.execute_with_retry(mock_func)
        
    assert result == "success"
    assert mock_func.call_count == 2
    assert "Connection error" in caplog.text
    mock_sleep.assert_called_once()


def test_execute_with_retry_not_found_error(api_client, caplog):
    """Test that execute_with_retry handles not found errors correctly."""
    caplog.set_level(logging.WARNING)
    
    mock_func = MagicMock()
    mock_func.side_effect = CensysNotFoundException(404, "Resource not found")
    
    with pytest.raises(CensysNotFoundException):
        api_client.execute_with_retry(mock_func)
    
    assert mock_func.call_count == 1
    assert "Resource not found" in caplog.text


def test_execute_with_retry_bad_request_error(api_client, caplog):
    """Test that execute_with_retry handles bad request errors correctly."""
    caplog.set_level(logging.ERROR)
    
    mock_func = MagicMock()
    mock_func.side_effect = CensysInvalidRequestException(400, "Bad request")
    
    with pytest.raises(CensysInvalidRequestException):
        api_client.execute_with_retry(mock_func)
    
    assert mock_func.call_count == 1
    assert "Bad request error" in caplog.text


def test_execute_with_retry_search_error(api_client, caplog):
    """Test that execute_with_retry handles search errors correctly."""
    caplog.set_level(logging.ERROR)
    
    mock_func = MagicMock()
    mock_func.side_effect = CensysSearchException(400, "Search error")
    
    with pytest.raises(CensysSearchException):
        api_client.execute_with_retry(mock_func)
    
    assert mock_func.call_count == 1
    assert "Search error" in caplog.text


def test_execute_with_retry_max_retries_exceeded(api_client, caplog):
    """Test that execute_with_retry raises after max retries."""
    caplog.set_level(logging.ERROR)
    
    mock_func = MagicMock()
    mock_func.side_effect = CensysRateLimitExceededException(429, "Rate limit exceeded")
    
    with patch("time.sleep"), pytest.raises(CensysRateLimitExceededException):
        api_client.execute_with_retry(mock_func)
    
    assert mock_func.call_count == api_client.max_retries + 1
    assert "Exhausted retries" in caplog.text


def test_safe_api_call_success(api_client):
    """Test that _safe_api_call successfully handles operations."""
    mock_func = MagicMock()
    mock_func.return_value = "success"
    
    with patch.object(api_client, 'execute_with_retry', return_value="success") as mock_retry:
        result = api_client._safe_api_call("test_operation", mock_func, "arg1", kwarg1="value1")
    
    assert result == "success"
    mock_retry.assert_called_once_with(mock_func, "arg1", kwarg1="value1")


def test_safe_api_call_error(api_client, caplog):
    """Test that _safe_api_call properly handles and logs errors."""
    caplog.set_level(logging.ERROR)
    
    with patch.object(api_client, 'execute_with_retry') as mock_retry:
        mock_retry.side_effect = CensysInternalServerException(500, "Server error")
        
        with pytest.raises(CensysInternalServerException):
            api_client._safe_api_call("test_operation", lambda: None)
    
    assert "Server error during test_operation" in caplog.text


def test_get_account_information(api_client):
    """Test that get_account_information works correctly."""
    expected_result = {"quota": {"used": 0, "allowance": 100}}
    
    with patch.object(api_client, 'execute_with_retry', return_value=expected_result) as mock_retry:
        result = api_client.get_account_information()
    
    assert result == expected_result
    mock_retry.assert_called_once()


def test_get_date_filter_all(api_client):
    """Test that get_date_filter returns None for 'all'."""
    assert api_client.get_date_filter("all") is None
    assert api_client.get_date_filter(None) is None


def test_get_date_filter_days(api_client):
    """Test that get_date_filter returns correct filter for days."""
    # Now the api_client.get_date_filter delegates to utils.get_date_filter
    # so we need to patch utils.get_date_filter instead
    with patch("censyspy.utils.get_date_filter") as mock_get_date_filter:
        mock_get_date_filter.return_value = "[2023-01-08 TO *]"
        
        date_filter = api_client.get_date_filter("7")
        assert date_filter == "[2023-01-08 TO *]"
        mock_get_date_filter.assert_called_once_with("7")


def test_get_date_filter_invalid(api_client):
    """Test that get_date_filter raises for invalid days."""
    with pytest.raises(ValueError):
        api_client.get_date_filter("-1")
        
    with pytest.raises(ValueError):
        api_client.get_date_filter("0")
        
    with pytest.raises(ValueError):
        api_client.get_date_filter("not_a_number")


def test_build_dns_query_basic(api_client):
    """Test that build_dns_query returns correct query and fields."""
    query, fields = api_client.build_dns_query("example.com")
    
    # Verify the query structure
    assert "dns.names: example.com" in query
    assert "dns.reverse_dns.names: example.com" in query
    
    # Verify fields
    assert "ip" in fields
    assert "dns.names" in fields
    assert "dns.reverse_dns.names" in fields
    assert "last_updated_at" in fields


def test_build_dns_query_with_days(api_client):
    """Test that build_dns_query handles days parameter correctly."""
    with patch.object(api_client, 'get_date_filter', return_value="[2023-01-08 TO *]") as mock_filter:
        query, fields = api_client.build_dns_query("example.com", "7")
        
        # Verify the date filter is applied
        assert "last_updated_at:[2023-01-08 TO *]" in query
        mock_filter.assert_called_once_with("7")


def test_build_dns_query_empty_domain(api_client):
    """Test that build_dns_query raises for empty domain."""
    with pytest.raises(ValueError, match="Domain is required"):
        api_client.build_dns_query("")
        
    with pytest.raises(ValueError, match="Domain is required"):
        api_client.build_dns_query(None)


def test_build_certificate_query_basic(api_client):
    """Test that build_certificate_query returns correct query and fields."""
    query, fields = api_client.build_certificate_query("example.com")
    
    # Verify the query structure
    assert "names: example.com" in query
    
    # Verify fields
    assert "names" in fields
    assert "added_at" in fields


def test_build_certificate_query_with_days(api_client):
    """Test that build_certificate_query handles days parameter correctly."""
    with patch.object(api_client, 'get_date_filter', return_value="[2023-01-08 TO *]") as mock_filter:
        query, fields = api_client.build_certificate_query("example.com", "7")
        
        # Verify the date filter is applied
        assert "added_at:[2023-01-08 TO *]" in query
        mock_filter.assert_called_once_with("7")


def test_build_certificate_query_empty_domain(api_client):
    """Test that build_certificate_query raises for empty domain."""
    with pytest.raises(ValueError, match="Domain is required"):
        api_client.build_certificate_query("")
        
    with pytest.raises(ValueError, match="Domain is required"):
        api_client.build_certificate_query(None)


def test_search_with_invalid_data_type(api_client):
    """Test search method with invalid data type."""
    with pytest.raises(ValueError, match="Invalid data_type"):
        list(api_client.search("invalid", "query", ["field"]))


def test_search_dns_success(api_client, mock_censys_hosts):
    """Test search method with DNS queries."""
    mock_results = [{"ip": "192.0.2.1", "dns": {"names": ["example.com"]}}]
    
    with patch.object(api_client, '_safe_api_call') as mock_api_call:
        mock_api_call.return_value = mock_results
        results = list(api_client.search("dns", "dns.names: example.com", ["ip", "dns.names"]))
        
    assert results == mock_results
    mock_api_call.assert_called_once()
    args, kwargs = mock_api_call.call_args
    assert args[0] == "dns search"
    assert kwargs["fields"] == ["ip", "dns.names"]
    assert kwargs["per_page"] == 100
    assert kwargs["pages"] == -1


def test_search_certificate_success(api_client, mock_censys_certs):
    """Test search method with certificate queries."""
    mock_results = [{"names": ["example.com"], "added_at": "2023-01-01"}]
    
    with patch.object(api_client, '_safe_api_call') as mock_api_call:
        mock_api_call.return_value = mock_results
        results = list(api_client.search("certificate", "names: example.com", ["names", "added_at"]))
        
    assert results == mock_results
    mock_api_call.assert_called_once()
    args, kwargs = mock_api_call.call_args
    assert args[0] == "certificate search"
    assert kwargs["fields"] == ["names", "added_at"]


def test_search_with_pagination(api_client):
    """Test pagination handling in search method."""
    # Simulate a paginated response (first page has list, second has single result)
    mock_results = [
        [{"ip": "192.0.2.1"}, {"ip": "192.0.2.2"}],  # Page 1
        {"ip": "192.0.2.3"}                          # Page 2
    ]
    
    with patch.object(api_client, '_safe_api_call') as mock_api_call:
        mock_api_call.return_value = iter(mock_results)
        results = list(api_client.search(
            "dns", 
            "dns.names: example.com", 
            ["ip"], 
            page_size=2, 
            max_pages=2
        ))
        
    # Should flatten the results
    assert len(results) == 3
    assert results[0]["ip"] == "192.0.2.1"
    assert results[1]["ip"] == "192.0.2.2"
    assert results[2]["ip"] == "192.0.2.3"
    
    # Check pagination parameters were passed correctly
    args, kwargs = mock_api_call.call_args
    assert kwargs["per_page"] == 2
    assert kwargs["pages"] == 2


def test_search_no_results(api_client):
    """Test search method with no results."""
    with patch.object(api_client, '_safe_api_call') as mock_api_call:
        mock_api_call.side_effect = CensysNotFoundException(404, "No results found")
        results = list(api_client.search("dns", "dns.names: nonexistent.example", ["ip"]))
        
    assert results == []  # Should return empty list


def test_search_error_handling(api_client):
    """Test error handling during searches."""
    with patch.object(api_client, '_safe_api_call') as mock_api_call:
        mock_api_call.side_effect = CensysException(500, "API error")
        
        with pytest.raises(CensysException):
            list(api_client.search("dns", "dns.names: example.com", ["ip"]))