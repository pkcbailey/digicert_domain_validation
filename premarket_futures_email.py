
import requests
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

# Replace these with your actual credentials
TWELVE_DATA_API_KEY = "18a51baa209a437293df758734f30e19"
GMAIL_USER = "paula.bailey@gmail.com"
GMAIL_PASS = "qoer hjwl ombn xobq"
TO_EMAIL = "paula.bailey@gmail.com"

# List of futures symbols available on Twelve Data
symbols = {
    "S&P 500 Futures": "ES=F",
    "Nasdaq Futures": "NQ=F",
    "Dow Futures": "YM=F"
}

def fetch_futures():
    results = []
    for name, symbol in symbols.items():
        url = f"https://api.twelvedata.com/quote?symbol={symbol}&apikey={TWELVE_DATA_API_KEY}"
        response = requests.get(url)
        data = response.json()
        if 'price' in data:
            results.append(f"{name}: {data['price']}")
        else:
            results.append(f"{name}: Error fetching data")
    return results

def send_email(content):
    msg = MIMEText("\n".join(content))
    msg["Subject"] = f"Premarket Futures Update - {datetime.now().strftime('%Y-%m-%d')}"
    msg["From"] = GMAIL_USER
    msg["To"] = TO_EMAIL

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_PASS)
        server.send_message(msg)

if __name__ == "__main__":
    report = fetch_futures()
    send_email(report)
