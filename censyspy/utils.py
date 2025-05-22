"""
Utility functions for Censys toolkit.

This module provides helper functions used across the toolkit,
including logging, date manipulation, debugging, and file I/O.
"""

import json
import logging
import logging.handlers
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

# Default log format
DEFAULT_LOG_FORMAT = "%(asctime)s [%(levelname)8s] %(message)s (%(name)s:%(lineno)s)"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Log levels dictionary for easier configuration
LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}


def parse_log_level(level: Optional[Union[str, int]] = None, env_var: str = "CENSYS_LOG_LEVEL") -> int:
    """
    Parse log level from various inputs with priority order:
    1. Explicit level parameter
    2. Environment variable
    3. Default (INFO)
    
    This function provides a simple way to determine the log level for
    the application based on multiple sources, which is appropriate for
    short-running CLI tools.
    
    Args:
        level: Explicit log level (name or constant)
        env_var: Name of environment variable to check
        
    Returns:
        Log level as an integer constant
        
    Examples:
        >>> # Using explicit level
        >>> parse_log_level("debug")
        10  # logging.DEBUG
        
        >>> # Using environment variable (if CENSYS_LOG_LEVEL=error)
        >>> parse_log_level()
        40  # logging.ERROR
        
        >>> # Fallback to default
        >>> parse_log_level(None, "NONEXISTENT_VAR")
        20  # logging.INFO
    """
    # Check for explicit level
    if level is not None:
        if isinstance(level, str):
            level_str = level.lower()
            if level_str in LOG_LEVELS:
                return LOG_LEVELS[level_str]
            # Fall through to default if invalid level name
        elif isinstance(level, int):
            return level
    
    # Check environment variable
    env_level = os.environ.get(env_var)
    if env_level:
        env_level = env_level.lower()
        if env_level in LOG_LEVELS:
            return LOG_LEVELS[env_level]
    
    # Default to INFO level
    return logging.INFO


def get_logger(name: str, level: Optional[Union[str, int]] = None) -> logging.Logger:
    """
    Get a configured logger instance by name.
    
    This function retrieves or creates a logger with the specified name and
    configures its level if provided. It uses the root logger's configuration
    for handlers and formatting, which should be set up using configure_logging().
    
    The level parameter can be either a string name (debug, info, etc.) or 
    a logging level constant (logging.INFO, etc.). String names are converted
    to the appropriate constant using the parse_log_level function.

    Args:
        name: Name of the logger, typically __name__ of the calling module
        level: Optional override for log level (name or integer constant)

    Returns:
        Logger: Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Set level if specified
    if level is not None:
        logger.setLevel(parse_log_level(level))
    
    return logger


def configure_logging(
    level: Union[str, int] = "info",
    log_file: Optional[str] = None,
    log_format: Optional[str] = None,
    date_format: Optional[str] = None,
    console: bool = True,
) -> None:
    """
    Configure the logging system for the application.
    
    This function sets up the root logger with handlers for console and/or file output
    based on the parameters. It configures log levels, formatting, and ensures
    proper propagation of messages between loggers.
    
    By default, it sets up INFO level logging to the console with a standardized format.
    When a log file is specified, it adds a file handler that writes to that location.

    Args:
        level: Log level (debug, info, warning, error, critical) or logging constant
        log_file: Optional path to log file
        log_format: Optional custom log format
        date_format: Optional custom date format
        console: Whether to log to console
        
    Examples:
        >>> # Basic setup with INFO level to console
        >>> configure_logging()
        
        >>> # Debug level logging to both console and file
        >>> configure_logging(level="debug", log_file="/path/to/app.log")
        
        >>> # Custom format, only to file
        >>> configure_logging(
        ...     level="info",
        ...     log_file="app.log",
        ...     log_format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        ...     console=False
        ... )
        
        >>> # Using environment variable for log level
        >>> # CENSYS_LOG_LEVEL=debug python myscript.py
        >>> configure_logging(level=parse_log_level())
    """
    # Get the root logger
    root_logger = logging.getLogger()
    
    # Clear any existing handlers
    for handler in root_logger.handlers[:]:  # Use a copy to avoid modification during iteration
        root_logger.removeHandler(handler)
    
    # Parse log level using our utility function
    log_level = parse_log_level(level)
    root_logger.setLevel(log_level)
    
    # Set up formatting
    formatter = logging.Formatter(
        fmt=log_format or DEFAULT_LOG_FORMAT,
        datefmt=date_format or DEFAULT_DATE_FORMAT
    )
    
    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)
        root_logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        # Create directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # Use a rotating file handler to prevent huge log files
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        root_logger.addHandler(file_handler)
    
    # Log configuration details
    level_name = logging.getLevelName(log_level)
    root_logger.debug(f"Logging configured: level={level_name}")
    if log_file:
        root_logger.debug(f"Log file: {log_file}")


def get_date_filter(days: Optional[str]) -> Optional[str]:
    """
    Generate date filter string for the Censys API query.
    
    Creates a date range filter in the format required by the Censys Search API.
    The filter is based on the number of days from the current date, with
    the format "[START_DATE TO *]" where START_DATE is the date that many
    days in the past.
    
    Args:
        days: Number of days to include (1, 3, 7) or 'all'.
              If None or "all", no filter is applied.
    
    Returns:
        A Censys-compatible date filter string or None if no filtering should be applied
        
    Raises:
        ValueError: If days is not a positive integer or "all"
    """
    if not days or days == "all":
        return None

    try:
        days_int = int(days)
        if days_int <= 0:
            raise ValueError("Days must be positive")

        start_date = calculate_past_date(days_int)
        return format_date_for_api_query(start_date)
    except ValueError as e:
        raise ValueError(f"Invalid days value: {e}")


def calculate_past_date(days: int) -> datetime:
    """
    Calculate a date N days in the past from today.
    
    Args:
        days: Number of days to go back
        
    Returns:
        Datetime object representing the past date
        
    Raises:
        ValueError: If days is negative
    """
    if days < 0:
        raise ValueError("Days must be a non-negative integer")
        
    return datetime.now() - timedelta(days=days)


def format_date_for_api_query(start_date: datetime, end_date: Optional[datetime] = None) -> str:
    """
    Format a date range for Censys API queries.
    
    Creates a date range filter in the format required by the Censys Search API:
    "[START_DATE TO END_DATE]" or "[START_DATE TO *]" if no end date is provided.
    
    Args:
        start_date: The start date for the range
        end_date: Optional end date for the range. If None, uses "*" (no end date)
        
    Returns:
        A Censys-compatible date range filter string
    """
    start_str = format_date(start_date, "%Y-%m-%d")
    
    if end_date:
        end_str = format_date(end_date, "%Y-%m-%d")
    else:
        end_str = "*"
        
    return f"[{start_str} TO {end_str}]"


def format_date(date: datetime, format_string: str = "%Y-%m-%d") -> str:
    """
    Format a datetime object as a string using the specified format.
    
    Args:
        date: The datetime to format
        format_string: The format string to use (default: YYYY-MM-DD)
        
    Returns:
        Formatted date string
    """
    return date.strftime(format_string)


def parse_date_string(date_str: str, formats: Optional[List[str]] = None) -> Optional[datetime]:
    """
    Parse a date string into a datetime object.
    
    Attempts to parse the string using the provided formats or common formats
    if none are specified. Returns None if parsing fails with all formats.
    
    Args:
        date_str: String representation of a date
        formats: List of formats to try (defaults to common formats)
        
    Returns:
        Datetime object or None if parsing fails
    """
    if not date_str:
        return None
        
    # Default formats to try, in order
    default_formats = [
        "%Y-%m-%d",           # 2023-01-15
        "%Y-%m-%dT%H:%M:%S",  # 2023-01-15T14:30:45
        "%Y-%m-%dT%H:%M:%SZ", # 2023-01-15T14:30:45Z
        "%Y%m%d",             # 20230115
        "%d/%m/%Y",           # 15/01/2023
        "%m/%d/%Y",           # 01/15/2023
    ]
    
    formats_to_try = formats or default_formats
    
    for fmt in formats_to_try:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
            
    return None


def is_valid_date_string(date_str: str, formats: Optional[List[str]] = None) -> bool:
    """
    Check if a string is a valid date in any of the supported formats.
    
    Args:
        date_str: String to validate as a date
        formats: List of formats to try (defaults to common formats)
        
    Returns:
        True if the string is a valid date, False otherwise
    """
    return parse_date_string(date_str, formats) is not None


def is_valid_file_path(file_path: str) -> bool:
    """
    Check if a file path is valid and writable.

    Args:
        file_path: Path to check

    Returns:
        True if valid and writable, False otherwise
    """
    # Check if the path is empty
    if not file_path:
        return False
    
    # Get the directory part of the path
    directory = os.path.dirname(file_path)
    if not directory:  # If no directory was specified, use current directory
        directory = '.'
        
    # Check if the directory exists and is writable
    try:
        if not os.path.exists(directory):
            return False
        if not os.access(directory, os.W_OK):
            return False
        return True
    except Exception:
        return False


def is_valid_domain(domain: str) -> bool:
    """
    Check if a domain name has a valid format.
    
    This is a basic validation that ensures:
    - Contains at least one period
    - Contains only alphanumeric chars, hyphens, and periods
    - Does not start or end with a hyphen or period
    - Does not have consecutive periods
    
    Args:
        domain: Domain name to validate
        
    Returns:
        True if the domain has a valid format, False otherwise
    """
    # Basic checks for a valid domain format
    if not domain:
        return False
        
    # Check for at least one period (needed for a valid domain)
    if '.' not in domain:
        return False
        
    # Remove trailing dot if present (valid in DNS)
    if domain.endswith('.'):
        domain = domain[:-1]
        
    # Domain parts should be 1-63 chars and contain only alphanumeric and hyphens
    parts = domain.split('.')
    for part in parts:
        # Check for empty parts (consecutive periods)
        if not part:
            return False
            
        # Check length
        if len(part) > 63:
            return False
            
        # Check for invalid characters or patterns
        if not all(c.isalnum() or c == '-' for c in part):
            return False
            
        # Check for hyphens at start or end of parts
        if part.startswith('-') or part.endswith('-'):
            return False
    
    return True


# File I/O Utilities

def ensure_directory_exists(file_path: str) -> None:
    """
    Ensure the directory for a file path exists, creating it if necessary.
    
    This utility function extracts the directory part from a file path and
    creates the directory if it doesn't exist. It's useful before writing
    to files to ensure the target directory is available.
    
    Args:
        file_path: Path to a file
        
    Raises:
        IOError: If the directory cannot be created
    """
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        try:
            os.makedirs(directory, exist_ok=True)
        except (IOError, OSError) as e:
            raise IOError(f"Failed to create directory {directory}: {str(e)}")


def read_json_file(file_path: str) -> Any:
    """
    Read and parse a JSON file.
    
    This function handles the common operation of reading a JSON file
    and parsing its contents, with appropriate error handling.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Parsed JSON content (typically a dict or list)
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        json.JSONDecodeError: If the file contains invalid JSON
        IOError: If there's an error reading the file
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"JSON file not found: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        # Re-raise with more context about which file failed
        raise json.JSONDecodeError(
            f"Invalid JSON in {file_path}: {str(e)}", 
            e.doc, 
            e.pos
        )
    except IOError as e:
        raise IOError(f"Error reading JSON file {file_path}: {str(e)}")


def write_json_file(data: Any, file_path: str, indent: int = 2) -> None:
    """
    Write data to a JSON file.
    
    This function serializes data to JSON and writes it to a file,
    creating the directory if necessary.
    
    Args:
        data: Data to serialize to JSON
        file_path: Path where the file should be written
        indent: Number of spaces for indentation
        
    Raises:
        IOError: If there's an error writing to the file
        TypeError: If the data cannot be serialized to JSON
    """
    # Ensure the directory exists
    ensure_directory_exists(file_path)
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent)
    except (IOError, OSError) as e:
        raise IOError(f"Error writing JSON file {file_path}: {str(e)}")
    except TypeError as e:
        raise TypeError(f"Cannot serialize data to JSON: {str(e)}")


def read_text_file(file_path: str, ignore_comments: bool = False, encoding: str = 'utf-8') -> List[str]:
    """
    Read a text file into a list of lines.
    
    This function reads a text file line by line, optionally ignoring
    comments and empty lines, and returns the result as a list of strings.
    
    Args:
        file_path: Path to the text file
        ignore_comments: If True, exclude lines starting with '#'
        encoding: File encoding (default: utf-8)
        
    Returns:
        List of non-empty lines from the file
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        IOError: If there's an error reading the file
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Text file not found: {file_path}")
    
    try:
        lines = []
        with open(file_path, 'r', encoding=encoding) as f:
            for line in f:
                line = line.strip()
                # Skip empty lines
                if not line:
                    continue
                # Skip comments if requested
                if ignore_comments and line.startswith('#'):
                    continue
                lines.append(line)
        return lines
    except IOError as e:
        raise IOError(f"Error reading text file {file_path}: {str(e)}")


def write_text_file(
    lines: List[str], 
    file_path: str, 
    add_newlines: bool = True,
    encoding: str = 'utf-8'
) -> None:
    """
    Write a list of lines to a text file.
    
    This function writes a list of strings to a text file, optionally
    adding newlines between each entry. It creates the directory if necessary.
    
    Args:
        lines: List of lines to write
        file_path: Path where the file should be written
        add_newlines: Whether to add newlines between entries (if not already present)
        encoding: File encoding (default: utf-8)
        
    Raises:
        IOError: If there's an error writing to the file
    """
    # Ensure the directory exists
    ensure_directory_exists(file_path)
    
    try:
        with open(file_path, 'w', encoding=encoding) as f:
            for line in lines:
                if add_newlines and not line.endswith('\n'):
                    f.write(line + '\n')
                else:
                    f.write(line)
    except (IOError, OSError) as e:
        raise IOError(f"Error writing text file {file_path}: {str(e)}")


# Debug Utilities

def debug_object(obj: Any, label: Optional[str] = None) -> None:
    """
    Log detailed information about an object at DEBUG level.
    
    This function formats the object with a detailed representation
    and logs it at DEBUG level, optionally with a descriptive label.
    It's useful for inspecting objects during development or troubleshooting.
    
    The function will log the object's type and representation.
    For dictionaries, lists, and other container types, it will use
    pretty formatting to make the structure more readable in logs.
    
    Args:
        obj: The object to debug
        label: Optional descriptive label for the logged object
    
    Examples:
        >>> # Basic usage
        >>> debug_object(my_data, "API response data")
        
        >>> # Debugging an exception
        >>> try:
        ...     result = process_data()
        ... except Exception as e:
        ...     debug_object(e, "Exception during data processing")
        ...     raise
    """
    # Get the root logger to ensure the debug message is captured
    # regardless of which module's logger is currently in use
    logger = logging.getLogger()
    
    if logger.level > logging.DEBUG:
        # Skip processing if not in debug mode to avoid overhead
        return
    
    prefix = f"{label}: " if label else ""
    obj_type = type(obj).__name__
    
    try:
        # Format based on object type for better readability
        if isinstance(obj, dict):
            # Pretty format for dictionaries
            representation = json.dumps(obj, indent=2, default=str)
        elif isinstance(obj, (list, tuple)):
            # For lists and tuples, format each item on a new line if there are many items
            if len(obj) > 5:
                items = [f"  {i}: {repr(item)}" for i, item in enumerate(obj)]
                representation = "[\n" + ",\n".join(items) + "\n]"
            else:
                representation = repr(obj)
        elif isinstance(obj, Exception):
            # Special handling for exceptions to include traceback info
            representation = f"{type(obj).__name__}: {str(obj)}"
        else:
            # Default to standard representation
            representation = repr(obj)
        
        logger.debug(f"{prefix}Object of type {obj_type}: {representation}")
    except Exception as e:
        # Fallback if object representation raises an error
        logger.debug(f"{prefix}Object of type {obj_type}: <error during representation: {str(e)}>")
