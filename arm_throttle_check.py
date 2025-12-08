#!/usr/bin/env python3
"""
ElevateXY - Arm with Throttle Check
The ACCEPTED message means we need to check throttle position
"""

import time
from dronekit import connect, VehicleMode
from pymavlink import mavutil

def arm_with_throttle_check():
    print("="*70)
    print("ARM WITH THROTTLE CHECK")
    print("="*70)
    print()
    print("⚠️  CRITICAL: The arm command is ACCEPTED but not executing")
    print("   This usually means THROTTLE is not at minimum")
    print()
    print("   If you have an RC transmitter:")
    print("   - Make sure throttle stick is all the way DOWN")
    print("   - Check that it's calibrated correctly")
    print()
    print("   If NO RC transmitter:")
    print("   - We'll use the FORCE arm command (param2=21196)")
    print("="*70)
    print()
    
    # Connect
    print("🔌 Connecting...")
    vehicle = connect('/dev/ttyUSB0', baud=57600, wait_ready=False, timeout=30)
    
    print("⏳ Waiting for telemetry...")
    vehicle.wait_ready('mode', 'armed', timeout=10)
    print("✅ Connected\n")
    
    # Set GUIDED
    if vehicle.mode.name != "GUIDED":
        print("📍 Setting GUIDED mode...")
        vehicle.mode = VehicleMode("GUIDED")
        time.sleep(3)
        print(f"   Mode: {vehicle.mode.name}\n")
    
    # Method 1: Normal arm with throttle check
    print("METHOD 1: Normal Arm (requires throttle at minimum)")
    print("-" * 70)
    print("🔧 Sending normal arm command...")
    
    msg = vehicle.message_factory.command_long_encode(
        vehicle._master.target_system,
        vehicle._master.target_component,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        0,      # confirmation
        1,      # param1: 1=arm
        0,      # param2: 0=check throttle position
        0, 0, 0, 0, 0
    )
    vehicle.send_mavlink(msg)
    vehicle.flush()
    
    # Wait
    time.sleep(3)
    
    if vehicle.armed:
        print("✅ SUCCESS! Armed with throttle check\n")
        print("Disarming...")
        vehicle.armed = False
        time.sleep(2)
        vehicle.close()
        return
    else:
        print("❌ Failed (throttle not at minimum or RC issue)\n")
    
    # Method 2: FORCE arm (bypass throttle check)
    print("METHOD 2: Force Arm (bypass throttle check)")
    print("-" * 70)
    print("🔧 Sending FORCE arm command (21196)...")
    print("   This bypasses throttle position safety check")
    print()
    
    msg = vehicle.message_factory.command_long_encode(
        vehicle._master.target_system,
        vehicle._master.target_component,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        0,          # confirmation
        1,          # param1: 1=arm
        21196,      # param2: 21196=force arm (bypass checks)
        0, 0, 0, 0, 0
    )
    vehicle.send_mavlink(msg)
    vehicle.flush()
    
    # Wait
    print("Waiting for arm...")
    for i in range(10):
        time.sleep(1)
        print(f"   {i+1}s: Armed = {vehicle.armed}")
        
        if vehicle.armed:
            print("\n" + "="*70)
            print("✅ SUCCESS! FORCE ARM WORKED!")
            print("="*70)
            print()
            print("🎉 This means:")
            print("   - The communication works perfectly")
            print("   - The issue was throttle position check")
            print("   - You can now arm via Python using force parameter")
            print()
            print("Disarming in 5 seconds...")
            time.sleep(5)
            vehicle.armed = False
            time.sleep(2)
            vehicle.close()
            return
    
    print("\n❌ Even force arm failed")
    print("   This is very unusual")
    
    # Method 3: Check RC input
    print("\nMETHOD 3: Checking RC Input")
    print("-" * 70)
    
    try:
        # Read RC channels
        print("RC Channel 3 (Throttle):", vehicle.channels['3'])
        print("RC Channel 5 (Mode):", vehicle.channels.get('5', 'N/A'))
        print()
        print("For arming, Channel 3 should be < 1200 (throttle at minimum)")
        
        if vehicle.channels['3'] > 1200:
            print("❌ PROBLEM: Throttle is NOT at minimum!")
            print(f"   Current: {vehicle.channels['3']}")
            print("   Need: < 1200")
            print()
            print("   Solution: Lower throttle stick on RC transmitter")
    except Exception as e:
        print(f"Cannot read RC channels: {e}")
    
    vehicle.close()
    print()

if __name__ == "__main__":
    arm_with_throttle_check()
