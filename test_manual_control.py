#!/usr/bin/env python3
"""
ElevateXY Manual Control Diagnostic
Test if commands are reaching the drone
"""

import time
from dronekit import connect, VehicleMode
from pymavlink import mavutil

def test_manual_commands(connection_string, baud=57600):
    """Test sending velocity commands"""
    
    print("="*70)
    print("  ELEVATEXY MANUAL CONTROL DIAGNOSTIC")
    print("="*70)
    
    # Connect
    print(f"\nConnecting to: {connection_string}")
    if connection_string.startswith('/dev/'):
        vehicle = connect(connection_string, baud=baud, wait_ready=False, timeout=60)
    else:
        vehicle = connect(connection_string, wait_ready=False, timeout=60)
    
    print("✓ Connected!")
    time.sleep(3)
    
    # Check status
    print("\n" + "-"*70)
    print("  INITIAL STATUS")
    print("-"*70)
    print(f"Mode: {vehicle.mode.name}")
    print(f"Armed: {vehicle.armed}")
    print(f"Battery: {vehicle.battery.voltage:.1f}V")
    
    # Check if armed
    if not vehicle.armed:
        print("\n⚠️  Drone is not armed!")
        print("   Commands will not work until armed.")
        response = input("\nContinue anyway? (y/n): ")
        if response.lower() != 'y':
            vehicle.close()
            return
    
    # Check mode
    print(f"\nCurrent mode: {vehicle.mode.name}")
    
    if vehicle.mode.name != "GUIDED":
        print("⚠️  Drone is not in GUIDED mode!")
        print("   Velocity commands require GUIDED mode.")
        
        response = input("\nSwitch to GUIDED mode? (y/n): ")
        if response.lower() == 'y':
            print("Switching to GUIDED...")
            vehicle.mode = VehicleMode("GUIDED")
            time.sleep(2)
            
            if vehicle.mode.name == "GUIDED":
                print("✓ Now in GUIDED mode")
            else:
                print(f"❌ Still in {vehicle.mode.name} mode")
                print("   Commands may not work!")
    
    # Test commands
    print("\n" + "="*70)
    print("  TESTING VELOCITY COMMANDS")
    print("="*70)
    
    if not vehicle.armed:
        print("\n❌ Cannot test - drone not armed")
        vehicle.close()
        return
    
    tests = [
        ("FORWARD (vx=2)", 2, 0, 0),
        ("BACKWARD (vx=-2)", -2, 0, 0),
        ("LEFT (vy=-2)", 0, -2, 0),
        ("RIGHT (vy=2)", 0, 2, 0),
        ("UP (vz=-0.5)", 0, 0, -0.5),
        ("DOWN (vz=0.5)", 0, 0, 0.5),
        ("STOP", 0, 0, 0),
    ]
    
    print("\nEach command will be sent for 2 seconds.")
    print("Watch your SITL/drone to see if it responds.\n")
    
    for test_name, vx, vy, vz in tests:
        print(f"Testing: {test_name}")
        
        # Send command repeatedly for 2 seconds
        start_time = time.time()
        while time.time() - start_time < 2.0:
            try:
                msg = vehicle.message_factory.set_position_target_local_ned_encode(
                    0, 0, 0,
                    mavutil.mavlink.MAV_FRAME_BODY_NED,
                    0b0000111111000111,  # Use velocity
                    0, 0, 0,  # Position (not used)
                    vx, vy, vz,  # Velocity
                    0, 0, 0,  # Acceleration (not used)
                    0, 0  # Yaw, yaw_rate
                )
                vehicle.send_mavlink(msg)
                
                # Check if command was sent
                print(f"  Sent: vx={vx}, vy={vy}, vz={vz}")
                
            except Exception as e:
                print(f"  ❌ Error sending: {e}")
            
            time.sleep(0.1)  # Send at 10Hz
        
        print(f"  ✓ {test_name} test complete\n")
        time.sleep(0.5)
    
    # Final stop
    print("Sending final STOP command...")
    for _ in range(10):
        try:
            msg = vehicle.message_factory.set_position_target_local_ned_encode(
                0, 0, 0,
                mavutil.mavlink.MAV_FRAME_BODY_NED,
                0b0000111111000111,
                0, 0, 0,
                0, 0, 0,  # All zeros = stop
                0, 0, 0,
                0, 0
            )
            vehicle.send_mavlink(msg)
        except:
            pass
        time.sleep(0.1)
    
    print("✓ All tests complete")
    
    # Summary
    print("\n" + "="*70)
    print("  DIAGNOSTIC SUMMARY")
    print("="*70)
    print("\nIf your drone/SITL did NOT move:")
    print("  1. Check that drone is ARMED")
    print("  2. Check that mode is GUIDED")
    print("  3. Check ArduCopter console for errors")
    print("  4. Verify telemetry connection is bidirectional")
    print("\nIf drone moved correctly:")
    print("  ✓ Commands are working!")
    print("  ✓ Issue might be with key detection in simulation")
    
    vehicle.close()
    print("\n✓ Connection closed")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='ElevateXY Manual Control Test')
    parser.add_argument('--connect', required=True, help='Connection string')
    parser.add_argument('--baud', type=int, default=57600, help='Baud rate')
    
    args = parser.parse_args()
    
    test_manual_commands(args.connect, args.baud)

if __name__ == "__main__":
    main()
