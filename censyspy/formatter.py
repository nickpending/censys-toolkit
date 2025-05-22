"""
Output formatting module for Censys toolkit.

This module handles the formatting of results from the Censys API
into various output formats, including JSON and text. It provides
a consistent interface for all formatters and a factory function
to create formatters based on the requested format type.

The module includes:
- Output format definitions (JSON, text)
- Formatter interfaces and base classes
- Format-specific implementations
- Factory functions for creating formatters
- Utility functions for console output
"""

import json
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Type, Union, cast

from censyspy.models import CertificateMatch, DNSMatch, SerializationFormat, serialize


class OutputFormat(str, Enum):
    """
    Output format types supported by the formatter.
    
    This enum defines the available output formats for the formatter.
    Currently supports JSON and plain text formats.
    
    Attributes:
        JSON: JSON format for machine readability
        TEXT: Plain text format with one domain per line
    """
    JSON = "json"
    TEXT = "text"
    

# Type definition for output format options
OutputOptions = Dict[str, Any]


class FormatterProtocol(Protocol):
    """
    Protocol defining the interface for formatters.
    
    This protocol ensures that all formatters implement a consistent
    interface regardless of their specific implementation. All formatters
    must provide a format method that converts match data to a string.
    
    This allows for type checking and verification of formatter implementations.
    """
    
    def format(
        self, 
        dns_matches: List[DNSMatch], 
        cert_matches: List[CertificateMatch], 
        **kwargs
    ) -> str:
        """
        Format the matches into a string representation.
        
        Args:
            dns_matches: List of DNS match objects to format
            cert_matches: List of certificate match objects to format
            **kwargs: Additional format-specific options
            
        Returns:
            String representation in the formatter's output format
        """
        ...


class BaseFormatter(ABC):
    """
    Base class for all formatters.
    
    This abstract base class provides the common interface for all
    formatter implementations and ensures they implement the required
    methods. Specific formatters inherit from this class and override
    the format method with their implementation.
    """
    
    @abstractmethod
    def format(
        self, 
        dns_matches: List[DNSMatch], 
        cert_matches: List[CertificateMatch], 
        **kwargs
    ) -> str:
        """
        Format the matches into a string representation.
        
        Args:
            dns_matches: List of DNS match objects to format
            cert_matches: List of certificate match objects to format
            **kwargs: Additional format-specific options
            
        Returns:
            String representation in the formatter's output format
        """
        pass


class JSONFormatter(BaseFormatter):
    """
    Formatter for JSON output.
    
    This formatter converts match data to a JSON string representation.
    It supports different serialization formats (flat, unified) and
    configurable indentation.
    """
    
    def format(
        self, 
        dns_matches: List[DNSMatch], 
        cert_matches: List[CertificateMatch], 
        **kwargs
    ) -> str:
        """
        Format matches as JSON.
        
        Args:
            dns_matches: DNS match objects to format
            cert_matches: Certificate match objects to format
            **kwargs: Additional options including:
                - serialization_format: Format type (flat, unified)
                - indent: JSON indentation level
            
        Returns:
            JSON string representation of the matches
            
        Raises:
            ValueError: If serialization_format is not supported
        """
        # Extract options with defaults
        serialization_format = kwargs.get('serialization_format', SerializationFormat.UNIFIED)
        indent = kwargs.get('indent', 2)
        
        # Validate the serialization format
        if not SerializationFormat.is_valid(serialization_format):
            valid_formats = SerializationFormat.FLAT + ", " + SerializationFormat.UNIFIED
            raise ValueError(
                f"Unsupported serialization format: {serialization_format}. "
                f"Valid formats are: {valid_formats}"
            )
        
        # Use the serialize function from models to get the structured data
        data = serialize(
            dns_matches=dns_matches,
            cert_matches=cert_matches,
            format_type=serialization_format
        )
        
        # Add metadata about the serialization
        result = {
            "format": serialization_format,
            "total_matches": len(data),
            "dns_matches": len(dns_matches),
            "certificate_matches": len(cert_matches),
            "data": data
        }
        
        # Convert to JSON string with specified indentation
        return json.dumps(result, indent=indent)


class TextFormatter(BaseFormatter):
    """
    Formatter for plain text output.
    
    This formatter converts match data to a plain text representation
    with one domain per line. It can optionally include additional
    metadata for each domain.
    """
    
    def format(
        self, 
        dns_matches: List[DNSMatch], 
        cert_matches: List[CertificateMatch], 
        **kwargs
    ) -> str:
        """
        Format matches as plain text (one domain per line).
        
        Args:
            dns_matches: DNS match objects to format
            cert_matches: Certificate match objects to format
            **kwargs: Additional options including:
                - include_metadata: Whether to include metadata like record types and sources
                
        Returns:
            Text string with one domain per line
        """
        # Extract options with defaults
        include_metadata = kwargs.get('include_metadata', False)
        
        # For simple text output, always use the FLAT serialization format
        # which gives us a list of domain names as strings
        domains = serialize(
            dns_matches=dns_matches,
            cert_matches=cert_matches,
            format_type=SerializationFormat.FLAT
        )
        
        if not include_metadata:
            # Simple mode: just return the domains, one per line
            return "\n".join(domains)
        
        # When metadata is requested, we need to gather information from both sources
        # Convert to the unified format which has all metadata combined
        unified_data = serialize(
            dns_matches=dns_matches,
            cert_matches=cert_matches,
            format_type=SerializationFormat.UNIFIED
        )
        
        result_lines = []
        
        # Add a header line
        result_lines.append("# Domains discovered through Censys searches")
        result_lines.append(f"# Total domains: {len(unified_data)}")
        result_lines.append("# Format: domain [sources] [ip] [last_updated/added]")
        result_lines.append("#")
        
        # Process each domain with its metadata
        for entry in unified_data:
            domain = entry["domain"]
            sources = ", ".join(entry.get("sources", []))
            ip = entry.get("ip", "")
            
            # Get the timestamp - prefer last_updated_at, fall back to added_at
            timestamp = entry.get("last_updated_at", entry.get("added_at", ""))
            
            # Format the line with metadata
            line = f"{domain} [{sources}]"
            if ip:
                line += f" [{ip}]"
            if timestamp:
                line += f" [{timestamp}]"
                
            result_lines.append(line)
        
        return "\n".join(result_lines)


def is_valid_format(format_type: str) -> bool:
    """
    Check if the provided format type is supported.
    
    This function validates that a string format type is one of the
    supported output formats defined in the OutputFormat enum.
    
    Args:
        format_type: The format type to validate
        
    Returns:
        True if the format is supported, False otherwise
        
    Examples:
        >>> is_valid_format("json")
        True
        >>> is_valid_format("text")
        True
        >>> is_valid_format("invalid")
        False
    """
    return format_type.lower() in [fmt.value for fmt in OutputFormat]


def normalize_format_type(format_type: Union[str, OutputFormat]) -> OutputFormat:
    """
    Normalize format type to an OutputFormat enum value.
    
    This function handles various input formats (enum or string) and
    normalizes them to a consistent OutputFormat enum value for internal use.
    
    Args:
        format_type: The format type as string or enum
        
    Returns:
        The corresponding OutputFormat enum value
        
    Raises:
        ValueError: If format_type is not a supported format
        
    Examples:
        >>> normalize_format_type("json")
        <OutputFormat.JSON: 'json'>
        >>> normalize_format_type(OutputFormat.TEXT)
        <OutputFormat.TEXT: 'text'>
    """
    # If it's already an OutputFormat enum, just return it
    if isinstance(format_type, OutputFormat):
        return format_type
        
    # If it's a string, try to convert it to an enum
    if isinstance(format_type, str):
        format_str = format_type.lower()
        
        # Try to match with available formats
        for fmt in OutputFormat:
            if fmt.value == format_str:
                return fmt
                
    # If we get here, the format was not found
    valid_formats = ", ".join([f.value for f in OutputFormat])
    raise ValueError(
        f"Unsupported format type: {format_type}. "
        f"Valid formats are: {valid_formats}"
    )


def get_formatter(format_type: Union[str, OutputFormat]) -> FormatterProtocol:
    """
    Return the appropriate formatter for the given format type.
    
    This factory function creates and returns a formatter based on
    the requested format type. It serves as the main entry point
    for creating formatters and supports both string-based format
    types (for CLI integration) and enum-based types (for internal use).
    
    Args:
        format_type: The type of formatter to create (json, text)
                    Can be provided as a string or OutputFormat enum
        
    Returns:
        A formatter instance implementing the FormatterProtocol
        
    Raises:
        ValueError: If format_type is not a supported format
        
    Examples:
        >>> isinstance(get_formatter("json"), JSONFormatter)
        True
        >>> isinstance(get_formatter(OutputFormat.TEXT), TextFormatter)
        True
    """
    # Normalize the format type to an enum
    normalized_format = normalize_format_type(format_type)
    
    # Map of formatters
    formatters = {
        OutputFormat.JSON: JSONFormatter(),
        OutputFormat.TEXT: TextFormatter(),
    }
    
    # Get the formatter (this should not fail since we've already normalized)
    return formatters[normalized_format]


def format_results(
    dns_matches: List[DNSMatch],
    cert_matches: List[CertificateMatch],
    format_type: Union[str, OutputFormat] = OutputFormat.JSON,
    options: Optional[OutputOptions] = None
) -> str:
    """
    Format match results using the appropriate formatter.
    
    This function is the main entry point for formatting match results.
    It delegates to the appropriate formatter based on the format_type.
    The format_type can be provided as a string (e.g., "json", "text")
    or as an OutputFormat enum value for flexibility, especially when
    integrating with command-line interfaces.
    
    Args:
        dns_matches: DNS match objects to format
        cert_matches: Certificate match objects to format
        format_type: Output format type (json, text), can be string or enum
        options: Additional format-specific options
        
    Returns:
        Formatted string in the requested format
        
    Raises:
        ValueError: If format_type is not supported
        
    Examples:
        >>> matches = [Domain("example.com")]
        >>> # Using enum
        >>> format_results(matches, [], OutputFormat.JSON)
        '{"format": "unified", ...}'
        >>> # Using string
        >>> format_results(matches, [], "text")
        'example.com'
    """
    options = options or {}
    formatter = get_formatter(format_type)
    return formatter.format(dns_matches, cert_matches, **options)


def format_console_summary(
    dns_matches: List[DNSMatch],
    cert_matches: List[CertificateMatch],
    max_display: int = 10
) -> str:
    """
    Format a summary of results for display in the console.
    
    This function creates a human-readable summary of the match results,
    including statistics and a sample of the matched domains. It's designed
    to give users a quick overview of their search results without the 
    verbosity of full JSON or text output.
    
    Args:
        dns_matches: DNS match objects to summarize
        cert_matches: Certificate match objects to summarize
        max_display: Maximum number of sample domains to display
        
    Returns:
        Formatted string for console output
        
    Examples:
        >>> format_console_summary(dns_matches, cert_matches)
        '==================================================
        CENSYS SEARCH RESULTS SUMMARY
        ==================================================
        
        STATISTICS:
          Total unique domains: 42
          DNS records: 37
          Certificate records: 15
          
        SAMPLE DOMAINS:
          1. example.com (dns, certificate) [192.0.2.1]
          ...'
    """
    # Get a flat list of all unique domains
    domains = serialize(
        dns_matches=dns_matches,
        cert_matches=cert_matches,
        format_type=SerializationFormat.FLAT
    )
    
    # Use the unified format to get metadata
    unified_data = serialize(
        dns_matches=dns_matches,
        cert_matches=cert_matches,
        format_type=SerializationFormat.UNIFIED
    )
    
    # Create a dictionary to count sources for each domain
    source_counts = {
        "dns": len(dns_matches),
        "certificate": len(cert_matches),
        "total_unique": len(domains)
    }
    
    # Build the summary
    lines = []
    
    # Header section
    lines.append("=" * 50)
    lines.append("CENSYS SEARCH RESULTS SUMMARY")
    lines.append("=" * 50)
    
    # Statistics section
    lines.append("\nSTATISTICS:")
    lines.append(f"  Total unique domains: {source_counts['total_unique']}")
    lines.append(f"  DNS records: {source_counts['dns']}")
    lines.append(f"  Certificate records: {source_counts['certificate']}")
    
    # Sample domains section
    if domains:
        lines.append("\nSAMPLE DOMAINS:")
        
        # Calculate how many domains to display
        display_count = min(max_display, len(domains))
        
        # Display sample domains with their sources
        for i, domain_name in enumerate(domains[:display_count], 1):
            # Find this domain in the unified data to get sources
            domain_data = next((item for item in unified_data if item["domain"] == domain_name), None)
            
            if domain_data:
                sources = ", ".join(domain_data.get("sources", []))
                ip = domain_data.get("ip", "")
                
                # Format the display string
                domain_str = f"  {i}. {domain_name}"
                if sources:
                    domain_str += f" ({sources})"
                if ip:
                    domain_str += f" [{ip}]"
                    
                lines.append(domain_str)
            else:
                # Fallback if domain not found in unified data
                lines.append(f"  {i}. {domain_name}")
        
        # Add a note if there are more domains than what's displayed
        if len(domains) > display_count:
            remaining = len(domains) - display_count
            lines.append(f"\n  ... and {remaining} more domains")
    else:
        lines.append("\nNo matching domains found.")
    
    # Footer
    lines.append("\n" + "=" * 50)
    lines.append("Use --output to save full results to a file")
    lines.append("=" * 50)
    
    return "\n".join(lines)