#!/usr/bin/env python3
"""
Auth Module - API Credential Management

This module provides functions to load and retrieve API credentials
from a JSON vault file located at ~/.ApiVault.
"""

import json
import os
from typing import Dict, Any, Optional


def load_api_vault(path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load the API credentials from the JSON file.
    
    Args:
        path: Path to the API vault file (default: ~/.ApiVault)
        
    Returns:
        Dictionary containing all API credentials
        
    Raises:
        FileNotFoundError: If the vault file doesn't exist
        ValueError: If the vault file is not valid JSON
        PermissionError: If the vault file cannot be read
    """
    if path is None:
        path = os.path.expanduser("~/.ApiVault")
    
    try:
        with open(path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        raise FileNotFoundError(f"API vault file not found at {path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"API vault file is not valid JSON: {e}")
    except PermissionError:
        raise PermissionError(f"Permission denied reading API vault file at {path}")


def get_credentials(service_name: str, path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Retrieve credentials for a specific service.
    
    Args:
        service_name: Name of the service to get credentials for
        path: Path to the API vault file (default: ~/.ApiVault)
        
    Returns:
        Dictionary containing the service credentials, or None if not found
        
    Raises:
        FileNotFoundError: If the vault file doesn't exist
        ValueError: If the vault file is not valid JSON
        PermissionError: If the vault file cannot be read
    """
    vault = load_api_vault(path)
    return vault.get(service_name)


# Specific service functions
def get_digicert_credentials(path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get DigiCert API credentials.
    
    Returns:
        Dictionary with 'api' and 'customerID' keys, or None if not found
    """
    return get_credentials("digicert", path)


def get_email_credentials(path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get email service credentials.
    
    Returns:
        Dictionary with email credentials, or None if not found
    """
    return get_credentials("email_credentials", path)


def get_infoblox_credentials(path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get Infoblox API credentials.
    
    Returns:
        Dictionary with Infoblox credentials, or None if not found
    """
    return get_credentials("infoblox", path)


def get_sectigo_credentials(path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get Sectigo API credentials.
    
    Expected format:
    {
        "customeruri": "...",
        "login": "...",
        "password": "...",
        "orgID": "..."
    }
    
    Returns:
        Dictionary with Sectigo credentials, or None if not found
    """
    return get_credentials("Sectigo", path)


def get_venafi_credentials(path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get Venafi API credentials.
    
    Returns:
        Dictionary with Venafi credentials, or None if not found
    """
    return get_credentials("Venafi", path)


def get_azure_spn_credentials(path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get Azure Service Principal credentials.
    
    Returns:
        Dictionary with Azure SPN credentials, or None if not found
    """
    return get_credentials("Azure SPN", path)


def get_gemini_credentials(path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get Gemini API credentials.
    
    Returns:
        Dictionary with Gemini credentials, or None if not found
    """
    return get_credentials("Gemini", path)


def get_mailhardener_credentials(path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get Mailhardener API credentials.
    
    Returns:
        Dictionary with Mailhardener credentials, or None if not found
    """
    return get_credentials("mailhardener", path)


def list_available_services(path: Optional[str] = None) -> list:
    """
    List all available services in the API vault.
    
    Args:
        path: Path to the API vault file (default: ~/.ApiVault)
        
    Returns:
        List of service names available in the vault
        
    Raises:
        FileNotFoundError: If the vault file doesn't exist
        ValueError: If the vault file is not valid JSON
        PermissionError: If the vault file cannot be read
    """
    vault = load_api_vault(path)
    return list(vault.keys())


def validate_credentials(service_name: str, required_keys: list, path: Optional[str] = None) -> bool:
    """
    Validate that a service has all required credential keys.
    
    Args:
        service_name: Name of the service to validate
        required_keys: List of required keys that must be present
        path: Path to the API vault file (default: ~/.ApiVault)
        
    Returns:
        True if all required keys are present, False otherwise
    """
    credentials = get_credentials(service_name, path)
    if not credentials:
        return False
    
    return all(key in credentials for key in required_keys) 