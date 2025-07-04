#!/usr/bin/env python3

import argparse
import json
import logging
import os
import time
from pathlib import Path
import dns.resolver
import requests
from akamai.edgegrid import EdgeGridAuth
from azure.identity import ClientSecretCredential
from azure.mgmt.dns import DnsManagementClient

# --- Configuration ---
# Locations for credentials files
API_VAULT_PATH = Path.home() / ".ApiVault"
EDGERC_PATH = Path.home() / ".edgerc"
LOG_DIRECTORY = Path("..") / "log"

# --- Logging Setup ---
def setup_logging():
    """Sets up the logging configuration."""
    if not LOG_DIRECTORY.exists():
        LOG_DIRECTORY.mkdir()
    
    log_file = LOG_DIRECTORY / f"dcv_automation_{int(time.time())}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    logging.info("Logging initialized.")

def log_json_response(api_name, response):
    """Logs the JSON response from an API call."""
    try:
        logging.info(f"--- {api_name} JSON Response ---")
        logging.info(json.dumps(response.json(), indent=2))
        logging.info("--- End Response ---")
    except json.JSONDecodeError:
        logging.warning(f"Could not parse JSON response from {api_name}. Raw text: {response.text}")

# --- Credential Management ---
def get_api_vault_creds(service_name):
    """Loads credentials from the ~/.ApiVault JSON file."""
    if not API_VAULT_PATH.exists():
        raise FileNotFoundError(f"API Vault file not found at: {API_VAULT_PATH}")
    with open(API_VAULT_PATH, 'r') as f:
        creds = json.load(f)
    if service_name not in creds:
        raise KeyError(f"Credentials for '{service_name}' not found in {API_VAULT_PATH}")
    return creds[service_name]

# --- DNS Provider Determination ---
def get_dns_provider(domain):
    """Determines if the domain is hosted on Akamai or Azure."""
    try:
        ns_records = dns.resolver.resolve(domain, 'NS')
        nameservers = [str(ns.target).lower() for ns in ns_records]
        
        logging.info(f"Found nameservers for {domain}: {nameservers}")

        if any("akam.net" in ns or "akamaidns.net" in ns for ns in nameservers):
            return "akamai"
        if any("azure-dns" in ns for ns in nameservers):
            return "azure"
        
        return "unknown"
    except dns.resolver.NoAnswer:
        logging.error(f"No NS records found for {domain}.")
        return "unknown"
    except dns.resolver.NXDOMAIN:
        logging.error(f"Domain {domain} does not exist.")
        return "unknown"
    except Exception as e:
        logging.error(f"An error occurred during DNS resolution: {e}")
        return "unknown"

# --- Certificate Authority (CA) API Clients ---
class SectigoClient:
    def __init__(self):
        creds = get_api_vault_creds("Sectigo")
        self.customer_uri = creds["customeruri"]
        self.login = creds["login"]
        self.password = creds["password"]
        self.org_id = creds["orgID"]
        self.base_url = f"https://cert-manager.com/api/ssl/v1"
        logging.info("Sectigo client initialized.")

    def get_dcv(self, domain):
        """Retrieves DCV information for a domain."""
        logging.info(f"Sectigo: Requesting DCV for {domain}")
        # This is a placeholder for the actual API call.
        # You would replace this with the specific endpoint and payload.
        # For example:
        # endpoint = f"{self.base_url}/dcv"
        # payload = {"domain": domain, "orgId": self.org_id}
        # response = requests.post(endpoint, auth=(self.login, self.password), json=payload)
        # log_json_response("Sectigo DCV Request", response)
        # response.raise_for_status()
        # dcv_data = response.json()
        
        # --- MOCK DATA ---
        dcv_data = {
            "dcv": {
                "method": "cname",
                "host": f"_{domain.replace('.', '-')}.{domain}",
                "point": "dcv.sectigo.com"
            }
        }
        logging.info(f"Sectigo mock DCV data: {dcv_data}")
        return dcv_data['dcv']['host'], dcv_data['dcv']['point']

    def check_validation(self, domain):
        """Checks the validation status of a domain."""
        logging.info(f"Sectigo: Checking validation for {domain}")
        # Placeholder for the validation check API call
        # --- MOCK DATA ---
        validation_status = {"status": "validated"}
        logging.info(f"Sectigo mock validation status: {validation_status}")
        return validation_status

class DigicertClient:
    def __init__(self):
        creds = get_api_vault_creds("Digicert")
        self.api_key = creds["api"]
        self.customer_id = creds["customerID"]
        self.base_url = "https://www.digicert.com/services/v2"
        self.headers = {"X-DC-DEVKEY": self.api_key, "Content-Type": "application/json"}
        logging.info("Digicert client initialized.")

    def get_dcv(self, domain):
        """Retrieves DCV information for a domain."""
        logging.info(f"Digicert: Requesting DCV for {domain}")
        # Placeholder for the actual API call
        # --- MOCK DATA ---
        dcv_data = {
            "dcv": {
                "method": "cname",
                "host": f"{domain}.dcv.digicert.com",
                "point": "dcv.digicert.com"
            }
        }
        logging.info(f"Digicert mock DCV data: {dcv_data}")
        return dcv_data['dcv']['host'], dcv_data['dcv']['point']

    def check_validation(self, domain):
        """Checks the validation status of a domain."""
        logging.info(f"Digicert: Checking validation for {domain}")
        # Placeholder for the validation check API call
        # --- MOCK DATA ---
        validation_status = {"status": "validated"}
        logging.info(f"Digicert mock validation status: {validation_status}")
        return validation_status

# --- DNS Provider API Clients ---
class AkamaiClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.auth = EdgeGridAuth.from_edgerc(EDGERC_PATH)
        # Assuming the base URL is in the .edgerc file
        with open(EDGERC_PATH, 'r') as f:
            for line in f:
                if line.strip().startswith('host'):
                    self.base_url = f"https://{line.split('=')[1].strip()}"
                    break
        logging.info("Akamai client initialized.")

    def apply_cname(self, zone, record_name, record_value):
        """Applies a CNAME record in Akamai."""
        logging.info(f"Akamai: Applying CNAME {record_name} -> {record_value} in zone {zone}")
        endpoint = f"{self.base_url}/config-dns/v2/zones/{zone}/names/{record_name}/types/cname"
        payload = {
            "name": record_name,
            "type": "cname",
            "ttl": 300,
            "target": record_value
        }
        # Akamai requires a PUT request to create/update
        response = self.session.put(endpoint, json=payload)
        log_json_response("Akamai Apply CNAME", response)
        response.raise_for_status()
        logging.info("Akamai CNAME record applied successfully.")

class AzureClient:
    def __init__(self):
        creds = get_api_vault_creds("AzureSPN") # Assuming SPN creds are in ApiVault
        self.subscription_id = creds["subscriptionId"]
        self.resource_group = creds["resourceGroup"]
        
        credentials = ClientSecretCredential(
            tenant_id=creds["tenantId"],
            client_id=creds["clientId"],
            client_secret=creds["clientSecret"]
        )
        self.dns_client = DnsManagementClient(credentials, self.subscription_id)
        logging.info("Azure client initialized.")

    def apply_cname(self, zone, record_name, record_value):
        """Applies a CNAME record in Azure DNS."""
        logging.info(f"Azure: Applying CNAME {record_name} -> {record_value} in zone {zone}")
        
        # Azure record_name is relative to the zone
        relative_record_name = record_name.replace(f".{zone}", "")

        cname_record = {"cname_record": {"cname": record_value}}
        
        self.dns_client.record_sets.create_or_update(
            resource_group_name=self.resource_group,
            zone_name=zone,
            relative_record_set_name=relative_record_name,
            record_type="CNAME",
            parameters={
                "ttl": 300,
                "cname_record": {"cname": record_value}
            }
        )
        logging.info("Azure CNAME record applied successfully.")

# --- Main Application Logic ---
def main():
    parser = argparse.ArgumentParser(description="Automate DCV CNAME validation for Sectigo and Digicert.")
    parser.add_argument("domain", help="The DNS domain to validate (e.g., example.com).")
    args = parser.parse_args()
    
    domain = args.domain
    
    setup_logging()
    logging.info(f"Starting DCV process for domain: {domain}")

    try:
        # 1. Initialize clients
        sectigo = SectigoClient()
        digicert = DigicertClient()

        # 2. Get DCV tokens
        sectigo_host, sectigo_point = sectigo.get_dcv(domain)
        digicert_host, digicert_point = digicert.get_dcv(domain)
        
        # 3. Determine DNS provider
        provider = get_dns_provider(domain)
        logging.info(f"Determined DNS provider: {provider.upper()}")

        dns_client = None
        if provider == "akamai":
            dns_client = AkamaiClient()
        elif provider == "azure":
            # You might need to specify the resource group for Azure
            # This example assumes it's in the creds file
            dns_client = AzureClient()
        else:
            logging.error("Could not determine DNS provider or provider is not supported. Exiting.")
            return

        # 4. Apply CNAME records
        dns_client.apply_cname(domain, sectigo_host, sectigo_point)
        dns_client.apply_cname(domain, digicert_host, digicert_point)

        # 5. Wait for DNS propagation
        wait_time = 600 # 10 minutes
        logging.info(f"Waiting {wait_time // 60} minutes for DNS propagation...")
        time.sleep(wait_time)

        # 6. Check validation status
        logging.info("--- Final Validation Check ---")
        sectigo_status = sectigo.check_validation(domain)
        digicert_status = digicert.check_validation(domain)
        
        logging.info(f"Sectigo final status: {sectigo_status['status']}")
        logging.info(f"Digicert final status: {digicert_status['status']}")
        
        print("\n--- Validation Report ---")
        print(f"Domain: {domain}")
        print(f"Sectigo: {sectigo_status['status']}")
        print(f"Digicert: {digicert_status['status']}")
        print("-------------------------")

    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
        print(f"An error occurred. Check the log file in the '../log' directory for details.")

if __name__ == "__main__":
    main()
