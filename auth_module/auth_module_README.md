# Auth Module

A Python module for managing API credentials from a JSON vault file. This module provides secure access to API credentials stored in `~/.ApiVault` and can be used from anywhere on your system.

## Features

- 🔐 **Secure Credential Management**: Load credentials from JSON vault file
- 🎯 **Service-Specific Functions**: Easy access to credentials for specific services
- ✅ **Validation**: Validate that required credential keys are present
- 🖥️ **Command Line Interface**: Use from terminal with `auth` command
- 📦 **Modular Design**: Import and use in any Python script
- 🔒 **Security**: Sensitive values are masked in CLI output

## Supported Services

- **DigiCert**: API key and customer ID
- **Sectigo**: Customer URI, login, password, and org ID
- **Email Services**: Email credentials
- **Infoblox**: Infoblox API credentials
- **Venafi**: Venafi API credentials
- **Azure SPN**: Azure Service Principal credentials
- **Gemini**: Gemini API credentials
- **Mailhardener**: Mailhardener API credentials

## Installation

### Option 1: Quick Install Script
```bash
./install_auth.sh
```

### Option 2: Manual Installation
```bash
pip install -e . -f auth_module_setup.py
```

### Option 3: Global Installation
```bash
pip install . -f auth_module_setup.py
```

## Quick Start

### Command Line Usage

Once installed, you can use the `auth` command from anywhere:

```bash
# List all available services
auth list

# Get credentials for a specific service
auth get digicert
auth get Sectigo

# Validate that a service has required keys
auth validate digicert api customerID

# Use custom vault file
auth --vault /path/to/vault.json get digicert

# Get credentials in JSON format
auth get digicert --format json
```

### Programmatic Usage

```python
from auth_module import get_digicert_credentials, get_sectigo_credentials

# Get DigiCert credentials
digicert_creds = get_digicert_credentials()
if digicert_creds:
    api_key = digicert_creds['api']
    customer_id = digicert_creds['customerID']

# Get Sectigo credentials
sectigo_creds = get_sectigo_credentials()
if sectigo_creds:
    customer_uri = sectigo_creds['customeruri']
    login = sectigo_creds['login']
    password = sectigo_creds['password']
    org_id = sectigo_creds['orgID']
```

## API Vault Format

The module expects a JSON file at `~/.ApiVault` with the following structure:

```json
{
    "digicert": {
        "api": "your_api_key_here",
        "customerID": "your_customer_id_here"
    },
    "Sectigo": {
        "customeruri": "https://cert-manager.com/api/ssl/v1",
        "login": "your_login",
        "password": "your_password",
        "orgID": "your_org_id"
    },
    "email_credentials": {
        "smtp_server": "smtp.example.com",
        "username": "your_email@example.com",
        "password": "your_password"
    }
}
```

## Available Functions

### Core Functions

- `load_api_vault(path=None)`: Load the entire API vault
- `get_credentials(service_name, path=None)`: Get credentials for any service
- `list_available_services(path=None)`: List all available services
- `validate_credentials(service_name, required_keys, path=None)`: Validate credential keys

### Service-Specific Functions

- `get_digicert_credentials(path=None)`: Get DigiCert credentials
- `get_sectigo_credentials(path=None)`: Get Sectigo credentials
- `get_email_credentials(path=None)`: Get email credentials
- `get_infoblox_credentials(path=None)`: Get Infoblox credentials
- `get_venafi_credentials(path=None)`: Get Venafi credentials
- `get_azure_spn_credentials(path=None)`: Get Azure SPN credentials
- `get_gemini_credentials(path=None)`: Get Gemini credentials
- `get_mailhardener_credentials(path=None)`: Get Mailhardener credentials

## Command Line Interface

### Available Commands

| Command | Description | Example |
|---------|-------------|---------|
| `list` | List all available services | `auth list` |
| `get` | Get credentials for a service | `auth get digicert` |
| `validate` | Validate service credentials | `auth validate digicert api customerID` |

### Global Options

- `--vault, -v`: Path to API vault file (default: ~/.ApiVault)

### Get Command Options

- `--format, -f`: Output format (json, pretty) (default: pretty)

### Examples

```bash
# List all services
auth list

# Get DigiCert credentials (pretty format)
auth get digicert

# Get DigiCert credentials (JSON format)
auth get digicert --format json

# Validate DigiCert has required keys
auth validate digicert api customerID

# Use custom vault file
auth --vault /path/to/custom_vault.json get Sectigo

# Validate Sectigo credentials
auth validate Sectigo customeruri login password orgID
```

## Error Handling

The module provides comprehensive error handling:

- **FileNotFoundError**: When the vault file doesn't exist
- **ValueError**: When the vault file is not valid JSON
- **PermissionError**: When the vault file cannot be read
- **KeyError**: When a service is not found in the vault

## Security Features

- **Sensitive Data Masking**: Passwords, keys, and tokens are masked in CLI output
- **No Credential Logging**: Credentials are never logged or printed in full
- **File Permissions**: Respects file system permissions for vault access

## Advanced Usage

### Custom Vault Path

```python
from auth_module import get_credentials

# Use custom vault file
creds = get_credentials("digicert", path="/path/to/custom_vault.json")
```

### Validation

```python
from auth_module import validate_credentials

# Validate DigiCert has required keys
is_valid = validate_credentials("digicert", ["api", "customerID"])
if is_valid:
    print("DigiCert credentials are valid")
else:
    print("DigiCert credentials are missing required keys")
```

### List Services

```python
from auth_module import list_available_services

# List all available services
services = list_available_services()
print(f"Available services: {', '.join(services)}")
```

## Project Structure

```
auth_module/
├── auth_module_setup.py    # Package setup
├── install_auth.sh        # Installation script
├── auth_module_README.md  # This file
├── auth_module/           # Main package
│   ├── __init__.py        # Package initialization
│   ├── auth.py            # Core auth functions
│   └── cli.py             # Command-line interface
└── AUTH_MODULE_SUMMARY.md # Summary document
```

## Troubleshooting

### Common Issues

1. **Vault file not found**: Ensure `~/.ApiVault` exists and is readable
2. **Invalid JSON**: Check that your vault file is valid JSON
3. **Permission denied**: Check file permissions on the vault file
4. **Service not found**: Verify the service name matches exactly (case-sensitive)

### Error Messages

- `API vault file not found at ~/.ApiVault`: Create the vault file
- `API vault file is not valid JSON`: Fix JSON syntax in vault file
- `Permission denied reading API vault file`: Check file permissions
- `No credentials found for service 'service_name'`: Check service name spelling

## Development

### Running Tests

```bash
# Install in development mode
pip install -e . -f auth_module_setup.py

# Run the module
python -m auth_module.cli --help
```

### Adding New Services

To add support for a new service:

1. Add a new function in `auth_module/auth.py`:
```python
def get_newservice_credentials(path=None):
    """Get NewService API credentials."""
    return get_credentials("newservice", path)
```

2. Update `auth_module/__init__.py` to export the new function
3. Update the CLI if needed

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues and questions:
1. Check the troubleshooting section
2. Search existing issues
3. Create a new issue with detailed information 