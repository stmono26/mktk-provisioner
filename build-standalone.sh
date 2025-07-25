#!/bin/bash

# Create standalone executable using PyInstaller
# Run this on your development machine

echo "📦 Creating standalone executable..."

# Install PyInstaller
pip install pyinstaller

# Create executable
pyinstaller --onefile \
    --add-data "templates:templates" \
    --add-data "modules:modules" \
    --name "mktk-provisioner" \
    app.py

echo "✅ Executable created in dist/mktk-provisioner"
echo ""
echo "📋 To distribute:"
echo "1. Copy dist/mktk-provisioner to target machine"
echo "2. Make executable: chmod +x mktk-provisioner"
echo "3. Run: ./mktk-provisioner"
echo ""
echo "⚠️  Note: Target machine still needs arp-scan installed"
echo "   sudo apt install arp-scan"
