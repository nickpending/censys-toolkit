"""
API client module for Censys Search.

This module provides a client for interacting with the Censys Search API,
handling authentication, query building, pagination, and error processing.
It builds on the official Censys Python library to add enhanced error handling,
retry logic, and domain-specific query building.
"""

import logging
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, Union

from censys.common.exceptions import (
    CensysException,
    CensysRateLimitExceededException,
    CensysNotFoundException,
    CensysUnauthorizedException,
    CensysInvalidRequestException,
    CensysInternalServerException,
    CensysSearchException,
)
from censys.search import CensysCerts, CensysHosts
from dotenv import load_dotenv

from censyspy import utils

# Load environment variables from .env file
load_dotenv()

# Type definition for collected data structure
DataDict = Dict[str, Dict[str, Union[Set[str], str, None]]]

# Set up module logger
logger = logging.getLogger(__name__)


class CensysClient:
    """
    Client for interacting with the Censys Search API.
    
    This client provides a high-level interface to the Censys Search API, with
    features like automatic retry handling, pagination support, and query building.
    It uses the official Censys SDK but adds additional error handling and 
    domain-specific functionality.
    
    The client handles both the Hosts API (for DNS records) and the Certificates API,
    allowing searches for domains across both data sources.
    """

    def __init__(
        self,
        api_id: Optional[str] = None,
        api_secret: Optional[str] = None,
        timeout: int = 300,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize the Censys API client.
        
        Handles authentication with the Censys API using either explicitly provided
        credentials or environment variables. Validates credentials on initialization
        to ensure they are valid.

        Args:
            api_id: Censys API ID (defaults to CENSYS_API_ID environment variable)
            api_secret: Censys API secret (defaults to CENSYS_API_SECRET environment variable)
            timeout: Timeout for API requests in seconds
            max_retries: Maximum number of retry attempts for failed requests

        Raises:
            ValueError: If API credentials cannot be found or are invalid
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self._hosts_client = None
        self._certs_client = None
        
        # Load API credentials
        self.api_id, self.api_secret = self._load_credentials(api_id, api_secret)
        
        # Validate credentials
        if not self._validate_credentials():
            raise ValueError(
                "Invalid Censys API credentials. Please check your API ID and secret."
            )
            
        logger.debug("CensysClient initialized successfully")
        
    def _load_credentials(self, api_id: Optional[str], api_secret: Optional[str]) -> Tuple[str, str]:
        """
        Load API credentials from parameters or environment variables.
        
        Args:
            api_id: Explicitly provided API ID or None
            api_secret: Explicitly provided API secret or None
            
        Returns:
            Tuple containing API ID and secret
            
        Raises:
            ValueError: If credentials cannot be found
        """
        # First try explicit parameters
        if api_id and api_secret:
            logger.debug("Using explicitly provided API credentials")
            return api_id, api_secret
            
        # Then try environment variables
        env_api_id = os.getenv("CENSYS_API_ID")
        env_api_secret = os.getenv("CENSYS_API_SECRET")
        
        if env_api_id and env_api_secret:
            logger.debug("Using API credentials from environment variables")
            return env_api_id, env_api_secret
            
        # No valid credentials found
        logger.error("No valid Censys API credentials found")
        raise ValueError(
            "Censys API credentials not found. Please provide API ID and secret "
            "either as parameters or set CENSYS_API_ID and CENSYS_API_SECRET "
            "environment variables."
        )

    def _validate_credentials(self) -> bool:
        """
        Validate that the API credentials are valid.
        
        Attempts to retrieve account information to confirm credentials work.
        
        Returns:
            True if credentials are valid, False otherwise
        """
        try:
            # Create a temporary client to validate credentials
            temp_client = CensysHosts(
                api_id=self.api_id, 
                api_secret=self.api_secret, 
                timeout=self.timeout
            )
            
            # Attempt to get account information (lightweight operation)
            temp_client.account()
            logger.debug("API credentials validated successfully")
            return True
            
        except CensysUnauthorizedException:
            logger.error("Invalid API credentials")
            return False
            
        except CensysException as e:
            # Other API errors might indicate service issues, not credential problems
            logger.warning(f"Could not validate credentials: {str(e)}")
            # Assume credentials are valid but service has issues
            return True

    @property
    def hosts_client(self) -> CensysHosts:
        """
        Get the Censys Hosts API client, initializing it if needed.
        
        Returns:
            CensysHosts client instance
        """
        if not self._hosts_client:
            logger.debug("Initializing Censys Hosts client")
            self._hosts_client = CensysHosts(
                api_id=self.api_id, 
                api_secret=self.api_secret, 
                timeout=self.timeout
            )
        return self._hosts_client

    @property
    def certs_client(self) -> CensysCerts:
        """
        Get the Censys Certificates API client, initializing it if needed.
        
        Returns:
            CensysCerts client instance
        """
        if not self._certs_client:
            logger.debug("Initializing Censys Certificates client")
            self._certs_client = CensysCerts(
                api_id=self.api_id, 
                api_secret=self.api_secret, 
                timeout=self.timeout
            )
        return self._certs_client

    def execute_with_retry(
        self, 
        operation_func: callable, 
        *args: Any, 
        **kwargs: Any
    ) -> Any:
        """
        Execute an API operation with retry logic for transient failures.
        
        Implements exponential backoff for recoverable failures like rate limiting,
        connection issues, or temporary server errors. The method distinguishes
        between transient errors (which should be retried) and permanent errors
        (which should be raised immediately).
        
        Transient errors that trigger retries:
        - Rate limiting (CensysRateLimitExceededException)
        - Connection errors (ConnectionError, TimeoutError)
        - Server errors (CensysInternalServerException)
        
        Permanent errors that are raised immediately:
        - Authentication errors (CensysUnauthorizedException)
        - Bad requests (CensysInvalidRequestException)
        - Resource not found (CensysNotFoundException)
        - Search syntax errors (CensysSearchException)
        
        Args:
            operation_func: Function to execute (usually a Censys API method)
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            The result from the operation function
            
        Raises:
            CensysException: For non-transient failures or when retries are exhausted
            ConnectionError: When connection errors persist after max retries
            TimeoutError: When timeout errors persist after max retries
        """
        retry_count = 0
        last_exception = None
        
        while retry_count <= self.max_retries:
            try:
                return operation_func(*args, **kwargs)
                
            except CensysRateLimitExceededException as e:
                logger.warning(f"Rate limit exceeded (attempt {retry_count+1}/{self.max_retries+1})")
                last_exception = e
                
                if retry_count == self.max_retries:
                    break
                    
                # Calculate backoff time (with jitter)
                backoff_time = min(2 ** retry_count + (retry_count * 0.1), 30)
                logger.info(f"Retrying after {backoff_time:.1f} seconds")
                time.sleep(backoff_time)
                
            except (ConnectionError, TimeoutError) as e:
                logger.warning(f"Connection error: {str(e)} (attempt {retry_count+1}/{self.max_retries+1})")
                last_exception = e
                
                if retry_count == self.max_retries:
                    break
                    
                # Calculate backoff time (with jitter)
                backoff_time = min(2 ** retry_count + (retry_count * 0.1), 30)
                logger.info(f"Retrying after {backoff_time:.1f} seconds")
                time.sleep(backoff_time)
                
            except CensysNotFoundException as e:
                # Resource not found is a permanent error, no retry needed
                logger.warning(f"Resource not found: {str(e)}")
                raise
                
            except CensysInvalidRequestException as e:
                # Bad requests are client errors, no retry needed
                logger.error(f"Bad request error: {str(e)}")
                raise
                
            except CensysUnauthorizedException as e:
                # Auth errors are permanent, no retry needed
                logger.error(f"Authentication error: {str(e)}")
                raise
                
            except CensysInternalServerException as e:
                # Server errors might be transient, so retry
                logger.warning(f"Censys server error (attempt {retry_count+1}/{self.max_retries+1}): {str(e)}")
                last_exception = e
                
                if retry_count == self.max_retries:
                    break
                    
                # Calculate backoff time (with jitter)
                backoff_time = min(2 ** retry_count + (retry_count * 0.1), 30)
                logger.info(f"Retrying after {backoff_time:.1f} seconds")
                time.sleep(backoff_time)
                
            except CensysSearchException as e:
                # Search errors are likely permanent, no retry needed
                logger.error(f"Search error: {str(e)}")
                raise
                
            except CensysException as e:
                # Other API errors - assume permanent
                logger.error(f"Censys API error: {str(e)}")
                raise
                
            except Exception as e:
                # Unexpected errors
                logger.error(f"Unexpected error during API operation: {str(e)}")
                raise
                
            retry_count += 1
            
        # If we've exhausted retries, raise the last exception
        if last_exception:
            logger.error(f"Exhausted retries ({self.max_retries}), last error: {str(last_exception)}")
            raise last_exception

    def get_account_information(self) -> Dict[str, Any]:
        """
        Retrieve account information and API quota details.
        
        Gets information about the authenticated account, including API quota usage
        and limits. This method can be useful for checking if you're approaching
        quota limits before running large queries.
        
        The returned dictionary contains information such as:
        - email: The account email address
        - login: The account login name
        - quota: Details about API usage quota including:
          - used: Number of API calls used in current period
          - allowance: Total API calls allowed in current period
          - resets_at: When the quota will reset
        
        Returns:
            Dict containing account information and quota
            
        Raises:
            CensysException: For API errors
        """
        logger.debug("Retrieving account information")
        return self.execute_with_retry(self.hosts_client.account)
    
    def get_date_filter(self, days: Optional[str] = None) -> Optional[str]:
        """
        Generate a date filter string for Censys queries based on days parameter.
        
        Creates a date range filter in the format required by the Censys Search API.
        The filter is based on the number of days from the current date, with
        the format "[START_DATE TO *]" where START_DATE is the date that many
        days in the past.
        
        This method delegates to utils.get_date_filter for implementation.
        
        Args:
            days: Number of days to filter by (as string) or "all" for no filtering.
                 If None or "all", no filter is applied.
            
        Returns:
            A Censys-compatible date filter string or None if no filtering should be applied
            
        Raises:
            ValueError: If days is not a positive integer or "all"
        """
        logger.debug(f"Creating date filter for days: {days}")
        
        try:
            date_filter = utils.get_date_filter(days)
            if date_filter:
                logger.debug(f"Created date filter: {date_filter}")
            else:
                logger.debug("No day filter specified, returning None")
            return date_filter
        except ValueError as e:
            logger.error(f"Invalid days value: {e}")
            raise
    
    def build_dns_query(self, domain: str, days: Optional[str] = None) -> Tuple[str, List[str]]:
        """
        Build a query string and field list for DNS record searches in Censys.
        
        Constructs a query that searches for the specified domain in both forward DNS
        records (dns.names) and reverse DNS records (dns.reverse_dns.names). Optionally
        applies a date filter based on the last_updated_at field.
        
        The query format follows Censys Search API syntax, and returns fields needed
        for DNS record processing including IP addresses and timestamps.
        
        Args:
            domain: The domain to search for (e.g., example.com)
            days: Optional number of days to filter by or "all" for no filtering
            
        Returns:
            Tuple containing (query_string, fields_list) where:
                - query_string: The complete Censys query string
                - fields_list: List of fields to retrieve in search results
            
        Raises:
            ValueError: If domain is empty or invalid
        """
        if not domain:
            logger.error("Domain cannot be empty for DNS query")
            raise ValueError("Domain is required for DNS queries")
            
        logger.debug(f"Building DNS query for domain: {domain}")
        
        # Get date filter if specified
        date_filter = self.get_date_filter(days)
        
        # Standard fields to retrieve for DNS records
        fields = ["ip", "dns.names", "dns.reverse_dns.names", "last_updated_at"]
        
        # Build base query that includes both forward and reverse DNS lookups
        base_query = f"(dns.names: {domain} or dns.reverse_dns.names: {domain})"
        
        # Apply date filter if specified
        if date_filter:
            query = f"({base_query}) and last_updated_at:{date_filter}"
        else:
            query = base_query
            
        logger.debug(f"Generated DNS query: {query}")
        logger.debug(f"Query fields: {fields}")
        
        return query, fields
        
    def build_certificate_query(self, domain: str, days: Optional[str] = None) -> Tuple[str, List[str]]:
        """
        Build a query string and field list for certificate searches in Censys.
        
        Constructs a query that searches for the specified domain in certificate names.
        Optionally applies a date filter based on the added_at field, which represents
        when the certificate was added to the Censys database.
        
        The query format follows Censys Search API syntax for certificate searches,
        and returns fields needed for certificate processing including the names
        list and timestamp.
        
        Args:
            domain: The domain to search for (e.g., example.com)
            days: Optional number of days to filter by or "all" for no filtering
            
        Returns:
            Tuple containing (query_string, fields_list) where:
                - query_string: The complete Censys query string
                - fields_list: List of fields to retrieve in search results
            
        Raises:
            ValueError: If domain is empty or invalid
        """
        if not domain:
            logger.error("Domain cannot be empty for certificate query")
            raise ValueError("Domain is required for certificate queries")
            
        logger.debug(f"Building certificate query for domain: {domain}")
        
        # Get date filter if specified
        date_filter = self.get_date_filter(days)
        
        # Standard fields to retrieve for certificate records
        fields = ["names", "added_at"]
        
        # Build base query that searches for the domain in certificate names
        base_query = f"names: {domain}"
        
        # Apply date filter if specified
        if date_filter:
            query = f"({base_query}) and added_at:{date_filter}"
        else:
            query = base_query
            
        logger.debug(f"Generated certificate query: {query}")
        logger.debug(f"Query fields: {fields}")
        
        return query, fields
        
    def search(
        self,
        data_type: str,
        query: str,
        fields: List[str],
        page_size: int = 100,
        max_pages: int = -1
    ) -> Iterable[Dict[str, Any]]:
        """
        Execute a search query with pagination support.
        
        This method queries the Censys Search API using the specified parameters and
        handles pagination automatically. It leverages the Censys SDK's built-in
        pagination support and adds error handling, logging, and result normalization.
        
        Results are yielded one at a time as they're retrieved, minimizing memory
        usage for large result sets. The method automatically detects and handles
        different result formats returned by the SDK.
        
        For DNS searches, the method uses the CensysHosts client; for certificate
        searches, it uses the CensysCerts client.
        
        Usage example with the query builders:
            query, fields = client.build_dns_query("example.com", "7")
            results = client.search("dns", query, fields)
            for item in results:
                # Process each result
        
        Args:
            data_type: Type of data to search ("dns" or "certificate")
            query: Query string to execute (usually from build_dns_query or build_certificate_query)
            fields: List of fields to return in results
            page_size: Number of results per page (max 100)
            max_pages: Maximum number of pages to retrieve (-1 for all)
            
        Returns:
            Generator yielding result items across all pages
            
        Raises:
            ValueError: For invalid data_type
            CensysException: For API errors (except CensysNotFoundException)
        """
        # Validate data_type
        if data_type not in ("dns", "certificate"):
            logger.error(f"Invalid data_type: {data_type}")
            raise ValueError("Invalid data_type. Choose 'dns' or 'certificate'.")
            
        logger.info(f"Executing {data_type} search with query: {query}")
        logger.debug(f"Search parameters: page_size={page_size}, max_pages={max_pages}")
        logger.debug(f"Requested fields: {fields}")
        
        # Get appropriate client based on data_type
        client = self.hosts_client if data_type == "dns" else self.certs_client
        
        # Execute search with pagination
        try:
            # Use safe_api_call to ensure proper error handling and retries
            search_results = self._safe_api_call(
                f"{data_type} search",
                client.search,
                query,
                fields=fields,
                per_page=page_size,
                pages=max_pages
            )
            
            # Process results
            result_count = 0
            for result in search_results:
                # The SDK's search method can return individual items or lists
                # depending on how results are paged, so normalize to a list
                if isinstance(result, list):
                    items = result
                else:
                    items = [result]
                    
                result_count += len(items)
                logger.debug(f"Processing batch of {len(items)} results (total so far: {result_count})")
                
                # Yield each item individually
                for item in items:
                    yield item
                    
            logger.info(f"Search completed. Total results processed: {result_count}")
            
        except CensysNotFoundException:
            logger.warning(f"No results found for query: {query}")
            # Return empty generator
            return
            
        except CensysException as e:
            logger.error(f"Error during search: {str(e)}")
            raise
    
    def _safe_api_call(self, operation_name: str, call_func, *args, **kwargs) -> Any:
        """
        Execute an API call with standardized error handling and logging.
        
        This is a wrapper around execute_with_retry that adds consistent logging
        for different error types. It provides more detailed error messages that
        include the operation name for better troubleshooting.
        
        The method catches and logs all Censys-specific exceptions with appropriate
        log levels (warning vs error) based on the exception type, then re-raises
        the exception for handling by the caller.
        
        Args:
            operation_name: Name of the operation for logging purposes
            call_func: Function to call (usually a Censys API method)
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            The result from the API call
            
        Raises:
            CensysException: For API errors, with contextual logging
        """
        logger.debug(f"Executing {operation_name}")
        try:
            return self.execute_with_retry(call_func, *args, **kwargs)
        except CensysUnauthorizedException as e:
            logger.error(f"Authentication error during {operation_name}: {str(e)}")
            raise
        except CensysRateLimitExceededException as e:
            logger.error(f"Rate limit exceeded during {operation_name}: {str(e)}")
            raise
        except CensysNotFoundException as e:
            logger.warning(f"Resource not found during {operation_name}: {str(e)}")
            raise
        except CensysInvalidRequestException as e:
            logger.error(f"Bad request during {operation_name}: {str(e)}")
            raise
        except CensysInternalServerException as e:
            logger.error(f"Server error during {operation_name}: {str(e)}")
            raise
        except CensysException as e:
            logger.error(f"Censys API error during {operation_name}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during {operation_name}: {str(e)}")
            raise