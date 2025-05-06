import socket
import ipaddress
import csv
from datetime import datetime

# File paths (update these as needed)
input_file = '/mnt/data/your_input_file.txt'  # Replace with your actual file name
search_suffixes_file = '/mnt/data/search.suffix'
output_file = f"/mnt/data/dns_validation_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

# Read DNS entries from input file
def parse_input_file(file_path):
    entries = []
    with open(file_path, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 2:
                ip, hostname = parts[0], parts[1]
                try:
                    ipaddress.ip_address(ip)
                    entries.append((ip, hostname))
                except ValueError:
                    continue
    return entries

# Read search suffixes
def parse_search_suffixes(file_path):
    suffixes = []
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                suffixes.append(line)
    return suffixes

# Resolve hostname
def resolve_hostname(hostname):
    try:
        return [addr[4][0] for addr in socket.getaddrinfo(hostname, None)]
    except socket.gaierror:
        return []

# Check forward DNS
def check_dns(ip, hostname, suffixes):
    result = {
        'hostname': hostname,
        'expected_ip': ip,
        'resolved_ips': resolve_hostname(hostname),
        'status': 'UNKNOWN',
        'short_name_checks': []
    }

    if ip in result['resolved_ips']:
        result['status'] = 'MATCH'
    elif result['resolved_ips']:
        result['status'] = 'MISMATCH'
    else:
        result['status'] = 'UNRESOLVED'

    short_name = hostname.split('.')[0]
    for suffix in suffixes:
        fqdn = f"{short_name}.{suffix}"
        resolved_ips = resolve_hostname(fqdn)
        result['short_name_checks'].append({
            'suffix': suffix,
            'full_name': fqdn,
            'resolved_ips': resolved_ips,
            'matches': ip in resolved_ips
        })

    return result

# Parse files and run validation
entries = parse_input_file(input_file)
suffixes = parse_search_suffixes(search_suffixes_file)

# Validate entries and write results
flattened_data = []
for ip, hostname in entries:
    result = check_dns(ip, hostname, suffixes)
    matched_suffix = ''
    resolved_fqdn = ''
    for check in result['short_name_checks']:
        if check['matches']:
            matched_suffix = check['suffix']
            resolved_fqdn = check['full_name']
            break
    flattened_data.append({
        'Hostname': result['hostname'],
        'Expected IP': result['expected_ip'],
        'Status': result['status'],
        'Resolved IPs': '; '.join(result['resolved_ips']),
        'Matching Suffix': matched_suffix,
        'Resolved FQDN': resolved_fqdn
    })

# Write to CSV
with open(output_file, 'w', newline='') as csvfile:
    fieldnames = ['Hostname', 'Expected IP', 'Status', 'Resolved IPs', 'Matching Suffix', 'Resolved FQDN']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for row in flattened_data:
        writer.writerow(row)

output_file

