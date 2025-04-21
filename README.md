# Azure DNS Report Generator

A Python script that generates a comprehensive report of all DNS zones and records across Azure subscriptions, including both public and private zones.

## Features

- Automatically discovers all accessible Azure subscriptions
- Retrieves both public and private DNS zones
- Collects all DNS records for each zone
- Identifies linked VNETs for private zones
- Generates a formatted Excel report with:
  - Subscription ID
  - Resource Group
  - Zone Name
  - Zone Type (Public/Private)
  - Record Type
  - Record Name
  - Record Values
  - Linked VNETs (for private zones)
- Highlights problematic zones:
  - Light Red: Zones with no records (other than NS/SOA)
  - Light Yellow: Private zones with no linked VNETs

## Prerequisites

- Python 3.6 or higher
- Azure subscription(s) with DNS zones
- Azure authentication credentials

## Installation

1. Clone this repository
2. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Authentication

The script uses `DefaultAzureCredential` which supports multiple authentication methods:

### Windows Authentication
1. Install Azure CLI:
   - Download from: https://learn.microsoft.com/en-us/cli/azure/install-azure-cli-windows
2. Log in to Azure:
```powershell
az login
```

### Alternative Authentication Methods
- Environment variables
- Managed identity (when running in Azure)
- Visual Studio Code credentials
- Visual Studio credentials

## Usage

Run the script:
```bash
python azure_dns_report.py
```

The script will:
1. Authenticate to Azure
2. Discover all accessible subscriptions
3. Collect DNS zone information
4. Generate an Excel report at `~/Desktop/azure_dns_report.xlsx`

## Report Format

The generated Excel report includes:
- All DNS zones across all subscriptions
- Detailed record information
- Conditional formatting to highlight:
  - Empty zones (light red)
  - Private zones without VNETs (light yellow)

## Dependencies

- azure-identity>=1.15.0
- azure-mgmt-dns>=8.0.0
- azure-mgmt-resource>=23.0.1
- pandas>=2.0.0
- openpyxl>=3.1.2

## Error Handling

The script includes comprehensive error handling for:
- Authentication failures
- Subscription access issues
- DNS zone retrieval errors
- Record set processing errors

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is licensed under the MIT License - see the LICENSE file for details. 