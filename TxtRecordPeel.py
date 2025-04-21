#!/usr/bin/env python3
"""
TxtRecordPeel - Process DigiCert output files and create CSV with NS records

This script:
1. Reads today's files from digicert_output/
2. Queries NS records for each domain
3. Categorizes the NS provider
4. Creates a CSV with the combined data
"""

import json
import os
import csv
import subprocess
from datetime import datetime
from typing import Dict, List, Optional

def get_ns_provider(ns_record: str) -> str:
    """Determine the NS provider based on the record content"""
    ns_lower = ns_record.lower()
    if 'akam' in ns_lower:
        return 'Akamai'
    elif 'azure' in ns_lower:
        return 'Azure'
    elif 'csc' in ns_lower:
        return 'CSC'
    else:
        return 'Other'

def query_ns_record(domain: str) -> Optional[str]:
    """Query NS record for a domain using dig"""
    try:
        result = subprocess.run(
            ['dig', '@10.20.20.151', domain, 'NS'],
            capture_output=True,
            text=True,
            check=True
        )
        # Extract NS records from dig output
        ns_records = []
        for line in result.stdout.split('\n'):
            if 'IN\tNS\t' in line:
                ns_record = line.split('IN\tNS\t')[-1].strip()
                ns_records.append(ns_record)
        return ns_records[0] if ns_records else None
    except subprocess.CalledProcessError:
        return None

def process_digicert_files() -> List[Dict]:
    """Process today's DigiCert output files"""
    today = datetime.now().strftime("%Y%m%d")
    output_dir = "digicert_output"
    results = []
    
    # Get all files from today
    try:
        files = os.listdir(output_dir)
        print(f"Found {len(files)} files in {output_dir}")
        print(f"Looking for files containing: {today}")
        print("Files found:")
        for f in files:
            print(f"- {f}")
        
        for filename in files:
            if today in filename:
                filepath = os.path.join(output_dir, filename)
                print(f"Processing file: {filepath}")
                
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        if data and isinstance(data, list) and len(data) > 0:
                            domain_data = data[0]
                            domain = domain_data.get('domain')
                            
                            if domain:
                                print(f"Processing domain: {domain}")
                                # Query NS record
                                ns_record = query_ns_record(domain)
                                ns_provider = get_ns_provider(ns_record) if ns_record else 'Unknown'
                                
                                # Add to results
                                results.append({
                                    'domain': domain,
                                    'id': domain_data.get('id'),
                                    'status': domain_data.get('status'),
                                    'error': domain_data.get('error'),
                                    'txt_record': domain_data.get('txt_record'),
                                    'ns_record': ns_record,
                                    'ns_provider': ns_provider
                                })
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON in {filename}: {str(e)}")
                except PermissionError as e:
                    print(f"Permission error reading {filename}: {str(e)}")
                except Exception as e:
                    print(f"Error processing {filename}: {str(e)}")
    except Exception as e:
        print(f"Error accessing directory {output_dir}: {str(e)}")
    
    return results

def save_to_csv(results: List[Dict]) -> str:
    """Save results to a CSV file"""
    today = datetime.now().strftime("%Y%m%d")
    csv_filename = f"ns_records_{today}.csv"
    
    with open(csv_filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'domain', 'id', 'status', 'error', 'txt_record', 
            'ns_record', 'ns_provider'
        ])
        writer.writeheader()
        writer.writerows(results)
    
    return csv_filename

def main():
    # Ensure digicert_output directory exists
    output_dir = "digicert_output"
    if not os.path.exists(output_dir):
        print(f"Creating directory: {output_dir}")
        os.makedirs(output_dir)
        print("No files found in digicert_output directory")
        return
    
    print("Processing DigiCert output files...")
    results = process_digicert_files()
    
    if results:
        csv_file = save_to_csv(results)
        print(f"\nResults saved to: {csv_file}")
        print(f"\nProcessed {len(results)} domains")
    else:
        print("No DigiCert output files found for today")

if __name__ == "__main__":
    main() 