"""
Unit tests for the CLI module.

This module contains tests for the command-line interface,
including argument parsing, command execution, and output formatting.
"""

import json
import os
import pytest
from click.testing import CliRunner

from censyspy.cli import cli
from censyspy.models import Domain


class TestCLI:
    """Tests for the CLI framework."""

    def test_cli_shows_help(self):
        """Test that the CLI displays help information."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'Command-line utilities for Censys domain discovery' in result.output
        assert 'collect' in result.output
        assert 'update-master' in result.output
        assert 'version' in result.output

    def test_version_command(self):
        """Test that the version command displays version information."""
        runner = CliRunner()
        result = runner.invoke(cli, ['version'])
        assert result.exit_code == 0
        assert 'Censys-toolkit version:' in result.output
        assert 'Python version:' in result.output
        assert 'Censys library version:' in result.output
        assert 'Click version:' in result.output

    def test_collect_command_help(self):
        """Test that the collect command shows help information."""
        runner = CliRunner()
        result = runner.invoke(cli, ['collect', '--help'])
        assert result.exit_code == 0
        assert 'Collect domain information from Censys Search API' in result.output
        assert '--data-type' in result.output
        assert '--domain' in result.output
        assert '--days' in result.output
        assert '--output' in result.output
        assert '--format' in result.output
        
    def test_collect_command_required_options(self):
        """Test that the collect command requires necessary options."""
        runner = CliRunner()
        result = runner.invoke(cli, ['collect'])
        assert result.exit_code != 0
        assert 'Error: Missing option' in result.output
        
    def test_collect_command_with_options(self):
        """Test that the collect command accepts all required options."""
        runner = CliRunner()
        result = runner.invoke(cli, [
            'collect',
            '--data-type', 'both',
            '--domain', 'example.com',
            '--output', 'results.json'
        ])
        assert result.exit_code == 0
        assert 'Domain collection for example.com (both) requested' in result.output
        assert 'Results will be saved to results.json' in result.output

    def test_update_master_command_help(self):
        """Test that the update-master command shows help information."""
        runner = CliRunner()
        result = runner.invoke(cli, ['update-master', '--help'])
        assert result.exit_code == 0
        assert 'Update a master domain list with new discoveries' in result.output
        assert '--source' in result.output
        assert '--master' in result.output
        assert '--mode' in result.output
        
    def test_update_master_command_required_options(self):
        """Test that the update-master command requires necessary options."""
        runner = CliRunner()
        result = runner.invoke(cli, ['update-master'])
        assert result.exit_code != 0
        assert 'Error: Missing option' in result.output
        
    def test_update_master_command_with_options(self, tmp_path):
        """Test that the update-master command accepts all required options."""
        # Create temporary files to make the test work
        source_file = tmp_path / "results.json"
        master_file = tmp_path / "master-domains.txt"
        
        # Create mock domain data
        domains = [
            Domain("example.com").to_dict(),
            Domain("test.org").to_dict()
        ]
        
        # Create the source file with valid JSON
        source_data = {
            "format": "flat",
            "data": ["example.com", "test.org"]
        }
        source_file.write_text(json.dumps(source_data))
        
        # Create the master file (empty initially)
        master_file.touch()
        
        # Run the command with the temp files
        runner = CliRunner()
        result = runner.invoke(cli, [
            'update-master',
            '--source', str(source_file),
            '--master', str(master_file)
        ])
        
        # Since we're using real files, the command should succeed
        assert result.exit_code == 0
        assert 'Master list update requested' in result.output
        assert f'Source: {source_file}' in result.output
        assert f'Master: {master_file}' in result.output
        assert 'Mode: update' in result.output  # Default mode

    def test_debug_flag_is_recognized(self):
        """Test that the debug flag is properly recognized."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--debug', 'version'])
        assert result.exit_code == 0