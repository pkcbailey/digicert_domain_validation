#!/usr/bin/env python3
import requests
import json
import csv
import os
import sys

# Configuration
DATA_DIR = "data"
INPUT_CSV = os.path.join(DATA_DIR, "domain_id_lookup.csv")
OUTPUT_FILE = os.path.join(DATA_DIR, "digicert_domains.csv")
API_VAULT_PATH = os.path.expanduser('~/.ApiVault')

def ensure_datadir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def load_credentials():
    if not os.path.exists(API_VAULT_PATH):
        print(f"Error: API vault not found at {API_VAULT_PATH}")
        sys.exit(1)
    with open(API_VAULT_PATH, 'r') as f:
        data = json.load(f)
    
    digicert = data.get('digicert')
    if not digicert:
        print("Error: No 'digicert' section in API vault")
        sys.exit(1)
        
    api_key = digicert.get('api')
    if not api_key:
        print("Error: No 'api' key found in digicert section")
        sys.exit(1)
    return api_key

def get_domain_details(domain_id, api_key):
    # Added include_dcv and include_validation as requested
    url = f"https://www.digicert.com/services/v2/domain/{domain_id}?include_dcv=true&include_validation=true"
    headers = {
        'X-DC-DEVKEY': api_key,
        'Content-Type': 'application/json'
    }
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            return resp.json()
        print(f"Warning: Failed to get details for {domain_id}: {resp.status_code}")
        return None
    except Exception as e:
        print(f"Error fetching details for {domain_id}: {e}")
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
            if ca.lower() == 'digicert':
                domains_to_check.append(row)
    return domains_to_check

def map_dcv_method(method):
    if not method:
        return "OTHER"
    l_method = method.lower()
    if 'dns-cname-token' in l_method:
        return 'CNAME'
    elif 'dns-txt-token' in l_method:
        return 'TXT'
    elif 'email' in l_method:
        return 'EMAIL'
    else:
        return 'OTHER'

def main():
    ensure_datadir()
    api_key = load_credentials()
    
    domains_list = read_lookup_csv()
    print(f"Found {len(domains_list)} Digicert domains in lookup CSV.")
    
    final_data = []
    
    # Header: id,name,active,dcv_method,Expiration
    
    for entry in domains_list:
        d_id = entry.get('id')
        d_name_csv = entry.get('domain')
        
        if not d_id:
            continue
            
        print(f"Fetching details for ID {d_id} ({d_name_csv})...")
        details = get_domain_details(d_id, api_key)
        
        if details:
            # Expiration
            raw_expiry = details.get('dcv_expiration_datetime')
            expiration_date = ""
            if raw_expiry:
                try:
                    expiration_date = raw_expiry.split('T')[0]
                except Exception:
                    expiration_date = raw_expiry
            
            # Active status
            # Check is_active boolean
            is_active = details.get('is_active', False)
            active_str = "ACTIVE" if is_active else ""
            
            # DCV Method
            raw_method = details.get('dcv_method')
            dcv_method_str = map_dcv_method(raw_method)
            
            # Name (prefer API name, fallback to CSV)
            api_name = details.get('name') or details.get('common_name') or d_name_csv
            
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
