# Stock Tracker

A Python application that tracks stock purchases and sends daily performance reports via email.

## Features

- Track multiple stock purchases
- Daily price updates at 4:30 PM EST
- Individual and total performance calculations
- Email reports with detailed performance metrics
- Persistent storage of stock purchases

## Setup

1. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create a `.env` file with your configuration:
   ```
   SMTP_EMAIL=your_gmail@gmail.com
   ```

3. Set up Gmail for the application:
   - Enable 2-Step Verification in your Google Account settings
   - Generate an App Password:
     1. Go to your Google Account settings
     2. Navigate to Security > 2-Step Verification
     3. Scroll down to "App passwords"
     4. Generate a new app password for "Mail"
     5. Copy the generated 16-character password

4. Add your credentials to the keychain:
   ```bash
   # Add your Gmail App Password
   keyring set gmail_app_password password YOUR_16_CHARACTER_APP_PASSWORD
   
   # Add your Alpha Vantage API key
   keyring set alpha_vantage_api api_key YOUR_API_KEY
   ```

5. Get an API key from [Alpha Vantage](https://www.alphavantage.co/support/#api-key)

## Usage

1. Add stocks to track:
   - Option 1: Create a `stocks.csv` file with the following headers:
     ```
     ticker,purchase_date,shares,purchase_price
     AAPL,2024-01-01,10,150.0
     MSFT,2024-01-15,5,300.0
     ```
   - Option 2: Add stocks programmatically:
     ```python
     from stock_tracker import StockTracker
     
     tracker = StockTracker()
     tracker.add_stock("AAPL", "2024-01-01", 10, 150.0)
     ```

2. Run the tracker:
   ```bash
   python stock_tracker.py
   ```

The application will:
- Load stock purchases from `stocks.csv` (if available) or fall back to `stocks.json`
- Save updates to both `stocks.csv` and `stocks.json`
- Send daily reports at 4:30 PM EST
- Calculate individual and total gains/losses
- Email reports to pkcbailey@gmail.com

## Report Format

Daily reports include:
- Current date and time
- Individual stock performance:
  - Shares owned
  - Purchase price
  - Current price
  - Gain/loss in dollars and percentage
- Total portfolio performance:
  - Total investment
  - Total gain/loss
  - Overall percentage change

## Notes

- The free tier of Alpha Vantage has rate limits (5 API calls per minute)
- Stock prices are fetched at 4:30 PM EST each weekday
- Reports are sent via email using Gmail's SMTP server
- Stock purchases are stored in `stocks.json` 