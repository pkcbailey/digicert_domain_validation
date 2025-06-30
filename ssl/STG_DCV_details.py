#!/usr/bin/env python3

import json
import csv
import os
import requests
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    filename='sectigo_domain_checker.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_config():
    """Load Sectigo configuration from ~/.ApiVault"""
    config_path = os.path.expanduser('~/.ApiVault')
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            sectigo_config = config.get('Sectigo', {})
            
            # Validate required fields
            required_fields = ['CustomerUri', 'login', 'password', 'orgID']
            missing_fields = [field for field in required_fields if field not in sectigo_config]
            
            if missing_fields:
                raise ValueError(f"Missing required fields in ~/.ApiVault: {missing_fields}")
            
            return sectigo_config
    except FileNotFoundError:
        logger.error("Configuration file not found at ~/.ApiVault")
        raise
    except json.JSONDecodeError:
        logger.error("Invalid JSON in configuration file")
        raise
    except Exception as e:
        logger.error(f"Error reading configuration: {str(e)}")
        raise

def get_all_domains(config, page_size=100):
    """Get all domains from Sectigo API using pagination"""
    all_domains = []
    position = 0
    while True:
        url = f'https://cert-manager.com/api/domain/v1?size={page_size}&position={position}'
        headers = {
            'login': config['login'],
            'password': config['password'],
            'customerUri': config['CustomerUri']
        }
        logger.info(f"Fetching domain list from: {url}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list):
            domains = data
        else:
            domains = data.get('domains', [])
        if not domains:
            break
        all_domains.extend(domains)
        if len(domains) < page_size:
            break
        position += page_size
    logger.info(f"Total domains fetched: {len(all_domains)}")
    return all_domains

def get_domain_dcv_details(config, domain_name):
    """Get DCV details for a specific domain"""
    try:
        url = 'https://cert-manager.com/api/dcv/v2/validation/status' # Corrected URL
        headers = {
            'login': config['login'],
            'password': config['password'],
            'customerUri': config['CustomerUri'],
            'Content-Type': 'application/json;charset=utf-8', # Added Content-Type header
            'Accept': 'application/json' # Added Accept header as in curl
        }
        payload = {"domain": domain_name} # Corrected payload for POST request
        
        logger.info(f"Fetching DCV details for domain: {domain_name}")
        response = requests.post(url, headers=headers, json=payload) # Changed to POST request with json payload
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"Successfully retrieved DCV details for {domain_name}")
        logger.debug(f"DCV details for {domain_name}: {json.dumps(data, indent=2)}")
        
        # The API returns a list of objects for the validation status, we're interested in the first one
        # Assuming the response is a list and we want the first item's details, or handle multiple if needed.
        if isinstance(data, list) and data:
            return data[0] # Return the first DCV detail object
        elif isinstance(data, dict):
            return data # If it's a single dict, return it directly
        else:
            logger.warning(f"Unexpected DCV details format for {domain_name}: {data}")
            return {} # Return an empty dict if format is unexpected
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching DCV details for {domain_name}: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response status: {e.response.status_code}")
            logger.error(f"Response body: {e.response.text}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching DCV details for {domain_name}: {str(e)}")
        return None

def process_all_domains(config):
    """Process all domains and get DCV details"""
    try:
        # Get domain list
        domains = get_all_domains(config, page_size=100)
        
        if not domains:
            logger.warning("No domains found in the response")
            return []
        
        logger.info(f"Processing {len(domains)} domains")
        
        results = []
        for i, domain in enumerate(domains, 1):
            domain_name = domain.get('name', 'Unknown')
            logger.info(f"Processing domain {i}/{len(domains)}: {domain_name}")
            
            # Get DCV details for this domain
            dcv_details = get_domain_dcv_details(config, domain_name)
            
            # Prepare result row
            result_row = {
                'domain_name': domain_name,
                'domain_id': domain.get('id', ''),
                'domain_status': domain.get('status', ''),
                'domain_active': domain.get('active', False),
                'domain_enabled': domain.get('enabled', False),
                # Ensure dcv_details is a dictionary before trying to get keys from it
                'dcv_status': dcv_details.get('status', 'ERROR') if isinstance(dcv_details, dict) else 'ERROR',
                'dcv_validation_type': dcv_details.get('validationType', '') if isinstance(dcv_details, dict) else '',
                'dcv_validation_status': dcv_details.get('validationStatus', '') if isinstance(dcv_details, dict) else '',
                'dcv_last_checked': dcv_details.get('lastChecked', '') if isinstance(dcv_details, dict) else '',
                'dcv_expires': dcv_details.get('expires', '') if isinstance(dcv_details, dict) else '',
                'dcv_error': 'Failed to fetch DCV details' if dcv_details is None or (isinstance(dcv_details, dict) and not dcv_details) else ''
            }
            
            results.append(result_row)
            
            # Small delay to be respectful to the API
            import time
            time.sleep(0.5)
        
        return results
        
    except Exception as e:
        logger.error(f"Error processing domains: {str(e)}")
        raise

def save_to_csv(results, filename=None):
    """Save results to CSV file"""
    if filename is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'sectigo_domain_dcv_{timestamp}.csv'
    
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            if results:
                fieldnames = results[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(results)
        
        logger.info(f"Results saved to {filename}")
        print(f"✅ Results saved to {filename}")
        return filename
        
    except Exception as e:
        logger.error(f"Error saving to CSV: {str(e)}")
        raise

def main():
    """Main function"""
    try:
        logger.info("Starting Sectigo domain DCV checker")
        print("🔍 Starting Sectigo domain DCV checker...")
        
        # Load configuration
        config = load_config()
        logger.info("Configuration loaded successfully")
        print("✅ Configuration loaded successfully")
        
        # Process all domains
        results = process_all_domains(config)
        
        if results:
            # Save results to CSV
            csv_filename = save_to_csv(results)
            
            # Print summary
            total_domains = len(results)
            successful_dcv = len([r for r in results if r['dcv_error'] == ''])
            failed_dcv = total_domains - successful_dcv
            
            print(f"\n📊 Summary:")
            print(f"   Total domains processed: {total_domains}")
            print(f"   Successful DCV lookups: {successful_dcv}")
            print(f"   Failed DCV lookups: {failed_dcv}")
            print(f"   Results saved to: {csv_filename}")
            
            logger.info(f"Processing completed. Total: {total_domains}, Successful: {successful_dcv}, Failed: {failed_dcv}")
        else:
            print("❌ No domains found to process")
            logger.warning("No domains found to process")
        
    except Exception as e:
        error_msg = f"Fatal error: {str(e)}"
        logger.error(error_msg)
        print(f"❌ {error_msg}")
        raise

if __name__ == "__main__":
    main()
