#!/usr/bin/env python3
import sys
import os
import json
import requests
import csv
from datetime import datetime
import subprocess

DATA_DIR = "data"
LOG_DIR = "log"
LOG_FILE = os.path.join(LOG_DIR, "add-remove.log")
COMBINED_DOMAINS_CSV = os.path.join(DATA_DIR, "combined_domains.csv")

def ensure_dirs():
    for d in [DATA_DIR, LOG_DIR]:
        if not os.path.exists(d):
            os.makedirs(d)

def delete_log():
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)

def log_line(msg):
    ensure_dirs()
    with open(LOG_FILE, "a", encoding="utf-8") as logf:
        logf.write(msg + "\n")

def log_error(section, domain, error):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line("="*60)
    log_line(f"[{timestamp}] [{section}] ERROR for domain: {domain}")
    log_line(str(error))
    log_line("="*60)

def log_json(section, domain, data):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line(f"[{timestamp}] [{section}] RAW JSON for domain: {domain}")
    try:
        log_line(json.dumps(data, indent=2, sort_keys=True))
    except Exception as e:
        log_line(f"Could not JSON-encode object: {str(e)}; Original: {repr(data)}")
    log_line("="*60)

# --- DigiCert API ---
def add_to_digicert(domain, api_key, organization_id):
    url = "https://www.digicert.com/services/v2/domain"
    headers = {
        'X-DC-DEVKEY': api_key,
        'Content-Type': 'application/json'
    }
    payload = {
        "name": domain,
        "organization": {"id": organization_id},
        "validations": [{"type": "ov"}, {"type": "ev"}],
        "dcv_method": "dns-cname-token"
    }
    try:
        resp = requests.post(url, headers=headers, json=payload)
        try:
            resp_data = resp.json()
        except Exception:
            log_line(f"--- DigiCert-ADD: HTTP {resp.status_code}, body: {repr(resp.text)}")
            resp_data = {"error": "No JSON in response", "content": resp.text, "status_code": resp.status_code}
        log_json("DigiCert-ADD", domain, resp_data)
        resp.raise_for_status()
        print(f"[DigiCert] ✅ Added: {domain}")
        return resp_data
    except Exception as e:
        log_error("DigiCert-ADD", domain, e)
        print(f"[DigiCert] ❌ ERROR creating domain '{domain}': {str(e)}")
        return None

def remove_from_digicert_by_id(domain_id, api_key, domain):
    url = f"https://www.digicert.com/services/v2/domain/{domain_id}"
    headers = {'X-DC-DEVKEY': api_key}
    try:
        resp = requests.delete(url, headers=headers)
        try:
            data = resp.json()
        except Exception:
            log_line(f"--- DigiCert-REMOVE: HTTP {resp.status_code}, body: {repr(resp.text)}")
            data = {"error": "No JSON in response", "content": resp.text, "status_code": resp.status_code}
        log_json("DigiCert-REMOVE", domain, data)
        resp.raise_for_status()
        print(f"[DigiCert] 🗑️ Removed: {domain}")
        return True
    except Exception as e:
        log_error("DigiCert-REMOVE", domain, e)
        print(f"[DigiCert] ❌ ERROR removing domain '{domain}': {str(e)}")
        return None

# --- Sectigo API ---
def remove_from_sectigo_by_id(domain_id, login, password, customer_uri, domain):
    url = f"https://cert-manager.com/api/domain/v1/{domain_id}"
    headers = {
        'login': login,
        'password': password,
        'customerUri': customer_uri
    }
    try:
        resp = requests.delete(url, headers=headers)
        if resp.status_code == 204:
            log_line(f"[Sectigo-REMOVE] HTTP 204: Domain '{domain}' successfully deleted.")
            print(f"[Sectigo] 🗑️ Removed: {domain} (ID {domain_id})")
            return True
        else:
            try:
                resp_data = resp.json()
            except Exception:
                log_line(f"--- Sectigo-REMOVE: HTTP {resp.status_code}, body: {repr(resp.text)}")
                resp_data = {"error": "No JSON in response", "content": resp.text, "status_code": resp.status_code}
            log_json("Sectigo-REMOVE", domain, resp_data)
            print(f"[Sectigo] ❌ ERROR removing domain '{domain}': HTTP {resp.status_code}")
            return None
    except Exception as e:
        log_error("Sectigo-REMOVE", domain, e)
        print(f"[Sectigo] ❌ ERROR removing domain '{domain}': {str(e)}")
        return None

def add_to_sectigo(domain, login, password, customer_uri, org_id):
    url = 'https://cert-manager.com/api/domain/v1'
    headers = {
        'Content-Type': 'application/json;charset=utf-8',
        'login': login,
        'password': password,
        'customerUri': customer_uri
    }
    payload = {
        "name": domain,
        "description": "Domain created via Add_Remove_domain.py",
        "active": True,
        "enabled": True,
        "includeSubdomains": True,
        "delegations": [{
            "orgId": org_id,
            "certTypes": ["SSL"],
            "domainCertificateRequestPrivileges": ["SUBDOMAIN", "DOMAIN"]
        }]
    }
    try:
        resp = requests.post(url, headers=headers, json=payload)
        try:
            resp_data = resp.json()
        except Exception:
            log_line(f"--- Sectigo-ADD: HTTP {resp.status_code}, body: {repr(resp.text)}")
            resp_data = {"error": "No JSON in response", "content": resp.text, "status_code": resp.status_code}
        log_json("Sectigo-ADD", domain, resp_data)
        resp.raise_for_status()
        print(f"[Sectigo] ✅ Added: {domain}")
        return resp_data
    except Exception as e:
        log_error("Sectigo-ADD", domain, e)
        print(f"[Sectigo] ❌ ERROR creating domain '{domain}': {str(e)}")
        return None

# --- Verification Helpers ---

def get_digicert_domain_details(domain_id, api_key):
    url = f"https://www.digicert.com/services/v2/domain/{domain_id}"
    headers = {
        'X-DC-DEVKEY': api_key,
        'Content-Type': 'application/json'
    }
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            return resp.json()
        log_line(f"[DigiCert-GET] Failed to get details for {domain_id}: {resp.status_code} {resp.text}")
        return None
    except Exception as e:
        log_line(f"[DigiCert-GET] Exception for {domain_id}: {e}")
        return None

def verify_digicert_removal(domain, api_key):
    # Search for the domain in the list to confirm it is gone.
    # Note: This assumes we can list domains. If the list is huge, this might be slow,
    # but still likely faster than the full Get_CA_data.py if that script does much more.
    url = "https://www.digicert.com/services/v2/domain"
    headers = {
        'X-DC-DEVKEY': api_key,
        'Content-Type': 'application/json'
    }
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            domains = resp.json().get('domains', []) # Adjust structure if needed, assuming dict with list or list
            if isinstance(domains, list):
                # direct list
                pass
            elif isinstance(resp.json(), list):
                domains = resp.json()
            
            found = False
            for d in domains:
                d_name = d.get('name', '').lower()
                if d_name == domain.lower():
                    found = True
                    break
            
            if not found:
                print(f"[DigiCert] Verification: Domain '{domain}' is successfully removed (not found in list).")
            else:
                print(f"[DigiCert] ⚠️ Verification: Domain '{domain}' was still found in the list!")
        else:
            print(f"[DigiCert] Verification failed: Could not list domains. HTTP {resp.status_code}")
    except Exception as e:
        print(f"[DigiCert] Verification error: {e}")

def get_sectigo_domain_details(domain_id, login, password, customer_uri):
    url = f"https://cert-manager.com/api/domain/v1/{domain_id}"
    headers = {
        'login': login,
        'password': password,
        'customerUri': customer_uri,
        'Content-Type': 'application/json'
    }
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            return resp.json()
        log_line(f"[Sectigo-GET] Failed to get details for {domain_id}: {resp.status_code} {resp.text}")
        return None
    except Exception as e:
        log_line(f"[Sectigo-GET] Exception for {domain_id}: {e}")
        return None

def verify_sectigo_removal(domain, login, password, customer_uri):
    url = 'https://cert-manager.com/api/domain/v1'
    headers = {
        'login': login,
        'password': password,
        'customerUri': customer_uri,
        'Content-Type': 'application/json'
    }
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            domains = resp.json() # Sectigo usually returns a list
            found = False
            if isinstance(domains, list):
                for d in domains:
                    d_name = d.get('name', '').lower()
                    if d_name == domain.lower():
                        found = True
                        break
            
            if not found:
                print(f"[Sectigo] Verification: Domain '{domain}' is successfully removed (not found in list).")
            else:
                print(f"[Sectigo] ⚠️ Verification: Domain '{domain}' was still found in the list!")
        else:
            print(f"[Sectigo] Verification failed: Could not list domains. HTTP {resp.status_code}")
    except Exception as e:
        print(f"[Sectigo] Verification error: {e}")

# --- CSV lookup ---
def find_domain_in_csv(domain, ca):
    """Return row from CSV for matching CA and domain, or None if not found."""
    if not os.path.exists(COMBINED_DOMAINS_CSV):
        print(f"CSV file not found: {COMBINED_DOMAINS_CSV}")
        return None
    with open(COMBINED_DOMAINS_CSV, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            # Expected: CA,ID,domain,ACTIVE,TXT,expiry,provider/ERROR
            if len(row) < 3:
                continue
            ca_name = row[0].strip().lower()
            csv_domain = row[2].strip().lower()
            if ca_name == ca.strip().lower() and csv_domain == domain.strip().lower():
                return row
    return None

# --- Main script logic ---
def main():
    ensure_dirs()
    delete_log()

    if len(sys.argv) != 3:
        print("Usage: python3 Add_Remove_domain.py <add|remove> <domain>")
        sys.exit(1)
    mode = sys.argv[1].strip().lower()
    target_domain = sys.argv[2].strip().lower()
    if mode not in ("add", "remove"):
        print("First argument must be 'add' or 'remove'.")
        sys.exit(1)
    if not target_domain:
        print("No domain specified.")
        sys.exit(1)

    # Load credentials from ~/.ApiVault
    api_vault_path = os.path.expanduser('~/.ApiVault')
    if not os.path.exists(api_vault_path):
        print(f"API vault file not found: {api_vault_path}")
        sys.exit(1)
    with open(api_vault_path, 'r') as f:
        vault = json.load(f)

    # DigiCert credentials
    digicert = vault.get('digicert') or {}
    digicert_api_key = digicert.get('api')
    
    # Enforce customerID as per user request
    digicert_org_id = digicert.get('customerID') or digicert.get('customer_id') or digicert.get('cid')
    
    if not digicert_org_id:
        print("Error: No 'customerID' found in digicert section of .ApiVault")
        sys.exit(1)

    print(f"Using DigiCert Customer ID: {digicert_org_id}")

    # Sectigo credentials
    sectigo = vault.get('Sectigo') or {}
    sectigo_login = sectigo.get('login')
    sectigo_password = sectigo.get('password')
    sectigo_customer_uri = sectigo.get('customeruri')
    sectigo_org_id = sectigo.get('orgID')

    print(f"\n{mode.title()}ing domain '{target_domain}' with DigiCert and Sectigo...\n")

    # --- Add mode ---
    if mode == "add":
        if digicert_api_key and digicert_org_id:
            dc_resp = add_to_digicert(target_domain, digicert_api_key, digicert_org_id)
            if dc_resp and 'id' in dc_resp:
                print(f"[DigiCert] Verifying details for ID {dc_resp['id']}...")
                details = get_digicert_domain_details(dc_resp['id'], digicert_api_key)
                if details:
                    print(json.dumps(details, indent=2))
                else:
                    print("[DigiCert] Could not retrieve details.")
        else:
            print("Missing DigiCert credentials/org ID in ~/.ApiVault")

        if sectigo_login and sectigo_password and sectigo_customer_uri and sectigo_org_id:
            sec_resp = add_to_sectigo(target_domain, sectigo_login, sectigo_password, sectigo_customer_uri, sectigo_org_id)
            if sec_resp and 'id' in sec_resp:
                print(f"[Sectigo] Verifying details for ID {sec_resp['id']}...")
                details = get_sectigo_domain_details(sec_resp['id'], sectigo_login, sectigo_password, sectigo_customer_uri)
                if details:
                    print(json.dumps(details, indent=2))
                else:
                    print("[Sectigo] Could not retrieve details.")
        else:
            print("Missing Sectigo credentials in ~/.ApiVault")

    # --- Remove mode ---
    elif mode == "remove":
        # Sectigo
        row = find_domain_in_csv(target_domain, "sectigo")
        if row:
            sectigo_id = row[1]
            if remove_from_sectigo_by_id(sectigo_id, sectigo_login, sectigo_password, sectigo_customer_uri, target_domain):
                verify_sectigo_removal(target_domain, sectigo_login, sectigo_password, sectigo_customer_uri)
        else:
            print(f"[Sectigo] Could not find domain '{target_domain}' in CSV for Sectigo (will not attempt removal).")
        # DigiCert
        row = find_domain_in_csv(target_domain, "digicert")
        if row:
            digicert_id = row[1]
            if remove_from_digicert_by_id(digicert_id, digicert_api_key, target_domain):
                verify_digicert_removal(target_domain, digicert_api_key)
        else:
            print(f"[DigiCert] Could not find domain '{target_domain}' in CSV for DigiCert (will not attempt removal).")

    print("\nDone.")
    print(f"\nAll activity logged in {LOG_FILE}")

if __name__ == "__main__":
    main()