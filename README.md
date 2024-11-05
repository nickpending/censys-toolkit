# censys-toolkit
Command-line utilities to support Censys reconnaissance and data gathering

## Overview
This repository contains a collection of command-line utilities designed to extend and streamline Censys operations. Each tool is focused on specific use cases to help security researchers, penetration testers, and system administrators efficiently gather and analyze data from Censys.

## Installation
### Requirements
- Python 3.8 or higher
- Censys API credentials
- python-dotenv

1. Clone the repository:
```bash
git clone https://github.com/yourusername/censys-toolkit.git
cd censys-toolkit
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure Censys credentials:

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
- Outputs results in JSON format for easy parsing
- Configurable search depth and result limits
- Flexible data collection timeframes (1, 3, 7 days, or all historical data)
- Supports multiple credential configuration methods

#### Usage
```bash
censyspy --data-type both --domain example.com --output results.json
```

#### Options
```
 -h, --help                           show this help message and exit
 --data-type {dns,certificate,both}   Type of data to fetch
 --domain DOMAIN                      Domain to filter results (e.g., example.com)
 --days {1,3,7,all}                  Filter results by last update time (1, 3, 7 days, or all)
 --page-size PAGE_SIZE               Number of results per page (max 100)
 --max-pages MAX_PAGES               Maximum number of pages to process. Use -1 for all pages.
 --output OUTPUT                     Output file for JSON results
 --debug                            Enable debug mode
 --json                             Print full JSON output to console
```

#### Examples
1. Fetch complete historical dataset:
```bash
censyspy --data-type both --domain example.com --days all --output example.com.json
```

2. Fetch only the last 24 hours of data:
```bash
censyspy --data-type both --domain example.com --days 1 --output example.com-daily.json
```

3. Fetch the last week of certificate data:
```bash
censyspy --data-type certificate --domain example.com --days 7 --output example.com-certs.json
```

Sample output:
```
Results written to example.com.json
Collected data summary:
DNS Data:
1. www.example.com (forward)
2. mail.example.com (forward)
3. dev.example.com (forward)
4. api.example.com (forward)
5. test.example.com (forward)
... and 5 more entries

CERTIFICATE Data:
1. www.example.com (certificate)
2. *.example.com (certificate)
3. mail.example.com (certificate)
4. example.com (certificate)
5. api.example.com (certificate)
... and 3 more entries
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