# Domain Validator

A Python script that validates domain names and their DNS records, checking for common configuration issues and potential problems.

## Features

- Validates domain name format and structure
- Checks DNS record types (A, AAAA, CNAME, MX, TXT, etc.)
- Verifies DNS resolution
- Identifies common configuration issues
- Generates detailed validation reports
- Supports bulk domain validation from input files

## Prerequisites

- Python 3.6 or higher
- Internet connection for DNS queries
- Required Python packages (see Dependencies section)

## Installation

1. Clone this repository
2. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage
```bash
python domain_validator.py example.com
```

### Bulk Validation
```bash
python domain_validator.py --file domains.txt
```

### Command Line Options
- `--domain`: Single domain to validate
- `--file`: Path to file containing list of domains (one per line)
- `--output`: Path to save validation report (default: validation_report.xlsx)
- `--verbose`: Enable detailed output
- `--timeout`: DNS query timeout in seconds (default: 5)

## Validation Checks

The script performs the following checks:
1. Domain Format Validation
   - Valid characters
   - Proper length
   - Correct structure
2. DNS Resolution
   - A records
   - AAAA records
   - MX records
   - TXT records
   - CNAME records
3. Common Issues
   - Missing records
   - Misconfigured records
   - Potential security issues

## Report Format

The generated report includes:
- Domain name
- Validation status
- DNS record details
- Identified issues
- Recommendations

## Dependencies

- dnspython>=2.0.0
- pandas>=2.0.0
- openpyxl>=3.1.2
- tqdm>=4.65.0 (for progress bars)

## Error Handling

The script includes error handling for:
- Invalid domain formats
- DNS resolution failures
- Network connectivity issues
- File I/O errors

## Examples

### Validate Single Domain
```bash
python domain_validator.py example.com
```

### Validate Multiple Domains
```bash
python domain_validator.py --file domains.txt --output results.xlsx
```

### Verbose Output
```bash
python domain_validator.py example.com --verbose
```

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is licensed under the MIT License - see the LICENSE file for details. 