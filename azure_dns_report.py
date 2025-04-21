#!/usr/bin/env python3
"""
Azure DNS Report Generator

This script generates a comprehensive report of all DNS zones and records
across all Azure subscriptions, including both public and private zones.
"""

import os
from typing import List, Dict, Optional
from azure.identity import DefaultAzureCredential
from azure.mgmt.dns import DnsManagementClient
from azure.mgmt.resource import ResourceManagementClient
import pandas as pd
from datetime import datetime

class AzureDNSReporter:
    """Main class for Azure DNS reporting operations"""
    
    def __init__(self):
        self.credential = DefaultAzureCredential()
        self.resource_client = ResourceManagementClient(self.credential, "")
        self.dns_data = []
        
    def get_subscriptions(self) -> List[str]:
        """Get list of all accessible subscriptions"""
        try:
            subscriptions = list(self.resource_client.subscriptions.list())
            return [sub.subscription_id for sub in subscriptions]
        except Exception as e:
            print(f"Error getting subscriptions: {str(e)}")
            return []
            
    def get_dns_zones(self, subscription_id: str) -> List[Dict]:
        """Get all DNS zones (public and private) for a subscription"""
        dns_client = DnsManagementClient(self.credential, subscription_id)
        zones = []
        
        try:
            # Get public DNS zones
            public_zones = dns_client.zones.list()
            for zone in public_zones:
                zones.append({
                    'subscription_id': subscription_id,
                    'resource_group': zone.id.split('/')[4],
                    'zone_name': zone.name,
                    'zone_type': 'Public',
                    'location': zone.location
                })
                
            # Get private DNS zones
            private_zones = dns_client.private_zones.list()
            for zone in private_zones:
                zones.append({
                    'subscription_id': subscription_id,
                    'resource_group': zone.id.split('/')[4],
                    'zone_name': zone.name,
                    'zone_type': 'Private',
                    'location': zone.location
                })
                
        except Exception as e:
            print(f"Error getting DNS zones for subscription {subscription_id}: {str(e)}")
            
        return zones
        
    def get_record_sets(self, subscription_id: str, zone: Dict) -> List[Dict]:
        """Get all record sets for a DNS zone"""
        dns_client = DnsManagementClient(self.credential, subscription_id)
        records = []
        
        try:
            if zone['zone_type'] == 'Public':
                record_sets = dns_client.record_sets.list_all_by_dns_zone(
                    zone['resource_group'],
                    zone['zone_name']
                )
            else:
                record_sets = dns_client.record_sets.list(
                    zone['resource_group'],
                    zone['zone_name']
                )
                
            for record in record_sets:
                # Skip SOA and NS records for public zones
                if zone['zone_type'] == 'Public' and record.record_type in ['SOA', 'NS']:
                    continue
                    
                record_data = {
                    'subscription_id': subscription_id,
                    'resource_group': zone['resource_group'],
                    'zone_name': zone['zone_name'],
                    'zone_type': zone['zone_type'],
                    'record_type': record.record_type,
                    'record_name': record.name,
                    'record_values': self._get_record_values(record),
                    'linked_vnets': ''
                }
                
                # Get linked VNETs for private zones
                if zone['zone_type'] == 'Private':
                    vnets = dns_client.virtual_network_links.list(
                        zone['resource_group'],
                        zone['zone_name']
                    )
                    vnet_info = []
                    for vnet in vnets:
                        vnet_info.append(f"{vnet.name} ({vnet.virtual_network.id})")
                    record_data['linked_vnets'] = '; '.join(vnet_info)
                    
                records.append(record_data)
                
        except Exception as e:
            print(f"Error getting record sets for zone {zone['zone_name']}: {str(e)}")
            
        return records
        
    def _get_record_values(self, record) -> str:
        """Extract record values based on record type"""
        try:
            if record.record_type == 'A':
                return '; '.join([ip.ipv4_address for ip in record.a_records])
            elif record.record_type == 'AAAA':
                return '; '.join([ip.ipv6_address for ip in record.aaaa_records])
            elif record.record_type == 'CNAME':
                return record.cname_record.cname
            elif record.record_type == 'TXT':
                return '; '.join([''.join(txt.value) for txt in record.txt_records])
            elif record.record_type == 'MX':
                return '; '.join([f"{mx.preference} {mx.exchange}" for mx in record.mx_records])
            elif record.record_type == 'PTR':
                return record.ptr_records[0].ptrdname
            elif record.record_type == 'SRV':
                return '; '.join([f"{srv.priority} {srv.weight} {srv.port} {srv.target}" for srv in record.srv_records])
            else:
                return str(record)
        except Exception:
            return str(record)
            
    def generate_report(self) -> None:
        """Generate the DNS report"""
        print("Starting Azure DNS report generation...")
        
        # Get all subscriptions
        subscriptions = self.get_subscriptions()
        print(f"Found {len(subscriptions)} subscriptions")
        
        # Process each subscription
        for sub_id in subscriptions:
            print(f"\nProcessing subscription: {sub_id}")
            
            # Get all DNS zones
            zones = self.get_dns_zones(sub_id)
            print(f"Found {len(zones)} DNS zones")
            
            # Get all record sets for each zone
            for zone in zones:
                records = self.get_record_sets(sub_id, zone)
                self.dns_data.extend(records)
                print(f"Processed {len(records)} records for zone {zone['zone_name']}")
                
        # Create DataFrame and save to Excel
        if self.dns_data:
            df = pd.DataFrame(self.dns_data)
            
            # Reorder columns
            columns = [
                'subscription_id',
                'resource_group',
                'zone_name',
                'zone_type',
                'record_type',
                'record_name',
                'record_values',
                'linked_vnets'
            ]
            df = df[columns]
            
            # Create a function to apply conditional formatting
            def highlight_zones(row):
                # Initialize styles
                styles = [''] * len(row)
                
                # Check if zone has no records (other than NS/SOA)
                zone_records = df[
                    (df['zone_name'] == row['zone_name']) & 
                    (df['subscription_id'] == row['subscription_id'])
                ]
                if len(zone_records) == 0:
                    # Highlight entire row in light red for empty zones
                    styles = ['background-color: #FFB6C1'] * len(row)
                
                # Check if private zone has no VNETs
                elif row['zone_type'] == 'Private' and not row['linked_vnets']:
                    # Highlight entire row in light yellow for private zones without VNETs
                    styles = ['background-color: #FFFACD'] * len(row)
                
                return styles
            
            # Apply the styling
            styled_df = df.style.apply(highlight_zones, axis=1)
            
            # Save to Excel
            report_file = os.path.expanduser("~/Desktop/azure_dns_report.xlsx")
            with pd.ExcelWriter(report_file, engine='openpyxl') as writer:
                styled_df.to_excel(writer, index=False, sheet_name='DNS Report')
                
                # Auto-adjust column widths
                worksheet = writer.sheets['DNS Report']
                for idx, col in enumerate(df.columns):
                    max_length = max(
                        df[col].astype(str).apply(len).max(),
                        len(str(col))
                    )
                    worksheet.column_dimensions[chr(65 + idx)].width = max_length + 2
                    
            print(f"\nReport saved to: {report_file}")
            print(f"Total records processed: {len(self.dns_data)}")
            print("\nColor Legend:")
            print("- Light Red: Zones with no records (other than NS/SOA)")
            print("- Light Yellow: Private zones with no linked VNETs")
        else:
            print("No DNS data found to report")

def main():
    """Main entry point"""
    reporter = AzureDNSReporter()
    reporter.generate_report()

if __name__ == "__main__":
    main() 