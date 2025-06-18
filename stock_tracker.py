#!/usr/bin/env python3
"""
Stock Tracker Application

This application tracks stock purchases and saves daily performance reports as spreadsheets.
"""

import os
import json
import csv
import schedule
import time
from datetime import datetime, timezone
from typing import List, Dict, Optional
import pandas as pd
from dotenv import load_dotenv
import pytz
import requests
from functools import lru_cache

# Load environment variables
load_dotenv()

class StockTracker:
    """Main class for stock tracking operations"""
    
    def __init__(self, config_file="config.json"):
        self.config = self.load_config(config_file)
        self.html_file = "stocks.html"
        self.initialize_html()
        self.stocks_file = "stocks.json"
        self.csv_file = "stocks.csv"
        self.report_file = os.path.expanduser("~/Desktop/stock_report.xlsx")
        self.finnhub_api_key = os.getenv("FINNHUB_API_KEY", "d09t8r9r01qus8rfa1ogd09t8r9r01qus8rfa1p0")
        self.last_api_call = {}  # Track last API call time for each ticker
        self.min_api_interval = 1  # Minimum seconds between API calls
        self.load_stocks()
        
    def load_config(self, config_file):
        with open(config_file, 'r') as f:
            return json.load(f)

    def initialize_html(self):
        html_header = """<!DOCTYPE html>
<html>
<head>
    <title>Stock Tracker</title>
    <style>
        body { font-family: Arial, sans-serif; }
        table { border-collapse: collapse; width: 100%; }
        th, td { 
            padding: 8px; 
            text-align: left; 
            border-bottom: 1px solid #ddd;
            font-size: 16pt;
        }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <h1>Stock Prices</h1>
    <table>
        <tr>
            <th>Symbol</th>
            <th>Price</th>
            <th>Change</th>
            <th>Change %</th>
            <th>Timestamp</th>
        </tr>
"""
        with open(self.html_file, 'w') as f:
            f.write(html_header)

    def load_stocks(self) -> None:
        """Load stock purchases from JSON file and CSV file"""
        self.stocks = []
        
        # Try to load from CSV first
        if os.path.exists(self.csv_file):
            try:
                with open(self.csv_file, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        try:
                            # Clean up the data
                            ticker = row['ticker'].strip().upper()
                            purchase_date = row['purchase_date'].strip()
                            shares = float(row['shares'].strip())
                            purchase_price = float(row['purchase_price'].strip())
                            
                            # Validate the data
                            if not ticker or not purchase_date:
                                print(f"Warning: Skipping row with missing ticker or date: {row}")
                                continue
                                
                            self.stocks.append({
                                'ticker': ticker,
                                'purchase_date': purchase_date,
                                'shares': shares,
                                'purchase_price': purchase_price
                            })
                        except (ValueError, KeyError) as e:
                            print(f"Warning: Skipping invalid row: {row}. Error: {e}")
                            continue
                            
                if self.stocks:
                    print(f"Successfully loaded {len(self.stocks)} stocks from {self.csv_file}")
                    return
                else:
                    print(f"No valid stock data found in {self.csv_file}")
            except Exception as e:
                print(f"Error reading CSV file: {e}")
                print("Please check the CSV file format. It should have headers: ticker,purchase_date,shares,purchase_price")
        
        # Fall back to JSON if CSV fails or doesn't exist
        try:
            with open(self.stocks_file, 'r') as f:
                self.stocks = json.load(f)
            print(f"Loaded {len(self.stocks)} stocks from {self.stocks_file}")
        except FileNotFoundError:
            self.stocks = []
            print("No existing stock data found")
            
    def save_stocks(self) -> None:
        """Save stock purchases to both JSON and CSV files"""
        # Save to JSON
        with open(self.stocks_file, 'w') as f:
            json.dump(self.stocks, f, indent=4)
            
        # Save to CSV
        with open(self.csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['ticker', 'purchase_date', 'shares', 'purchase_price'])
            writer.writeheader()
            for stock in self.stocks:
                writer.writerow(stock)
                
    def add_stock(self, ticker: str, purchase_date: str, shares: float, purchase_price: float) -> None:
        """Add a new stock purchase"""
        self.stocks.append({
            'ticker': ticker.upper(),
            'purchase_date': purchase_date,
            'shares': shares,
            'purchase_price': purchase_price
        })
        self.save_stocks()
        
    @lru_cache(maxsize=100)
    def get_cached_price(self, ticker: str) -> Optional[Dict]:
        """Get cached price data for a ticker"""
        return None  # Cache is managed by lru_cache decorator

    def get_current_price(self, ticker: str) -> Dict:
        """Fetch current stock price and change from Finnhub with rate limiting"""
        # Check cache first
        cached_data = self.get_cached_price(ticker)
        if cached_data:
            return cached_data

        # Check if we need to wait before making another API call
        current_time = time.time()
        if ticker in self.last_api_call:
            time_since_last = current_time - self.last_api_call[ticker]
            if time_since_last < self.min_api_interval:
                time.sleep(self.min_api_interval - time_since_last)

        try:
            # Get quote data from Finnhub
            quote_url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={self.finnhub_api_key}"
            quote_response = requests.get(quote_url)
            
            if quote_response.status_code != 200:
                print(f"Warning: Failed to get quote data for {ticker}")
                return {'price': 0.0, 'change': 0.0, 'change_percent': 0.0}
            
            quote_data = quote_response.json()
            current_price = quote_data.get('c', 0.0)  # Current price
            previous_close = quote_data.get('pc', 0.0)  # Previous close
            
            if not current_price or not previous_close:
                print(f"Warning: No price data available for {ticker}")
                return {'price': 0.0, 'change': 0.0, 'change_percent': 0.0}
            
            change = current_price - previous_close
            change_percent = (change / previous_close) * 100 if previous_close > 0 else 0
            
            result = {
                'price': float(current_price),
                'change': float(change),
                'change_percent': float(change_percent)
            }
            
            # Update cache and last API call time
            self.get_cached_price.cache_clear()  # Clear old cache entries
            self.get_cached_price(ticker)  # Cache the new result
            self.last_api_call[ticker] = time.time()
            
            return result
            
        except Exception as e:
            print(f"Error fetching price for {ticker}: {str(e)}")
            return {'price': 0.0, 'change': 0.0, 'change_percent': 0.0}
            
    def get_finnhub_rating(self, symbol: str) -> Dict:
        """Get stock rating from Finnhub API"""
        try:
            url = f"https://finnhub.io/api/v1/stock/recommendation?symbol={symbol}&token={self.finnhub_api_key}"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                if data:
                    # Get the most recent rating
                    latest = data[0]
                    return {
                        'rating': latest.get('buy', 0),
                        'strong_buy': latest.get('strongBuy', 0),
                        'buy': latest.get('buy', 0),
                        'hold': latest.get('hold', 0),
                        'sell': latest.get('sell', 0),
                        'strong_sell': latest.get('strongSell', 0),
                        'period': latest.get('period', '')
                    }
        except Exception as e:
            print(f"Error getting Finnhub rating for {symbol}: {str(e)}")
        return {
            'rating': 0,
            'strong_buy': 0,
            'buy': 0,
            'hold': 0,
            'sell': 0,
            'strong_sell': 0,
            'period': 'N/A'
        }

    def calculate_performance(self) -> List[Dict]:
        """Calculate performance for all stocks"""
        performance = []
        unique_tickers = set(stock['ticker'] for stock in self.stocks)
        
        # Pre-fetch all prices with rate limiting
        price_cache = {}
        for ticker in unique_tickers:
            price_cache[ticker] = self.get_current_price(ticker)
        
        for stock in self.stocks:
            current_data = price_cache[stock['ticker']]
            finnhub_data = self.get_finnhub_rating(stock['ticker'])
            purchase_value = stock['shares'] * stock['purchase_price']
            current_value = stock['shares'] * current_data['price']
            gain_loss = current_value - purchase_value
            gain_loss_percent = (gain_loss / purchase_value) * 100 if purchase_value > 0 else 0
            
            # Calculate consensus rating
            total_ratings = sum([
                finnhub_data['strong_buy'],
                finnhub_data['buy'],
                finnhub_data['hold'],
                finnhub_data['sell'],
                finnhub_data['strong_sell']
            ])
            
            if total_ratings > 0:
                rating_score = (
                    (finnhub_data['strong_buy'] * 5) +
                    (finnhub_data['buy'] * 4) +
                    (finnhub_data['hold'] * 3) +
                    (finnhub_data['sell'] * 2) +
                    (finnhub_data['strong_sell'] * 1)
                ) / total_ratings
                
                if rating_score >= 4.5:
                    consensus = "Strong Buy"
                elif rating_score >= 3.5:
                    consensus = "Buy"
                elif rating_score >= 2.5:
                    consensus = "Hold"
                elif rating_score >= 1.5:
                    consensus = "Sell"
                else:
                    consensus = "Strong Sell"
            else:
                consensus = "No Ratings"
            
            performance.append({
                'Ticker': stock['ticker'],
                'Shares': stock['shares'],
                'Purchase Date': stock['purchase_date'],
                'Purchase Price': stock['purchase_price'],
                'Current Price': current_data['price'],
                'Change': current_data['change'],
                'Change %': current_data['change_percent'],
                'Purchase Value': purchase_value,
                'Current Value': current_value,
                'Gain/Loss ($)': gain_loss,
                'Gain/Loss (%)': gain_loss_percent,
                'Consensus Rating': consensus,
                'Strong Buy': finnhub_data['strong_buy'],
                'Buy': finnhub_data['buy'],
                'Hold': finnhub_data['hold'],
                'Sell': finnhub_data['sell'],
                'Strong Sell': finnhub_data['strong_sell'],
                'Rating Period': finnhub_data['period']
            })
            
        return performance
        
    def generate_report(self) -> None:
        """Generate and save spreadsheet report with stock performance"""
        performance = self.calculate_performance()
        
        # Create DataFrame
        df = pd.DataFrame(performance)
        
        # Calculate totals
        total_investment = df['Purchase Value'].sum()
        total_current = df['Current Value'].sum()
        total_gain_loss = total_current - total_investment
        total_percent = (total_gain_loss / total_investment) * 100 if total_investment > 0 else 0
        
        # Add summary row
        summary = pd.DataFrame([{
            'Ticker': 'TOTAL',
            'Shares': '',
            'Purchase Date': '',
            'Purchase Price': '',
            'Current Price': '',
            'Change': '',
            'Change %': '',
            'Purchase Value': total_investment,
            'Current Value': total_current,
            'Gain/Loss ($)': total_gain_loss,
            'Gain/Loss (%)': total_percent,
            'Consensus Rating': '',
            'Strong Buy': '',
            'Buy': '',
            'Hold': '',
            'Sell': '',
            'Strong Sell': '',
            'Rating Period': ''
        }])
        
        # Combine data and summary
        df = pd.concat([df, summary], ignore_index=True)
        
        # Format numbers
        df['Purchase Price'] = df['Purchase Price'].apply(lambda x: '${:,.2f}'.format(x) if pd.notna(x) and x != '' else '')
        df['Current Price'] = df['Current Price'].apply(lambda x: '${:,.2f}'.format(x) if pd.notna(x) and x != '' else '')
        df['Change'] = df['Change'].apply(lambda x: '${:,.2f}'.format(x) if pd.notna(x) and x != '' else '')
        df['Change %'] = df['Change %'].apply(lambda x: '{:,.2f}%'.format(x) if pd.notna(x) and x != '' else '')
        df['Purchase Value'] = df['Purchase Value'].apply(lambda x: '${:,.2f}'.format(x) if pd.notna(x) and x != '' else '')
        df['Current Value'] = df['Current Value'].apply(lambda x: '${:,.2f}'.format(x) if pd.notna(x) and x != '' else '')
        df['Gain/Loss ($)'] = df['Gain/Loss ($)'].apply(lambda x: '${:,.2f}'.format(x) if pd.notna(x) and x != '' else '')
        df['Gain/Loss (%)'] = df['Gain/Loss (%)'].apply(lambda x: '{:,.2f}%'.format(x) if pd.notna(x) and x != '' else '')
        
        # Save to Excel
        with pd.ExcelWriter(self.report_file, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Stock Performance')
            
            # Auto-adjust column widths
            worksheet = writer.sheets['Stock Performance']
            for idx, col in enumerate(df.columns):
                max_length = max(
                    df[col].astype(str).apply(len).max(),
                    len(str(col))
                )
                worksheet.column_dimensions[chr(65 + idx)].width = max_length + 2
            
        print(f"Report saved to {self.report_file}")
            
    def generate_text_report(self) -> None:
        """Generate a human-readable text report"""
        performance = self.calculate_performance()
        text_file = os.path.join(os.path.dirname(self.report_file), "stock_report.txt")
        
        with open(text_file, 'w') as f:
            # Write header
            f.write("=" * 80 + "\n")
            f.write("STOCK PORTFOLIO REPORT\n")
            f.write("=" * 80 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            
            # Write individual stock performance
            f.write("INDIVIDUAL STOCK PERFORMANCE\n")
            f.write("-" * 80 + "\n")
            
            for stock in performance[:-1]:  # Exclude the total row
                f.write(f"\nStock: {stock['Ticker']}\n")
                f.write(f"Shares: {stock['Shares']}\n")
                f.write(f"Purchase Date: {stock['Purchase Date']}\n")
                f.write(f"Purchase Price: ${stock['Purchase Price']:,.2f}\n")
                f.write(f"Current Price: ${stock['Current Price']:,.2f}\n")
                
                # Format change with color indicators
                change = stock['Change']
                change_percent = stock['Change %']
                if change > 0:
                    change_str = f"+${change:,.2f} (+{change_percent:,.2f}%)"
                else:
                    change_str = f"-${abs(change):,.2f} (-{abs(change_percent):,.2f}%)"
                
                f.write(f"Today's Change: {change_str}\n")
                f.write(f"Purchase Value: ${stock['Purchase Value']:,.2f}\n")
                f.write(f"Current Value: ${stock['Current Value']:,.2f}\n")
                
                # Format gain/loss with color indicators
                gain_loss = stock['Gain/Loss ($)']
                gain_loss_percent = stock['Gain/Loss (%)']
                if gain_loss > 0:
                    gain_loss_str = f"+${gain_loss:,.2f} (+{gain_loss_percent:,.2f}%)"
                else:
                    gain_loss_str = f"-${abs(gain_loss):,.2f} (-{abs(gain_loss_percent):,.2f}%)"
                
                f.write(f"Total Gain/Loss: {gain_loss_str}\n")
                
                # Write analyst ratings
                f.write("\nAnalyst Ratings:\n")
                f.write(f"Consensus: {stock['Consensus Rating']}\n")
                f.write(f"Strong Buy: {stock['Strong Buy']}\n")
                f.write(f"Buy: {stock['Buy']}\n")
                f.write(f"Hold: {stock['Hold']}\n")
                f.write(f"Sell: {stock['Sell']}\n")
                f.write(f"Strong Sell: {stock['Strong Sell']}\n")
                f.write(f"Rating Period: {stock['Rating Period']}\n")
                
                f.write("-" * 40 + "\n")
            
            # Write summary
            total = performance[-1]  # Get the total row
            f.write("\nPORTFOLIO SUMMARY\n")
            f.write("=" * 80 + "\n")
            f.write(f"Total Investment: ${total['Purchase Value']:,.2f}\n")
            f.write(f"Current Value: ${total['Current Value']:,.2f}\n")
            
            # Format total gain/loss
            total_gain_loss = total['Gain/Loss ($)']
            total_percent = total['Gain/Loss (%)']
            if total_gain_loss > 0:
                total_str = f"+${total_gain_loss:,.2f} (+{total_percent:,.2f}%)"
            else:
                total_str = f"-${abs(total_gain_loss):,.2f} (-{abs(total_percent):,.2f}%)"
            
            f.write(f"Total Gain/Loss: {total_str}\n")
            f.write("=" * 80 + "\n")
        
        print(f"Text report saved to: {text_file}")

    def run_daily_report(self) -> None:
        """Run the daily report at 4:30 PM EST"""
        self.generate_report()

    def update_stocks(self):
        # Sort symbols alphabetically
        symbols = sorted(self.config['symbols'])
        
        for symbol in symbols:
            try:
                stock_data = self.get_current_price(symbol)
                self.write_to_html(symbol, stock_data)
                print(f"Updated {symbol}: ${stock_data['price']:.2f} ({stock_data['change']:+.2f}, {stock_data['change_percent']:+.2f}%)")
            except Exception as e:
                print(f"Error fetching {symbol}: {str(e)}")

    def write_to_html(self, symbol: str, stock_data: Dict):
        html_row = f"""
        <tr>
            <td>{symbol}</td>
            <td>${stock_data['price']:.2f}</td>
            <td>{stock_data['change']:+.2f}</td>
            <td>{stock_data['change_percent']:+.2f}%</td>
            <td>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td>
        </tr>
"""
        with open(self.html_file, 'a') as f:
            f.write(html_row)

    def run(self):
        try:
            while True:
                self.update_stocks()
                time.sleep(self.config['update_frequency'] * 60)  # Convert minutes to seconds
        except KeyboardInterrupt:
            # Write HTML footer when program is stopped
            with open(self.html_file, 'a') as f:
                f.write("""
    </table>
</body>
</html>""")
            print("\nProgram stopped. HTML file updated.")

def main():
    """Main entry point"""
    print("Starting stock tracker...")
    tracker = StockTracker()
    
    print("\nProcessing stocks...")
    # Generate reports
    tracker.generate_report()
    print("✓ Excel report generated")
    
    tracker.generate_text_report()
    print("✓ Text report generated")
    
    print(f"\nReports updated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Excel report saved to: {tracker.report_file}")
    print("Processing complete!")

if __name__ == "__main__":
    main() 