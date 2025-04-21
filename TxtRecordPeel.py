#!/usr/bin/env python3
"""
TxtRecordPeel - Process DigiCert output files and create CSV with NS records

This script:
1. Reads today's files from digicert_output/
2. Queries NS records for each domain
3. Categorizes the NS provider
4. Creates separate CSVs for Akamai and non-Akamai domains
5. Emails the non-Akamai domains report
"""

import json
import os
import csv
import subprocess
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, List, Optional
import keyring

def get_email_credentials() -> tuple:
    """Get email address from keyring"""
    service = "email"
    email = keyring.get_password(service, "email")
    
    if not email:
        print("Error: Missing email address in keyring")
        print("Please store the following in keyring:")
        print("1. Service: email")
        print("2. Username: email (your email address)")
        raise ValueError("Missing email address")
    
    return email

def send_email(subject: str, body: str, to_email: str):
    """Send email using sendmail"""
    try:
        from_email = keyring.get_password("email", "email")
        
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Use sendmail without authentication
        server = smtplib.SMTP('localhost')
        server.send_message(msg)
        server.quit()
        
        print(f"Email sent successfully to {to_email}")
    except Exception as e:
        print(f"Error sending email: {str(e)}")

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

def save_to_csv(results: List[Dict], provider: str) -> str:
    """Save results to a CSV file for specific provider"""
    today = datetime.now().strftime("%Y%m%d")
    csv_filename = f"ns_records_{provider.lower()}_{today}.csv"
    
    with open(csv_filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'domain', 'id', 'status', 'error', 'txt_record', 
            'ns_record', 'ns_provider'
        ])
        writer.writeheader()
        writer.writerows(results)
    
    return csv_filename

def create_email_body(results: List[Dict]) -> str:
    """Create email body from non-Akamai results"""
    body = "Non-Akamai Domains Report\n\n"
    body += "Domain,ID,Status,NS Provider,TXT Record\n"
    body += "-" * 80 + "\n"
    
    for result in results:
        body += f"{result['domain']},{result['id']},{result['status']},"
        body += f"{result['ns_provider']},{result['txt_record']}\n"
    
    return body

def main():
    print("Processing DigiCert output files...")
    results = process_digicert_files()
    
    if results:
        # Split results into Akamai and non-Akamai
        akamai_results = [r for r in results if r['ns_provider'] == 'Akamai']
        non_akamai_results = [r for r in results if r['ns_provider'] != 'Akamai']
        
        # Save Akamai results
        if akamai_results:
            akamai_file = save_to_csv(akamai_results, "akamai")
            print(f"\nAkamai results saved to: {akamai_file}")
        
        # Save and email non-Akamai results
        if non_akamai_results:
            non_akamai_file = save_to_csv(non_akamai_results, "non_akamai")
            print(f"\nNon-Akamai results saved to: {non_akamai_file}")
            
            # Create and send email
            email_body = create_email_body(non_akamai_results)
            try:
                from_email = get_email_credentials()
                send_email(
                    "Non-Akamai Domains Report",
                    email_body,
                    from_email  # Sending to self for now
                )
            except Exception as e:
                print(f"Error sending email: {str(e)}")
        
        print(f"\nProcessed {len(results)} domains total")
        print(f"- Akamai domains: {len(akamai_results)}")
        print(f"- Non-Akamai domains: {len(non_akamai_results)}")
    else:
        print("No DigiCert output files found for today")

if __name__ == "__main__":
    main() 