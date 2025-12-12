# DigiCert Domain Validation Automation

Menu-driven CLI tool to manage domain inventory, DCV validation,
and DNS automation across:

- DigiCert
- Sectigo
- Akamai EdgeDNS
- AWS Route53
- Azure DNS

## Features
- Unified inventory from multiple CAs
- Expiration reporting
- Per-domain inspection
- Automated DCV CNAME creation & cleanup
- Full audit logging

## Run
```bash
python src/dcv_automation/main.py
