#!/usr/bin/env python3
"""
ElevateXY - Quick Arm Test
Now that safety is disabled, this should work!
"""

import time
from dronekit import connect, VehicleMode

def quick_arm_test():
    print("="*60)
    print("QUICK ARM TEST (Safety Disabled)")
    print("="*60)
    
    # Connect
    print("\n🔌 Connecting...")
    vehicle = connect('/dev/ttyUSB0', baud=57600, wait_ready=False, timeout=30)
    
    print("⏳ Waiting for telemetry...")
    vehicle.wait_ready('mode', 'armed', timeout=10)
    
    print(f"\n✅ Connected!")
    print(f"   Mode: {vehicle.mode.name}")
    print(f"   Armed: {vehicle.armed}")
    
    # Set GUIDED
    if vehicle.mode.name != "GUIDED":
        print("\n📍 Setting GUIDED mode...")
        vehicle.mode = VehicleMode("GUIDED")
        time.sleep(3)
    
    # Try to arm
    print("\n🔧 Attempting to arm...")
    print("   (Safety switch is now disabled)\n")
    
    vehicle.armed = True
    
    # Wait
    for i in range(15):
        time.sleep(1)
        print(f"   {i+1}s: Armed = {vehicle.armed}")
        
        if vehicle.armed:
            print("\n" + "="*60)
            print("✅ SUCCESS! PYTHON CAN NOW ARM!")
            print("="*60)
            print("\n🎉 The safety switch was the problem!")
            print("   Now that it's disabled, Python works!\n")
            
            # Disarm
            print("Disarming in 3 seconds...")
            time.sleep(3)
            vehicle.armed = False
            time.sleep(2)
            print("✅ Disarmed\n")
            
            vehicle.close()
            return True
    
    print("\n❌ Still didn't arm")
    print("   Something else is wrong\n")
    vehicle.close()
    return False

if __name__ == "__main__":
    quick_arm_test()
