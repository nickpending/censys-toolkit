"""
Unit tests for the masterlist module.

This module contains tests for master list management functionality,
including reading, writing, updating domain lists, domain deduplication
and set operations.
"""

import os
import pytest
from pathlib import Path
from typing import List

from censyspy.models import Domain
from censyspy.masterlist import (
    read_master_list, 
    write_master_list,
    deduplicate_domains,
    combine_domain_lists,
    domain_set_difference,
    count_new_domains,
    update_master_list,
    UpdateMode
)


# Test fixtures
@pytest.fixture
def sample_domains() -> List[Domain]:
    """Create a sample list of Domain objects for testing."""
    return [
        Domain("example.com"),
        Domain("test.org"),
        Domain("subdomain.example.com"),
        Domain("another.domain.com")
    ]


@pytest.fixture
def duplicate_domains() -> List[Domain]:
    """Create a sample list of Domain objects with duplicates."""
    return [
        Domain("example.com"),
        Domain("test.org"),
        Domain("Example.com"),  # Duplicate (different case)
        Domain("subdomain.example.com"),
        Domain("test.org"),     # Duplicate (exact)
        Domain("another.domain.com")
    ]


@pytest.fixture
def master_list_content() -> str:
    """Create sample content for a master list file."""
    return """# Master list of domains discovered through Censys searches
# Total domains: 3

example.com
subdomain.example.com
test.org
"""


@pytest.fixture
def master_list_with_comments_content() -> str:
    """Create sample content with comments and empty lines."""
    return """# Master list of domains discovered through Censys searches
# Total domains: 3

# This is a test domain
example.com

# This is another domain
test.org

# This is a subdomain
subdomain.example.com

# End of list"""


@pytest.fixture
def invalid_domains_content() -> str:
    """Create content with some invalid domains."""
    return """# Master list with valid and invalid domains
valid-domain.com
invalid-domain!
example.com
"""


# Read function tests
def test_read_master_list_valid_file(tmp_path, sample_domains) -> None:
    """Test reading a valid master list file."""
    # Create a test file
    file_path = tmp_path / "valid_list.txt"
    with open(file_path, 'w') as f:
        f.write("example.com\ntest.org\nsubdomain.example.com\n")
    
    # Read the file
    domains = read_master_list(str(file_path))
    
    # Check the results
    assert len(domains) == 3
    domain_names = [d.name for d in domains]
    assert "example.com" in domain_names
    assert "test.org" in domain_names
    assert "subdomain.example.com" in domain_names


def test_read_master_list_empty_file(tmp_path) -> None:
    """Test reading an empty master list file."""
    # Create an empty file
    file_path = tmp_path / "empty_list.txt"
    file_path.touch()
    
    # Read the file
    domains = read_master_list(str(file_path))
    
    # Should return an empty list
    assert len(domains) == 0


def test_read_master_list_with_comments(tmp_path, master_list_with_comments_content) -> None:
    """Test reading a master list file with comments and empty lines."""
    # Create a test file with comments
    file_path = tmp_path / "comments_list.txt"
    with open(file_path, 'w') as f:
        f.write(master_list_with_comments_content)
    
    # Read the file
    domains = read_master_list(str(file_path))
    
    # Should skip comments and empty lines
    assert len(domains) == 3
    domain_names = [d.name for d in domains]
    assert "example.com" in domain_names
    assert "test.org" in domain_names
    assert "subdomain.example.com" in domain_names


def test_read_master_list_file_not_found() -> None:
    """Test reading a non-existent file raises FileNotFoundError."""
    # Use a path that almost certainly doesn't exist
    file_path = "/path/that/does/not/exist/domains.txt"
    
    # Attempt to read the file
    with pytest.raises(FileNotFoundError):
        read_master_list(file_path)


def test_read_master_list_invalid_domains(tmp_path, invalid_domains_content, monkeypatch, capsys) -> None:
    """Test reading a file with some invalid domains."""
    # Create a test file with invalid domains
    file_path = tmp_path / "invalid_domains.txt"
    with open(file_path, 'w') as f:
        f.write(invalid_domains_content)
    
    # Mute stdout during this test to avoid printing the warning messages
    # Read the file (should skip invalid domains with a warning)
    domains = read_master_list(str(file_path))
    
    # Should include only valid domains
    assert len(domains) == 2
    domain_names = [d.name for d in domains]
    assert "valid-domain.com" in domain_names
    assert "example.com" in domain_names
    
    # Check that warnings were printed
    captured = capsys.readouterr()
    assert "Warning: Skipping invalid domain" in captured.out


# Write function tests
def test_write_master_list(tmp_path, sample_domains) -> None:
    """Test writing domains to a master list file."""
    # Define output file
    file_path = tmp_path / "output_list.txt"
    
    # Write domains to file
    write_master_list(sample_domains, str(file_path))
    
    # Verify file exists
    assert file_path.exists()
    
    # Verify content
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Should contain header and all domains (sorted)
    assert "# Master list of domains" in content
    assert "# Total domains: 4" in content
    assert "another.domain.com" in content
    assert "example.com" in content
    assert "subdomain.example.com" in content
    assert "test.org" in content


def test_write_master_list_creates_directory(tmp_path, sample_domains) -> None:
    """Test that write_master_list creates the directory structure if needed."""
    # Define output file in a non-existent directory
    file_path = tmp_path / "new_dir" / "subdir" / "output_list.txt"
    
    # Directory shouldn't exist yet
    assert not file_path.parent.exists()
    
    # Write domains to file
    write_master_list(sample_domains, str(file_path))
    
    # Verify directory and file exist
    assert file_path.parent.exists()
    assert file_path.exists()


def test_write_master_list_sorts_domains(tmp_path, sample_domains) -> None:
    """Test that domains are sorted alphabetically when written."""
    # Define output file
    file_path = tmp_path / "sorted_list.txt"
    
    # Write domains to file
    write_master_list(sample_domains, str(file_path))
    
    # Read back the file (skipping header lines)
    domains = []
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            domains.append(line)
    
    # Check that domains are sorted
    sorted_domains = sorted(domains)
    assert domains == sorted_domains


# Deduplication tests
def test_deduplicate_domains(duplicate_domains) -> None:
    """Test deduplication of domains."""
    # Deduplicate the list
    unique_domains = deduplicate_domains(duplicate_domains)
    
    # Check that duplicates were removed
    assert len(unique_domains) == 4  # Down from 6
    domain_names = [d.name for d in unique_domains]
    assert domain_names.count("example.com") == 1
    assert domain_names.count("test.org") == 1


def test_deduplicate_domains_preserves_order() -> None:
    """Test that deduplication preserves the original order of first appearance."""
    # Create a list with specific order and duplicates
    domains = [
        Domain("first.com"),
        Domain("second.com"),
        Domain("third.com"),
        Domain("First.com"),  # Duplicate of first
        Domain("fourth.com"),
        Domain("Second.com")  # Duplicate of second
    ]
    
    # Deduplicate
    unique_domains = deduplicate_domains(domains)
    
    # Check order is preserved for first occurrences
    domain_names = [d.name for d in unique_domains]
    assert domain_names[0] == "first.com"
    assert domain_names[1] == "second.com"
    assert domain_names[2] == "third.com"
    assert domain_names[3] == "fourth.com"


def test_deduplicate_domains_empty_list() -> None:
    """Test deduplication of an empty domain list."""
    # Deduplicate an empty list
    unique_domains = deduplicate_domains([])
    
    # Should return an empty list
    assert len(unique_domains) == 0


# Domain set operations tests
def test_combine_domain_lists_update_mode(sample_domains) -> None:
    """Test combining domain lists in update mode (default)."""
    # Create two lists
    existing = [Domain("example.com"), Domain("old-domain.com")]
    new_domains = [Domain("example.com"), Domain("new-domain.com")]
    
    # Combine them with default mode (update)
    combined = combine_domain_lists(existing, new_domains)
    
    # Should include all unique domains from both lists
    assert len(combined) == 3  # Deduplicates the common domain
    domain_names = [d.name for d in combined]
    assert "example.com" in domain_names
    assert "old-domain.com" in domain_names
    assert "new-domain.com" in domain_names


def test_combine_domain_lists_replace_mode(sample_domains) -> None:
    """Test combining domain lists in replace mode."""
    # Create two lists
    existing = [Domain("example.com"), Domain("old-domain.com")]
    new_domains = [Domain("example.com"), Domain("new-domain.com")]
    
    # Combine them with replace mode
    combined = combine_domain_lists(existing, new_domains, mode=UpdateMode.REPLACE)
    
    # Should only include domains from the new list
    assert len(combined) == 2
    domain_names = [d.name for d in combined]
    assert "example.com" in domain_names
    assert "new-domain.com" in domain_names
    assert "old-domain.com" not in domain_names


def test_combine_domain_lists_invalid_mode(sample_domains) -> None:
    """Test combining domain lists with an invalid mode raises ValueError."""
    # Create two lists
    existing = [Domain("example.com")]
    new_domains = [Domain("new-domain.com")]
    
    # Attempt to combine with invalid mode
    with pytest.raises(ValueError):
        combine_domain_lists(existing, new_domains, mode="invalid_mode")


def test_domain_set_difference() -> None:
    """Test finding the difference between two domain lists."""
    # Create two lists with some overlap
    domains1 = [
        Domain("example.com"),
        Domain("unique1.com"),
        Domain("shared.com"),
        Domain("unique2.com")
    ]
    
    domains2 = [
        Domain("other.com"),
        Domain("shared.com"),
        Domain("example.com")
    ]
    
    # Get domains that are in domains1 but not domains2
    difference = domain_set_difference(domains1, domains2)
    
    # Should only include the unique domains from domains1
    assert len(difference) == 2
    domain_names = [d.name for d in difference]
    assert "unique1.com" in domain_names
    assert "unique2.com" in domain_names
    assert "shared.com" not in domain_names
    assert "example.com" not in domain_names


def test_domain_set_difference_no_overlap() -> None:
    """Test finding the difference between two domain lists with no overlap."""
    # Create two lists with no overlap
    domains1 = [Domain("a.com"), Domain("b.com")]
    domains2 = [Domain("c.com"), Domain("d.com")]
    
    # Get the difference
    difference = domain_set_difference(domains1, domains2)
    
    # Should include all domains from domains1
    assert len(difference) == 2
    domain_names = [d.name for d in difference]
    assert "a.com" in domain_names
    assert "b.com" in domain_names


# Master list update tests
def test_update_master_list_new_file(tmp_path, sample_domains) -> None:
    """Test updating a non-existent master list (creating a new one)."""
    # Define file path that doesn't exist
    file_path = tmp_path / "new_master.txt"
    
    # Update the non-existent master list
    updated = update_master_list(str(file_path), sample_domains)
    
    # File should be created with the sample domains
    assert file_path.exists()
    assert len(updated) == 4
    
    # Read back the file to verify content
    domains = read_master_list(str(file_path))
    assert len(domains) == 4


def test_update_master_list_existing_file(tmp_path, master_list_content) -> None:
    """Test updating an existing master list."""
    # Create an existing master list
    file_path = tmp_path / "existing_master.txt"
    with open(file_path, 'w') as f:
        f.write(master_list_content)
    
    # Create new domains to add
    new_domains = [
        Domain("example.com"),  # Already exists
        Domain("new-domain.com")  # New domain
    ]
    
    # Update the master list
    updated = update_master_list(str(file_path), new_domains)
    
    # Should include all unique domains
    assert len(updated) == 4  # 3 existing + 1 new
    domain_names = [d.name for d in updated]
    assert "example.com" in domain_names
    assert "new-domain.com" in domain_names
    assert "test.org" in domain_names
    assert "subdomain.example.com" in domain_names


def test_count_new_domains(tmp_path, master_list_content) -> None:
    """Test counting how many domains would be added to a master list."""
    # Create an existing master list
    file_path = tmp_path / "count_master.txt"
    with open(file_path, 'w') as f:
        f.write(master_list_content)
    
    # Create a mix of new and existing domains
    domains = [
        Domain("example.com"),  # Already exists
        Domain("test.org"),     # Already exists
        Domain("new1.com"),     # New
        Domain("new2.com"),     # New
        Domain("subdomain.example.com"), # Already exists
        Domain("new1.com")      # Duplicate of a new domain (should be counted once)
    ]
    
    # Count new domains
    count = count_new_domains(domains, str(file_path))
    
    # Should count unique new domains only
    assert count == 2