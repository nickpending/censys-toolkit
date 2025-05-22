"""
Master list management for Censys toolkit.

This module provides functionality for managing master lists of domains
discovered through Censys searches. It supports reading, writing, 
and updating text-based master domain lists with deduplication.
"""

import os
from enum import Enum
from pathlib import Path
from typing import List, Optional, Set

from censyspy.models import Domain


class UpdateMode(str, Enum):
    """
    Update modes for master list operations.
    
    This enum defines the available modes for updating a master list:
    - UPDATE: Merge and deduplicate both lists (default behavior)
    - REPLACE: Replace entire list with new domains
    """
    UPDATE = "update"
    REPLACE = "replace"
    
    @classmethod
    def is_valid(cls, mode: str) -> bool:
        """
        Check if the provided update mode is valid.
        
        Args:
            mode: The update mode to validate
            
        Returns:
            True if the mode is valid, False otherwise
        """
        return mode.lower() in [m.value for m in cls]


def read_master_list(file_path: str) -> List[Domain]:
    """
    Read domains from a master list file.
    
    This function reads a text file containing domain names (one per line)
    and converts them to Domain objects. Empty lines and comments 
    (starting with #) are ignored.
    
    Args:
        file_path: Path to the master list file
        
    Returns:
        List of Domain objects
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If the file contains invalid domain names
    """
    domains = []
    
    # Handle case where file doesn't exist yet
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Master list file not found: {file_path}")
    
    with open(file_path, 'r') as f:
        for line in f:
            # Strip whitespace and skip empty lines or comments
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            try:
                # Create a Domain object for validation and normalization
                domain = Domain(line)
                domains.append(domain)
            except ValueError as e:
                # Log the error but continue processing
                print(f"Warning: Skipping invalid domain '{line}': {str(e)}")
    
    return domains


def write_master_list(domains: List[Domain], file_path: str) -> None:
    """
    Write domains to a master list file.
    
    This function writes a list of Domain objects to a text file,
    with one domain per line. The domains are sorted alphabetically
    for consistency.
    
    Args:
        domains: List of Domain objects to write
        file_path: Path to the output file
        
    Raises:
        IOError: If there's an error writing to the file
    """
    # Create directory if it doesn't exist
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
    
    # Sort domains for consistent output
    sorted_domains = sorted(domains, key=lambda d: d.name)
    
    with open(file_path, 'w') as f:
        # Add a header comment
        f.write("# Master list of domains discovered through Censys searches\n")
        f.write(f"# Total domains: {len(sorted_domains)}\n\n")
        
        # Write one domain per line
        for domain in sorted_domains:
            f.write(f"{domain.name}\n")


def deduplicate_domains(domains: List[Domain]) -> List[Domain]:
    """
    Remove duplicate domains from a list.
    
    This function creates a new list with duplicates removed, preserving
    the original order of first appearance. Domains are considered duplicates
    if they have the same normalized name.
    
    Args:
        domains: List of Domain objects potentially containing duplicates
        
    Returns:
        New list with duplicates removed
    """
    seen = set()
    unique_domains = []
    
    for domain in domains:
        if domain.name not in seen:
            seen.add(domain.name)
            unique_domains.append(domain)
    
    return unique_domains


def combine_domain_lists(
    existing: List[Domain], 
    new_domains: List[Domain], 
    mode: str = UpdateMode.UPDATE
) -> List[Domain]:
    """
    Combine two lists of domains according to the specified mode.
    
    Args:
        existing: List of existing Domain objects
        new_domains: List of new Domain objects to add
        mode: Update mode (update or replace)
        
    Returns:
        Combined list of Domain objects
        
    Raises:
        ValueError: If the update mode is invalid
    """
    # Validate the update mode
    if not UpdateMode.is_valid(mode):
        valid_modes = ", ".join([m.value for m in UpdateMode])
        raise ValueError(f"Invalid update mode: {mode}. Valid modes: {valid_modes}")
    
    mode = mode.lower()
    
    # Apply the appropriate combination strategy
    if mode == UpdateMode.REPLACE:
        # Just use the new domains (still deduplicate them)
        return deduplicate_domains(new_domains)
    else:  # mode == UpdateMode.UPDATE (default)
        # Combine both lists and deduplicate
        all_domains = existing + new_domains
        return deduplicate_domains(all_domains)


def update_master_list(
    file_path: str, 
    new_domains: List[Domain], 
    mode: str = UpdateMode.UPDATE
) -> List[Domain]:
    """
    Update a master list file with new domains.
    
    This function reads a master list file, updates it with new domains
    according to the specified mode, and writes the result back to the file.
    If the file doesn't exist, it will be created.
    
    Args:
        file_path: Path to the master list file
        new_domains: List of new Domain objects to add
        mode: Update mode (update or replace)
        
    Returns:
        List of Domain objects in the updated master list
        
    Raises:
        ValueError: If the update mode is invalid
    """
    # If file doesn't exist, create an empty master list
    existing_domains = []
    if os.path.exists(file_path):
        try:
            existing_domains = read_master_list(file_path)
        except FileNotFoundError:
            # This shouldn't happen since we just checked, but handle it anyway
            pass
    
    # Combine the lists according to the update mode
    updated_domains = combine_domain_lists(existing_domains, new_domains, mode)
    
    # Write the updated list back to the file
    write_master_list(updated_domains, file_path)
    
    return updated_domains


def domain_set_difference(
    domains1: List[Domain], 
    domains2: List[Domain]
) -> List[Domain]:
    """
    Find domains in the first list that are not in the second list.
    
    This function is useful for identifying new domains that have been
    added since a previous scan.
    
    Args:
        domains1: First list of Domain objects
        domains2: Second list of Domain objects
        
    Returns:
        List of Domain objects that are in domains1 but not in domains2
    """
    # Create a set of domain names from the second list for efficient lookup
    domains2_names = {domain.name for domain in domains2}
    
    # Filter domains1 to only include domains not in domains2
    difference = [domain for domain in domains1 if domain.name not in domains2_names]
    
    return difference


def count_new_domains(
    new_domains: List[Domain], 
    master_list_path: str
) -> int:
    """
    Count how many domains would be added to the master list.
    
    This function calculates how many new domains are not already
    in the master list, without actually updating the list.
    
    Args:
        new_domains: List of Domain objects to check
        master_list_path: Path to the master list file
        
    Returns:
        Number of new domains that would be added
    """
    # If master list doesn't exist, all domains are new
    if not os.path.exists(master_list_path):
        return len(deduplicate_domains(new_domains))
    
    # Read the existing master list
    existing_domains = read_master_list(master_list_path)
    
    # Deduplicate the new domains first
    unique_domains = deduplicate_domains(new_domains)
    
    # Find domains that are in unique_domains but not in existing_domains
    difference = domain_set_difference(unique_domains, existing_domains)
    
    return len(difference)