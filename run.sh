#!/bin/bash

# Simple run script for junior technicians
# Just double-click this file to start the provisioner

echo "🚀 Starting Mikrotik RouterBoard Provisioner..."
echo ""

# Check if running from correct directory
if [ ! -f "app.py" ]; then
    echo "❌ Error: Please run this script from the mktk-provisioner directory"
    echo "   Navigate to the folder containing app.py and try again"
    read -p "Press Enter to exit..."
    exit 1
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed"
    echo "   Please install Python 3 first"
    read -p "Press Enter to exit..."
    exit 1
fi

# Check if required packages are installed
echo "🔍 Checking dependencies..."
python3 -c "import flask, paramiko" 2>/dev/null || {
    echo "📦 Installing required packages..."
    pip3 install --user Flask==2.3.3 paramiko==3.3.1
}

# Check if arp-scan is available
if ! command -v arp-scan &> /dev/null; then
    echo "⚠️  Warning: arp-scan not found"
    echo "   Network discovery may not work properly"
    echo "   Install with: sudo apt install arp-scan"
    echo ""
fi

# Get IP address
IP_ADDRESS=$(hostname -I | awk '{print $1}')

echo "✅ Starting application..."
echo ""
echo "🌐 Web interface will be available at:"
echo "   http://localhost:5000"
echo "   http://$IP_ADDRESS:5000"
echo ""
echo "💡 Tip: Open your web browser and go to http://localhost:5000"
echo ""
echo "🛑 Press Ctrl+C to stop the application"
echo ""

# Start the application
python3 app.py
