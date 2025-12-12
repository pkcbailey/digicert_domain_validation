#!/usr/bin/env python3
import requests
import json
import csv
import os
import sys

# Configuration
DATA_DIR = "data"
INPUT_CSV = os.path.join(DATA_DIR, "domain_id_lookup.csv")
OUTPUT_FILE = os.path.join(DATA_DIR, "sectigo_domains.csv")
API_VAULT_PATH = os.path.expanduser('~/.ApiVault')
SECTIGO_BASE_URL = "https://cert-manager.com/api/domain/v1/"

def ensure_datadir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def load_credentials():
    if not os.path.exists(API_VAULT_PATH):
        print(f"Error: API vault not found at {API_VAULT_PATH}")
        sys.exit(1)
    with open(API_VAULT_PATH, 'r') as f:
        data = json.load(f)
    
    sectigo = data.get('Sectigo')
    if not sectigo:
        # Fallback to lowercase just in case
        sectigo = data.get('sectigo')

    if not sectigo:
        print("Error: No 'Sectigo' section in API vault")
        sys.exit(1)
        
    # Expecting login, password, customeruri (as per user)
    login = sectigo.get('login')
    password = sectigo.get('password')
    # User specified 'customeruri', mapping to customer_uri variable
    customer_uri = sectigo.get('customeruri')
    
    if not all([login, password, customer_uri]):
        print("Error: Incomplete Sectigo credentials. Need 'login', 'password', 'customeruri'.")
        sys.exit(1)
        
    return login, password, customer_uri

def get_domain_details(domain_id, login, password, customer_uri):
    # Using V1 API: GET https://cert-manager.com/api/domain/v1/{id}
    url = f"{SECTIGO_BASE_URL}{domain_id}"
    headers = {
        'login': login,
        'password': password,
        'customerUri': customer_uri,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 404:
             # Domain not found
            print(f"Warning: Domain ID {domain_id} not found (404).")
            return None
        else:
            print(f"Warning: Failed to get details for ID {domain_id}: {resp.status_code} - {resp.text}")
            return None
    except Exception as e:
        print(f"Error fetching details for ID {domain_id}: {e}")
        return None

def read_lookup_csv():
    if not os.path.exists(INPUT_CSV):
        print(f"Error: Input file {INPUT_CSV} not found.")
        sys.exit(1)
    
    domains_to_check = []
    with open(INPUT_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Expected schema: id,domain,CA
            ca = row.get('CA', '').strip()
            if ca.lower() == 'sectigo':
                domains_to_check.append(row)
    return domains_to_check

def map_sectigo_method(method_str):
    if not method_str:
        return 'OTHER'
    
    m = method_str.upper()
    if m == 'CNAME_CSR_HASH':
        return 'CNAME'
    elif m == 'EMAIL':
        return 'EMAIL'
    elif m == 'DNSTXT_RANDOM_VALUE':
        return 'TXT'
    else:
        return method_str

def main():
    ensure_datadir()
    login, password, customer_uri = load_credentials()
    
    domains_list = read_lookup_csv()
    print(f"Found {len(domains_list)} Sectigo domains in lookup CSV.")
    
    final_data = []
    
    # Output Header: id,name,active,dcv_method,Expiration
    
    for entry in domains_list:
        d_id = entry.get('id')
        d_name_csv = entry.get('domain')
        
        if not d_id:
            continue
            
        print(f"Fetching details for ID {d_id} ({d_name_csv})...")
        details = get_domain_details(d_id, login, password, customer_uri)
        
        if details:
            # Parse fields based on V1 response
            
            # Active status: Check 'state'
            # "Return for state should be for the active column"
            state = details.get('state', '')
            # If state is "ACTIVE", we put "ACTIVE". If it's something else, we put that.
            # Digicert was "ACTIVE" or empty. User said "Return for state should be for the active column".
            # Assuming if state is "ACTIVE" -> "ACTIVE".
            active_str = state if state else ""
            
            # Expiration
            # "dcvExpiration should go in Expiration"
            expiration_date = details.get('dcvExpiration', '')
            
            # DCV Method
            # "validationMethod conversion..."
            raw_method = details.get('validationMethod')
            dcv_method_str = map_sectigo_method(raw_method)
            
            # Name
            api_name = details.get('name') or d_name_csv
            
            final_data.append({
                'id': d_id,
                'name': api_name,
                'active': active_str,
                'dcv_method': dcv_method_str,
                'Expiration': expiration_date
            })
        else:
            print(f"Skipping {d_id} due to API error/missing data.")

    print(f"Writing results to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['id', 'name', 'active', 'dcv_method', 'Expiration']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in final_data:
            writer.writerow(row)
            
    print("Done.")

if __name__ == "__main__":
    main()
