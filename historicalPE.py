import pandas as pd
import requests
import datetime
import time

# Load your stock file
stocks_df = pd.read_csv("stocks.csv")
unique_tickers = stocks_df['ticker'].unique()

# Add your Finnhub API key here
API_KEY = "d09t8r9r01qus8rfa1ogd09t8r9r01qus8rfa1p0"
base_url = "https://finnhub.io/api/v1/stock/metric"

# Function to get valuation metrics
def get_ratios(ticker):
    url = f"{base_url}?symbol={ticker}&metric=all&token={API_KEY}"
    try:
        r = requests.get(url)
        if r.status_code == 200:
            data = r.json()
            pe = data['metric'].get('peBasicExclExtraTTM')
            ps = data['metric'].get('priceToSalesTTM')
            return pe, ps
    except:
        pass
    return None, None

# Collect data
results = []
for ticker in unique_tickers:
    pe, ps = get_ratios(ticker)
    results.append({
        'ticker': ticker,
        'P/E': pe,
        'P/S': ps,
        'date': datetime.date.today().isoformat()
    })
    time.sleep(1)  # Avoid rate limiting

# Save to CSV
ratios_df = pd.DataFrame(results)
ratios_df.to_csv(f"valuation_ratios_{datetime.date.today()}.csv", index=False)
print(ratios_df)

