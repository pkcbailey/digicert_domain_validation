import csv
import logging
import os
from datetime import datetime
from akamai.edgegrid import EdgeGridAuth
import requests
import re
from urllib.parse import urljoin
import configparser # Import configparser

# --- Configuration ---
# Set up logging to file and console
LOG_FILE = 'domain_processing.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler() # Also print to console
    ]
)
logger = logging.getLogger(__name__)

# Akamai API configuration
# Ensure your .edgerc file is correctly set up in your home directory,
# or specify its path and section here.
# For example: ~/.edgerc and [default] section.
AKAMAI_API_BASE_URL = "https://{}/config-dns/v2/" # Host from .edgerc will replace {}
EDGERC_FILE = os.path.join(os.path.expanduser("~"), ".edgerc")
EDGERC_SECTION = "default" # Or your specific Akamai section

# --- Akamai API Client ---

class AkamaiDNSClient:
    def __init__(self, edgerc_file, edgerc_section):
        self.session = requests.Session()
        try:
            # First, parse the .edgerc file to get the host
            config = configparser.ConfigParser()
            if not os.path.exists(edgerc_file):
                raise FileNotFoundError(f".edgerc file not found at: {edgerc_file}")
            config.read(edgerc_file)

            if edgerc_section not in config:
                raise ValueError(f"Section '{edgerc_section}' not found in .edgerc file.")

            self.akamai_host = config.get(edgerc_section, 'host')
            if not self.akamai_host:
                raise ValueError(f"Host not found in .edgerc section '{edgerc_section}'")

            self.base_url = AKAMAI_API_BASE_URL.format(self.akamai_host)
            
            # Now, initialize EdgeGridAuth for the session
            self.session.auth = EdgeGridAuth.from_edgerc(edgerc_file, edgerc_section)
            
            logger.info(f"AkamaiDNSClient initialized with base URL: {self.base_url}")
        except Exception as e:
            logger.error(f"Failed to initialize Akamai EdgeGrid authentication: {e}")
            raise

    def _make_request(self, method, path, **kwargs):
        url = urljoin(self.base_url, path)
        logger.debug(f"Making {method} request to: {url}")
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error for {method} {url}: {e.response.status_code} - {e.response.text}")
            raise
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error for {method} {url}: {e}")
            raise
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout error for {method} {url}: {e}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"An unexpected request error occurred for {method} {url}: {e}")
            raise

    def get_zones(self, search_domain=None):
        """Fetches all Akamai DNS zones, optionally filtered by domain."""
        path = "zones"
        params = {}
        if search_domain:
            params['search'] = search_domain # Akamai API might not directly support this for zones list
        logger.info(f"Fetching Akamai DNS zones, searching for: {search_domain or 'all'}")
        response = self._make_request('GET', path, params=params)
        return response.get('zones', [])

    def find_zone_for_domain(self, target_domain):
        """
        Attempts to find the most specific Akamai DNS zone that
        manages the given target_domain (e.g., for sub.example.com, find example.com zone).
        """
        parts = target_domain.split('.')
        for i in range(len(parts)):
            potential_zone = ".".join(parts[i:]).strip() # Ensure potential_zone is stripped here
            logger.debug(f"Checking potential zone: {potential_zone}")
            # Akamai's API has a direct endpoint for a specific zone.
            # We can check if it exists and if it's managed.
            try:
                zone_details = self._make_request('GET', f"zones/{potential_zone}")
                if zone_details.get('zone'):
                    logger.info(f"Found Akamai DNS zone '{potential_zone}' for domain '{target_domain}'")
                    return potential_zone
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    logger.debug(f"Zone '{potential_zone}' not found on Akamai.")
                else:
                    logger.warning(f"Error checking zone '{potential_zone}': {e.response.text}")
            except Exception as e:
                logger.error(f"An error occurred while finding zone for '{target_domain}': {e}")
                return None
        logger.error(f"Could not find a managed Akamai DNS zone for domain: {target_domain}")
        return None

    def get_rrsets(self, zone, record_name, record_type='TXT'):
        """Fetches all resource record sets of a specific type for a given name within a zone."""
        # Updated path as per user request: zones/<domain>/names/<record_name>/types/<record_type>
        clean_zone = zone.strip()
        clean_record_name = record_name.strip()
        clean_record_type = record_type.strip()
        path = f"zones/{clean_zone}/names/{clean_record_name}/types/{clean_record_type}" 
        
        logger.debug(f"Getting {record_type} RRSets for name '{record_name}' in zone '{zone}' from path: {path}")
        try:
            response = self._make_request('GET', path) # Parameters are now part of the URL path
            # The API returns a list of RRSets if successful, even if empty.
            # It might return a 404 if the name doesn't exist at all, or an empty list if no records of that type.
            return response.get('rsets', []) # Assuming 'rsets' key is still used in response
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.debug(f"No RRSet found for name '{record_name}' type '{record_type}' in zone '{zone}'.")
                return []
            else:
                raise # Re-raise other HTTP errors
        except Exception:
            raise # Re-raise any other exceptions

    def add_rrset(self, zone, record_name, record_type, ttl, rdata):
        """Adds a new resource record set."""
        # Ensure all components of the URL path are stripped
        clean_zone = zone.strip()
        clean_record_name = record_name.strip()
        clean_record_type = record_type.strip()

        # Updated path as per user request: zones/<domain>/names/<record_name>/types/<record_type>
        path = f"zones/{clean_zone}/names/{clean_record_name}/types/{clean_record_type}"
        payload = {
            "name": clean_record_name,
            "type": clean_record_type,
            "ttl": ttl,
            "rdata": [rdata] # rdata is expected as a list of strings
        }
        logger.info(f"Adding {record_type} record '{record_name}' in zone '{zone}' with data: '{rdata}'")
        return self._make_request('POST', path, json=payload)

    def update_rrset(self, zone, record_name, record_type, ttl, rdata):
        """Updates an existing resource record set."""
        # Ensure all components of the URL path are stripped
        clean_zone = zone.strip()
        clean_record_name = record_name.strip()
        clean_record_type = record_type.strip()

        # Updated path as per user request: zones/<domain>/names/<record_name>/types/<record_type>
        path = f"zones/{clean_zone}/names/{clean_record_name}/types/{clean_record_type}"
        payload = {
            "name": clean_record_name,
            "type": clean_record_type,
            "ttl": ttl,
            "rdata": [rdata] # rdata is expected as a list of strings
        }
        logger.info(f"Updating {record_type} record '{record_name}' in zone '{zone}' with data: '{rdata}'")
        return self._make_request('PUT', path, json=payload)

    def delete_rrset(self, zone, record_name, record_type='TXT', ttl=60, rdata=None):
        """Deletes a specific resource record set."""
        # Ensure all components of the URL path are stripped
        clean_zone = zone.strip()
        clean_record_name = record_name.strip()
        clean_record_type = record_type.strip()

        # Updated path as per user request: zones/<domain>/names/<record_name>/types/<record_type>
        path = f"zones/{clean_zone}/names/{clean_record_name}/types/{clean_record_type}"
        
        logger.info(f"Attempting to delete {record_type} record '{record_name}' in zone '{zone}' from path: {path}")
        try:
            # For deletion, we still want to check if it exists before trying to delete
            # We'll use the new path for get_rrsets too.
            existing_rrsets = self.get_rrsets(zone, record_name, record_type) 
            if not existing_rrsets:
                logger.warning(f"No existing {record_type} record '{record_name}' found to delete in zone '{zone}'. Skipping deletion.")
                return {"status": "skipped", "message": "Record not found for deletion"}

            return self._make_request('DELETE', path)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"Failed to delete {record_type} record '{record_name}' in zone '{zone}': Record not found. It might have been deleted already.")
                return {"status": "not_found", "message": "Record not found for deletion, likely already removed."}
            else:
                raise # Re-raise other HTTP errors
        except Exception:
            raise # Re-raise any other exceptions


# --- Main Processing Logic ---

def process_dcv_records(csv_file_path):
    """
    Reads the CSV, processes each domain for Akamai, and manages TXT records.
    """
    logger.info(f"Starting DCV record processing from file: {csv_file_path}")

    try:
        akamai_client = AkamaiDNSClient(EDGERC_FILE, EDGERC_SECTION)
    except Exception as e:
        logger.critical(f"Exiting: Akamai API client initialization failed: {e}")
        return

    processed_count = 0
    skipped_count = 0

    try:
        with open(csv_file_path, mode='r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            if not all(col in reader.fieldnames for col in ['domain', 'host', 'token', 'message', 'ns_type']):
                logger.error(f"CSV header is incorrect. Expected: domain,host,token,message,ns_type. Found: {reader.fieldnames}")
                return

            for row in reader:
                domain_name = row['domain'].strip()
                host = row['host'].strip() # Not directly used for _pki-validation.<domain> but kept for data integrity
                token = row['token'].strip()
                ns_type = row['ns_type'].strip()

                full_record_name = f"_pki-validation.{domain_name}"
                record_type = "TXT"
                # Standard TTL for DCV records is often low, e.g., 60 seconds (1 minute)
                record_ttl = 60

                if ns_type.lower() == 'akamai':
                    logger.info(f"\n--- Processing Akamai domain: {domain_name} ---")
                    try:
                        # 1. Find the Akamai DNS Zone
                        akamai_zone = akamai_client.find_zone_for_domain(domain_name)
                        if not akamai_zone:
                            logger.error(f"Skipping {domain_name}: Could not determine Akamai zone.")
                            skipped_count += 1
                            continue

                        # 2. Check if the TXT record already exists
                        existing_rrsets = akamai_client.get_rrsets(akamai_zone, full_record_name, record_type)
                        
                        record_value_to_add = token # Akamai API expects clean strings, it handles quoting if needed.
                                                    # For DCV tokens, they usually don't have spaces or special characters
                                                    # that require explicit quoting in the payload.

                        if existing_rrsets:
                            # 3. If exists, update the record
                            logger.info(f"Existing TXT record for {full_record_name} found in zone {akamai_zone}. Updating...")
                            # Akamai DNS API typically requires you to replace the entire RRSet values
                            # For DCV, we just need one value. So replace the existing rdata list with the new one.
                            update_response = akamai_client.update_rrset(
                                akamai_zone, full_record_name, record_type, record_ttl, record_value_to_add
                            )
                            logger.info(f"Update API Response: {update_response}")
                            print(f"Updated Akamai record for {full_record_name}: {update_response.get('message', 'Success')}")
                        else:
                            # 4. If not exists, add a new record
                            logger.info(f"No existing TXT record for {full_record_name} found in zone {akamai_zone}. Adding new record...")
                            add_response = akamai_client.add_rrset(
                                akamai_zone, full_record_name, record_type, record_ttl, record_value_to_add
                            )
                            logger.info(f"Add API Response: {add_response}")
                            print(f"Added Akamai record for {full_record_name}: {add_response.get('message', 'Success')}")

                        processed_count += 1

                        # --- Validation and Cleanup (Placeholder for next steps) ---
                        logger.info(f"Domain {domain_name} processed successfully for record update/add. "
                                    f"Next steps (external validation, then cleanup) would follow here.")
                        
                        # Example of cleanup - would typically be triggered *after* successful DCV validation by vendor
                        # For demonstration, we'll just log this part as a reminder for future modularity.
                        # clean_up_after_validation = True # Set to True to test deletion immediately
                        # if clean_up_after_validation:
                        #     logger.info(f"Attempting to clean up record for {full_record_name} in zone {akamai_zone}...")
                        #     delete_response = akamai_client.delete_rrset(akamai_zone, full_record_name, record_type)
                        #     logger.info(f"Delete API Response: {delete_response}")
                        #     print(f"Cleaned up Akamai record for {full_record_name}: {delete_response.get('message', 'Success')}")


                    except Exception as e:
                        logger.error(f"Error processing domain {domain_name} for Akamai: {e}")
                        print(f"Error processing Akamai domain {domain_name}: {e}")
                        skipped_count += 1
                else:
                    logger.info(f"Skipping domain {domain_name}: ns_type is '{ns_type}', not 'Akamai'.")
                    skipped_count += 1

    except FileNotFoundError:
        logger.critical(f"Error: CSV file not found at {csv_file_path}")
        print(f"Error: CSV file not found at {csv_file_path}")
    except Exception as e:
        logger.critical(f"An unhandled error occurred during processing: {e}")
        print(f"An unhandled error occurred: {e}")

    logger.info(f"Processing finished. Processed Akamai domains: {processed_count}, Skipped domains: {skipped_count}")

# --- Script Execution ---
if __name__ == "__main__":
    # Get current date for CSV file naming
    current_date = datetime.now().strftime("%Y-%m-%d")
    csv_filename = f"sectigo.{current_date}.csv"

    # For testing, you might want to force a specific CSV file:
    # csv_filename = "sectigo.2025-06-18.csv" 

    print(f"Looking for CSV file: {csv_filename}")
    process_dcv_records(csv_filename)
