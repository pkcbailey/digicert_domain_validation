#!/usr/bin/env python3
"""
Domain Validator

This script validates domain names and their DNS records, checking for common
configuration issues and potential problems. It associates domains with a specific
organization ID for proper categorization using DigiCert's CertCentral API.
"""

import argparse
import dns.resolver
import pandas as pd
from typing import List, Dict, Optional
import socket
import re
from tqdm import tqdm
import sys
import requests
import json
from datetime import datetime
import keyring

class DomainValidator:
    """Main class for domain validation operations"""
    
    def __init__(self, org_id: str = None):
        self.org_id = org_id or self._get_org_id()
        self.digicert_api_key = self._get_digicert_api_key()
        self.digicert_base_url = "https://www.digicert.com/services/v2"
        self.results = []
        
    def _get_org_id(self) -> str:
        """Get organization ID from keyring or prompt for it"""
        service_name = "digicert_api"
        org_id = keyring.get_password(service_name, "org_id")
        
        if not org_id:
            org_id = input("Please enter your DigiCert Organization ID: ").strip()
            if org_id:
                keyring.set_password(service_name, "org_id", org_id)
            else:
                raise ValueError("DigiCert Organization ID is required")
                
        return org_id
        
    def _get_digicert_api_key(self) -> str:
        """Get DigiCert API key from keyring or prompt for it"""
        service_name = "digicert_api"
        key = keyring.get_password(service_name, "api_key")
        
        if not key:
            key = input("Please enter your DigiCert API key: ").strip()
            if key:
                keyring.set_password(service_name, "api_key", key)
            else:
                raise ValueError("DigiCert API key is required")
                
        return key
        
    def validate_domain_format(self, domain: str) -> bool:
        """Validate domain name format"""
        if not domain:
            return False
            
        # Domain name regex pattern
        pattern = r'^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
        return bool(re.match(pattern, domain))
        
    def check_digicert_domain(self, domain: str) -> Dict:
        """Check domain status in DigiCert"""
        headers = {
            'X-DC-DEVKEY': self.digicert_api_key,
            'Content-Type': 'application/json'
        }
        
        try:
            # Check if domain exists in DigiCert
            response = requests.get(
                f"{self.digicert_base_url}/domain/{domain}",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'exists': True,
                    'status': data.get('status', 'unknown'),
                    'validation_method': data.get('validation_method', 'unknown'),
                    'org_id': data.get('organization', {}).get('id'),
                    'is_org_match': str(data.get('organization', {}).get('id')) == str(self.org_id)
                }
            elif response.status_code == 404:
                # Domain not found, let's add it to the organization with TXT validation
                add_response = requests.post(
                    f"{self.digicert_base_url}/domain",
                    headers=headers,
                    json={
                        "name": domain,
                        "organization": {
                            "id": int(self.org_id)
                        },
                        "validation": {
                            "method": "dns_txt"
                        }
                    }
                )
                
                if add_response.status_code == 201:
                    add_data = add_response.json()
                    validation_record = add_data.get('validation', {}).get('txt_record')
                    return {
                        'exists': True,
                        'status': 'pending',
                        'validation_method': 'dns_txt',
                        'org_id': self.org_id,
                        'is_org_match': True,
                        'message': 'Domain added to organization',
                        'validation_record': validation_record,
                        'validation_instructions': f"Add the following TXT record to your domain's DNS:\nHost: _digicert-validation\nValue: {validation_record}"
                    }
                else:
                    return {
                        'exists': False,
                        'status': 'error',
                        'validation_method': 'none',
                        'org_id': None,
                        'is_org_match': False,
                        'error': f"Failed to add domain: {add_response.status_code}"
                    }
            else:
                return {
                    'exists': False,
                    'status': 'error',
                    'validation_method': 'none',
                    'org_id': None,
                    'is_org_match': False,
                    'error': f"API error: {response.status_code}"
                }
                
        except Exception as e:
            return {
                'exists': False,
                'status': 'error',
                'validation_method': 'none',
                'org_id': None,
                'is_org_match': False,
                'error': str(e)
            }
            
    def check_dns_records(self, domain: str) -> Dict:
        """Check various DNS records for the domain"""
        record_types = ['A', 'AAAA', 'MX', 'TXT', 'CNAME', 'NS']
        results = {
            'domain': domain,
            'org_id': self.org_id,
            'format_valid': self.validate_domain_format(domain),
            'records': {},
            'issues': []
        }
        
        if not results['format_valid']:
            results['issues'].append('Invalid domain format')
            return results
            
        # Check DigiCert domain status
        digicert_status = self.check_digicert_domain(domain)
        results['digicert_status'] = digicert_status
        
        if not digicert_status['exists']:
            results['issues'].append('Domain not found in DigiCert')
        elif not digicert_status['is_org_match']:
            results['issues'].append(f"Domain belongs to different organization (ID: {digicert_status['org_id']})")
            
        for record_type in record_types:
            try:
                answers = dns.resolver.resolve(domain, record_type)
                results['records'][record_type] = [str(rdata) for rdata in answers]
            except dns.resolver.NoAnswer:
                results['records'][record_type] = []
            except dns.resolver.NXDOMAIN:
                results['issues'].append(f'Domain does not exist (NXDOMAIN)')
                break
            except Exception as e:
                results['issues'].append(f'Error checking {record_type} records: {str(e)}')
                
        # Additional checks
        if not results['issues']:
            if not results['records'].get('A') and not results['records'].get('AAAA'):
                results['issues'].append('No A or AAAA records found')
            if not results['records'].get('MX'):
                results['issues'].append('No MX records found')
            if not results['records'].get('NS'):
                results['issues'].append('No NS records found')
                
        return results
        
    def validate_domains(self, domains: List[str]) -> None:
        """Validate a list of domains"""
        for domain in tqdm(domains, desc="Validating domains"):
            result = self.check_dns_records(domain.strip())
            self.results.append(result)
            
    def generate_report(self, output_file: str) -> None:
        """Generate Excel report from validation results"""
        if not self.results:
            print("No validation results to report")
            return
            
        # Prepare data for DataFrame
        report_data = []
        for result in self.results:
            row = {
                'Organization ID': result['org_id'],
                'Domain': result['domain'],
                'Format Valid': 'Yes' if result['format_valid'] else 'No',
                'DigiCert Status': result['digicert_status']['status'],
                'DigiCert Org Match': 'Yes' if result['digicert_status']['is_org_match'] else 'No',
                'Validation Method': result['digicert_status']['validation_method'],
                'Validation Record': result['digicert_status'].get('validation_record', 'N/A'),
                'Issues': '; '.join(result['issues']) if result['issues'] else 'None'
            }
            
            # Add record counts
            for record_type in ['A', 'AAAA', 'MX', 'TXT', 'CNAME', 'NS']:
                row[f'{record_type} Records'] = len(result['records'].get(record_type, []))
                
            report_data.append(row)
            
        # Create DataFrame
        df = pd.DataFrame(report_data)
        
        # Reorder columns
        columns = [
            'Organization ID',
            'Domain',
            'Format Valid',
            'DigiCert Status',
            'DigiCert Org Match',
            'Validation Method',
            'Validation Record',
            'A Records',
            'AAAA Records',
            'MX Records',
            'TXT Records',
            'CNAME Records',
            'NS Records',
            'Issues'
        ]
        df = df[columns]
        
        # Save to Excel
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Validation Report')
            
            # Auto-adjust column widths
            worksheet = writer.sheets['Validation Report']
            for idx, col in enumerate(df.columns):
                max_length = max(
                    df[col].astype(str).apply(len).max(),
                    len(str(col))
                )
                worksheet.column_dimensions[chr(65 + idx)].width = max_length + 2
                
        print(f"\nReport saved to: {output_file}")
        
        # Print validation instructions for any domains that need validation
        for result in self.results:
            if result['digicert_status'].get('validation_instructions'):
                print(f"\nValidation required for {result['domain']}:")
                print(result['digicert_status']['validation_instructions'])
        
def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Domain Validator')
    parser.add_argument('--domain', help='Single domain to validate')
    parser.add_argument('--file', help='File containing list of domains (one per line)')
    parser.add_argument('--output', default='validation_report.xlsx', 
                       help='Output Excel file path')
    parser.add_argument('--org-id', help='Organization ID for domain categorization (optional if stored in keychain)')
    parser.add_argument('--verbose', action='store_true', 
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    if not args.domain and not args.file:
        parser.error("Either --domain or --file must be specified")
        
    validator = DomainValidator(args.org_id)
    
    if args.domain:
        domains = [args.domain]
    else:
        try:
            with open(args.file, 'r') as f:
                domains = f.readlines()
        except Exception as e:
            print(f"Error reading domain file: {str(e)}")
            sys.exit(1)
            
    validator.validate_domains(domains)
    validator.generate_report(args.output)
    
if __name__ == "__main__":
    main() 