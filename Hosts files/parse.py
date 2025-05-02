#!/usr/bin/env python3
"""
DNS Validator - Validates entries in a hosts file and checks short names with search suffixes
"""

import socket
import re
import argparse
from typing import List, Dict, Tuple
import ipaddress
import sys
import csv
from datetime import datetime

def parse_hosts_file(file_path: str) -> List[Tuple[str, str]]:
    """Parse a hosts file and return list of (ip, hostname) tuples"""
    entries = []
    try:
        with open(file_path, 'r') as f:
            for line in f:
                # Skip comments and empty lines
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Split on whitespace
                parts = line.split()
                if len(parts) < 2:
                    continue
                
                ip = parts[0]
                # Validate IP address format
                try:
                    ipaddress.ip_address(ip)
                except ValueError:
                    continue
                
                # Add all hostnames for this IP
                for hostname in parts[1:]:
                    if not hostname.startswith('#'):
                        entries.append((ip, hostname))
    except FileNotFoundError:
        print(f"Error: Hosts file not found: {file_path}")
        sys.exit(1)
    
    return entries

def parse_search_suffixes(file_path: str) -> List[str]:
    """Parse a file containing search suffixes (one per line)"""
    suffixes = []
    try:
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    suffixes.append(line)
    except FileNotFoundError:
        print(f"Error: Search suffixes file not found: {file_path}")
        sys.exit(1)
    
    return suffixes

def resolve_hostname(hostname: str) -> List[str]:
    """Resolve a hostname to IP addresses"""
    try:
        return [addr[4][0] for addr in socket.getaddrinfo(hostname, None)]
    except socket.gaierror:
        return []

def check_forward_dns(ip: str, hostname: str, search_suffixes: List[str]) -> Dict:
    """Check forward DNS resolution for a hostname"""
    result = {
        'hostname': hostname,
        'expected_ip': ip,
        'resolved_ips': [],
        'status': 'UNKNOWN',
        'short_name_checks': []
    }
    
    # Check full hostname
    resolved_ips = resolve_hostname(hostname)
    result['resolved_ips'] = resolved_ips
    
    if ip in resolved_ips:
        result['status'] = 'MATCH'
    elif resolved_ips:
        result['status'] = 'MISMATCH'
    else:
        result['status'] = 'UNRESOLVED'
    
    # Check short name with search suffixes
    short_name = hostname.split('.')[0]
    for suffix in search_suffixes:
        full_name = f"{short_name}.{suffix}"
        resolved_ips = resolve_hostname(full_name)
        result['short_name_checks'].append({
            'suffix': suffix,
            'full_name': full_name,
            'resolved_ips': resolved_ips,
            'matches': ip in resolved_ips
        })
    
    return result

def print_results_csv(results: List[Dict], output_file: str = None) -> None:
    """Print validation results in CSV format"""
    if output_file is None:
        output_file = f"dns_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    with open(output_file, 'w', newline='') as csvfile:
        fieldnames = [
            'Hostname',
            'Expected IP',
            'Status',
            'Resolved IPs',
            'Short Name',
            'Suffix',
            'Short Name Resolved IPs',
            'Short Name Match'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for result in results:
            # Write main entry
            writer.writerow({
                'Hostname': result['hostname'],
                'Expected IP': result['expected_ip'],
                'Status': result['status'],
                'Resolved IPs': '; '.join(result['resolved_ips']),
                'Short Name': '',
                'Suffix': '',
                'Short Name Resolved IPs': '',
                'Short Name Match': ''
            })
            
            # Write short name checks
            for check in result['short_name_checks']:
                writer.writerow({
                    'Hostname': '',
                    'Expected IP': '',
                    'Status': '',
                    'Resolved IPs': '',
                    'Short Name': check['full_name'],
                    'Suffix': check['suffix'],
                    'Short Name Resolved IPs': '; '.join(check['resolved_ips']),
                    'Short Name Match': 'Yes' if check['matches'] else 'No'
                })
    
    print(f"Results saved to: {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Validate DNS entries in a hosts file')
    parser.add_argument('hosts_file', help='Path to the hosts file')
    parser.add_argument('search_suffixes_file', help='Path to file containing search suffixes')
    parser.add_argument('--output', '-o', help='Output CSV file path (default: dns_validation_YYYYMMDD_HHMMSS.csv)')
    
    args = parser.parse_args()
    
    # Parse files
    entries = parse_hosts_file(args.hosts_file)
    search_suffixes = parse_search_suffixes(args.search_suffixes_file)
    
    # Validate entries
    results = []
    for ip, hostname in entries:
        result = check_forward_dns(ip, hostname, search_suffixes)
        results.append(result)
    
    # Print results in CSV format
    print_results_csv(results, args.output)

if __name__ == "__main__":
    main()

    # Execution: python dns_validator.py /etc/hosts search_suffixes.txt --output results.csv