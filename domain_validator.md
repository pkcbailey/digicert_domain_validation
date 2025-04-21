# Domain Validator

A Python script that validates domain names and their DNS records, checking for common configuration issues and potential problems. It associates domains with a specific organization ID for proper categorization using DigiCert's CertCentral API.

## Features

- Validates domain name format
- Checks various DNS record types (A, AAAA, MX, TXT, CNAME, NS)
- Verifies DNS resolution
- Identifies common configuration issues
- Generates comprehensive validation reports
- Supports bulk domain validation
- Secure storage of API keys and organization IDs using system keychain
- Automatic domain addition to DigiCert with TXT record validation

## Prerequisites

- Python 3.6 or higher
- Internet connection for DNS queries
- DigiCert API access
- Organization ID in DigiCert

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd domain-validator
```

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Authentication Setup

### First-time Setup

1. Run the script with any domain to trigger the authentication setup:
```bash
python domain_validator.py --domain example.com
```

2. When prompted:
   - Enter your DigiCert API key
   - Enter your DigiCert Organization ID

The credentials will be securely stored in your system's keychain and won't need to be entered again.

### Using Stored Credentials

Once credentials are stored in the keychain, you can run the script without providing them:

```bash
# Validate a single domain using stored credentials
python domain_validator.py --domain example.com

# Validate multiple domains from a file using stored credentials
python domain_validator.py --file domains.txt
```

### Overriding Stored Credentials

If you need to use different credentials, you can override the stored values:

```bash
# Override organization ID
python domain_validator.py --domain example.com --org-id 1234567

# Note: There is no command-line option for the API key for security reasons
```

## Usage

### Basic Usage

```bash
# Validate a single domain
python domain_validator.py --domain example.com

# Validate multiple domains from a file
python domain_validator.py --file domains.txt
```

### Command Line Options

- `--domain`: Single domain to validate
- `--file`: File containing list of domains (one per line)
- `--output`: Output Excel file path (default: validation_report.xlsx)
- `--org-id`: Organization ID for domain categorization (optional if stored in keychain)
- `--verbose`: Enable verbose output

### Validation Checks

The script performs the following checks:

1. Domain Format Validation:
   - Validates domain name syntax
   - Checks for proper TLD format

2. DNS Resolution:
   - Verifies domain exists in DNS
   - Checks for A/AAAA records
   - Validates MX records
   - Verifies NS records
   - Checks for TXT records
   - Validates CNAME records

3. DigiCert Integration:
   - Checks if domain exists in DigiCert
   - Verifies organization association
   - Adds domain to organization if not found
   - Provides TXT record for validation

### Report Format

The generated Excel report includes:

- Organization ID
- Domain name
- Format validation status
- DigiCert status
- Organization match status
- Validation method
- Validation TXT record (if applicable)
- Record counts for each type
- Any identified issues

## Dependencies

- dnspython
- pandas
- openpyxl
- requests
- keyring
- tqdm

## Error Handling

The script includes comprehensive error handling for:
- Invalid domain formats
- DNS resolution failures
- API communication errors
- File I/O operations
- Keychain access issues

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is licensed under the MIT License. 