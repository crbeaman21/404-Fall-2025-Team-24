#!/bin/bash
# ElevateXY Connection Troubleshooting Script

echo "=================================="
echo "ElevateXY Connection Diagnostics"
echo "=================================="
echo ""

# Step 1: Check if we're on Jetson
echo "Step 1: System Check"
echo "-------------------"
echo "Hostname: $(hostname)"
echo "User: $(whoami)"
echo ""

# Step 2: Ask for laptop IP
echo "Step 2: Get Laptop IP"
echo "-------------------"
echo "What is your laptop's IP address?"
echo "(Run 'ipconfig' on Windows and look for IPv4 Address)"
read -p "Enter laptop IP (e.g., 192.168.1.100): " LAPTOP_IP

if [ -z "$LAPTOP_IP" ]; then
    echo "ERROR: No IP address entered!"
    exit 1
fi

echo "Using laptop IP: $LAPTOP_IP"
echo ""

# Step 3: Ping test
echo "Step 3: Network Connectivity Test"
echo "-------------------"
echo "Testing ping to $LAPTOP_IP..."
if ping -c 3 -W 2 $LAPTOP_IP > /dev/null 2>&1; then
    echo "✓ Ping successful - Jetson can reach laptop"
else
    echo "✗ Ping FAILED - Jetson cannot reach laptop"
    echo ""
    echo "Troubleshooting steps:"
    echo "  1. Check both devices are on same network"
    echo "  2. Check Windows firewall isn't blocking ping"
    echo "  3. Verify laptop IP address is correct"
    exit 1
fi
echo ""

# Step 4: Port 14550 test
echo "Step 4: MAVLink Port Test"
echo "-------------------"
echo "Testing port 14550 on $LAPTOP_IP..."

# Check if nc (netcat) is available
if ! command -v nc &> /dev/null; then
    echo "Installing netcat..."
    sudo apt-get update -qq && sudo apt-get install -y netcat > /dev/null 2>&1
fi

if timeout 3 nc -zv $LAPTOP_IP 14550 2>&1 | grep -q "succeeded\|open"; then
    echo "✓ Port 14550 is OPEN - MAVLink should work!"
else
    echo "✗ Port 14550 is CLOSED or not accessible"
    echo ""
    echo "Possible causes:"
    echo "  1. SITL is not running on laptop"
    echo "  2. Windows firewall is blocking port 14550"
    echo "  3. MAVProxy is not forwarding to network"
    echo ""
    echo "On your laptop, check:"
    echo "  - Is sim_vehicle.py running?"
    echo "  - In MAVProxy console, type: link"
    echo "  - Should show: udp:172.22.240.1:14550"
    echo ""
    read -p "Press Enter after checking laptop, or Ctrl+C to exit..."
    
    # Try again
    if timeout 3 nc -zv $LAPTOP_IP 14550 2>&1 | grep -q "succeeded\|open"; then
        echo "✓ Port 14550 is now OPEN!"
    else
        echo "✗ Still cannot connect to port 14550"
        echo ""
        echo "Windows Firewall Fix:"
        echo "Run this in PowerShell (as Administrator) on laptop:"
        echo ""
        echo "New-NetFirewallRule -DisplayName 'SITL MAVLink' -Direction Inbound -LocalPort 14550 -Protocol TCP -Action Allow"
        echo "New-NetFirewallRule -DisplayName 'SITL MAVLink' -Direction Inbound -LocalPort 14550 -Protocol UDP -Action Allow"
        exit 1
    fi
fi
echo ""

# Step 5: Check Python dependencies
echo "Step 5: Python Dependencies"
echo "-------------------"
if python3 -c "import dronekit" 2>/dev/null; then
    echo "✓ DroneKit installed"
else
    echo "✗ DroneKit NOT installed"
    echo "Installing DroneKit..."
    pip3 install dronekit --break-system-packages
fi

if python3 -c "import cv2" 2>/dev/null; then
    echo "✓ OpenCV installed"
else
    echo "✗ OpenCV NOT installed (needed for camera)"
fi
echo ""

# Step 6: Test connection
echo "Step 6: Test Connection"
echo "-------------------"
echo "Testing DroneKit connection to tcp:$LAPTOP_IP:14550..."
echo ""

# Create test script
cat > /tmp/test_connection.py << 'EOFPYTHON'
import sys
from dronekit import connect

connection_string = sys.argv[1]
print(f"Connecting to {connection_string}...")

try:
    vehicle = connect(connection_string, wait_ready=False, timeout=10)
    print("✓ Connected successfully!")
    print(f"  Mode: {vehicle.mode.name}")
    print(f"  Armed: {vehicle.armed}")
    vehicle.close()
    sys.exit(0)
except Exception as e:
    print(f"✗ Connection failed: {e}")
    sys.exit(1)
EOFPYTHON

if python3 /tmp/test_connection.py "tcp:$LAPTOP_IP:14550"; then
    echo ""
    echo "=================================="
    echo "✓ ALL TESTS PASSED!"
    echo "=================================="
    echo ""
    echo "Your connection string is: tcp:$LAPTOP_IP:14550"
    echo ""
    echo "Run ElevateXY with:"
    echo "python3 elevatexy_simulation.py --connect tcp:$LAPTOP_IP:14550"
    echo ""
else
    echo ""
    echo "=================================="
    echo "✗ CONNECTION FAILED"
    echo "=================================="
    echo ""
    echo "Common issues and fixes:"
    echo ""
    echo "1. SITL not running on laptop"
    echo "   → Start: sim_vehicle.py -v ArduCopter -f gazebo-iris --console --map"
    echo ""
    echo "2. Windows Firewall blocking"
    echo "   → Run in PowerShell (Admin):"
    echo "   New-NetFirewallRule -DisplayName 'SITL MAVLink' -Direction Inbound -LocalPort 14550 -Protocol TCP -Action Allow"
    echo "   New-NetFirewallRule -DisplayName 'SITL MAVLink' -Direction Inbound -LocalPort 14550 -Protocol UDP -Action Allow"
    echo ""
    echo "3. MAVProxy not forwarding"
    echo "   → In MAVProxy console type: link"
    echo "   → Should show: udp:172.22.240.1:14550"
    echo ""
    echo "4. Wrong IP address"
    echo "   → Double-check: ipconfig on Windows"
    echo "   → Use IPv4 Address from 'Wireless LAN adapter' or 'Ethernet adapter'"
    echo ""
fi

# Cleanup
rm -f /tmp/test_connection.py
