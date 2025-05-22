# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-05-21

### Added
- Initial stable release
- `censyspy collect` command for domain discovery via Censys API
- `censyspy update-master` command for managing domain lists
- `censyspy version` command for version information
- Support for DNS and certificate data collection
- Multiple output formats (JSON, text)
- Master list management with deduplication
- Wildcard domain handling
- Comprehensive error handling with specific error types
- Retry logic for API calls with exponential backoff
- Click-based CLI with proper help messages
- Structured data models with validation
- Modular architecture with clear separation of concerns

### Technical Details
- Python 3.9+ support
- Built on official Censys Python library (>=2.2.16)
- Uses Click for CLI framework
- Implements structured logging
- Comprehensive test coverage
- Type annotations throughout

## [Unreleased]

### Added
- Placeholder for future changes

### Changed
- Placeholder for future changes

### Fixed
- Placeholder for future changes