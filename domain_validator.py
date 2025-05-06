import csv
from datetime import datetime

# Simulated results for demonstration
results = [
    {
        'hostname': 'server1',
        'expected_ip': '192.168.1.10',
        'resolved_ips': ['192.168.1.20'],
        'status': 'MISMATCH',
        'short_name_checks': [
            {'suffix': 'corp.local', 'full_name': 'server1.corp.local', 'resolved_ips': ['192.168.1.10'], 'matches': True},
            {'suffix': 'prod.local', 'full_name': 'server1.prod.local', 'resolved_ips': [], 'matches': False},
        ]
    },
    {
        'hostname': 'server2',
        'expected_ip': '192.168.1.11',
        'resolved_ips': [],
        'status': 'UNRESOLVED',
        'short_name_checks': [
            {'suffix': 'corp.local', 'full_name': 'server2.corp.local', 'resolved_ips': [], 'matches': False},
            {'suffix': 'prod.local', 'full_name': 'server2.prod.local', 'resolved_ips': ['192.168.1.11'], 'matches': True},
        ]
    }
]

# Prepare flat data including matched FQDN and suffix
flattened_data = []
for result in results:
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

# Export to CSV
output_file = f"dns_validation_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
with open(output_file, 'w', newline='') as csvfile:
    fieldnames = ['Hostname', 'Expected IP', 'Status', 'Resolved IPs', 'Matching Suffix', 'Resolved FQDN']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for row in flattened_data:
        writer.writerow(row)

output_file

