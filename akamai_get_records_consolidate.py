#!/usr/bin/env python3
import csv
import json
import keyring
import requests
from datetime import datetime
import os
import argparse
from typing import List, Dict

class AkamaiDNSChecker:
    def __init__(self, record_type: str):
        self.api_key = self._get_api_key()
        self.client_token = self._get_client_token()
        self.client_secret = self._get_client_secret()
        self.access_token = self._get_access_token()
        self.base_url = "https://api.akamai.com/api/dns/v2"
        self.record_type = record_type.upper()
        self.output_file = f"akamai_{self.record_type.lower()}_records_{datetime.now().strftime('%Y%m%d')}.csv"

    def _get_api_key(self) -> str:
        """Get API key from keyring"""
        key = keyring.get_password("akamai", "api_key")
        if not key:
            key = input("Enter Akamai API Key: ")
            keyring.set_password("akamai", "api_key", key)
        return key

    def _get_client_token(self) -> str:
        """Get client token from keyring"""
        token = keyring.get_password("akamai", "client_token")
        if not token:
            token = input("Enter Akamai Client Token: ")
            keyring.set_password("akamai", "client_token", token)
        return token

    def _get_client_secret(self) -> str:
        """Get client secret from keyring"""
        secret = keyring.get_password("akamai", "client_secret")
        if not secret:
            secret = input("Enter Akamai Client Secret: ")
            keyring.set_password("akamai", "client_secret", secret)
        return secret

    def _get_access_token(self) -> str:
        """Get access token using client credentials"""
        url = "https://api.akamai.com/oauth/token"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_token,
            "client_secret": self.client_secret
        }
        
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        return response.json()["access_token"]

    def get_zone_records(self, domain: str) -> List[Dict]:
        """Get all records of specified type for a domain with pagination"""
        all_records = []
        page = 1
        page_size = 100  # Maximum records per page
        
        while True:
            url = f"{self.base_url}/zones/{domain}/records"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json"
            }
            params = {
                "page": page,
                "pageSize": page_size
            }
            
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            records = data.get("records", [])
            if not records:
                break
                
            # Filter for specified record type
            filtered_records = [record for record in records if record["recordType"] == self.record_type]
            all_records.extend(filtered_records)
            
            # Check if we've reached the last page
            if len(records) < page_size:
                break
                
            page += 1
            
        return all_records

    def process_domains(self, input_file: str) -> None:
        """Process domains from input file and write results to CSV"""
        # Read domains from input file
        domains = []
        with open(input_file, 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                if row:  # Skip empty lines
                    domains.append(row[0].strip())

        # Prepare output file
        with open(self.output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Domain', 'Record Name', 'Record Type', 'Target', 'TTL'])

            # Process each domain
            for domain in domains:
                try:
                    print(f"Processing domain: {domain}")
                    records = self.get_zone_records(domain)
                    
                    if not records:
                        print(f"No {self.record_type} records found for {domain}")
                        writer.writerow([domain, f'No {self.record_type} records found', '', '', ''])
                        continue

                    for record in records:
                        writer.writerow([
                            domain,
                            record.get('name', ''),
                            record.get('recordType', ''),
                            record.get('target', ''),
                            record.get('ttl', '')
                        ])

                except Exception as e:
                    print(f"Error processing {domain}: {str(e)}")
                    writer.writerow([domain, 'Error processing domain', '', '', str(e)])

        print(f"\nResults saved to {self.output_file}")

def main():
    # Set up command line argument parser
    parser = argparse.ArgumentParser(description='Fetch DNS records from Akamai')
    parser.add_argument('--type', '-t', choices=['A', 'CNAME', 'TXT', 'MX'], 
                      required=True, help='Type of DNS record to fetch')
    parser.add_argument('--input', '-i', default='dns_domains.csv',
                      help='Input CSV file with domains (default: dns_domains.csv)')
    
    args = parser.parse_args()
    
    checker = AkamaiDNSChecker(args.type)
    checker.process_domains(args.input)

if __name__ == "__main__":
    main()