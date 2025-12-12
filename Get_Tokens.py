#!/usr/bin/env python3
import csv
import json
import os
import sys
import datetime
import requests

# Base configuration
DATA_DIR = "data"
LOG_DIR = "log"
INPUT_FILE = os.path.join(DATA_DIR, "combined_domains.csv")
# We update the same file or should we? User says "placing these in the combined_domains.csv"
# Safest is to read all, process, and write back.
OUTPUT_FILE = os.path.join(DATA_DIR, "combined_domains.csv")
API_VAULT_PATH = os.path.expanduser('~/.ApiVault')

def ensure_dirs():
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

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

def log_to_file(filename, content):
    """Writes content to a file in the log directory with a timestamp."""
    filepath = os.path.join(LOG_DIR, filename)
    timestamp = datetime.datetime.now().isoformat()
    try:
        with open(filepath, 'a') as f:
            f.write(f"--- {timestamp} ---\n")
            if isinstance(content, (dict, list)):
                f.write(json.dumps(content, indent=2))
            else:
                f.write(str(content))
            f.write("\n\n")
    except Exception as e:
        print(f"Failed to write to log {filename}: {e}")

def change_dcv_method(domain_id, api_key):
    url = f"https://www.digicert.com/services/v2/domain/{domain_id}/dcv/method"
    headers = {
        'X-DC-DEVKEY': api_key,
        'Content-Type': 'application/json'
    }
    payload = {"dcv_method": "dns-cname-token"}
    
    try:
        resp = requests.put(url, headers=headers, json=payload)
        # Log response
        log_name = f"dcv_method_change_{domain_id}.log"
        if resp.status_code in [200, 201, 204]:
             log_to_file(log_name, f"Success: {resp.status_code}\n{resp.text}")
             return True
        else:
             log_to_file(log_name, f"Error: {resp.status_code}\n{resp.text}")
             return False
    except Exception as e:
        log_to_file("errors.log", f"Exception changing DCV method for {domain_id}: {e}")
        return False

def get_dcv_token(domain_id, api_key):
    url = f"https://www.digicert.com/services/v2/domain/{domain_id}/dcv/token"
    headers = {
        'X-DC-DEVKEY': api_key,
        'Content-Type': 'application/json'
    }
    try:
        resp = requests.post(url, headers=headers)
        # Log response
        log_name = f"dcv_token_{domain_id}.log"
        if resp.status_code in [200, 201]:
            data = resp.json()
            log_to_file(log_name, data)
            return data
        else:
            log_to_file(log_name, f"Error: {resp.status_code}\n{resp.text}")
            return None
    except Exception as e:
        log_to_file("errors.log", f"Exception getting token for {domain_id}: {e}")
        return None

def load_sectigo_credentials():
    if not os.path.exists(API_VAULT_PATH):
        print(f"Error: API vault not found at {API_VAULT_PATH}")
        sys.exit(1)
    try:
        with open(API_VAULT_PATH, 'r') as f:
            data = json.load(f)
        sectigo = data.get('Sectigo', {})
        if not sectigo:
             print("Error: Sectigo section not found in vault")
             sys.exit(1)
        
        required = ['login', 'password', 'customeruri'] # orgID is meantioned but maybe not needed for this specific call?
        # User example uses login, password, customerUri.
        creds = {k: sectigo.get(k) for k in required}
        if not all(creds.values()):
             # Try case sensitive keys if lowercase failed
             creds['login'] = sectigo.get('login') or sectigo.get('Login')
             creds['password'] = sectigo.get('password') or sectigo.get('Password')
             creds['customeruri'] = sectigo.get('customeruri') or sectigo.get('customerUri')
        
        if not all(creds.values()):
            print(f"Error: Missing Sectigo credentials. Found: {list(creds.keys())}")
            sys.exit(1)
            
        return creds
    except Exception as e:
        print(f"Error loading Sectigo credentials: {e}")
        sys.exit(1)

def process_sectigo_domain(domain, creds):
    url = 'https://cert-manager.com/api/dcv/v1/validation/start/domain/cname'
    headers = {
        'Content-Type': 'application/json;charset=utf-8',
        'login': creds['login'],
        'password': creds['password'],
        'customerUri': creds['customeruri']
    }
    payload = {"domain": domain}
    
    try:
        resp = requests.post(url, headers=headers, json=payload)
        log_name = f"sectigo_dcv_{domain}.log"
        
        if resp.status_code == 200:
            data = resp.json()
            log_to_file(log_name, data)
            return data
        else:
            log_to_file(log_name, f"Error: {resp.status_code}\n{resp.text}")
            return None
    except Exception as e:
        log_to_file("errors.log", f"Exception processing Sectigo domain {domain}: {e}")
        return None

def main():
    ensure_dirs()
    digicert_key = load_digicert_api_key()
    sectigo_creds = load_sectigo_credentials()
    
    if not os.path.exists(INPUT_FILE):
        print(f"Error: Input file {INPUT_FILE} does not exist.")
        sys.exit(1)

    rows = []
    fieldnames = []
    
    print(f"Reading {INPUT_FILE}...")
    with open(INPUT_FILE, 'r', newline='') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)

    # Add new columns if they don't exist
    if 'Value' not in fieldnames:
        fieldnames.append('Value')
    if 'token' not in fieldnames:
        fieldnames.append('token')

    updated_rows = []
    
    print(f"Processing {len(rows)} domains...")
    
    # Test case filter
    TEST_DOMAINS = ['finastra.ai', 'misys.ai']
    
    for row in rows:
        provider = row.get('provider', '')
        domain_name = row.get('name', '')
        
        # Filter for test case
        if domain_name not in TEST_DOMAINS:
             updated_rows.append(row)
             continue

        # Filter for Sectigo only test
        if provider.lower() != 'sectigo':
             updated_rows.append(row)
             continue

        # Digicert Logic
        if provider.lower() == 'digicert':
            dcv_method = row.get('dcv_method', 'OTHER')
            domain_id = row.get('id')
            
            print(f"Processing Digicert Test Domain: {domain_name} (ID: {domain_id})")
            
            is_ready_for_token = False
            
            if dcv_method != 'CNAME':
                print(f"  Attempting to change DCV method for {domain_name}...")
                success = change_dcv_method(domain_id, digicert_key)
                if success:
                    row['dcv_method'] = 'CNAME'
                    is_ready_for_token = True
                else:
                    print(f"  Failed to set DCV method for {domain_id}")
            else:
                is_ready_for_token = True
                
            if is_ready_for_token:
                token_data = get_dcv_token(domain_id, digicert_key)
                if token_data:
                    row['Value'] = token_data.get('verification_value', '')
                    row['token'] = token_data.get('token', '')
                    print(f"  Token retrieved for {domain_name}")
                else:
                    print(f"  Failed to retrieve token for {domain_name}")

        # Sectigo Logic
        elif provider.lower() == 'sectigo':
            print(f"Processing Sectigo Test Domain: {domain_name}")
            # For Sectigo, we just call the start/domain/cname endpoint
            # It returns the host/point values directly
            
            sectigo_data = process_sectigo_domain(domain_name, sectigo_creds)
            if sectigo_data:
                # "return json from host into Value and point to token"
                row['Value'] = sectigo_data.get('host', '')
                row['token'] = sectigo_data.get('point', '')
                # Should we update dcv_method to CNAME? The call is literally start/domain/cname
                row['dcv_method'] = 'CNAME' 
                print(f"  Token retrieved for {domain_name}")
            else:
                 print(f"  Failed to retrieve token for {domain_name}")
        
        updated_rows.append(row)

    print(f"Writing updates to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_rows)
    print("Done.")

if __name__ == "__main__":
    main()
