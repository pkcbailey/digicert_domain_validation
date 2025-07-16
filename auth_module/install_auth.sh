#!/bin/bash

# Auth Module Installation Script

set -e

echo "🔐 Installing Auth Module..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Check Python version
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.8 or higher is required. Current version: $python_version"
    exit 1
fi

echo "✅ Python $python_version detected"

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is required but not installed. Please install pip3."
    exit 1
fi

echo "✅ pip3 detected"

# Install the package in development mode
echo "🔧 Installing Auth Module package..."
pip3 install -e . -f auth_module_setup.py

echo ""
echo "✅ Installation complete!"
echo ""
echo "🎯 Quick start:"
echo "  auth list                           # List all available services"
echo "  auth get digicert                   # Get DigiCert credentials"
echo "  auth get Sectigo                    # Get Sectigo credentials"
echo "  auth validate digicert api customerID  # Validate credentials"
echo "  auth --help                         # See all commands"
echo ""
echo "📚 For more information, see auth_module_README.md"
echo "" 