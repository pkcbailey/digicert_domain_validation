#!/usr/bin/env python3

import sqlite3
import requests
import os
import matplotlib.pyplot as plt

def load_api_key():
    """Load Finnhub API key from ~/.ApiKey file"""
    api_key_file = os.path.expanduser('~/.ApiKey')
    try:
        with open(api_key_file, 'r') as f:
            for line in f:
                if line.strip().startswith('finnhub='):
                    return line.split('=', 1)[1].strip().strip('"')
        raise ValueError("Finnhub API key not found in ~/.ApiKey")
    except FileNotFoundError:
        raise FileNotFoundError("~/.ApiKey file not found")

def get_price(ticker, api_key):
    """Get current stock price using Finnhub API"""
    try:
        url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={api_key}"
        response = requests.get(url)
        response.raise_for_status()
        
        data = response.json()
        
        if 'c' in data and data['c'] is not None:
            return float(data['c'])  # Current price
        else:
            print(f"Could not find price for {ticker}")
            return None
            
    except Exception as e:
        print(f"Error fetching data for {ticker}: {str(e)}")
        return None

def calculate_pnl():
    """Calculate profit/loss for all stocks in the database"""
    try:
        # Load API key
        api_key = load_api_key()
        print("✅ API key loaded successfully")
        
        # Connect to database
        conn = sqlite3.connect('portfolio.db')
        cursor = conn.cursor()
        
        # Get all stocks from database
        cursor.execute("SELECT ticker, purchase_date, shares, buy_price FROM stocks")
        rows = cursor.fetchall()
        
        if not rows:
            print("No stocks found in database. Run ticker_buy_price.py first to import data.")
            return
        
        print(f"Found {len(rows)} stock entries to analyze")
        print("-" * 60)
        
        total_pnl = 0
        total_invested = 0
        total_current_value = 0
        
        # Lists for matplotlib
        tickers = []
        profits = []
        
        for ticker, purchase_date, shares, buy_price in rows:
            current_price = get_price(ticker, api_key)
            
            if current_price is not None:
                invested = buy_price * shares
                current_value = current_price * shares
                pnl = current_value - invested
                
                print(f"{ticker:6} | Shares: {shares:3} | Buy: ${buy_price:7.2f} | Current: ${current_price:7.2f} | P&L: ${pnl:8.2f}")
                
                # Add data for matplotlib
                tickers.append(ticker)
                profits.append(pnl)
                
                total_pnl += pnl
                total_invested += invested
                total_current_value += current_value
            else:
                print(f"{ticker:6} | Shares: {shares:3} | Buy: ${buy_price:7.2f} | Current: ERROR | P&L: ERROR")
        
        print("-" * 60)
        print(f"Total Invested: ${total_invested:,.2f}")
        print(f"Total Current Value: ${total_current_value:,.2f}")
        print(f"Total P&L: ${total_pnl:,.2f}")
        
        if total_invested > 0:
            percent_change = (total_pnl / total_invested) * 100
            print(f"Total Return: {percent_change:+.2f}%")
        
        conn.close()
        
        # Create matplotlib visualization
        if tickers and profits:
            create_portfolio_chart(tickers, profits, total_pnl)
        
    except Exception as e:
        print(f"Error: {str(e)}")

def create_portfolio_chart(tickers, profits, total_pnl):
    """Create a bar chart of portfolio P&L"""
    try:
        # Create the bar chart
        colors = ['green' if x > 0 else 'red' for x in profits]
        plt.figure(figsize=(12, 8))
        bars = plt.bar(tickers, profits, color=colors, alpha=0.7)
        
        # Add value labels on bars
        for bar, profit in zip(bars, profits):
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height,
                    f'${profit:.0f}', ha='center', va='bottom' if height > 0 else 'top',
                    fontweight='bold')
        
        # Customize the chart
        plt.title(f"Portfolio P&L by Stock (Total: ${total_pnl:,.0f})", fontsize=16, fontweight='bold')
        plt.ylabel("Profit / Loss ($)", fontsize=12)
        plt.xlabel("Ticker Symbol", fontsize=12)
        plt.grid(axis='y', alpha=0.3)
        plt.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        
        # Rotate x-axis labels for better readability
        plt.xticks(rotation=45)
        
        # Adjust layout to prevent label cutoff
        plt.tight_layout()
        
        # Save the chart
        plt.savefig('portfolio_pnl_chart.png', dpi=300, bbox_inches='tight')
        print("📊 Chart saved as 'portfolio_pnl_chart.png'")
        
        # Show the chart
        plt.show()
        
    except Exception as e:
        print(f"Error creating chart: {str(e)}")

if __name__ == "__main__":
    calculate_pnl() 