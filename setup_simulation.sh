#!/bin/bash
# ElevateXY Simulation Quick Start
# Run this on your Jetson to set up for simulation

echo "========================================"
echo "ElevateXY Simulation Setup"
echo "========================================"
echo ""

# Check if running on Jetson
if [ ! -f /etc/nv_tegra_release ]; then
    echo "⚠️  Warning: Not running on Jetson"
    echo "This script is designed for Jetson devices"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Step 1: Check Python
echo "1. Checking Python..."
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
echo "   ✓ Python $PYTHON_VERSION"

# Step 2: Install DroneKit
echo ""
echo "2. Installing DroneKit..."
if pip3 list | grep -q dronekit; then
    echo "   ✓ DroneKit already installed"
else
    pip3 install dronekit pymavlink --break-system-packages
    echo "   ✓ DroneKit installed"
fi

# Step 3: Check OpenCV
echo ""
echo "3. Checking OpenCV..."
if python3 -c "import cv2" 2>/dev/null; then
    CV_VERSION=$(python3 -c "import cv2; print(cv2.__version__)")
    echo "   ✓ OpenCV $CV_VERSION"
else
    echo "   ✗ OpenCV not found"
    echo "   Installing..."
    sudo apt-get update
    sudo apt-get install -y python3-opencv
fi

# Step 4: Check GStreamer
echo ""
echo "4. Checking GStreamer..."
if python3 -c "import gi; gi.require_version('Gst', '1.0')" 2>/dev/null; then
    echo "   ✓ GStreamer Python bindings installed"
else
    echo "   ✗ GStreamer not found"
    echo "   Installing..."
    sudo apt-get install -y python3-gi python3-gi-cairo gir1.2-gstreamer-1.0
fi

# Step 5: Check camera
echo ""
echo "5. Checking camera..."
if [ -e /dev/video0 ]; then
    echo "   ✓ Camera device found at /dev/video0"
    
    # Try GStreamer test
    echo "   Testing camera..."
    timeout 2 gst-launch-1.0 nvarguscamerasrc num-buffers=10 ! fakesink 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "   ✓ Camera test passed"
    else
        echo "   ⚠️  Camera test failed (may need reconnection)"
    fi
else
    echo "   ⚠️  No camera device found"
    echo "   Connect CSI camera and try again"
fi

# Step 6: Check face cascade
echo ""
echo "6. Checking face detection..."
CASCADE_PATH=~/opencv_cascades/haarcascade_frontalface_default.xml
if [ -f "$CASCADE_PATH" ]; then
    echo "   ✓ Face cascade found"
else
    echo "   ✗ Face cascade not found"
    echo "   Downloading..."
    mkdir -p ~/opencv_cascades
    cd ~/opencv_cascades
    wget -q https://raw.githubusercontent.com/opencv/opencv/3.4/data/haarcascades/haarcascade_frontalface_default.xml
    if [ -f "$CASCADE_PATH" ]; then
        echo "   ✓ Face cascade downloaded"
    else
        echo "   ✗ Download failed"
    fi
    cd - > /dev/null
fi

# Step 7: Network check
echo ""
echo "7. Network configuration..."
read -p "   Enter your laptop's IP address: " LAPTOP_IP

if [ -z "$LAPTOP_IP" ]; then
    echo "   ⚠️  No IP provided"
    echo "   You can find it on Windows with: ipconfig"
    LAPTOP_IP="192.168.1.100"
    echo "   Using example: $LAPTOP_IP"
fi

echo "   Testing connection to $LAPTOP_IP..."
if ping -c 1 -W 2 $LAPTOP_IP > /dev/null 2>&1; then
    echo "   ✓ Can reach $LAPTOP_IP"
else
    echo "   ✗ Cannot reach $LAPTOP_IP"
    echo "   Check network connection"
fi

echo ""
echo "   Testing MAVLink port..."
timeout 2 nc -zv $LAPTOP_IP 14550 2>&1 | grep -q succeeded
if [ $? -eq 0 ]; then
    echo "   ✓ Port 14550 is open"
else
    echo "   ⚠️  Port 14550 not reachable"
    echo "   Make sure SITL is running on laptop"
fi

# Step 8: Performance mode
echo ""
echo "8. Setting performance mode..."
if [ -f /usr/sbin/nvpmodel ]; then
    sudo nvpmodel -m 0
    sudo jetson_clocks
    echo "   ✓ Max performance mode enabled"
else
    echo "   ⚠️  nvpmodel not found (not critical)"
fi

# Summary
echo ""
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "Quick Start:"
echo "  1. On laptop, run:"
echo "     sim_vehicle.py -v ArduCopter -f gazebo-iris --console --map"
echo ""
echo "  2. On Jetson, run:"
echo "     python3 elevatexy_simulation.py --connect tcp:$LAPTOP_IP:14550"
echo ""
echo "  3. In laptop console:"
echo "     mode guided"
echo "     arm throttle"
echo "     takeoff 3"
echo ""
echo "  4. Control from Jetson:"
echo "     - SPACE to toggle manual/autonomous"
echo "     - WASD for manual movement"
echo "     - Face tracking in autonomous mode"
echo ""
echo "========================================"
echo ""

# Save connection string
echo "tcp:$LAPTOP_IP:14550" > ~/.elevatexy_connection
echo "Connection saved to ~/.elevatexy_connection"
echo "Run with: python3 elevatexy_simulation.py --connect \$(cat ~/.elevatexy_connection)"
