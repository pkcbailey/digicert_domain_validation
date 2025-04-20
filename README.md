# Domain Validator

A Python script that helps validate domains by:
1. Adding domains to Digicert for validation
2. Retrieving required TXT records
3. Checking for Akamai hosting
4. Managing DNS records accordingly

## Features

- Secure API key storage using keyring
- Both GUI and command-line interfaces
- Automatic detection of Akamai hosting
- Email notifications for non-Akamai domains
- Python 3.10+ compatible

## Installation

1. Clone this repository
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

1. Create a `.env` file in the project directory with the following variables:
   ```
   DIGICERT_API_KEY=your_digicert_api_key
   AKAMAI_API_KEY=your_akamai_api_key
   AKAMAI_API_SECRET=your_akamai_api_secret
   SMTP_SERVER=your_smtp_server
   SMTP_PORT=587
   ADMIN_EMAIL=domainadmin@example.com
   ```

2. Alternatively, you can use the keyring to store API keys:
   ```bash
   python -c "import keyring; keyring.set_password('domain_validator', 'digicert', 'your_digicert_api_key')"
   python -c "import keyring; keyring.set_password('domain_validator', 'akamai', 'your_akamai_api_key')"
   python -c "import keyring; keyring.set_password('domain_validator', 'akamai_secret', 'your_akamai_api_secret')"
   ```

## Usage

### GUI Mode
Simply run the script without arguments:
```bash
python domain_validator.py
```

### Command Line Mode
Run the script with a domain as an argument:
```bash
python domain_validator.py example.com
```

## Security Notes

- API keys are stored securely using the system's keyring service
- Environment variables are loaded from a `.env` file
- The script uses HTTPS for all API communications
- Email credentials are not stored in the script

## Error Handling

The script includes comprehensive error handling for:
- Invalid domains
- API connection issues
- DNS resolution problems
- Email sending failures 