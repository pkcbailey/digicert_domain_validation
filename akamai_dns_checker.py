#!/usr/bin/env python3
import csv
import json
import keyring
import requests
from datetime import datetime
import os
from typing import List, Dict

class AkamaiDNSChecker:
    def __init__(self):
        self.api_key = self._get_api_key()
        self.client_token = self._get_client_token()
        self.client_secret = self._get_client_secret()
        self.access_token = self._get_access_token()
        self.base_url = "https://api.akamai.com/api/dns/v2"
        self.output_file = f"akamai_a_records_{datetime.now().strftime('%Y%m%d')}.csv"

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
        """Get all A records for a domain"""
        url = f"{self.base_url}/zones/{domain}/records"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json"
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        records = response.json()["records"]
        
        # Filter for A records
        return [record for record in records if record["recordType"] == "A"]

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
                        print(f"No A records found for {domain}")
                        writer.writerow([domain, 'No A records found', '', '', ''])
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
    checker = AkamaiDNSChecker()
    checker.process_domains("dns_domains.csv")

if __name__ == "__main__":
    main() 