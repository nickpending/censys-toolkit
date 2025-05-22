# censys-toolkit
Command-line utilities to support Censys reconnaissance and data gathering

## Overview
This repository contains a collection of command-line utilities designed to extend and streamline Censys operations. Each tool is focused on specific use cases to help security researchers, penetration testers, and system administrators efficiently gather and analyze data from Censys.

Currently, the project includes `censyspy`, a tool for discovering FQDNs using the Censys Search API through both DNS records and SSL/TLS certificates.

The project follows a modular, maintainable architecture with clear separation of concerns between API interactions, business logic, and the command-line interface.

## Project Structure

```
censys-toolkit/
├── censyspy/                # Main package
│   ├── __init__.py          # Package initialization
│   ├── api.py               # API client functionality
│   ├── cli.py               # Command-line interface
│   ├── formatter.py         # Output formatting
│   ├── masterlist.py        # Master list management
│   ├── models.py            # Data models
│   ├── processor.py         # Data processing logic
│   └── utils.py             # Utility functions
├── tests/                   # Tests mirror package structure
├── pyproject.toml           # Project configuration
├── scripts/                 # Development scripts
└── README.md
```

The repository is organized according to a layered architecture pattern:
- **API Layer**: Handles external API interactions, authentication, and raw data retrieval
- **Processing Layer**: Processes data and implements business logic
- **CLI Layer**: Provides command-line interface and user interaction
- **Model Layer**: Defines structured data models with validation
- **Formatter Layer**: Handles conversion of data to various output formats
- **Utilities**: Provides cross-cutting functionality like logging
- **Master List Management**: Tools for maintaining and updating domain lists

## Installation
### Requirements
- Python 3.9 or higher
- Censys API credentials

### Dependencies
- censys>=2.2.16 (Official Censys Python library)
- python-dotenv>=1.0.1 (Environment variable management)
- click>=8.1.8 (Command-line interface)
- rich>=13.7.1 (Improved terminal output)
- pydantic>=2.10.6 (Data validation)

### Quick Start (Recommended)
This project uses [uv](https://github.com/astral-sh/uv) for fast, reliable Python package management:

```bash
# Clone and set up in one go
git clone https://github.com/nickpending/censys-toolkit.git
cd censys-toolkit
./scripts/uv_manage.sh setup

# Activate environment and test
source .venv/bin/activate  # On Unix/Mac
censyspy --help
```

### Development Environment  
For development work, we standardize on [uv](https://github.com/astral-sh/uv) for package management and virtual environment handling:

1. **Install uv** (if not already installed):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# or
pip install uv
```

2. **Clone and set up**:
```bash
git clone https://github.com/nickpending/censys-toolkit.git
cd censys-toolkit
./scripts/uv_manage.sh setup    # Create venv and install dependencies
./scripts/uv_manage.sh dev      # Install development dependencies
```

3. **Verify installation**:
```bash
# Activate virtual environment
source .venv/bin/activate       # Unix/Mac
# .venv\Scripts\activate        # Windows

# Test the application
censyspy --help
```

#### Standard Development Workflow

The project uses a unified management script that standardizes common development tasks:

```bash
# Available commands:
./scripts/uv_manage.sh setup         # Create a virtual environment and install dependencies
./scripts/uv_manage.sh dev           # Install development dependencies
./scripts/uv_manage.sh update        # Update the lockfile with current dependencies
./scripts/uv_manage.sh format        # Format code with black and isort
./scripts/uv_manage.sh check         # Run type checking with mypy
./scripts/uv_manage.sh test          # Run all tests
./scripts/uv_manage.sh test unit     # Run only unit tests
./scripts/uv_manage.sh test cov      # Run tests with coverage report
./scripts/uv_manage.sh lint          # Run all linters and formatters
./scripts/uv_manage.sh clean         # Clean build artifacts
./scripts/uv_manage.sh build         # Build distribution packages
```

The project uses a lockfile (`uv.lock`) to ensure all developers have consistent dependencies. To update the lockfile after adding new dependencies to `pyproject.toml`:

```bash
./scripts/uv_manage.sh update
```

### API Credentials

You can configure your Censys API credentials using either method:

a. Using a `.env` file (recommended):
- Copy the example environment file:
  ```bash
  cp .env-example .env
  ```
- Edit `.env` and add your credentials:
  ```
  CENSYS_API_ID=your_api_id_here
  CENSYS_API_SECRET=your_api_secret_here
  ```

b. Using environment variables:
```bash
export CENSYS_API_ID="your_api_id"
export CENSYS_API_SECRET="your_api_secret"
```

## Tools

### censyspy
A fast and efficient reconnaissance tool that discovers FQDNs using Censys Search API

#### Features
- Discovers FQDNs through both DNS records and SSL/TLS certificates
- Combines forward and reverse DNS lookups
- Outputs results in multiple formats (JSON, text)
- Configurable search depth and result limits
- Flexible data collection timeframes (1, 3, 7 days, or all historical data)
- Structured data models for consistent processing

#### CLI Usage

**Collect domains:**
```bash
censyspy collect --data-type both --domain example.com --output results.json
```

**Update master lists:**
```bash
censyspy update-master --source domains.txt --master master_list.txt --mode update
```

**Check version:**
```bash
censyspy version
```

#### Options for `collect` command
```
 --data-type {dns,certificate,both}   Type of data to fetch
 --domain DOMAIN                      Domain to filter results (e.g., example.com) 
 --days {1,3,7,all}                   Filter results by last update time
 --page-size PAGE_SIZE                Number of results per page (default: 100)
 --max-pages MAX_PAGES                Maximum number of pages to process (-1 for all)
 --output OUTPUT                      Output file for results
 --format {json,text}                 Output format
 --debug                              Enable debug mode
```

#### Examples
1. Fetch complete historical dataset:
```bash
censyspy collect --data-type both --domain example.com --days all --output example.com.json
```

2. Fetch only the last 24 hours of data:
```bash
censyspy collect --data-type both --domain example.com --days 1 --output example.com-daily.json
```

3. Fetch certificate data as plain text:
```bash
censyspy collect --data-type certificate --domain example.com --format text --output domains.txt
```

4. Update a master domain list:
```bash
censyspy update-master --source new_domains.txt --master master_domains.txt --mode append
```

Sample output:
```
==================================================
CENSYS SEARCH RESULTS SUMMARY
==================================================

STATISTICS:
  Total unique domains: 5
  DNS records: 3
  Certificate records: 2

SAMPLE DOMAINS:
  1. example.com (dns) [93.184.216.34]
  2. www.example.com (certificate)
  3. api.example.com (dns) [93.184.216.34]

==================================================
Results saved to example.com.json
```

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments
- [Censys](https://censys.io/) for providing the API
- [Censys-Python](https://github.com/censys/censys-python) The Censys Python library maintainers
- [python-dotenv](https://github.com/theskumar/python-dotenv) for environment variable management

## Contact
Project Link: https://github.com/nickpending/censys-toolkit

## Architecture

The project follows a modular, layered architecture:

- **API Layer** (`api.py`): Handles Censys API interactions with retry logic and error handling
- **Processing Layer** (`processor.py`): Processes and filters domain data
- **CLI Layer** (`cli.py`): Click-based command interface
- **Data Models** (`models.py`): Structured domain entities with validation
- **Formatters** (`formatter.py`): Multiple output formats (JSON, text)
- **Master Lists** (`masterlist.py`): Domain list management and deduplication
- **Utilities** (`utils.py`): Logging, file I/O, and helper functions

Key features implemented:
✅ Modular architecture with clear separation of concerns  
✅ Structured data models with validation  
✅ Click-based CLI with intuitive commands  
✅ Multiple output formats (JSON, text)  
✅ Master list management and deduplication  
✅ Wildcard domain handling  
✅ Comprehensive error handling and retry logic