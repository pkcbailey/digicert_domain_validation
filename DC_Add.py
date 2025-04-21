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
        service_name = "digicert"
        username = "digicert_api"
        try:
            print("Checking keyring for DigiCert API key...")
            key = keyring.get_password(service_name, username)
            
            if not key:
                print(f"Error: No API key found in keyring for service '{service_name}' and username '{username}'")
                print("Please store your DigiCert API key in the keyring:")
                print("1. Open Keychain Access")
                print("2. Create a new password item")
                print("3. Set Keychain Item Name to 'digicert'")
                print("4. Set Account Name to 'digicert_api'")
                print("5. Enter your API key as the password")
                raise ValueError("DigiCert API key not found in keychain")
                
            return key
            
        except Exception as e:
            print(f"Error accessing keyring: {str(e)}")
            print("Please ensure keyring is properly installed and configured.")
            raise
        
    def _get_org_id(self) -> str:
        """Get organization ID from keyring"""
        service_name = "digicert"
        username = "OrgID"
        org_id = keyring.get_password(service_name, username)
        if not org_id:
            print(f"Error: No Organization ID found in keyring for service '{service_name}' and username '{username}'")
            print("Please store your Organization ID in the keyring:")
            print("1. Open Keychain Access")
            print("2. Create a new password item")
            print("3. Set Keychain Item Name to 'digicert'")
            print("4. Set Account Name to 'OrgID'")
            print("5. Enter your Organization ID as the password")
            raise ValueError("Organization ID not found in keychain")
        return org_id
        
    def add_domain(self, domain: str) -> Dict:
        """Add a single domain to DigiCert"""
        try:
            # Get organization ID from keychain
            org_id = self._get_org_id()
            
            # Prepare the request payload
            payload = {
                "name": domain,
                "organization": {
                    "id": int(org_id)
                },
                "validations": [
                    {
                        "type": "ov"
                    },
                    {
                        "type": "ev"
                    }
                ],
                "dcv_method": "dns-txt-token"
            }
            
            # Make the API request
            print("\n=== DigiCert API Call ===")
            print(f"URL: {self.base_url}/domain")
            print(f"Method: POST")
            print(f"Headers: {json.dumps(self.headers, indent=2)}")
            print(f"Payload: {json.dumps(payload, indent=2)}")
            
            response = requests.post(
                f"{self.base_url}/domain",
                headers=self.headers,
                json=payload
            )
            
            print("\n=== API Response ===")
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {json.dumps(dict(response.headers), indent=2)}")
            
            response_data = None
            try:
                response_data = response.json()
                print(f"Response Body: {json.dumps(response_data, indent=2)}")
            except:
                print(f"Response Body: {response.text}")
            
            if response.status_code == 201:
                # Extract TXT record information from dcv_token
                txt_record = None
                if response_data and 'dcv_token' in response_data:
                    token = response_data['dcv_token'].get('token')
                    if token:
                        txt_record = token
                        print("\n=== TXT Record Information ===")
                        print(f"TXT Record: digicert-validation={txt_record}")
                        print(f"Add this TXT record to your DNS for domain: {domain}")
                
                return {
                    'domain': domain,
                    'id': response_data.get('id'),
                    'status': 'success',
                    'error': None,
                    'txt_record': txt_record
                }
            else:
                error_msg = f"API error: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f" - {json.dumps(error_data)}"
                except:
                    error_msg += f" - {response.text}"
                return {
                    'domain': domain,
                    'id': None,
                    'status': 'error',
                    'error': error_msg,
                    'txt_record': None
                }
                
        except Exception as e:
            return {
                'domain': domain,
                'id': None,
                'status': 'error',
                'error': str(e),
                'txt_record': None
            }
            
    def process_domains(self, domains: List[str]) -> List[Dict]:
        """Process a list of domains and return results"""
        results = []
        for domain in tqdm(domains, desc="Adding domains"):
            result = self.add_domain(domain.strip())
            results.append(result)
        return results
        
    def save_results(self, results: List[Dict], output_file: str = None) -> str:
        """Save results to a JSON file in the digicert_output directory"""
        # Create output directory if it doesn't exist
        output_dir = "digicert_output"
        os.makedirs(output_dir, exist_ok=True)
        
        # Save each domain's result to its own file
        saved_files = []
        for result in results:
            domain = result.get('domain', 'unknown')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{domain}_{timestamp}.json"
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump([result], f, indent=2)
            
            saved_files.append(filepath)
            print(f"Results for {domain} saved to: {filepath}")
            
        return saved_files

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
        output_files = adder.save_results(results, args.output)
        
        # Print summary
        success_count = sum(1 for r in results if r['status'] == 'success')
        error_count = len(results) - success_count
        
        print(f"\nProcessing complete:")
        print(f"Total domains processed: {len(results)}")
        print(f"Successfully added: {success_count}")
        print(f"Failed: {error_count}")
        print(f"\nResults saved to: {output_files}")
        
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