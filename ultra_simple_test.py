#!/usr/bin/env python3
"""
Ultra Simple Command Test
Just sends FORWARD for 3 seconds to see if ANY commands work
"""

from dronekit import connect, VehicleMode
from pymavlink import mavutil
import time
import sys

def simple_test(connection_string, baud=57600):
    """Dead simple test - just send forward command"""
    
    print("="*70)
    print("  ULTRA SIMPLE COMMAND TEST")
    print("="*70)
    print("\nThis will:")
    print("  1. Connect to drone")
    print("  2. Check if armed")
    print("  3. Check if GUIDED")
    print("  4. Send FORWARD commands for 3 seconds")
    print("  5. Tell you if it works")
    print("\nMake sure drone is ARMED and HOVERING!")
    print("="*70)
    
    input("\nPress ENTER when ready...")
    
    # Connect
    print("\nConnecting...")
    vehicle = connect(connection_string, baud=baud, wait_ready=False, timeout=60)
    time.sleep(3)
    print("✓ Connected")
    
    # Check status
    print(f"\nStatus:")
    print(f"  Mode: {vehicle.mode.name}")
    print(f"  Armed: {vehicle.armed}")
    
    if not vehicle.armed:
        print("\n❌ STOP! Drone is not armed!")
        print("   Arm it first, then try again.")
        vehicle.close()
        return
    
    # Check mode
    if vehicle.mode.name != "GUIDED":
        print(f"\n⚠️  Mode is {vehicle.mode.name}, not GUIDED")
        print("   Trying to switch to GUIDED...")
        
        vehicle.mode = VehicleMode("GUIDED")
        time.sleep(2)
        
        if vehicle.mode.name != "GUIDED":
            print(f"   ❌ Still in {vehicle.mode.name}")
            print("\n   SOLUTION: Manually switch to GUIDED on laptop")
            print("   Then run this test again.")
            vehicle.close()
            return
        else:
            print("   ✓ Switched to GUIDED")
    
    # Send commands
    print("\n" + "="*70)
    print("  SENDING FORWARD COMMANDS FOR 3 SECONDS")
    print("="*70)
    print("\nWatch your drone/SITL - it should move FORWARD!")
    print("Sending commands in 3... 2... 1...")
    time.sleep(2)
    
    start_time = time.time()
    count = 0
    
    while time.time() - start_time < 3.0:
        try:
            # FORWARD command: vx = 2.0 m/s
            msg = vehicle.message_factory.set_position_target_local_ned_encode(
                0, 0, 0,
                mavutil.mavlink.MAV_FRAME_BODY_NED,
                0b0000111111000111,
                0, 0, 0,
                2.0, 0, 0,  # 2 m/s forward
                0, 0, 0,
                0, 0
            )
            vehicle.send_mavlink(msg)
            count += 1
            
            if count % 10 == 0:
                print(f"  Sent {count} commands...")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        time.sleep(0.1)  # 10Hz
    
    # Stop
    print(f"\n✓ Sent {count} commands total")
    print("\nSending STOP commands...")
    
    for _ in range(10):
        try:
            msg = vehicle.message_factory.set_position_target_local_ned_encode(
                0, 0, 0,
                mavutil.mavlink.MAV_FRAME_BODY_NED,
                0b0000111111000111,
                0, 0, 0,
                0, 0, 0,  # STOP
                0, 0, 0,
                0, 0
            )
            vehicle.send_mavlink(msg)
        except:
            pass
        time.sleep(0.1)
    
    print("✓ STOP commands sent")
    
    # Ask user
    print("\n" + "="*70)
    print("  RESULT")
    print("="*70)
    
    print("\nDid the drone move FORWARD?")
    response = input("  (y/n): ")
    
    if response.lower() == 'y':
        print("\n✅ SUCCESS! Commands are working!")
        print("\nThis means:")
        print("  ✓ Telemetry is bidirectional")
        print("  ✓ Mode is GUIDED")
        print("  ✓ Commands reach the drone")
        print("\nIf keyboard doesn't work in simulation:")
        print("  → Click on OpenCV window to give it focus")
        print("  → Make sure OpenCV window is active")
        print("  → Try pressing keys while window is focused")
    else:
        print("\n❌ Commands not working")
        print("\nChecklist:")
        print("  1. On laptop SITL console, did you see:")
        print("     'APM: Received SET_POSITION_TARGET_LOCAL_NED'?")
        print("     If NO → Telemetry is one-way (not sending commands back)")
        print("\n  2. What mode is shown on laptop?")
        print("     If not GUIDED → That's the problem")
        print("\n  3. Are there errors in SITL console?")
        print("     Check for EKF, GPS, or other errors")
    
    vehicle.close()
    print("\n✓ Test complete")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Ultra Simple Command Test')
    parser.add_argument('--connect', default='/dev/ttyUSB0')
    parser.add_argument('--baud', type=int, default=57600)
    
    args = parser.parse_args()
    
    simple_test(args.connect, args.baud)

if __name__ == "__main__":
    main()
