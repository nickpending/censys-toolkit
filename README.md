# censys-toolkit

Power tools for enhancing Censys searches and data analysis workflows.

## Overview

This repository contains a collection of command-line utilities designed to extend and streamline Censys operations. Each tool is focused on specific use cases to help security researchers, penetration testers, and system administrators efficiently gather and analyze data from Censys.

## Installation

### Requirements
- Python 3.8 or higher
- Censys API credentials

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
- Set your Censys API ID and API Secret as environment variables:
```bash
export CENSYS_API_ID="your_api_id"
export CENSYS_API_SECRET="your_api_secret"
```
- Or use the Censys configuration file: `~/.config/censys/censys.cfg`

## Tools

### censyspy

A fast (depending on the domain you choose) and efficient reconnaissance tool that discovers FQDNs using Censys Search API

#### Features
- Discovers FQDNs through both DNS records and SSL/TLS certificates
- Combines forward and reverse DNS lookups
- Outputs results in JSON format for easy parsing
- Configurable search depth and result limits

#### Usage
```bash
python censyspy.py --data-type both --domain example.com --output results.json
```

#### Options
```
--data-type     Type of data to fetch (dns, certificate, or both)
--domain        Target domain to search
--page-size     Number of results per page (default: 100)
--max-pages     Maximum number of pages to process (-1 for all)
--output        Output file for JSON results
--debug         Enable debug mode
--json          Print full JSON output to console
```

#### Example
```bash
python censyspy.py --data-type both --domain example.com --output example.com.json
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
- [Censys-Python] (https://github.com/censys/censys-python) The Censys Python library maintainers

## Contact

Project Link: https://github.com/nickpending/censys-toolkit
