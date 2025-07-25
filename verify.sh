#!/bin/bash
#
# Quick verification script for mktk-provisioner
# Tests basic functionality without requiring RouterOS devices
#

echo "🔍 Mikrotik RouterBoard Provisioner - Verification Script"
echo "======================================================="

# Check Python version
echo "📋 Checking Python version..."
python3 --version
if [ $? -ne 0 ]; then
    echo "❌ Python 3 not found!"
    exit 1
fi

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "🐍 Activating virtual environment..."
    source venv/bin/activate
fi

# Check dependencies
echo "📦 Checking Python dependencies..."
pip list | grep -E "(Flask|paramiko)" > /dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  Installing dependencies..."
    pip install -r requirements.txt
fi

# Check system dependencies
echo "🔧 Checking system dependencies..."
which arp-scan > /dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  arp-scan not found. Install with: sudo apt install arp-scan"
fi

# Test module imports
echo "🧩 Testing module imports..."
python3 -c "
try:
    import app
    import modules.network_discovery
    import modules.ssh_operations
    import modules.config_generator
    import modules.status_manager
    print('✅ All modules imported successfully')
except ImportError as e:
    print(f'❌ Import error: {e}')
    exit(1)
"

if [ $? -eq 0 ]; then
    echo "✅ Basic verification completed successfully!"
    echo ""
    echo "🚀 To start the application:"
    echo "   ./run.sh"
    echo ""
    echo "🌐 Then open: http://localhost:5000"
else
    echo "❌ Verification failed!"
    exit 1
fi
