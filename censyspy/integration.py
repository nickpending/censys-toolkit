"""
Integration module for Censys toolkit.

This module provides the integration layer between the API client and processor,
implementing the data flow from Censys API queries to domain processing.
It connects the various components of the toolkit into a coherent pipeline.
"""

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple, Union, cast

from censyspy.api import CensysClient
from censyspy.formatter import (
    OutputFormat,
    format_results,
    format_console_summary
)
from censyspy.models import CertificateMatch, DNSMatch, Domain
from censyspy.processor import (
    aggregate_results,
    process_cert_result,
    process_dns_result,
    process_wildcards
)

# Set up module logger
logger = logging.getLogger(__name__)


def fetch_and_process_domains(
    domain: str,
    data_type: str = "both",
    days: Optional[str] = None,
    page_size: int = 100,
    max_pages: int = -1,
    api_id: Optional[str] = None,
    api_secret: Optional[str] = None,
    expand_wildcards: bool = True,
    format_output: bool = False,
    output_format: str = "json"
) -> Union[Dict[str, Union[DNSMatch, CertificateMatch]], str]:
    """
    Fetch domain data from Censys API and process it through the full pipeline.
    
    This function implements the complete data flow from API queries to processed
    results. It handles querying the API, processing results through the domain
    matching logic, aggregating results from different sources, and optionally
    expanding wildcard domains.
    
    When format_output is True, the function will also format the processed results
    using the specified output_format, returning a formatted string instead of
    the raw result objects.
    
    The processing pipeline follows these steps:
    1. Fetch data from Censys API (dns, certificate, or both)
    2. Process DNS and certificate results to extract matching domains
    3. Aggregate results from both sources
    4. Process wildcard domains if requested
    
    Args:
        domain: Domain to search for (e.g., "example.com")
        data_type: Type of data to fetch ("dns", "certificate", or "both")
        days: Number of days to filter by (e.g., "7" for last week) or "all" for no filter
        page_size: Number of results per page (max 100)
        max_pages: Maximum number of pages to process (-1 for all pages)
        api_id: Optional Censys API ID (defaults to env variables)
        api_secret: Optional Censys API secret (defaults to env variables)
        expand_wildcards: Whether to process wildcard domains into base domains
        format_output: Whether to format the results into a string
        output_format: Format type to use if format_output is True ("json" or "text")
        
    Returns:
        If format_output is False (default):
            Dictionary mapping domain names to match objects
        If format_output is True:
            Formatted string in the specified output_format
        
    Raises:
        ValueError: If domain or data_type is invalid
    """
    logger.info(f"Starting domain collection for {domain} with type {data_type}")
    
    # Initialize the API client
    api_client = CensysClient(api_id=api_id, api_secret=api_secret)
    
    # Ensure valid data type
    valid_types = ["dns", "certificate", "both"]
    if data_type not in valid_types:
        logger.error(f"Invalid data_type: {data_type}")
        raise ValueError(f"Invalid data_type. Choose from: {', '.join(valid_types)}")
    
    # Process DNS and certificate data based on data_type
    dns_results, cert_results = _process_api_results(
        api_client=api_client,
        domain=domain,
        data_type=data_type,
        days=days,
        page_size=page_size,
        max_pages=max_pages
    )
    
    # Process the raw results into structured data
    results = process_domain_results(
        domain=domain,
        dns_results=dns_results,
        cert_results=cert_results,
        expand_wildcards=expand_wildcards
    )
    
    # If format_output is True, format the results using the specified format
    if format_output:
        return process_and_format(results, output_format)
    
    return results


def process_domain_results(
    domain: str,
    dns_results: List[Dict[str, Any]], 
    cert_results: List[Dict[str, Any]],
    expand_wildcards: bool = True
) -> Dict[str, Union[DNSMatch, CertificateMatch]]:
    """
    Process raw API results into structured domain matches.
    
    This function takes the raw results from the API and processes them through
    the domain matching logic, aggregates results from different sources, and
    optionally processes wildcard domains.
    
    Args:
        domain: Domain pattern to match against
        dns_results: Raw DNS results from the API
        cert_results: Raw certificate results from the API
        expand_wildcards: Whether to process wildcard domains into base domains
        
    Returns:
        Dictionary mapping domain names to match objects
    """
    logger.info(f"Processing results for {domain}: {len(dns_results)} DNS records, "
                f"{len(cert_results)} certificate records")
    
    # Process DNS results
    dns_matches = {}
    if dns_results:
        dns_matches = _process_dns_records(dns_results, domain)
        logger.info(f"Processed {len(dns_matches)} DNS matches")
    
    # Process certificate results
    cert_matches = {}
    if cert_results:
        cert_matches = _process_certificate_records(cert_results, domain)
        logger.info(f"Processed {len(cert_matches)} certificate matches")
    
    # Aggregate results from both sources
    combined_results = aggregate_results(dns_matches, cert_matches)
    logger.info(f"Aggregated {len(combined_results)} unique domains")
    
    # Process wildcards if requested
    if expand_wildcards:
        final_results = process_wildcards(combined_results)
        wildcard_diff = len(combined_results) - len(final_results)
        if wildcard_diff != 0:
            logger.info(f"Wildcard processing: {wildcard_diff} wildcards expanded, "
                      f"{len(final_results)} final domains")
        return final_results
    
    return combined_results


def _process_api_results(
    api_client: CensysClient,
    domain: str,
    data_type: str,
    days: Optional[str] = None,
    page_size: int = 100,
    max_pages: int = -1
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Execute API searches and return raw results for processing.
    
    This function executes the API searches for DNS and/or certificate data
    based on the specified data type, and returns the raw results for further
    processing.
    
    Args:
        api_client: Initialized CensysClient
        domain: Domain to search for
        data_type: Type of data to fetch ("dns", "certificate", or "both")
        days: Number of days to filter by or "all" for no filter
        page_size: Number of results per page
        max_pages: Maximum number of pages to process
        
    Returns:
        Tuple of (dns_results, cert_results) as lists of raw result dictionaries
    """
    dns_results = []
    cert_results = []
    
    # Fetch DNS data if requested
    if data_type in ["dns", "both"]:
        logger.info(f"Fetching DNS data for {domain}")
        query, fields = api_client.build_dns_query(domain, days)
        dns_results = list(api_client.search(
            data_type="dns",
            query=query,
            fields=fields,
            page_size=page_size,
            max_pages=max_pages
        ))
        logger.info(f"Fetched {len(dns_results)} DNS results")
    
    # Fetch certificate data if requested
    if data_type in ["certificate", "both"]:
        logger.info(f"Fetching certificate data for {domain}")
        query, fields = api_client.build_certificate_query(domain, days)
        cert_results = list(api_client.search(
            data_type="certificate",
            query=query,
            fields=fields,
            page_size=page_size,
            max_pages=max_pages
        ))
        logger.info(f"Fetched {len(cert_results)} certificate results")
    
    return dns_results, cert_results


def _process_dns_records(
    dns_results: List[Dict[str, Any]], 
    domain: str
) -> Dict[str, DNSMatch]:
    """
    Process DNS records to extract matching domains.
    
    Args:
        dns_results: Raw DNS results from the API
        domain: Domain pattern to match against
        
    Returns:
        Dictionary mapping domain names to DNSMatch objects
    """
    collected_data = defaultdict(dict)
    
    for result in dns_results:
        process_dns_result(result, domain, collected_data)
    
    return collected_data


def _process_certificate_records(
    cert_results: List[Dict[str, Any]], 
    domain: str
) -> Dict[str, CertificateMatch]:
    """
    Process certificate records to extract matching domains.
    
    Args:
        cert_results: Raw certificate results from the API
        domain: Domain pattern to match against
        
    Returns:
        Dictionary mapping domain names to CertificateMatch objects
    """
    collected_data = defaultdict(dict)
    
    for result in cert_results:
        process_cert_result(result, domain, collected_data)
    
    return collected_data


def process_and_format(
    results: Dict[str, Union[DNSMatch, CertificateMatch]],
    output_format: str = "json",
    **format_options: Any
) -> str:
    """
    Format processor results into the specified output format.
    
    This function serves as the bridge between processor output and formatters.
    It converts the dictionary of match objects into separate lists of DNS and
    certificate matches, then passes them to the appropriate formatter.
    
    Args:
        results: Dictionary of domain matches from the processor
        output_format: Format type to use ("json" or "text")
        **format_options: Additional format-specific options
        
    Returns:
        Formatted string in the specified output format
        
    Raises:
        ValueError: If output_format is not supported
    """
    logger.info(f"Formatting results in {output_format} format")
    
    # Separate results into DNS and certificate matches
    dns_matches = []
    cert_matches = []
    
    for domain_name, match in results.items():
        if isinstance(match, DNSMatch):
            dns_matches.append(match)
        elif isinstance(match, CertificateMatch):
            cert_matches.append(match)
    
    logger.debug(f"Formatting {len(dns_matches)} DNS matches and {len(cert_matches)} certificate matches")
    
    # Use the format_results function from the formatter module
    return format_results(
        dns_matches=dns_matches,
        cert_matches=cert_matches,
        format_type=output_format,
        options=format_options
    )