#!/usr/bin/env python3
"""
Auth Module Package

A Python module for managing API credentials from a JSON vault file.
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .auth import (
    load_api_vault,
    get_credentials,
    get_digicert_credentials,
    get_email_credentials,
    get_infoblox_credentials,
    get_sectigo_credentials,
    get_venafi_credentials,
    get_azure_spn_credentials,
    get_gemini_credentials,
    get_mailhardener_credentials
)

__all__ = [
    "load_api_vault",
    "get_credentials",
    "get_digicert_credentials",
    "get_email_credentials",
    "get_infoblox_credentials",
    "get_sectigo_credentials",
    "get_venafi_credentials",
    "get_azure_spn_credentials",
    "get_gemini_credentials",
    "get_mailhardener_credentials"
] 