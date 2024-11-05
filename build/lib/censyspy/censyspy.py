#!/usr/bin/env python3
from censys.search import CensysHosts, CensysCerts
from collections import defaultdict
from typing import Dict, Set, Optional, Union, List
import argparse
import json
import logging
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)



DataTypes = Union[Dict[str, Set[str]], Dict[str, Dict[str, List[str]]]]

def print_banner():
    banner = r"""
  ________  ____  _______  ___________  __  __
 / ___/ _ \/ __ \/ ___/ / / / ___/ __ \/ / / /
/ /__/  __/ / / (__  ) /_/ (__  ) /_/ / /_/ / 
\___/\___/_/ /_/____/\__, /____/ .___/\__, /  
                    /____/    /_/    /____/    
                                     v0.1.0
FQDN Enumeration through Censys Search API
    """
    print(banner)

def is_domain_match(hostname: str, domain: str) -> Optional[str]:
    """Returns hostname if it matches the domain pattern, None otherwise."""
    if not hostname or not domain:
        return None

    hostname = hostname.rstrip('.').lower()
    domain = domain.rstrip('.').lower()
    
    if hostname.endswith(f'.{domain}') or hostname == domain:
        return hostname
    
    return None

def get_date_filter(days: Optional[str]) -> Optional[str]:
    """Generate date filter string for the query based on days parameter."""
    if not days or days == 'all':
        return None
        
    try:
        days_int = int(days)
        if days_int <= 0:
            raise ValueError("Days must be positive")
        
        start_date = (datetime.now() - timedelta(days=days_int)).strftime("%Y-%m-%d")
        return f"[{start_date} TO *]"
    except ValueError as e:
        logger.error(f"Invalid days value: {e}")
        raise

class CensysDataFetcher:
    def __init__(self, debug: bool = False):
        self.debug = debug
        self._hosts_client = None
        self._certs_client = None
        self.timeout = 300  # 5 minute timeout

    @property
    def hosts_client(self):
        if not self._hosts_client:
            self._hosts_client = CensysHosts(timeout=self.timeout)
        return self._hosts_client

    @property
    def certs_client(self):
        if not self._certs_client:
            self._certs_client = CensysCerts(timeout=self.timeout)
        return self._certs_client

    def _build_query(self, data_type: str, domain: Optional[str], days: Optional[str]) -> tuple[str, List[str]]:
        """Build query and fields based on data type, domain, and days filter."""
        date_filter = get_date_filter(days)
    
        if data_type == 'dns':
            base_query = f'dns.names: *.{domain} or dns.names: {domain}' if domain else 'dns.names: *'
            fields = ['ip', 'dns.names', 'dns.reverse_dns.names']
            date_field = 'last_updated_at'
        else:  # certificate
            base_query = f'names: {domain}' if domain else 'names: *'
            fields = ['names']
            date_field = 'added_at'
        
        if date_filter:
            query = f"({base_query}) and {date_field}:{date_filter}"
        else:
            query = base_query
        
        if self.debug:
            logger.debug(f"Generated query: {query}")
        
        return query, fields

    def _process_dns_result(self, result: dict, domain: str, collected_data: defaultdict) -> None:
        """Process DNS search result and update collected data."""
        if 'dns' not in result:
            return

        dns_data = result['dns']
        
        # Process forward DNS names
        for name in dns_data.get('names', []):
            if matched_hostname := is_domain_match(name, domain):
                collected_data[matched_hostname].add('forward')
        
        # Process reverse DNS names
        for name in dns_data.get('reverse_dns', {}).get('names', []):
            if matched_hostname := is_domain_match(name, domain):
                collected_data[matched_hostname].add('reverse')

    def _process_cert_result(self, result: dict, domain: str, collected_data: defaultdict) -> None:
        """Process certificate search result and update collected data."""
        for name in result.get('names', []):
            if matched_hostname := is_domain_match(name, domain):
                collected_data[matched_hostname].add('certificate')

    def fetch_data(self, data_type: str, domain: Optional[str] = None, 
                  days: Optional[str] = None, page_size: int = 100, 
                  max_pages: int = -1) -> Dict[str, Set[str]]:
        """
        Fetch data from Censys Search API for either DNS or certificates.

        Args:
            data_type: Type of data to fetch ('dns' or 'certificate')
            domain: Domain to filter results
            days: Number of days to look back ('1', '3', '7', 'all', or None)
            page_size: Number of results per page
            max_pages: Maximum number of pages to process (-1 for all)

        Returns:
            Dictionary mapping hostnames to sets of record types
        """
        if data_type not in ('dns', 'certificate'):
            raise ValueError("Invalid data_type. Choose 'dns' or 'certificate'.")

        collected_data = defaultdict(set)
        query, fields = self._build_query(data_type, domain, days)
        
        try:
            client = self.hosts_client if data_type == 'dns' else self.certs_client
            search_results = client.search(query, fields=fields, per_page=page_size, pages=max_pages)

            for result in search_results:
                if isinstance(result, list):
                    items = result
                else:
                    items = [result]

                for item in items:
                    if data_type == 'dns':
                        self._process_dns_result(item, domain, collected_data)
                    else:
                        self._process_cert_result(item, domain, collected_data)

        except Exception as e:
            logger.error(f"Error during search: {str(e)}")
            raise

        if self.debug:
            logger.debug(f"Found {len(collected_data)} matches: {dict(collected_data)}")

        return collected_data

def parse_arguments() -> argparse.Namespace:
    """Parse and return command line arguments."""
    parser = argparse.ArgumentParser(description="Fetch DNS and certificate data from Censys Search.")
    parser.add_argument('--data-type', choices=['dns', 'certificate', 'both'], required=True,
                       help='Type of data to fetch')
    parser.add_argument('--domain', help='Domain to filter results (e.g., example.com)')
    parser.add_argument('--days', choices=['1', '3', '7', 'all'],
                       help='Filter results by last update time (1, 3, 7 days, or all)')
    parser.add_argument('--page-size', type=int, default=100,
                       help='Number of results per page (max 100)')
    parser.add_argument('--max-pages', type=int, default=-1,
                       help='Maximum number of pages to process. Use -1 for all pages.')
    parser.add_argument('--output', required=True,
                       help='Output file for JSON results')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug mode')
    parser.add_argument('--json', action='store_true',
                       help='Print full JSON output to console')
    
    return parser.parse_args()

def format_results(data: DataTypes, max_display: int = 10) -> str:
    """Format results for display."""
    output = []
    
    # Handle both types of data structures
    if isinstance(data, dict) and any(isinstance(v, dict) for v in data.values()):
        # Handle nested dictionary structure (for --data-type both)
        for data_type, data_items in data.items():
            output.append(f"\n{data_type.upper()} Data:")
            for i, (name, types) in enumerate(data_items.items(), 1):
                output.append(f"{i}. {name} ({', '.join(types)})")
                if i >= max_display:
                    remaining = len(data_items) - max_display
                    if remaining > 0:
                        output.append(f"... and {remaining} more entries")
                    break
    else:
        # Handle flat dictionary structure (for single data type)
        for i, (name, types) in enumerate(data.items(), 1):
            output.append(f"{i}. {name} ({', '.join(types)})")
            if i >= max_display:
                remaining = len(data) - max_display
                if remaining > 0:
                    output.append(f"... and {remaining} more entries")
                break
    
    return "\n".join(output)

def main():

    print_banner()
    
    args = parse_arguments()
        
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Command line arguments: %s", vars(args))

    fetcher = CensysDataFetcher(debug=args.debug)

    # Fetch data based on type
    if args.data_type == 'both':
        result = {
            'dns': {dns: list(types) for dns, types in 
                   fetcher.fetch_data('dns', args.domain, args.days, args.page_size, args.max_pages).items()},
            'certificate': {cert: list(types) for cert, types in 
                          fetcher.fetch_data('certificate', args.domain, args.days, args.page_size, args.max_pages).items()}
        }
    else:
        collected_data = fetcher.fetch_data(args.data_type, args.domain, args.days, args.page_size, args.max_pages)
        result = {name: list(types) for name, types in collected_data.items()}

    # Write results to file
    with open(args.output, 'w') as f:
        json.dump(result, f, indent=2)
    logger.info(f"Results written to {args.output}")

    # Handle output display - only print once
    if args.json or args.debug:
        print(json.dumps(result, indent=2))
    else:
        print("\nCollected data summary:")
        print(format_results(result))

if __name__ == "__main__":
    main()

