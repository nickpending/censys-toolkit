"""
Data models for Censys toolkit.

This module provides data models for domain names and matches
from Censys API searches, including validation and serialization.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Union


@dataclass(frozen=True)
class Domain:
    """
    Represents a domain name with validation and normalization.

    This class provides a standardized representation of a domain name
    that can be searched via the Censys API. It handles normalization
    and implements proper string representation. It also provides support
    for wildcard domains (e.g., *.example.com).

    Domain names are normalized to lowercase and have trailing dots removed.
    Validation includes checking for proper format, length constraints,
    and special handling for wildcard domains.

    Attributes:
        name: The normalized domain name (lowercase, no trailing dots)

    Examples:
        >>> domain = Domain("Example.com.")
        >>> str(domain)
        'example.com'
        
        >>> wildcard = Domain("*.example.com")
        >>> wildcard.is_wildcard
        True
        >>> str(wildcard.base_domain)
        'example.com'
    """
    name: str
    
    def __post_init__(self) -> None:
        """
        Validate and normalize the domain name after initialization.
        
        Raises:
            ValueError: If the domain name is empty or invalid
        """
        if not self.name:
            raise ValueError("Domain name cannot be empty")
            
        # Normalize the domain name (frozen dataclass requires this approach)
        normalized = self.normalize_domain(self.name)
        object.__setattr__(self, 'name', normalized)
        
        # Validate the normalized domain
        errors = self.validate()
        if errors:
            raise ValueError(f"Invalid domain: {'; '.join(errors)}")
    
    @staticmethod
    def normalize_domain(domain: str) -> str:
        """
        Normalize a domain name by converting to lowercase and removing trailing dots.
        
        This method standardizes domain representations to ensure consistent
        comparison and storage. All domain names are converted to lowercase
        and any trailing dots are removed.
        
        Args:
            domain: The domain name to normalize
            
        Returns:
            The normalized domain name
            
        Examples:
            >>> Domain.normalize_domain("Example.com.")
            'example.com'
            >>> Domain.normalize_domain("SUB.DOMAIN.COM")
            'sub.domain.com'
        """
        return domain.lower().rstrip('.')
        
    @staticmethod
    def normalize_wildcard(domain: str) -> str:
        """
        Normalize a wildcard domain pattern to a standard form.
        
        Converts various wildcard notations to the standard '*.domain.com' format.
        Handles forms like '%example.com', '.example.com', etc.
        
        Args:
            domain: The domain name with potential wildcard notation
            
        Returns:
            The normalized wildcard domain
            
        Examples:
            >>> Domain.normalize_wildcard(".example.com")
            '*.example.com'
            >>> Domain.normalize_wildcard("%example.com")
            '*.example.com'
            >>> Domain.normalize_wildcard("*.Example.com.")
            '*.example.com'
        """
        # First normalize the base domain
        domain = domain.lower().rstrip('.')
        
        # Convert various wildcard notations to standard *.domain form
        if domain.startswith('*.'):
            # Already in standard form
            return domain
        elif domain.startswith('.'):
            # .example.com format - convert to *.example.com
            return '*' + domain
        elif domain.startswith('%'):
            # %example.com format (sometimes used in SQL-like patterns)
            return '*.' + domain[1:]
        
        return domain
    
    def validate(self) -> List[str]:
        """
        Validate this domain object and return a list of validation errors.
        
        Performs a series of validation checks:
        1. Ensures the domain name is not empty
        2. For wildcard domains, validates the base domain part
        3. Checks for valid domain format using regex pattern
        4. Verifies length constraints (max 253 characters)
        5. Special handling for test/local domains (.local, .test, etc.)
        
        Returns:
            List of validation error messages (empty if valid)
            
        Examples:
            >>> domain = Domain("example.com")
            >>> domain.validate()
            []
            
            >>> # This would raise ValueError during initialization
            >>> # but we can see what validation errors would occur
            >>> d = object.__new__(Domain)
            >>> object.__setattr__(d, 'name', 'invalid domain!')
            >>> d.validate()
            ['Domain name has invalid format: invalid domain!']
        """
        errors = []
        
        if not self.name:
            errors.append("Domain name cannot be empty")
            return errors
        
        # For wildcard domains, validate the base domain part
        if self.is_wildcard:
            base_domain = self.base_domain
            if base_domain is None:
                errors.append(f"Invalid wildcard domain format: {self.name}")
                return errors
            # The base domain validation will be handled by its own validation
            return []
            
        # Check for valid domain format (simplified)
        # This is a basic validation - in a real implementation, you might
        # want to use a more comprehensive domain validation library
        domain_pattern = r'^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$'
        if not re.match(domain_pattern, self.name) and self.name != 'localhost':
            # Special case for common test domain or local domains
            if not (self.name.endswith('.local') or self.name.endswith('.test') or 
                    self.name.endswith('.example') or self.name.endswith('.invalid')):
                errors.append(f"Domain name has invalid format: {self.name}")
        
        # Check length constraints
        if len(self.name) > 253:
            errors.append("Domain name is too long (max 253 characters)")
            
        return errors
        
    @property
    def is_wildcard(self) -> bool:
        """
        Determine if this is a wildcard domain.
        
        A wildcard domain is one that starts with the '*.'' prefix, indicating
        that it matches any subdomain at that level. For example, '*.example.com'
        matches 'sub1.example.com', 'sub2.example.com', etc.
        
        Returns:
            True if the domain is a wildcard domain (starts with *.)
            
        Examples:
            >>> Domain("example.com").is_wildcard
            False
            >>> Domain("*.example.com").is_wildcard
            True
        """
        return self.name.startswith('*.')
        
    @property
    def base_domain(self) -> Optional['Domain']:
        """
        Extract the base domain without wildcard prefix.
        
        For wildcard domains (*.example.com), returns the base domain
        (example.com). For non-wildcard domains, returns None.
        
        This property is useful when you need to work with the concrete domain
        that a wildcard represents, such as when validating or comparing against
        other domains.
        
        Returns:
            Domain instance with the base domain, or None if not a wildcard
            
        Examples:
            >>> domain = Domain("example.com")
            >>> domain.base_domain is None
            True
            
            >>> wildcard = Domain("*.example.com")
            >>> base = wildcard.base_domain
            >>> str(base)
            'example.com'
        """
        if not self.is_wildcard:
            return None
            
        # Extract the part after '*.'
        base_name = self.name[2:]
        if not base_name:
            return None
            
        try:
            return Domain(base_name)
        except ValueError:
            return None
    
    @classmethod
    def validate_str(cls, domain_str: str) -> List[str]:
        """
        Validate a domain string without creating a full Domain object.
        
        This method allows checking if a domain string is valid without the
        overhead of creating a Domain instance. It normalizes the string and
        runs it through the same validation logic as used by the Domain class.
        
        Args:
            domain_str: Domain name to validate
            
        Returns:
            List of validation error messages (empty if valid)
            
        Examples:
            >>> Domain.validate_str("example.com")
            []
            >>> Domain.validate_str("invalid domain!")
            ['Domain name has invalid format: invalid domain!']
            >>> Domain.validate_str("")
            ['Domain name cannot be empty']
        """
        # First normalize like we would in the constructor
        if not domain_str:
            return ["Domain name cannot be empty"]
            
        normalized = cls.normalize_domain(domain_str)
        
        # Then create a temporary object for validation
        # We use object.__new__ and set attributes directly to avoid
        # triggering __post_init__ validation, which would be recursive
        domain = object.__new__(cls)
        object.__setattr__(domain, 'name', normalized)
        return domain.validate()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the domain object to a dictionary.
        
        Creates a serializable dictionary representation of this domain.
        This is useful for storing domains in JSON format or passing
        between components that work with dictionaries.
        
        Returns:
            A dictionary representation of the domain with a 'name' key
            
        Examples:
            >>> Domain("example.com").to_dict()
            {'name': 'example.com'}
            >>> Domain("*.test.com").to_dict()
            {'name': '*.test.com'}
        """
        return {'name': self.name}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Domain':
        """
        Create a Domain instance from a dictionary.
        
        Factory method that constructs a Domain object from a dictionary
        representation, typically one created by the to_dict method or
        from serialized JSON data.
        
        Args:
            data: A dictionary containing domain data with a 'name' key
            
        Returns:
            A new Domain instance
            
        Raises:
            ValueError: If the dictionary does not contain a name key or the name is invalid
            
        Examples:
            >>> data = {'name': 'example.com'}
            >>> domain = Domain.from_dict(data)
            >>> str(domain)
            'example.com'
            
            >>> # Empty name raises ValueError
            >>> Domain.from_dict({'name': ''})
            Traceback (most recent call last):
              ...
            ValueError: Domain name cannot be empty
        """
        name = data.get('name', '')
        return cls(name=name)
        
    @classmethod
    def from_str(cls, domain_str: str) -> 'Domain':
        """
        Create a Domain instance from a string with normalization.
        
        Factory method that constructs a Domain object from a string
        representation, applying normalization rules before creating
        the instance.
        
        Args:
            domain_str: The domain name string
            
        Returns:
            A new Domain instance
            
        Raises:
            ValueError: If the domain string is empty or invalid
            
        Examples:
            >>> domain = Domain.from_str("Example.com.")
            >>> str(domain)
            'example.com'
            
            >>> # Empty string raises ValueError
            >>> Domain.from_str("")
            Traceback (most recent call last):
              ...
            ValueError: Domain name cannot be empty
        """
        return cls(name=domain_str)
        
    @classmethod
    def from_wildcard(cls, wildcard_str: str) -> 'Domain':
        """
        Create a Domain instance from a wildcard string with normalization.
        
        This method takes a string that may contain wildcard notation in
        various formats and normalizes it to the standard *.domain.com format.
        It handles multiple wildcard formats for flexibility.
        
        Args:
            wildcard_str: The wildcard domain string (e.g., '*.example.com', 
                         '.example.com', '%example.com')
                         
        Returns:
            A new Domain instance with normalized wildcard notation
            
        Raises:
            ValueError: If the wildcard domain string is empty or invalid
            
        Examples:
            >>> domain = Domain.from_wildcard(".example.com")
            >>> str(domain)
            '*.example.com'
            
            >>> domain = Domain.from_wildcard("%subdomains.test.com")
            >>> str(domain)
            '*.subdomains.test.com'
        """
        normalized = cls.normalize_wildcard(wildcard_str)
        return cls(name=normalized)
    
    def __str__(self) -> str:
        """
        Return the string representation of the domain.
        
        Returns the normalized domain name as a string. This allows
        Domain objects to be used directly in string contexts.
        
        Returns:
            The domain name string
            
        Examples:
            >>> str(Domain("example.com"))
            'example.com'
            >>> f"Domain: {Domain('test.org')}"
            'Domain: test.org'
        """
        return self.name


@dataclass
class DNSMatch:
    """
    Represents a DNS match from Censys search results.

    This class provides a structured representation of DNS match data
    returned from the Censys API, including record types and metadata.
    It stores both the domain name and associated information like record
    types, update timestamp, and IP address.

    Attributes:
        hostname: The matched domain name as a Domain object
        types: Set of DNS record types (e.g., "forward", "reverse")
        last_updated_at: When the DNS record was last updated in Censys (ISO format timestamp)
        ip: Optional IP address associated with the record (IPv4 or IPv6)
        source: Source of the data (default is "censys")
        
    Examples:
        >>> from censyspy.models import Domain, DNSMatch
        >>> domain = Domain("example.com")
        >>> match = DNSMatch(
        ...     hostname=domain,
        ...     types={"forward", "a"},
        ...     last_updated_at="2023-01-15T14:32:10Z",
        ...     ip="93.184.216.34"
        ... )
        >>> match.hostname.name
        'example.com'
        >>> 'forward' in match.types
        True
    """

    hostname: Domain
    types: Set[str] = field(default_factory=set)
    last_updated_at: Optional[str] = None
    ip: Optional[str] = None
    source: str = "censys"

    def __post_init__(self) -> None:
        """
        Validate the DNS match data after initialization.
        
        Validates that all fields have the correct types and formats.
        For example, ensures hostname is a Domain object and types is a set.
        
        Raises:
            ValueError: If any validation checks fail
        """
        errors = self.validate()
        if errors:
            raise ValueError(f"Invalid DNS match: {'; '.join(errors)}")
            
    def validate(self) -> List[str]:
        """
        Validate this DNS match and return a list of validation errors.
        
        Performs a series of validation checks on the DNS match object:
        1. Ensures hostname is a Domain object
        2. Verifies types is a set containing only strings
        3. Checks that last_updated_at is either None or a string
        4. Validates IP address format if one is provided
        5. Ensures source is a non-empty string
        
        Returns:
            List of validation error messages (empty if valid)
            
        Examples:
            >>> domain = Domain("example.com")
            >>> match = DNSMatch(hostname=domain)
            >>> match.validate()
            []
            
            >>> # Invalid IP would cause validation errors
            >>> match_with_bad_ip = DNSMatch(hostname=domain, ip="not.an.ip.address")
            >>> "Invalid IP format" in match_with_bad_ip.validate()[0]
            True
        """
        errors = []
        
        # Validate hostname (should be a Domain object)
        if not isinstance(self.hostname, Domain):
            errors.append("Hostname must be a Domain object")
            
        # Validate types (should be a set of strings)
        if not isinstance(self.types, set):
            errors.append("Types must be a set")
        else:
            # Check that all elements in the set are strings
            if not all(isinstance(t, str) for t in self.types):
                errors.append("All record types must be strings")
                
        # Validate last_updated_at (should be None or a string)
        if self.last_updated_at is not None and not isinstance(self.last_updated_at, str):
            errors.append("last_updated_at must be a string or None")
            
        # Validate IP (should be None or a string)
        if self.ip is not None and not isinstance(self.ip, str):
            errors.append("IP must be a string or None")
            
        # IP format validation (basic check if present)
        if self.ip is not None:
            # Simple IPv4 format check
            ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
            if not re.match(ip_pattern, self.ip):
                # Check for IPv6 format (simplified check)
                ipv6_pattern = r'^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$'
                if not re.match(ipv6_pattern, self.ip) and not ':' in self.ip:
                    errors.append(f"Invalid IP format: {self.ip}")
                    
        # Validate source (should be a non-empty string)
        if not isinstance(self.source, str) or not self.source:
            errors.append("Source must be a non-empty string")
            
        return errors
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the DNS match to a dictionary.
        
        Creates a serializable dictionary representation of this DNS match.
        The hostname is converted to its dictionary representation using
        the Domain.to_dict method, and the types set is converted to a list
        for JSON compatibility.
        
        Returns:
            A dictionary representation of the DNS match
            
        Examples:
            >>> domain = Domain("example.com")
            >>> match = DNSMatch(
            ...     hostname=domain,
            ...     types={"forward", "a"},
            ...     ip="93.184.216.34"
            ... )
            >>> result = match.to_dict()
            >>> result["hostname"]["name"]
            'example.com'
            >>> sorted(result["types"])  # Sort for consistent test output
            ['a', 'forward']
            >>> result["ip"]
            '93.184.216.34'
        """
        return {
            'hostname': self.hostname.to_dict(),
            'types': list(self.types),
            'last_updated_at': self.last_updated_at,
            'ip': self.ip,
            'source': self.source
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DNSMatch':
        """
        Create a DNSMatch instance from a dictionary.
        
        Factory method that constructs a DNSMatch object from a dictionary
        representation, typically one created by the to_dict method or
        from serialized JSON data. This method handles different formats
        for the hostname field (either as a dictionary or a string) and
        properly converts list-based types to a set.
        
        Args:
            data: A dictionary containing DNS match data
            
        Returns:
            A new DNSMatch instance
            
        Raises:
            ValueError: If the dictionary contains invalid data
            
        Examples:
            >>> data = {
            ...     'hostname': {'name': 'example.com'},
            ...     'types': ['forward', 'a'],
            ...     'ip': '93.184.216.34',
            ...     'last_updated_at': '2023-01-15T14:32:10Z'
            ... }
            >>> match = DNSMatch.from_dict(data)
            >>> str(match.hostname)
            'example.com'
            >>> sorted(list(match.types))  # Sort for consistent test output
            ['a', 'forward']
            >>> match.ip
            '93.184.216.34'
            
            >>> # It also accepts hostname as a string
            >>> data_with_string = {
            ...     'hostname': 'test.org',
            ...     'types': ['reverse']
            ... }
            >>> match = DNSMatch.from_dict(data_with_string)
            >>> str(match.hostname)
            'test.org'
        """
        # Extract hostname from data, either as a dict or a string
        hostname_data = data.get('hostname', {})
        if isinstance(hostname_data, dict):
            hostname = Domain.from_dict(hostname_data)
        elif isinstance(hostname_data, str):
            hostname = Domain.from_str(hostname_data)
        else:
            raise ValueError(f"Invalid hostname format: {hostname_data}")
            
        # Extract other fields with proper defaults
        types_data = data.get('types', [])
        # Convert types to a set if it's a list
        types = set(types_data) if isinstance(types_data, list) else set()
        
        return cls(
            hostname=hostname,
            types=types,
            last_updated_at=data.get('last_updated_at'),
            ip=data.get('ip'),
            source=data.get('source', 'censys')
        )


@dataclass
class CertificateMatch:
    """
    Represents a certificate match from Censys search results.

    This class provides a structured representation of certificate match data
    returned from the Censys API, including metadata about when the certificate
    was added to the Censys database. Certificate matches represent domains
    found in SSL/TLS certificates indexed by Censys.

    Attributes:
        hostname: The matched domain name as a Domain object
        types: Set of match types (typically contains "certificate")
        added_at: When the certificate was added to Censys (ISO format timestamp)
        source: Source of the data (default is "censys")
        
    Examples:
        >>> from censyspy.models import Domain, CertificateMatch
        >>> domain = Domain("example.com")
        >>> match = CertificateMatch(
        ...     hostname=domain,
        ...     types={"certificate", "subject_alt_name"},
        ...     added_at="2023-01-15T14:32:10Z"
        ... )
        >>> match.hostname.name
        'example.com'
        >>> 'certificate' in match.types
        True
    """

    hostname: Domain
    types: Set[str] = field(default_factory=set)
    added_at: Optional[str] = None
    source: str = "censys"

    def __post_init__(self) -> None:
        """
        Validate the certificate match data after initialization.
        
        Validates that all fields have the correct types and formats.
        For example, ensures hostname is a Domain object and types is a set.
        
        Raises:
            ValueError: If any validation checks fail
        """
        errors = self.validate()
        if errors:
            raise ValueError(f"Invalid certificate match: {'; '.join(errors)}")
            
    def validate(self) -> List[str]:
        """
        Validate this certificate match and return a list of validation errors.
        
        Performs a series of validation checks on the certificate match object:
        1. Ensures hostname is a Domain object
        2. Verifies types is a set containing only strings
        3. Checks that added_at is either None or a string
        4. Ensures source is a non-empty string
        
        Returns:
            List of validation error messages (empty if valid)
            
        Examples:
            >>> domain = Domain("example.com")
            >>> match = CertificateMatch(hostname=domain)
            >>> match.validate()
            []
            
            >>> # Invalid hostname would cause validation errors
            >>> import datetime
            >>> match_with_bad_hostname = object.__new__(CertificateMatch)
            >>> object.__setattr__(match_with_bad_hostname, 'hostname', "not-a-domain-object")
            >>> object.__setattr__(match_with_bad_hostname, 'types', set())
            >>> object.__setattr__(match_with_bad_hostname, 'added_at', None)
            >>> object.__setattr__(match_with_bad_hostname, 'source', "censys")
            >>> "Hostname must be a Domain object" in match_with_bad_hostname.validate()
            True
        """
        errors = []
        
        # Validate hostname (should be a Domain object)
        if not isinstance(self.hostname, Domain):
            errors.append("Hostname must be a Domain object")
            
        # Validate types (should be a set of strings)
        if not isinstance(self.types, set):
            errors.append("Types must be a set")
        else:
            # Check that all elements in the set are strings
            if not all(isinstance(t, str) for t in self.types):
                errors.append("All types must be strings")
                
        # Validate added_at (should be None or a string)
        if self.added_at is not None and not isinstance(self.added_at, str):
            errors.append("added_at must be a string or None")
            
        # Validate source (should be a non-empty string)
        if not isinstance(self.source, str) or not self.source:
            errors.append("Source must be a non-empty string")
            
        return errors
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the certificate match to a dictionary.
        
        Creates a serializable dictionary representation of this certificate match.
        The hostname is converted to its dictionary representation using
        the Domain.to_dict method, and the types set is converted to a list
        for JSON compatibility.
        
        Returns:
            A dictionary representation of the certificate match
            
        Examples:
            >>> domain = Domain("example.com")
            >>> match = CertificateMatch(
            ...     hostname=domain,
            ...     types={"certificate", "subject_alt_name"},
            ...     added_at="2023-01-15T14:32:10Z"
            ... )
            >>> result = match.to_dict()
            >>> result["hostname"]["name"]
            'example.com'
            >>> sorted(result["types"])  # Sort for consistent test output
            ['certificate', 'subject_alt_name']
            >>> result["added_at"]
            '2023-01-15T14:32:10Z'
        """
        return {
            'hostname': self.hostname.to_dict(),
            'types': list(self.types),
            'added_at': self.added_at,
            'source': self.source
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CertificateMatch':
        """
        Create a CertificateMatch instance from a dictionary.
        
        Factory method that constructs a CertificateMatch object from a dictionary
        representation, typically one created by the to_dict method or
        from serialized JSON data. This method handles different formats
        for the hostname field (either as a dictionary or a string) and
        properly converts list-based types to a set.
        
        Args:
            data: A dictionary containing certificate match data
            
        Returns:
            A new CertificateMatch instance
            
        Raises:
            ValueError: If the dictionary contains invalid data
            
        Examples:
            >>> data = {
            ...     'hostname': {'name': 'example.com'},
            ...     'types': ['certificate', 'subject_alt_name'],
            ...     'added_at': '2023-01-15T14:32:10Z'
            ... }
            >>> match = CertificateMatch.from_dict(data)
            >>> str(match.hostname)
            'example.com'
            >>> sorted(list(match.types))  # Sort for consistent test output
            ['certificate', 'subject_alt_name']
            >>> match.added_at
            '2023-01-15T14:32:10Z'
            
            >>> # It also accepts hostname as a string
            >>> data_with_string = {
            ...     'hostname': 'test.org',
            ...     'types': ['certificate']
            ... }
            >>> match = CertificateMatch.from_dict(data_with_string)
            >>> str(match.hostname)
            'test.org'
        """
        # Extract hostname from data, either as a dict or a string
        hostname_data = data.get('hostname', {})
        if isinstance(hostname_data, dict):
            hostname = Domain.from_dict(hostname_data)
        elif isinstance(hostname_data, str):
            hostname = Domain.from_str(hostname_data)
        else:
            raise ValueError(f"Invalid hostname format: {hostname_data}")
            
        # Extract other fields with proper defaults
        types_data = data.get('types', [])
        # Convert types to a set if it's a list
        types = set(types_data) if isinstance(types_data, list) else set()
        
        return cls(
            hostname=hostname,
            types=types,
            added_at=data.get('added_at'),
            source=data.get('source', 'censys')
        )


class SerializationFormat:
    """
    Constants for serialization output formats.
    
    This class defines the supported output formats for serializing domain matches.
    It provides constants for format types and utility methods for validation.
    
    The supported formats are:
    
    FLAT: A simple list of domain names without metadata, suitable for piping to other tools.
          This format returns just the domain names as strings.
          
    UNIFIED: A comprehensive format that combines data from both DNS and certificate 
             matches for each domain, showing all available metadata in a single record.
             This format returns dictionaries with combined metadata from all sources.
             
    Examples:
        >>> from censyspy.models import SerializationFormat
        >>> SerializationFormat.FLAT
        'flat'
        >>> SerializationFormat.UNIFIED
        'unified'
        >>> SerializationFormat.is_valid("flat")
        True
        >>> SerializationFormat.is_valid("unknown")
        False
    """

    FLAT = "flat"  # Simple list of FQDNs without metadata
    UNIFIED = "unified"  # Combined data for each FQDN from all sources
    
    @classmethod
    def is_valid(cls, format_type: str) -> bool:
        """
        Check if the provided format type is valid.
        
        Validates that the given format type is one of the supported formats
        (FLAT or UNIFIED). This is used to ensure that only valid format types
        are used in serialization functions.
        
        Args:
            format_type: The format type to validate
            
        Returns:
            True if the format type is valid, False otherwise
            
        Examples:
            >>> SerializationFormat.is_valid(SerializationFormat.FLAT)
            True
            >>> SerializationFormat.is_valid(SerializationFormat.UNIFIED)
            True
            >>> SerializationFormat.is_valid("json")
            False
        """
        return format_type in (cls.FLAT, cls.UNIFIED)


def serialize_flat(
    dns_matches: List[DNSMatch],
    cert_matches: List[CertificateMatch]
) -> List[str]:
    """
    Convert matches to a flat list of unique domain names.
    
    This function extracts domain names from both DNS and certificate matches,
    combines them into a single set to deduplicate, and returns them as a sorted
    list of strings. This format is useful for simple domain enumeration or
    for piping results to other tools that work with domain name lists.
    
    Args:
        dns_matches: List of DNS matches containing domain information
        cert_matches: List of certificate matches containing domain information
        
    Returns:
        List of unique domain names as strings, sorted alphabetically
        
    Examples:
        >>> from censyspy.models import Domain, DNSMatch, CertificateMatch
        >>> domain1 = Domain("example.com")
        >>> domain2 = Domain("test.org")
        >>> dns = [DNSMatch(hostname=domain1), DNSMatch(hostname=domain2)]
        >>> cert = [CertificateMatch(hostname=domain1)]
        >>> result = serialize_flat(dns, cert)
        >>> result
        ['example.com', 'test.org']
    """
    # Extract domain names from both match types
    domain_names = set()
    
    # Add DNS match domains
    for match in dns_matches:
        domain_names.add(str(match.hostname))
    
    # Add certificate match domains
    for match in cert_matches:
        domain_names.add(str(match.hostname))
    
    # Convert to sorted list for consistent output
    return sorted(list(domain_names))


def serialize_unified(
    dns_matches: List[DNSMatch],
    cert_matches: List[CertificateMatch]
) -> List[Dict[str, Any]]:
    """
    Convert matches to a unified format with combined metadata.
    
    This format combines data from both DNS and certificate matches for each
    domain, showing all available metadata in a single record per domain.
    It's useful for getting a comprehensive view of all data associated with
    each domain across different data sources.
    
    The unified format includes:
    - domain: The domain name as a string
    - sources: List of data sources (e.g., "dns", "certificate")
    - last_updated_at: When the DNS record was last updated (if available)
    - added_at: When the certificate was added (if available)
    - ip: IP address associated with the domain (if available)
    
    Args:
        dns_matches: List of DNS matches to combine
        cert_matches: List of certificate matches to combine
        
    Returns:
        List of dictionaries with combined domain data, sorted by domain name
        
    Examples:
        >>> from censyspy.models import Domain, DNSMatch, CertificateMatch
        >>> domain = Domain("example.com")
        >>> dns = [DNSMatch(
        ...     hostname=domain,
        ...     types={"forward"},
        ...     last_updated_at="2023-05-20T10:00:00Z",
        ...     ip="93.184.216.34"
        ... )]
        >>> cert = [CertificateMatch(
        ...     hostname=domain,
        ...     types={"certificate"},
        ...     added_at="2023-04-15T12:30:45Z"
        ... )]
        >>> result = serialize_unified(dns, cert)
        >>> result[0]["domain"]
        'example.com'
        >>> sorted(result[0]["sources"])
        ['certificate', 'dns']
        >>> result[0]["last_updated_at"]
        '2023-05-20T10:00:00Z'
        >>> result[0]["added_at"]
        '2023-04-15T12:30:45Z'
        >>> result[0]["ip"]
        '93.184.216.34'
    """
    # Create a dictionary to store combined data keyed by domain name
    combined_data: Dict[str, Dict[str, Any]] = {}
    
    # Process DNS matches
    for match in dns_matches:
        domain_name = str(match.hostname)
        
        if domain_name not in combined_data:
            # Initialize new domain entry
            combined_data[domain_name] = {
                "domain": domain_name,
                "sources": ["dns"],
                "last_updated_at": match.last_updated_at,
                "ip": match.ip
            }
        else:
            # Update existing entry
            if "dns" not in combined_data[domain_name]["sources"]:
                combined_data[domain_name]["sources"].append("dns")
            
            # Update metadata if previously missing
            if match.last_updated_at:
                combined_data[domain_name]["last_updated_at"] = match.last_updated_at
            
            if match.ip:
                combined_data[domain_name]["ip"] = match.ip
    
    # Process certificate matches
    for match in cert_matches:
        domain_name = str(match.hostname)
        
        if domain_name not in combined_data:
            # Initialize new domain entry
            combined_data[domain_name] = {
                "domain": domain_name,
                "sources": ["certificate"],
                "added_at": match.added_at
            }
        else:
            # Update existing entry
            if "certificate" not in combined_data[domain_name]["sources"]:
                combined_data[domain_name]["sources"].append("certificate")
            
            # Update metadata if previously missing
            if match.added_at:
                combined_data[domain_name]["added_at"] = match.added_at
    
    # Convert the dictionary to a list and sort by domain name for consistent output
    return [combined_data[domain] for domain in sorted(combined_data.keys())]


def serialize(
    dns_matches: List[DNSMatch],
    cert_matches: List[CertificateMatch],
    format_type: str = SerializationFormat.UNIFIED
) -> Union[List[str], List[Dict[str, Any]]]:
    """
    Serialize matches into the specified format.
    
    This function serves as the main entry point for serialization, delegating
    to the appropriate format-specific function based on the format_type.
    It provides a unified interface for all serialization operations, with
    format selection handled through the format_type parameter.
    
    Args:
        dns_matches: List of DNS matches to serialize
        cert_matches: List of certificate matches to serialize
        format_type: Output format (FLAT or UNIFIED), defaults to UNIFIED
        
    Returns:
        Serialized data in the requested format:
          - List[str] for FLAT format
          - List[Dict[str, Any]] for UNIFIED format
        
    Raises:
        ValueError: If format_type is not a supported format
        
    Examples:
        >>> from censyspy.models import Domain, DNSMatch, CertificateMatch, SerializationFormat
        >>> domain = Domain("example.com")
        >>> dns = [DNSMatch(hostname=domain)]
        >>> cert = [CertificateMatch(hostname=domain)]
        
        >>> # Get unified format (default)
        >>> result = serialize(dns, cert)
        >>> isinstance(result, list) and isinstance(result[0], dict)
        True
        >>> result[0]["domain"]
        'example.com'
        
        >>> # Get flat format
        >>> flat_result = serialize(dns, cert, SerializationFormat.FLAT)
        >>> flat_result
        ['example.com']
        
        >>> # Invalid format raises error
        >>> serialize(dns, cert, "unsupported_format")
        Traceback (most recent call last):
          ...
        ValueError: Unsupported format type: unsupported_format
    """
    # Validate format type
    if not SerializationFormat.is_valid(format_type):
        raise ValueError(f"Unsupported format type: {format_type}")
    
    # Delegate to appropriate serialization function
    if format_type == SerializationFormat.FLAT:
        return serialize_flat(dns_matches, cert_matches)
    else:  # UNIFIED format
        return serialize_unified(dns_matches, cert_matches)
