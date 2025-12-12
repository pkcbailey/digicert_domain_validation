import requests
import json
import os
import sys

API_VAULT_PATH = os.path.expanduser('~/.ApiVault')

def load_digicert_api_key():
    if not os.path.exists(API_VAULT_PATH):
        print(f"Error: API vault not found at {API_VAULT_PATH}")
        sys.exit(1)
    try:
        with open(API_VAULT_PATH, 'r') as f:
            data = json.load(f)
        key = data.get('digicert', {}).get('api')
        if not key:
            print("Error: Digicert API key not found in vault")
            sys.exit(1)
        return key
    except Exception as e:
        print(f"Error loading credentials: {e}")
        sys.exit(1)

def get_domain_info(domain_id, api_key):
    url = f"https://www.digicert.com/services/v2/domain/{domain_id}?include_dcv=true"
    headers = {
        'X-DC-DEVKEY': api_key,
        'Content-Type': 'application/json'
    }
    
    print(f"Getting info for domain {domain_id}...")
    resp = requests.get(url, headers=headers)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}")

if __name__ == "__main__":
    api_key = load_digicert_api_key()
    get_domain_info(5330778, api_key)
