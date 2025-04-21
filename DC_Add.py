#!/usr/bin/env python3
"""
DC_Add - DigiCert Domain Addition Tool

This script adds domains to DigiCert using the CertCentral API with DNS TXT token validation.
It retrieves credentials from the system keychain and can process domains from command line
or a text file. Results are saved in a format suitable for consumption by other scripts.
"""

import argparse
import json
import sys
from typing import List, Dict
import requests
import keyring
from tqdm import tqdm
import os
from datetime import datetime

class DigiCertDomainAdder:
    """Handles domain addition to DigiCert with TXT token validation"""
    
    def __init__(self):
        self.base_url = "https://www.digicert.com/services/v2"
        self.api_key = self._get_api_key()
        self.org_id = self._get_org_id()
        self.headers = {
            'X-DC-DEVKEY': self.api_key,
            'Content-Type': 'application/json'
        }
        
    def _get_api_key(self) -> str:
        """Get DigiCert API key from keyring"""
        service_name = "digicert_api"
        key = keyring.get_password(service_name, "api_key")
        if not key:
            raise ValueError("DigiCert API key not found in keychain. Please run domain_validator.py first.")
        return key
        
    def _get_org_id(self) -> str:
        """Get organization ID from keyring"""
        service_name = "digicert_api"
        org_id = keyring.get_password(service_name, "org_id")
        if not org_id:
            raise ValueError("Organization ID not found in keychain. Please run domain_validator.py first.")
        return org_id
        
    def add_domain(self, domain: str) -> Dict:
        """Add a single domain to DigiCert with TXT token validation"""
        try:
            # Prepare the request payload
            payload = {
                "name": domain,
                "organization": {
                    "id": int(self.org_id)
                },
                "validations": [
                    {
                        "type": "dns-txt-token"
                    }
                ],
                "dcv_method": "dns-txt-token"
            }
            
            # Make the API request
            response = requests.post(
                f"{self.base_url}/domain",
                headers=self.headers,
                json=payload
            )
            
            if response.status_code == 201:
                data = response.json()
                return {
                    'domain': domain,
                    'id': data.get('id'),
                    'token': data.get('dcv_token', {}).get('token'),
                    'status': 'success',
                    'error': None
                }
            else:
                return {
                    'domain': domain,
                    'id': None,
                    'token': None,
                    'status': 'error',
                    'error': f"API error: {response.status_code} - {response.text}"
                }
                
        except Exception as e:
            return {
                'domain': domain,
                'id': None,
                'token': None,
                'status': 'error',
                'error': str(e)
            }
            
    def process_domains(self, domains: List[str]) -> List[Dict]:
        """Process a list of domains and return results"""
        results = []
        for domain in tqdm(domains, desc="Adding domains"):
            result = self.add_domain(domain.strip())
            results.append(result)
        return results
        
    def save_results(self, results: List[Dict], output_file: str = None) -> str:
        """Save results to a JSON file"""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"digicert_domain_add_{timestamp}.json"
            
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
            
        return output_file

def main():
    parser = argparse.ArgumentParser(description='Add domains to DigiCert with TXT token validation')
    parser.add_argument('--domain', help='Single domain to add')
    parser.add_argument('--file', help='File containing list of domains (one per line)')
    parser.add_argument('--output', help='Output JSON file path (optional)')
    
    args = parser.parse_args()
    
    if not args.domain and not args.file:
        parser.error("Either --domain or --file must be specified")
        
    try:
        adder = DigiCertDomainAdder()
        
        # Get domains to process
        if args.domain:
            domains = [args.domain]
        else:
            with open(args.file, 'r') as f:
                domains = f.readlines()
                
        # Process domains
        results = adder.process_domains(domains)
        
        # Save results
        output_file = adder.save_results(results, args.output)
        
        # Print summary
        success_count = sum(1 for r in results if r['status'] == 'success')
        error_count = len(results) - success_count
        
        print(f"\nProcessing complete:")
        print(f"Total domains processed: {len(results)}")
        print(f"Successfully added: {success_count}")
        print(f"Failed: {error_count}")
        print(f"\nResults saved to: {output_file}")
        
        if error_count > 0:
            print("\nFailed domains:")
            for result in results:
                if result['status'] == 'error':
                    print(f"- {result['domain']}: {result['error']}")
                    
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 