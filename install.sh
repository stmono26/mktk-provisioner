#!/bin/bash

# Mikrotik RouterBoard Provisioner Installation Script
# For Debian 12 / Raspberry Pi OS

set -e  # Exit on any error

echo "🛠️  Mikrotik RouterBoard Provisioner Installation"
echo "=================================================="

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "❌ This script should not be run as root. Please run as regular user (pi)."
   exit 1
fi

# Check for required system packages
echo "📦 Checking system requirements..."

# Update package lists
sudo apt update

# Install required system packages
REQUIRED_PACKAGES="python3 python3-pip python3-venv arp-scan git"
for package in $REQUIRED_PACKAGES; do
    if ! dpkg -l | grep -q "^ii  $package "; then
        echo "Installing $package..."
        sudo apt install -y $package
    else
        echo "✅ $package already installed"
    fi
done

# Check Python version
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1-2)
if [[ $(echo "$PYTHON_VERSION >= 3.11" | bc -l) -eq 1 ]]; then
    echo "✅ Python $PYTHON_VERSION is supported"
else
    echo "⚠️  Python $PYTHON_VERSION detected. Python 3.11+ recommended."
fi

# Create application directory
APP_DIR="/home/pi/mktk-provisioner"
if [ ! -d "$APP_DIR" ]; then
    echo "📁 Creating application directory..."
    mkdir -p "$APP_DIR"
fi

# Copy application files (assuming this script is in the project directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "📋 Copying application files from $SCRIPT_DIR to $APP_DIR..."

cp -r "$SCRIPT_DIR"/* "$APP_DIR"/
chown -R pi:pi "$APP_DIR"

# Create virtual environment
echo "🐍 Creating Python virtual environment..."
cd "$APP_DIR"
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create logs directory
mkdir -p "$APP_DIR/logs"

# Create configs directory
mkdir -p "$APP_DIR/configs"

# Set proper permissions
chmod +x "$APP_DIR/app.py"
chmod +x "$APP_DIR/install.sh"

# Install systemd service
echo "⚙️  Installing systemd service..."
sudo cp "$APP_DIR/mktk-provisioner.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable mktk-provisioner

# Configure firewall (if ufw is active)
if sudo ufw status | grep -q "Status: active"; then
    echo "🔥 Configuring firewall..."
    sudo ufw allow 5000/tcp comment "Mikrotik Provisioner"
fi

# Check network configuration
echo "🌐 Network configuration check..."
IP_ADDRESS=$(hostname -I | awk '{print $1}')
echo "   Server IP: $IP_ADDRESS"
echo "   Web Interface: http://$IP_ADDRESS:5000"

# Test arp-scan functionality
echo "🔍 Testing arp-scan functionality..."
if arp-scan --local --plain | head -5 > /dev/null 2>&1; then
    echo "✅ arp-scan working correctly"
else
    echo "⚠️  arp-scan may require additional configuration"
    echo "   You may need to run: sudo setcap cap_net_raw+ep /usr/bin/arp-scan"
fi

# Create startup test script
cat > "$APP_DIR/test_installation.py" << 'EOF'
#!/usr/bin/env python3
"""Test script to verify installation"""

import sys
import subprocess

def test_imports():
    """Test that all required modules can be imported"""
    try:
        import flask
        import paramiko
        print("✅ All Python modules imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_arp_scan():
    """Test arp-scan functionality"""
    try:
        result = subprocess.run(['arp-scan', '--help'], 
                              capture_output=True, timeout=5)
        if result.returncode == 0:
            print("✅ arp-scan is available")
            return True
        else:
            print("❌ arp-scan not working")
            return False
    except Exception as e:
        print(f"❌ arp-scan test failed: {e}")
        return False

def main():
    print("🧪 Testing Mikrotik Provisioner Installation")
    print("=" * 45)
    
    all_tests_passed = True
    
    all_tests_passed &= test_imports()
    all_tests_passed &= test_arp_scan()
    
    if all_tests_passed:
        print("\n🎉 Installation test PASSED!")
        print("You can start the service with: sudo systemctl start mktk-provisioner")
        return 0
    else:
        print("\n❌ Installation test FAILED!")
        print("Please check the errors above and retry installation")
        return 1

if __name__ == "__main__":
    sys.exit(main())
EOF

chmod +x "$APP_DIR/test_installation.py"

# Run installation test
echo ""
echo "🧪 Running installation test..."
cd "$APP_DIR"
source venv/bin/activate
python test_installation.py

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Installation completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Start the service: sudo systemctl start mktk-provisioner"
    echo "2. Check status: sudo systemctl status mktk-provisioner"
    echo "3. View logs: sudo journalctl -u mktk-provisioner -f"
    echo "4. Access web interface: http://$IP_ADDRESS:5000"
    echo ""
    echo "Service will automatically start on boot."
    echo ""
else
    echo ""
    echo "❌ Installation test failed. Please check the errors above."
    exit 1
fi
