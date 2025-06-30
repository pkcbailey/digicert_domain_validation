#!/usr/bin/env python3

import json
import csv
import os
import requests
import logging
from datetime import datetime
import time

# --- Configuration for Logging ---
LOG_FILE_NAME = 'digicert_domain_checker.log'
# Set logging level: INFO for general messages, DEBUG for detailed JSON responses
LOG_LEVEL = logging.INFO 
# Change to logging.DEBUG to see full JSON responses in the log file

# Set up logging
logging.basicConfig(
    filename=LOG_FILE_NAME,
    level=LOG_LEVEL,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Configuration File Path ---
# This script expects your Digicert API key and domain IDs in this file.
# Example content for ~/.DigicertVault:
# {
#     "Digicert": {
#         "api_key": "YOUR_DIGICERT_API_KEY_HERE",
#         "domain_ids": ["123456", "789012"]
#     }
# }
CONFIG_FILE_PATH = os.path.expanduser('~/.DigicertVault')

# --- API Endpoints ---
DIGICERT_BASE_URL = "https://www.digicert.com/services/v2"

# --- Functions ---

def load_config():
    """
    Loads Digicert API configuration (API key and domain IDs) from the
    specified CONFIG_FILE_PATH.
    
    Raises:
        FileNotFoundError: If the configuration file does not exist.
        json.JSONDecodeError: If the configuration file contains invalid JSON.
        ValueError: If required fields are missing from the configuration.
        Exception: For any other errors during configuration loading.
    
    Returns:
        dict: A dictionary containing the Digicert configuration.
    """
    logger.info(f"Attempting to load configuration from {CONFIG_FILE_PATH}")
    try:
        with open(CONFIG_FILE_PATH, 'r') as f:
            config = json.load(f)
            digicert_config = config.get('Digicert', {})
            
            # Validate required fields
            required_fields = ['api_key', 'domain_ids']
            missing_fields = [field for field in required_fields if field not in digicert_config]
            
            if missing_fields:
                raise ValueError(f"Missing required fields in {CONFIG_FILE_PATH}: {missing_fields}")
            
            if not isinstance(digicert_config['domain_ids'], list):
                raise TypeError(f"'domain_ids' in {CONFIG_FILE_PATH} must be a list of strings/integers.")

            logger.info("Configuration loaded successfully.")
            return digicert_config
    except FileNotFoundError:
        error_msg = f"Configuration file not found at {CONFIG_FILE_PATH}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)
    except json.JSONDecodeError:
        error_msg = "Invalid JSON in configuration file"
        logger.error(error_msg)
        raise json.JSONDecodeError(error_msg, doc=CONFIG_FILE_PATH, pos=0)
    except Exception as e:
        error_msg = f"Error reading configuration: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)

def get_domain_details(api_key, domain_id):
    """
    Fetches detailed information for a specific domain from Digicert CertCentral API.
    Includes DCV and validation status.

    Args:
        api_key (str): Your Digicert CertCentral API key.
        domain_id (str): The ID of the domain to retrieve details for.

    Returns:
        dict: A dictionary containing the domain details if successful, otherwise None.
    """
    url = f"{DIGICERT_BASE_URL}/domain/{domain_id}?include_dcv=true&include_validation=true"
    headers = {
        'Content-Type': 'application/json',
        'X-DC-DEVKEY': api_key,
        'Accept': 'application/json'
    }
    
    logger.info(f"Fetching domain details for domain ID: {domain_id}")
    logger.debug(f"GET Request URL: {url}")
    logger.debug(f"Request Headers: {json.dumps(headers, indent=2)}")

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        
        data = response.json()
        logger.info(f"Successfully retrieved domain details for ID: {domain_id}")
        logger.debug(f"Domain details response for ID {domain_id}:\n{json.dumps(data, indent=2)}")
        return data
    except requests.exceptions.HTTPError as e:
        error_msg = f"HTTP error fetching domain details for ID {domain_id}: {e.response.status_code} - {e.response.text}"
        logger.error(error_msg)
        logger.debug(f"Full response for ID {domain_id}:\n{e.response.text}")
        print(f"❌ {error_msg}")
        return None
    except requests.exceptions.RequestException as e:
        error_msg = f"Network error fetching domain details for ID {domain_id}: {str(e)}"
        logger.error(error_msg)
        print(f"❌ {error_msg}")
        return None
    except json.JSONDecodeError:
        error_msg = f"Failed to decode JSON response for domain ID {domain_id}. Response: {response.text}"
        logger.error(error_msg)
        print(f"❌ {error_msg}")
        return None
    except Exception as e:
        error_msg = f"Unexpected error fetching domain details for ID {domain_id}: {str(e)}"
        logger.error(error_msg)
        print(f"❌ {error_msg}")
        return None

def generate_dcv_token(api_key, domain_id):
    """
    Generates a new DCV random value (token) for a specific domain.

    Args:
        api_key (str): Your Digicert CertCentral API key.
        domain_id (str): The ID of the domain to generate a DCV token for.

    Returns:
        dict: A dictionary containing the DCV token information if successful,
              otherwise None.
    """
    url = f"{DIGICERT_BASE_URL}/domain/{domain_id}/dcv/token"
    headers = {
        'X-DC-DEVKEY': api_key,
        'Content-Type': 'application/json', # Though body is empty, good practice to include
        'Accept': 'application/json'
    }
    
    logger.info(f"Generating DCV token for domain ID: {domain_id}")
    logger.debug(f"POST Request URL: {url}")
    logger.debug(f"Request Headers: {json.dumps(headers, indent=2)}")

    try:
        response = requests.post(url, headers=headers)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        
        data = response.json()
        logger.info(f"Successfully generated DCV token for ID: {domain_id}")
        logger.debug(f"DCV token generation response for ID {domain_id}:\n{json.dumps(data, indent=2)}")
        return data
    except requests.exceptions.HTTPError as e:
        error_msg = f"HTTP error generating DCV token for ID {domain_id}: {e.response.status_code} - {e.response.text}"
        logger.error(error_msg)
        logger.debug(f"Full response for ID {domain_id}:\n{e.response.text}")
        print(f"❌ {error_msg}")
        return None
    except requests.exceptions.RequestException as e:
        error_msg = f"Network error generating DCV token for ID {domain_id}: {str(e)}"
        logger.error(error_msg)
        print(f"❌ {error_msg}")
        return None
    except json.JSONDecodeError:
        error_msg = f"Failed to decode JSON response for DCV token generation for ID {domain_id}. Response: {response.text}"
        logger.error(error_msg)
        print(f"❌ {error_msg}")
        return None
    except Exception as e:
        error_msg = f"Unexpected error generating DCV token for ID {domain_id}: {str(e)}"
        logger.error(error_msg)
        print(f"❌ {error_msg}")
        return None

def process_domains(config):
    """
    Processes all domain IDs specified in the configuration: fetches details
    and generates DCV tokens.

    Args:
        config (dict): The Digicert configuration dictionary.

    Returns:
        list: A list of dictionaries, where each dictionary represents a row
              for the CSV output with combined domain and DCV token info.
    """
    api_key = config['api_key']
    domain_ids = config['domain_ids']
    
    if not domain_ids:
        logger.warning("No domain IDs found in the configuration to process.")
        print("❌ No domain IDs found in your ~/.DigicertVault file to process.")
        return []

    logger.info(f"Starting to process {len(domain_ids)} domains.")
    print(f"⚙️ Processing {len(domain_ids)} domains...")
    
    results = []
    for i, domain_id in enumerate(domain_ids, 1):
        print(f"Processing domain {i}/{len(domain_ids)} (ID: {domain_id})...")
        logger.info(f"Processing domain {i}/{len(domain_ids)}: ID {domain_id}")
        
        domain_details = get_domain_details(api_key, domain_id)
        dcv_token_info = generate_dcv_token(api_key, domain_id) # Call the token generation

        result_row = {
            'domain_id': domain_id,
            'domain_name': 'N/A', # Default
            'domain_status': 'N/A',
            'validation_status': 'N/A',
            'dcv_method': 'N/A',
            'dcv_status': 'N/A',
            'dcv_expires': 'N/A',
            'dcv_random_value': 'N/A',
            'dcv_error': '', # To indicate if something went wrong
            'token_generation_status': 'N/A',
            'token_generation_timestamp': 'N/A',
            'token_generation_error': '',
        }

        if domain_details:
            result_row['domain_name'] = domain_details.get('name', 'N/A')
            result_row['domain_status'] = domain_details.get('status', 'N/A')
            result_row['validation_status'] = domain_details.get('validation_status', {}).get('status', 'N/A')
            
            # Extract DCV details from the list (assuming we take the first one if multiple)
            if 'dcv_status' in domain_details and domain_details['dcv_status']:
                first_dcv_entry = domain_details['dcv_status'][0]
                result_row['dcv_method'] = first_dcv_entry.get('method', 'N/A')
                result_row['dcv_status'] = first_dcv_entry.get('status', 'N/A')
                result_row['dcv_expires'] = first_dcv_entry.get('expires', 'N/A')
                # The 'random_value' from get_domain_details is usually the current one for validation
                result_row['dcv_random_value'] = first_dcv_entry.get('random_value', 'N/A')
            else:
                result_row['dcv_error'] = 'No DCV status found'
        else:
            result_row['dcv_error'] = 'Failed to fetch domain details'

        if dcv_token_info:
            result_row['token_generation_status'] = dcv_token_info.get('status', 'N/A')
            result_row['token_generation_timestamp'] = dcv_token_info.get('generation_time', 'N/A')
            # The newly generated token is usually in 'token' or 'random_value' field.
            # Digicert API spec indicates it's in the 'token' field.
            result_row['generated_dcv_token'] = dcv_token_info.get('token', 'N/A') 
        else:
            result_row['token_generation_error'] = 'Failed to generate DCV token'

        results.append(result_row)
        
        # Add a small delay to be respectful to the API rate limits
        time.sleep(0.5)
        print(f"✅ Finished processing ID: {domain_id}")
    
    logger.info("Finished processing all domains.")
    return results

def save_to_csv(results, filename=None):
    """
    Saves the processed results to a CSV file.

    Args:
        results (list): A list of dictionaries, where each dictionary is a row.
        filename (str, optional): The name of the CSV file. If None, a default
                                  name with a timestamp will be generated.

    Returns:
        str: The name of the CSV file created.
    
    Raises:
        Exception: For any errors during CSV file writing.
    """
    if filename is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'digicert_dcv_report_{timestamp}.csv'
    
    logger.info(f"Attempting to save results to {filename}")
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            if results:
                # Use all keys from the first result dictionary as fieldnames
                fieldnames = list(results[0].keys())
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                writer.writerows(results)
        
        logger.info(f"Results successfully saved to {filename}")
        print(f"✅ Results saved to: {filename}")
        return filename
        
    except Exception as e:
        error_msg = f"Error saving to CSV: {str(e)}"
        logger.error(error_msg)
        print(f"❌ {error_msg}")
        raise

def main():
    """Main function to orchestrate the domain DCV checking process."""
    print("🚀 Starting Digicert Domain DCV Checker...")
    logger.info("Starting Digicert Domain DCV Checker script.")
    
    try:
        # Load configuration
        config = load_config()
        
        # Process all domains
        results = process_domains(config)
        
        if results:
            # Save results to CSV
            csv_filename = save_to_csv(results)
            
            # Print summary
            total_domains = len(results)
            failed_fetches = len([r for r in results if r['dcv_error'] or r['token_generation_error']])
            successful_fetches = total_domains - failed_fetches
            
            print(f"\n📊 Summary:")
            print(f"   Total domains processed: {total_domains}")
            print(f"   Successful API calls (both details & token): {successful_fetches}")
            print(f"   Domains with fetch/token generation issues: {failed_fetches}")
            print(f"   Detailed results saved to: {csv_filename}")
            
            logger.info(f"Script completed. Total: {total_domains}, Successful: {successful_fetches}, Failed: {failed_fetches}")
        else:
            print("⚠️ No domains processed or no results generated.")
            logger.warning("No domains processed or no results generated.")
        
    except FileNotFoundError as e:
        print(f"Exiting: {e}")
    except json.JSONDecodeError as e:
        print(f"Exiting due to invalid config file JSON: {e}")
    except ValueError as e:
        print(f"Exiting due to missing config fields: {e}")
    except Exception as e:
        error_msg = f"Fatal error during script execution: {str(e)}"
        logger.critical(error_msg, exc_info=True) # Log full traceback for critical errors
        print(f"❌ {error_msg}")
        
    print("👋 Digicert Domain DCV Checker Finished.")

if __name__ == "__main__":
    main()
