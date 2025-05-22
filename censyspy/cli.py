"""
Command-line interface for Censys toolkit.

This module provides the CLI functionality for the Censys toolkit,
using Click to create a command structure that matches the workflow
of collecting domain information and managing master lists of domains.
"""

import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Union

import click
import requests
from censys.common.exceptions import CensysUnauthorizedException, CensysRateLimitExceededException
from dotenv import load_dotenv
from importlib.metadata import version

from censyspy.formatter import format_console_summary, format_results, normalize_format_type, parse_json_file
from censyspy.integration import fetch_and_process_domains
from censyspy.masterlist import count_new_domains, deduplicate_domains, read_master_list, update_master_list, UpdateMode
from censyspy.models import CertificateMatch, DNSMatch, Domain
from censyspy.utils import configure_logging, is_valid_domain, is_valid_file_path, write_json_file, write_text_file

# Set up shared context for CLI commands
CONTEXT_SETTINGS = {
    'help_option_names': ['-h', '--help'],
    'auto_envvar_prefix': 'CENSYS',
}


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(package_name="censys-toolkit")
@click.option("--debug", is_flag=True, help="Enable debug mode with verbose output")
@click.option("--quiet", is_flag=True, help="Suppress all console output except errors")
@click.option("--log-file", help="Save logs to specified file")
@click.pass_context
def cli(ctx: click.Context, debug: bool, quiet: bool, log_file: Optional[str]) -> None:
    """
    Command-line utilities for Censys domain discovery.
    
    Collect domain information from Censys Search API and manage master
    lists of domains for security research and reconnaissance.
    """
    # Create a context object to share state between commands
    ctx.ensure_object(dict)
    ctx.obj['DEBUG'] = debug
    ctx.obj['QUIET'] = quiet
    ctx.obj['LOG_FILE'] = log_file
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Store options in context object
    ctx.obj['debug'] = debug
    ctx.obj['quiet'] = quiet
    
    # Configure logging based on command options
    log_level = "debug" if debug else "info"
    if quiet:
        log_level = "error"
    
    # Configure logging with file if specified
    configure_logging(level=log_level, log_file=log_file, console=True)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


@cli.command("collect")
@click.option(
    "--data-type",
    type=click.Choice(["dns", "certificate", "both"]),
    required=True,
    help="Type of data to fetch",
)
@click.option(
    "--domain", 
    required=True,
    help="Domain to filter results (e.g., example.com)"
)
@click.option(
    "--days",
    type=click.Choice(["1", "3", "7", "all"]),
    default="all",
    help="Filter results by last update time (1, 3, 7 days, or all)",
)
@click.option(
    "--output", 
    required=True, 
    help="Output file for results"
)
@click.option(
    "--format",
    type=click.Choice(["json", "text"]),
    default="json",
    help="Output format",
)
@click.option(
    "--page-size",
    type=int,
    default=100,
    help="Number of results per page (max 100)",
)
@click.option(
    "--max-pages",
    type=int,
    default=-1,
    help="Maximum number of pages to process. Use -1 for all pages",
)
@click.pass_context
def collect(
    ctx: click.Context,
    data_type: str,
    domain: str,
    days: str,
    output: str,
    format: str,
    page_size: int,
    max_pages: int,
) -> None:
    """
    Collect domain information from Censys Search API.
    
    This command searches for domains in the Censys database using either DNS records,
    certificate data, or both. Results can be filtered by domain and age.
    
    \b
    Examples:
        censyspy collect --data-type both --domain example.com --output results.json
        censyspy collect --data-type dns --domain example.com --days 7 --output recent.json
        censyspy collect --data-type certificate --domain example.com --format text --output domains.txt
    """
    # Validate domain format
    if not is_valid_domain(domain):
        click.echo(f"Error: '{domain}' is not a valid domain name.", err=True)
        click.echo("Domain should have a valid format (e.g., example.com)", err=True)
        sys.exit(1)
    
    # Validate output file path
    if not is_valid_file_path(output):
        click.echo(f"Error: Cannot write to output file path: {output}", err=True)
        click.echo("Please check that the directory exists and is writable.", err=True)
        sys.exit(1)
    
    # Get debug/quiet settings from context
    debug = ctx.obj.get('DEBUG', False)
    quiet = ctx.obj.get('QUIET', False)
    
    # Set up logging based on verbosity
    log_level = logging.DEBUG if debug else logging.INFO
    if quiet:
        log_level = logging.ERROR
    configure_logging(level=log_level, console=not quiet)
    logger = logging.getLogger(__name__)
    
    try:
        # Fetch and process domains ONCE
        logger.info(f"Starting domain collection for {domain}")
        results_dict = fetch_and_process_domains(
            domain=domain,
            data_type=data_type,
            days=days,
            page_size=page_size,
            max_pages=max_pages,
            expand_wildcards=True,
            format_output=False
        )
        
        # Convert the dictionary to lists for both file output and console summary
        dns_matches = []
        cert_matches = []
        for domain_name, match_obj in results_dict.items():
            if isinstance(match_obj, DNSMatch):
                dns_matches.append(match_obj)
            elif isinstance(match_obj, CertificateMatch):
                cert_matches.append(match_obj)
        
        # Format the results for file output
        formatted_output = format_results(dns_matches, cert_matches, format_type=normalize_format_type(format))
        
        # Save formatted output to file
        if format.lower() == "json":
            # For JSON, we can write the raw string
            with open(output, 'w') as f:
                f.write(formatted_output)
        else:
            # For text, write as lines
            lines = formatted_output.splitlines()
            write_text_file(lines, output)
        
        logger.info(f"Results saved to {output}")
        
        # Display summary in console
        if not quiet:
            summary = format_console_summary(dns_matches, cert_matches)
            click.echo(summary)
            click.echo(f"\nResults saved to {output}")
    
    except CensysUnauthorizedException:
        error_msg = "Authentication failed. Check your CENSYS_API_ID and CENSYS_API_SECRET environment variables."
        logger.error(error_msg)
        click.echo(f"Error: {error_msg}", err=True)
        sys.exit(1)
    except CensysRateLimitExceededException:
        error_msg = "API rate limit exceeded. Please wait and try again later."
        logger.error(error_msg)
        click.echo(f"Error: {error_msg}", err=True)
        sys.exit(1)
    except (FileNotFoundError, PermissionError) as e:
        error_msg = f"File access problem: {str(e)}"
        logger.error(error_msg)
        click.echo(f"Error: {error_msg}", err=True)
        sys.exit(1)
    except requests.exceptions.ConnectionError:
        error_msg = "Network connection failed. Check your internet connection."
        logger.error(error_msg)
        click.echo(f"Error: {error_msg}", err=True)
        sys.exit(1)
    except ValueError as e:
        error_msg = f"Invalid input: {str(e)}"
        logger.error(error_msg)
        click.echo(f"Error: {error_msg}", err=True)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error during domain collection: {str(e)}")
        if debug:
            # In debug mode, reraise to show traceback
            raise
        else:
            # In normal mode, show a user-friendly error
            click.echo(f"Error: {str(e)}", err=True)
            sys.exit(1)


@cli.command("update-master")
@click.option(
    "--source",
    required=True,
    help="Source file containing domain data to use for update",
)
@click.option(
    "--master",
    required=True,
    help="Master list file to update",
)
@click.option(
    "--mode",
    type=click.Choice(["update", "replace"]),
    default="update",
    help="Update mode: update (merge) or replace (overwrite)",
)
@click.pass_context
def update_master(
    ctx: click.Context,
    source: str,
    master: str,
    mode: str,
) -> None:
    """
    Update a master domain list with new discoveries.
    
    This command takes domain data from either JSON or text files and updates
    a master list of domains. The master list is saved as a text file with one domain per line.
    
    Source files can be:
    - JSON files from collect command output
    - Text files with one domain per line
    
    Two update modes are supported:
    - update: Merge new domains with the existing master list (default)
    - replace: Replace the entire master list with new domains
    
    \b
    Examples:
        censyspy update-master --source results.json --master master-domains.txt
        censyspy update-master --source domains.txt --master master-domains.txt --mode replace
    """
    # Set up logging based on context options
    debug = ctx.obj.get('DEBUG', False)
    quiet = ctx.obj.get('QUIET', False)
    log_level = logging.DEBUG if debug else logging.INFO
    if quiet:
        log_level = logging.ERROR
    configure_logging(level=log_level, console=not quiet)
    logger = logging.getLogger(__name__)
    
    # Validate source file exists
    if not os.path.exists(source):
        click.echo(f"Error: Source file not found: {source}", err=True)
        click.echo("Please provide a valid source file path.", err=True)
        sys.exit(1)
    
    # Validate master file path is writable
    if not is_valid_file_path(master):
        click.echo(f"Error: Cannot write to master file: {master}", err=True)
        click.echo("Please check that the directory exists and is writable.", err=True)
        sys.exit(1)
    
    try:
        # Determine source file type and extract domains
        source_extension = os.path.splitext(source)[1].lower()
        new_domains = []
        
        logger.info(f"Reading domain data from {source}")
        
        if source_extension == ".json":
            # Use the unified JSON parsing function from formatter
            try:
                new_domains = parse_json_file(source)
            except ValueError as e:
                raise ValueError(f"Error parsing JSON file: {e}")
                
        elif source_extension in (".txt", ".list", ""):
            # Handle text file with one domain per line
            with open(source, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    try:
                        new_domains.append(Domain(line))
                    except ValueError as e:
                        logger.warning(f"Skipping invalid domain '{line}': {str(e)}")
        else:
            raise ValueError(f"Unsupported file format: {source_extension}")
        
        if not new_domains:
            logger.warning(f"No valid domains found in {source}")
            if not quiet:
                click.echo(f"Warning: No valid domains found in {source}", err=True)
                click.echo("Master list was not updated.", err=True)
            sys.exit(0)
            
        # Count how many domains will be new before updating
        new_count = count_new_domains(new_domains, master) if mode == "update" else len(deduplicate_domains(new_domains))
        
        # Update the master list
        logger.info(f"Updating master list {master} with {len(new_domains)} domains in '{mode}' mode")
        updated_domains = update_master_list(master, new_domains, mode)
        if not quiet:
            click.echo(f"Master list updated successfully:")
            click.echo(f"  - Added {new_count} new domains")
            click.echo(f"  - Total domains in master list: {len(updated_domains)}")
            click.echo(f"  - Master list saved to: {master}")
        
        logger.info(f"Master list update completed: {new_count} new domains, {len(updated_domains)} total")
    
    except (FileNotFoundError, PermissionError) as e:
        error_msg = f"File access problem: {str(e)}"
        logger.error(error_msg)
        click.echo(f"Error: {error_msg}", err=True)
        sys.exit(1)
    except ValueError as e:
        error_msg = f"Invalid input: {str(e)}"
        logger.error(error_msg)
        click.echo(f"Error: {error_msg}", err=True)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error during master list update: {str(e)}")
        if debug:
            # In debug mode, reraise to show traceback
            raise
        else:
            # In normal mode, show a user-friendly error
            click.echo(f"Error: {str(e)}", err=True)
            sys.exit(1)


@cli.command("version")
def version_cmd() -> None:
    """Display detailed version information."""
    pkg_version = version("censys-toolkit")
    click.echo(f"Censys-toolkit version: {pkg_version}")
    click.echo(f"Python version: {__import__('sys').version.split()[0]}")
    click.echo(f"Censys library version: {version('censys')}")
    click.echo(f"Click version: {version('click')}")


def main() -> None:
    """Entry point for the CLI."""
    cli()
