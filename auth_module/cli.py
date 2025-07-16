#!/usr/bin/env python3
"""
Auth Module Command Line Interface

This module provides a command-line interface for the auth module.
"""

import argparse
import sys
import json
from typing import Optional

from .auth import (
    load_api_vault,
    get_credentials,
    get_digicert_credentials,
    get_sectigo_credentials,
    list_available_services,
    validate_credentials
)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Auth Module - API Credential Management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  auth list                           # List all available services
  auth get digicert                   # Get DigiCert credentials
  auth get Sectigo                    # Get Sectigo credentials
  auth validate digicert api customerID  # Validate DigiCert has required keys
  auth --vault /path/to/vault.json get digicert  # Use custom vault file
        """
    )
    
    parser.add_argument(
        '--vault', '-v',
        help='Path to API vault file (default: ~/.ApiVault)'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List command
    subparsers.add_parser('list', help='List all available services')
    
    # Get command
    get_parser = subparsers.add_parser('get', help='Get credentials for a service')
    get_parser.add_argument('service', help='Service name to get credentials for')
    get_parser.add_argument(
        '--format', '-f',
        choices=['json', 'pretty'],
        default='pretty',
        help='Output format (default: pretty)'
    )
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate service credentials')
    validate_parser.add_argument('service', help='Service name to validate')
    validate_parser.add_argument('keys', nargs='+', help='Required keys to validate')
    
    args = parser.parse_args()
    
    # If no command specified, show help
    if not args.command:
        parser.print_help()
        return
    
    try:
        # Execute command
        if args.command == 'list':
            services = list_available_services(args.vault)
            if services:
                print("📋 Available Services:")
                print("-" * 40)
                for service in sorted(services):
                    print(f"  • {service}")
                print(f"\nTotal: {len(services)} services")
            else:
                print("❌ No services found in vault")
                
        elif args.command == 'get':
            credentials = get_credentials(args.service, args.vault)
            if credentials:
                if args.format == 'json':
                    print(json.dumps(credentials, indent=2))
                else:
                    print(f"🔑 Credentials for '{args.service}':")
                    print("-" * 40)
                    for key, value in credentials.items():
                        # Mask sensitive values
                        if any(sensitive in key.lower() for sensitive in ['password', 'secret', 'key', 'token']):
                            masked_value = '*' * min(len(str(value)), 8) + '...' if len(str(value)) > 8 else '*' * len(str(value))
                            print(f"  {key}: {masked_value}")
                        else:
                            print(f"  {key}: {value}")
            else:
                print(f"❌ No credentials found for service '{args.service}'")
                print("💡 Available services:")
                services = list_available_services(args.vault)
                for service in sorted(services):
                    print(f"  • {service}")
                
        elif args.command == 'validate':
            is_valid = validate_credentials(args.service, args.keys, args.vault)
            if is_valid:
                print(f"✅ Service '{args.service}' has all required keys: {', '.join(args.keys)}")
            else:
                print(f"❌ Service '{args.service}' is missing required keys: {', '.join(args.keys)}")
                # Show what keys are available
                credentials = get_credentials(args.service, args.vault)
                if credentials:
                    available_keys = list(credentials.keys())
                    print(f"📋 Available keys: {', '.join(available_keys)}")
                else:
                    print(f"❌ Service '{args.service}' not found in vault")
            
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    except PermissionError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 