#!/usr/bin/env python3
"""
Domain Validator Script

This script helps validate domains by:
1. Adding domains to Digicert for validation
2. Retrieving required TXT records
3. Checking for Akamai hosting
4. Managing DNS records accordingly
"""

import os
import sys
import json
import smtplib
import dns.resolver
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Tuple
import tkinter as tk
from tkinter import messagebox
import keyring
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Handles configuration and API key management"""
    
    def __init__(self):
        self.digicert_api_key = self._get_api_key('digicert')
        self.akamai_api_key = self._get_api_key('akamai')
        self.akamai_api_secret = self._get_api_key('akamai_secret')
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.example.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.admin_email = os.getenv('ADMIN_EMAIL', 'domainadmin@example.com')
        
    def _get_api_key(self, service: str) -> str:
        """Retrieve API key from keyring or environment variable"""
        key = keyring.get_password('domain_validator', service)
        if not key:
            key = os.getenv(f'{service.upper()}_API_KEY')
            if key:
                keyring.set_password('domain_validator', service, key)
        return key

class DomainValidator:
    """Main class for domain validation operations"""
    
    def __init__(self, config: Config):
        self.config = config
        self.digicert_base_url = "https://www.digicert.com/services/v2"
        self.akamai_base_url = "https://api.akamai.com/api/v1"
        
    def add_domain_to_digicert(self, domain: str) -> Tuple[bool, str]:
        """Add domain to Digicert for validation"""
        headers = {
            'X-DC-DEVKEY': self.config.digicert_api_key,
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.post(
                f"{self.digicert_base_url}/domain/validate",
                headers=headers,
                json={"domain": domain}
            )
            response.raise_for_status()
            data = response.json()
            return True, data.get('txt_record', '')
        except requests.exceptions.RequestException as e:
            return False, str(e)
            
    def check_akamai_hosting(self, domain: str) -> bool:
        """Check if domain is hosted on Akamai"""
        try:
            ns_records = dns.resolver.resolve(domain, 'NS')
            return any('akam' in str(record).lower() for record in ns_records)
        except dns.resolver.NXDOMAIN:
            return False
        except Exception:
            return False
            
    def add_txt_record_akamai(self, domain: str, txt_record: str) -> bool:
        """Add TXT record using Akamai API"""
        headers = {
            'Authorization': f'Bearer {self.config.akamai_api_key}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.post(
                f"{self.akamai_base_url}/dns/records",
                headers=headers,
                json={
                    "domain": domain,
                    "type": "TXT",
                    "value": txt_record
                }
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException:
            return False
            
    def send_admin_email(self, domain: str, txt_record: str) -> bool:
        """Send email to admin with domain and TXT record"""
        msg = MIMEMultipart()
        msg['From'] = self.config.admin_email
        msg['To'] = self.config.admin_email
        msg['Subject'] = f"Domain Validation Required: {domain}"
        
        body = f"""
        Domain: {domain}
        TXT Record: {txt_record}
        
        Please add this TXT record to your DNS configuration.
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        try:
            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                server.send_message(msg)
            return True
        except Exception:
            return False

class DomainValidatorGUI:
    """Simple GUI for domain validation"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Domain Validator")
        self.config = Config()
        self.validator = DomainValidator(self.config)
        
        self.setup_gui()
        
    def setup_gui(self):
        """Setup the GUI components"""
        # Domain input
        tk.Label(self.root, text="Enter Domain:").pack(pady=5)
        self.domain_entry = tk.Entry(self.root, width=40)
        self.domain_entry.pack(pady=5)
        
        # Validate button
        tk.Button(
            self.root,
            text="Validate Domain",
            command=self.validate_domain
        ).pack(pady=10)
        
        # Status label
        self.status_label = tk.Label(self.root, text="")
        self.status_label.pack(pady=5)
        
    def validate_domain(self):
        """Handle domain validation process"""
        domain = self.domain_entry.get().strip()
        if not domain:
            messagebox.showerror("Error", "Please enter a domain name")
            return
            
        self.status_label.config(text="Processing...")
        self.root.update()
        
        success, txt_record = self.validator.add_domain_to_digicert(domain)
        if not success:
            messagebox.showerror("Error", f"Failed to add domain: {txt_record}")
            self.status_label.config(text="")
            return
            
        is_akamai = self.validator.check_akamai_hosting(domain)
        if is_akamai:
            success = self.validator.add_txt_record_akamai(domain, txt_record)
            if success:
                messagebox.showinfo("Success", "TXT record added to Akamai")
            else:
                messagebox.showerror("Error", "Failed to add TXT record to Akamai")
        else:
            success = self.validator.send_admin_email(domain, txt_record)
            if success:
                messagebox.showinfo("Success", "Email sent to admin with TXT record")
            else:
                messagebox.showerror("Error", "Failed to send email")
                
        self.status_label.config(text="")

def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        # Command line mode
        domain = sys.argv[1]
        config = Config()
        validator = DomainValidator(config)
        
        success, txt_record = validator.add_domain_to_digicert(domain)
        if not success:
            print(f"Error: {txt_record}")
            sys.exit(1)
            
        is_akamai = validator.check_akamai_hosting(domain)
        if is_akamai:
            success = validator.add_txt_record_akamai(domain, txt_record)
            if not success:
                print("Failed to add TXT record to Akamai")
                sys.exit(1)
            print("TXT record added to Akamai")
        else:
            success = validator.send_admin_email(domain, txt_record)
            if not success:
                print("Failed to send email")
                sys.exit(1)
            print("Email sent to admin with TXT record")
    else:
        # GUI mode
        app = DomainValidatorGUI()
        app.root.mainloop()

if __name__ == "__main__":
    main() 