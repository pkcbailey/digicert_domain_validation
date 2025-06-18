#!/usr/bin/env python3

import json
import csv
import os
import requests
from datetime import datetime
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    filename='domain_processing.log',
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_config():
    """Load configuration from ~/.ApiVault"""
    config_path = os.path.expanduser('~/.ApiVault')
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            return config.get('Sectigo', {})
    except FileNotFoundError:
        logger.error("Configuration file not found at ~/.ApiVault")
        raise
    except json.JSONDecodeError:
        logger.error("Invalid JSON in configuration file")
        raise

def process_domain(domain, config):
    """Process a single domain"""
    customer_uri = config.get('CustomerUri')
    org_id = config.get('orgID')
    username = config.get('login')
    password = config.get('password')

    headers = {
        'Content-Type': 'application/json;charset=utf-8',
        'login': username,
        'password': password,
        'customerUri': customer_uri
    }

    result = {
        'domain': domain,
        'host': '',
        'point': '',
        'message': ''
    }

    try:
        # 1. Create Domain via REST API
        domain_uri = 'https://cert-manager.com/api/domain/v1'
        domain_body = {
            'name': domain,
            'description': 'Domain created via REST API',
            'active': True,
            'enabled': True,
            'includeSubdomains': True,
            'delegations': [{
                'orgId': org_id,
                'certTypes': ['SSL'],
                'domainCertificateRequestPrivileges': ['SUBDOMAIN', 'DOMAIN']
            }]
        }

        domain_response = requests.post(
            domain_uri,
            headers=headers,
            json=domain_body
        )
        domain_response.raise_for_status()
        logger.info(f"Domain Creation Response for {domain}:\n{domain_response.json()}")

        # 2. Submit DNS TXT Validation
        dns_uri = 'https://cert-manager.com/api/dcv/v1/validation/submit/domain/txt'
        dns_body = {'domain': domain}

        dns_response = requests.post(
            dns_uri,
            headers=headers,
            json=dns_body
        )
        dns_response.raise_for_status()
        dns_data = dns_response.json()
        logger.info(f"DNS TXT Validation Response for {domain}:\n{dns_data}")

        # Capture DNS validation response
        result['host'] = dns_data.get('host', '')
        result['point'] = dns_data.get('point', '')
        result['message'] = dns_data.get('message', '')

    except requests.exceptions.RequestException as e:
        error_message = f"ERROR processing {domain}: {str(e)}"
        logger.error(error_message)
        result['message'] = error_message

    return result

def main():
    try:
        # Load configuration
        config = load_config()
        if not all(key in config for key in ['CustomerUri', 'orgID', 'login', 'password']):
            raise ValueError("Missing required configuration values in ~/.ApiVault")

        # Read domain list
        csv_path = "data.csv"
        results = []
        
        with open(csv_path, 'r') as f:
            domains = list(csv.DictReader(f))
            total_domains = len(domains)

        # Process each domain
        for index, entry in enumerate(domains, 1):
            domain = entry['domain']
            logger.info(f"Processing domain {index} of {total_domains}: {domain}")
            print(f"\nProcessing domain {index} of {total_domains}: {domain}")

            result = process_domain(domain, config)
            results.append(result)

            # Save progress after each domain
            with open(csv_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['domain', 'host', 'point', 'message'])
                writer.writeheader()
                writer.writerows(results)
            
            print(f"Progress saved: {index} of {total_domains} domains processed")

        # Backup original CSV
        backup_path = f"{csv_path}.bak"
        Path(csv_path).rename(backup_path)
        print(f"\n✅ {csv_path} has been updated. Original backed up as {backup_path}")
        logger.info("Processing completed")

    except Exception as e:
        error_message = f"Fatal error: {str(e)}"
        logger.error(error_message)
        print(error_message)
        raise

if __name__ == "__main__":
    main() 