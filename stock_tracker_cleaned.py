#!/usr/bin/env python3
"""
Stock Tracker Application

This application tracks stock purchases and saves daily performance reports as spreadsheets.
"""

import os
import json
import csv
from datetime import datetime, timezone
from typing import List, Dict
import yfinance as yf
import pandas as pd
from dotenv import load_dotenv
import pytz
import requests

# Load environment variables
load_dotenv()

class StockTracker:
    """Main class for stock tracking operations"""
    
    def __init__(self, config_file="config.json"):
        self.config = self.load_config(config_file)
                
        self.stocks_file = "stocks.json"
        self.csv_file = "stocks.csv"
        self.report_file = os.path.expanduser("~/Desktop/stock_report.xlsx")
        self.load_stocks()
        
    def load_config(self, config_file):
        with open(config_file, 'r') as f:
            return json.load(f)

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
        
    def get_current_price(self, ticker: str) -> float:
        """Fetch current stock price from Yahoo Finance"""
        try:
            stock = yf.Ticker(ticker)
            current_price = stock.info.get('regularMarketPrice', 0.0)
            if not current_price:
                print(f"Warning: No price data available for {ticker}")
                return 0.0
            return float(current_price)
        except Exception as e:
            print(f"Error fetching price for {ticker}: {str(e)}")
            return 0.0
            
    def calculate_performance(self) -> List[Dict]:
        """Calculate performance for all stocks"""
        performance = []
        for stock in self.stocks:
            current_price = self.get_current_price(stock['ticker'])
            purchase_value = stock['shares'] * stock['purchase_price']
            current_value = stock['shares'] * current_price
            gain_loss = current_value - purchase_value
            gain_loss_percent = (gain_loss / purchase_value) * 100 if purchase_value > 0 else 0
            
            performance.append({
                'Ticker': stock['ticker'],
                'Shares': stock['shares'],
                'Purchase Date': stock['purchase_date'],
                'Purchase Price': stock['purchase_price'],
                'Current Price': current_price,
                'Purchase Value': purchase_value,
                'Current Value': current_value,
                'Gain/Loss ($)': gain_loss,
                'Gain/Loss (%)': gain_loss_percent
            })
            
        return performance
        
    def generate_report(self) -> None:
        """Generate and save spreadsheet report with stock performance"""
        performance = self.calculate_performance()
        
        # Create DataFrame
        df = pd.DataFrame(performance)
        df = df.sort_values(by='Ticker')
        
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
            'Purchase Value': total_investment,
            'Current Value': total_current,
            'Gain/Loss ($)': total_gain_loss,
            'Gain/Loss (%)': total_percent
        }])
        
        # Combine data and summary
        df = pd.concat([df, summary], ignore_index=True)
        
        # Format numbers
        df['Purchase Price'] = df['Purchase Price'].apply(lambda x: '${:,.2f}'.format(x) if pd.notna(x) and x != '' else '')
        df['Current Price'] = df['Current Price'].apply(lambda x: '${:,.2f}'.format(x) if pd.notna(x) and x != '' else '')
        df['Purchase Value'] = df['Purchase Value'].apply(lambda x: '${:,.2f}'.format(x) if pd.notna(x) and x != '' else '')
        df['Current Value'] = df['Current Value'].apply(lambda x: '${:,.2f}'.format(x) if pd.notna(x) and x != '' else '')
        df['Gain/Loss ($)'] = df['Gain/Loss ($)'].apply(lambda x: '${:,.2f}'.format(x) if pd.notna(x) and x != '' else '')
        df['Gain/Loss (%)'] = df['Gain/Loss (%)'].apply(lambda x: '{:,.2f}%'.format(x) if pd.notna(x) and x != '' else '')
        
        # Save to Excel
        with pd.ExcelWriter(self.report_file, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Stock Performance')
        df.style.set_properties(**{'font-size': '16pt'})
            
            # Auto-adjust column widths
        worksheet = writer.sheets['Stock Performance']
        for idx, col in enumerate(df.columns):
            max_length = max(
                df[col].astype(str).apply(len).max(),
                len(str(col))
            )
            worksheet.column_dimensions[chr(65 + idx)].width = max_length + 2
            
        print(f"Report saved to {self.report_file}")
            
    def run_daily_report(self) -> None:
        """Run the daily report at 4:30 PM EST"""
        self.generate_report()

    def update_stocks(self):
        # Sort symbols alphabetically
        symbols = sorted(self.config['symbols'])
        
        for symbol in symbols:
            try:
                stock_data = self.fetch_stock_price(symbol)
                self.write_to_html(stock_data)
                print(f"Updated {symbol}: ${stock_data['price']:.2f} at {stock_data['timestamp']}")
            except Exception as e:
                print(f"Error fetching {symbol}: {str(e)}")

    def fetch_stock_price(self, symbol):
        url = f"https://www.alphavantage.co/query"
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": self.config['api_key']
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        quote = data['Global Quote']
        return {
            'symbol': symbol,
            'price': float(quote['05. price']),
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    def write_to_html(self, stock_data):
        html_row = f"""
        <tr>
            <td>{stock_data['symbol']}</td>
            <td>${stock_data['price']:.2f}</td>
            <td>{stock_data['timestamp']}</td>
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
    tracker = StockTracker()
    
    # Generate the report and exit
    tracker.generate_report()
    print("Report generated successfully. Exiting.")

if __name__ == "__main__":
    main() 
