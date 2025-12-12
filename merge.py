#!/usr/bin/env python3
import csv
import json
import os
import subprocess
import sys

def load_config():
    """Load the DNS resolver configuration from ~/.ApiVault."""
    vault_path = os.path.expanduser("~/.ApiVault")
    try:
        with open(vault_path, 'r') as f:
            data = json.load(f)
            return data.get("DNSResolver", {}).get("dns_resolver")
    except Exception as e:
        print(f"Error loading {vault_path}: {e}")
        return None

def get_ns_owner(domain, resolver_ip):
    """
    Perform a dig NS lookup and identify the provider.
    Returns: Akamai, Azure, AWS, or Other.
    """
    if not domain:
        return "Other"

    cmd = ["dig", f"@{resolver_ip}", "NS", domain, "+short"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        output = result.stdout.lower()
        
        if "akam" in output:
            return "Akamai"
        elif "azure" in output:
            return "Azure"
        elif "aws" in output:
            return "AWS"
        else:
            return "Other"
    except subprocess.TimeoutExpired:
        print(f"Timeout querying DNS for {domain}")
        return "Other"
    except Exception as e:
        print(f"Error querying DNS for {domain}: {e}")
        return "Other"

def process_files():
    resolver_ip = load_config()
    if not resolver_ip:
        print("Could not find 'dns_resolver' in ~/.ApiVault. Exiting.")
        sys.exit(1)
        
    print(f"Using DNS Resolver: {resolver_ip}")

    input_files = [
        {"path": "data/digicert_domains.csv", "provider": "Digicert"},
        {"path": "data/sectigo_domains.csv", "provider": "Sectigo"}
    ]
    
    combined_data = []
    fieldnames = []

    # Read and Combine
    for file_info in input_files:
        path = file_info["path"]
        provider = file_info["provider"]
        
        if not os.path.exists(path):
            print(f"Warning: {path} not found. Skipping.")
            continue

        print(f"Processing {path}...")
        with open(path, 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            if not fieldnames:
                fieldnames = reader.fieldnames
                # Ensure we have the base fieldnames. 
                # If the first file is empty or has different headers, this might need adjustment,
                # but we verified headers match.
            
            for row in reader:
                row['provider'] = provider
                # Strip unexpected whitespace from domain just in case
                domain = row.get('name', '').strip()
                owner = get_ns_owner(domain, resolver_ip)
                row['ns_provider'] = owner
                combined_data.append(row)

    if not combined_data:
        print("No data found to combine.")
        return

    # Prepare output
    output_headers = ['provider'] + fieldnames + ['ns_provider']
    output_path = "data/combined_domains.csv"
    
    print(f"Writing results to {output_path}...")
    with open(output_path, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=output_headers)
        writer.writeheader()
        writer.writerows(combined_data)

    print("Done.")

if __name__ == "__main__":
    process_files()
