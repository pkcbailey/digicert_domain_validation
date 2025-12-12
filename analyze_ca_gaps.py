#!/usr/bin/env python3
import csv
import sys
from collections import defaultdict

def analyze_gaps(csv_path):
    """
    Analyzes domain gaps between CAs from a CSV file.
    Schema: id,domain,CA
    """
    domains_by_ca = defaultdict(set)
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Strip whitespace to be safe
                domain = row['domain'].strip()
                ca = row['CA'].strip()
                if domain and ca:
                    domains_by_ca[ca].add(domain)
    except FileNotFoundError:
        print(f"Error: File not found at {csv_path}")
        return
    except KeyError as e:
        print(f"Error: Missing column in CSV: {e}")
        return

    ca_list = sorted(domains_by_ca.keys())
    print(f"Found CAs: {', '.join(ca_list)}")
    print("-" * 40)

    if len(ca_list) < 2:
        print("Not enough CAs found to compare.")
        return

    # Compare every CA against every other CA
    for i in range(len(ca_list)):
        for j in range(len(ca_list)):
            if i == j:
                continue
            
            ca_a = ca_list[i]
            ca_b = ca_list[j]
            
            domains_a = domains_by_ca[ca_a]
            domains_b = domains_by_ca[ca_b]
            
            # Domains in A but not in B
            diff = domains_a - domains_b
            
            if diff:
                print(f"\nDomains in '{ca_a}' but NOT in '{ca_b}' ({len(diff)}):")
                for domain in sorted(diff):
                    print(f"  - {domain}")
            else:
                print(f"\nAll domains in '{ca_a}' are also present in '{ca_b}'.")

if __name__ == "__main__":
    analyze_gaps("data/domain_id_lookup.csv")
