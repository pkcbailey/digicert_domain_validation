#!/usr/bin/env python3
import sys
import os
import json
import csv
import requests
from datetime import datetime

# Configuration
DATA_DIR = "data"
OUTPUT_CSV = os.path.join(DATA_DIR, "domain_id_lookup.csv")
API_VAULT_PATH = os.path.expanduser('~/.ApiVault')

def ensure_datadir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def load_vault():
    if not os.path.exists(API_VAULT_PATH):
        print(f"Error: API vault file not found at {API_VAULT_PATH}")
        sys.exit(1)
    with open(API_VAULT_PATH, 'r') as f:
        return json.load(f)

def get_digicert_domains(api_key):
    print("Fetching DigiCert domains...")
    url = "https://www.digicert.com/services/v2/domain"
    headers = {
        'X-DC-DEVKEY': api_key,
        'Content-Type': 'application/json'
    }
    domains = []
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            # DigiCert response usually has a 'domains' key which is a list
            if 'domains' in data:
                items = data['domains']
            elif isinstance(data, list):
                items = data
            else:
                items = []
                print(f"Warning: Unexpected DigiCert response format: {data.keys() if isinstance(data, dict) else type(data)}")

            for item in items:
                d_id = item.get('id')
                d_name = item.get('name')
                if d_id and d_name:
                    domains.append({'id': d_id, 'domain': d_name, 'ca': 'DigiCert'})
            print(f"  Found {len(domains)} domains.")
        else:
            print(f"  Error: HTTP {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"  Exception: {e}")
    return domains

def get_sectigo_domains(login, password, customer_uri):
    print("Fetching Sectigo domains...")
    url = "https://cert-manager.com/api/domain/v1"
    headers = {
        'login': login,
        'password': password,
        'customerUri': customer_uri,
        'Content-Type': 'application/json'
    }
    domains = []
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            items = resp.json()
            if isinstance(items, list):
                for item in items:
                    d_id = item.get('id')
                    d_name = item.get('name')
                    if d_id and d_name:
                        # Sectigo names might be case-sensitive or not, sticking to raw response
                        domains.append({'id': d_id, 'domain': d_name, 'ca': 'Sectigo'})
                print(f"  Found {len(domains)} domains.")
            else:
                print(f"  Warning: Expected list, got {type(items)}")
        else:
            print(f"  Error: HTTP {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"  Exception: {e}")
    return domains

def save_to_csv(all_domains):
    ensure_datadir()
    try:
        print(f"Saving {len(all_domains)} records to {OUTPUT_CSV}...")
        with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['id', 'domain', 'CA']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for d in all_domains:
                writer.writerow({'id': d['id'], 'domain': d['domain'], 'CA': d['ca']})
        print("Done.")
    except Exception as e:
        print(f"Error writing CSV: {e}")

def main():
    vault = load_vault()

    all_domains = []

    # DigiCert
    digicert = vault.get('digicert') or {}
    dc_key = digicert.get('api')
    if dc_key:
        all_domains.extend(get_digicert_domains(dc_key))
    else:
        print("Skipping DigiCert (no API key found)")

    # Sectigo
    sectigo = vault.get('Sectigo') or {}
    sec_login = sectigo.get('login')
    sec_pass = sectigo.get('password')
    sec_uri = sectigo.get('customeruri')
    
    if sec_login and sec_pass and sec_uri:
        all_domains.extend(get_sectigo_domains(sec_login, sec_pass, sec_uri))
    else:
        print("Skipping Sectigo (missing credentials)")

    save_to_csv(all_domains)

if __name__ == "__main__":
    main()
