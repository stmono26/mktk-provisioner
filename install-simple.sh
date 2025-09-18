#!/bin/bash

# Mikrotik RouterBoard Provisioner - Simple Installation
# For production use by junior technicians

set -e

echo "🛠️  Installing Mikrotik RouterBoard Provisioner (Simple Mode)"
echo "============================================================"

# Install system packages
echo "📦 Installing required packages..."
sudo apt update
sudo apt install -y python3 python3-pip arp-scan git

# Install Python packages system-wide
echo "📦 Installing Python dependencies..."
sudo pip3 install Flask==2.3.3 paramiko==3.3.1

# Create application directory
APP_DIR="/opt/mktk-provisioner"
sudo mkdir -p "$APP_DIR"

# Copy application files
echo "📋 Installing application..."
sudo cp -r * "$APP_DIR"/
sudo chown -R $USER:$USER "$APP_DIR"

# Create simple launcher script
sudo tee /usr/local/bin/mktk-provisioner > /dev/null << 'EOF'
#!/bin/bash
cd /opt/mktk-provisioner
python3 app.py
EOF

sudo chmod +x /usr/local/bin/mktk-provisioner

# Create desktop shortcut
mkdir -p ~/.local/share/applications
cat > ~/.local/share/applications/mktk-provisioner.desktop << 'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=Mikrotik Provisioner
Comment=RouterBoard Configuration Tool
Exec=gnome-terminal -- mktk-provisioner
Icon=network-wired
Terminal=true
Categories=Network;System;
EOF

echo ""
echo "🎉 Installation completed!"
echo ""
echo "🚀 How to run:"
echo "   Method 1: Type 'mktk-provisioner' in terminal"
echo "   Method 2: Look for 'Mikrotik Provisioner' in applications menu"
echo "   Method 3: Double-click desktop shortcut (if created)"
echo ""
echo "📱 Web interface will be available at: http://localhost:5000"
echo ""
