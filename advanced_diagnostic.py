#!/usr/bin/env python3
"""
ElevateXY Advanced Manual Control Diagnostic
Deep dive into why commands aren't working
"""

import time
from dronekit import connect, VehicleMode, LocationGlobalRelative
from pymavlink import mavutil
import sys

def advanced_diagnostic(connection_string, baud=57600):
    """Comprehensive diagnostic for manual control issues"""
    
    print("="*70)
    print("  ELEVATEXY ADVANCED DIAGNOSTIC")
    print("="*70)
    
    # Connect
    print(f"\nConnecting to: {connection_string}")
    if connection_string.startswith('/dev/'):
        vehicle = connect(connection_string, baud=baud, wait_ready=False, timeout=60)
    else:
        vehicle = connect(connection_string, wait_ready=False, timeout=60)
    
    print("✓ Connected!")
    time.sleep(3)
    
    # ========================================
    # TEST 1: Basic Status
    # ========================================
    print("\n" + "="*70)
    print("  TEST 1: BASIC STATUS CHECK")
    print("="*70)
    
    print(f"Mode: {vehicle.mode.name}")
    print(f"Armed: {vehicle.armed}")
    print(f"System Status: {vehicle.system_status.state}")
    print(f"Battery: {vehicle.battery.voltage:.1f}V")
    
    if hasattr(vehicle, 'location'):
        alt = vehicle.location.global_relative_frame.alt
        print(f"Altitude: {alt:.1f}m")
        
        if alt > 0.5:
            print("✓ Drone is airborne")
        else:
            print("⚠️  Drone is on ground")
    
    if not vehicle.armed:
        print("\n❌ PROBLEM: Drone is not armed!")
        print("   Commands require armed state.")
        vehicle.close()
        return
    
    # ========================================
    # TEST 2: Mode Check
    # ========================================
    print("\n" + "="*70)
    print("  TEST 2: FLIGHT MODE CHECK")
    print("="*70)
    
    print(f"Current mode: {vehicle.mode.name}")
    
    if vehicle.mode.name != "GUIDED":
        print("❌ PROBLEM: Not in GUIDED mode!")
        print("   Velocity commands REQUIRE GUIDED mode.")
        print("\nAttempting to switch to GUIDED...")
        
        vehicle.mode = VehicleMode("GUIDED")
        
        # Wait for mode change
        timeout = 10
        start = time.time()
        while vehicle.mode.name != "GUIDED" and time.time() - start < timeout:
            print(f"  Waiting... Mode: {vehicle.mode.name}")
            time.sleep(0.5)
        
        if vehicle.mode.name == "GUIDED":
            print("✓ Successfully switched to GUIDED")
        else:
            print(f"❌ FAILED to switch to GUIDED (still in {vehicle.mode.name})")
            print("\nPossible causes:")
            print("  1. RC transmitter overriding mode")
            print("  2. GUIDED mode not available in parameters")
            print("  3. Pre-arm checks preventing mode change")
            print("\nManually switch to GUIDED on laptop, then retry.")
            vehicle.close()
            return
    else:
        print("✓ Mode is GUIDED")
    
    # ========================================
    # TEST 3: MAVLink Message Test
    # ========================================
    print("\n" + "="*70)
    print("  TEST 3: MAVLINK MESSAGE SEND TEST")
    print("="*70)
    
    print("Sending SET_POSITION_TARGET_LOCAL_NED messages...")
    print("Watch your SITL console for 'Received SET_POSITION_TARGET' messages\n")
    
    # Send a few test messages
    for i in range(5):
        try:
            msg = vehicle.message_factory.set_position_target_local_ned_encode(
                0, 0, 0,
                mavutil.mavlink.MAV_FRAME_BODY_NED,
                0b0000111111000111,
                0, 0, 0,
                1.0, 0, 0,  # 1 m/s forward
                0, 0, 0,
                0, 0
            )
            vehicle.send_mavlink(msg)
            print(f"  Message {i+1} sent")
            time.sleep(0.2)
        except Exception as e:
            print(f"  ❌ Error sending message: {e}")
    
    print("\n✓ Messages sent successfully")
    print("\nDid you see 'Received SET_POSITION_TARGET' in SITL console?")
    response = input("  (y/n): ")
    
    if response.lower() != 'y':
        print("\n❌ PROBLEM: Messages not reaching SITL!")
        print("   This means telemetry is ONE-WAY (receiving only)")
        print("\nPossible causes:")
        print("  1. Telemetry radio not configured for bidirectional")
        print("  2. Baud rate mismatch")
        print("  3. Telemetry radio in wrong mode")
        print("\nCheck telemetry radio configuration on both ends.")
        vehicle.close()
        return
    
    print("✓ Messages reaching SITL")
    
    # ========================================
    # TEST 4: Sustained Velocity Command
    # ========================================
    print("\n" + "="*70)
    print("  TEST 4: SUSTAINED VELOCITY COMMAND")
    print("="*70)
    
    print("Sending FORWARD command for 3 seconds...")
    print("Watch your SITL - drone should move forward!\n")
    
    input("Press ENTER to start 3-second forward test...")
    
    start_time = time.time()
    command_count = 0
    
    while time.time() - start_time < 3.0:
        try:
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
            command_count += 1
        except Exception as e:
            print(f"Error: {e}")
        
        time.sleep(0.1)  # 10Hz
    
    # Stop
    print(f"\n✓ Sent {command_count} commands over 3 seconds")
    print("Sending STOP command...")
    
    for _ in range(10):
        try:
            msg = vehicle.message_factory.set_position_target_local_ned_encode(
                0, 0, 0,
                mavutil.mavlink.MAV_FRAME_BODY_NED,
                0b0000111111000111,
                0, 0, 0,
                0, 0, 0,  # Stop
                0, 0, 0,
                0, 0
            )
            vehicle.send_mavlink(msg)
        except:
            pass
        time.sleep(0.1)
    
    print("\nDid the drone move forward?")
    response = input("  (y/n): ")
    
    if response.lower() != 'y':
        print("\n❌ PROBLEM: Commands sent but drone didn't move!")
        print("\nDebugging steps:")
        print("  1. Check SITL console for errors")
        print("  2. Verify EKF is OK (EKF errors prevent movement)")
        print("  3. Check if GPS is locked")
        print("  4. Verify no RC override")
        print("  5. Check for geofence restrictions")
    else:
        print("\n✓ SUCCESS! Drone moved!")
        print("   Commands are working correctly.")
        print("\nIf commands work here but not in your simulation:")
        print("  1. Check key detection (OpenCV window focus)")
        print("  2. Verify continuous command sending in simulation")
        print("  3. Check mode stays GUIDED during flight")
    
    # ========================================
    # TEST 5: RC Override Check
    # ========================================
    print("\n" + "="*70)
    print("  TEST 5: RC OVERRIDE CHECK")
    print("="*70)
    
    if hasattr(vehicle, 'channels'):
        print("RC Channels:")
        for i in range(1, 9):
            try:
                ch = vehicle.channels[str(i)]
                print(f"  CH{i}: {ch}")
                
                if i <= 4 and ch != 0 and abs(ch - 1500) > 100:
                    print(f"    ⚠️  CH{i} has significant input!")
            except:
                pass
        
        print("\nIf RC channels show activity, your RC transmitter might be")
        print("interfering with GUIDED mode commands.")
    else:
        print("RC channel data not available")
    
    # ========================================
    # TEST 6: Parameter Check
    # ========================================
    print("\n" + "="*70)
    print("  TEST 6: PARAMETER CHECK")
    print("="*70)
    
    important_params = [
        'GUID_TIMEOUT',
        'FS_GCS_ENABLE',
        'RC_OVERRIDE_TIME',
    ]
    
    print("Checking relevant parameters...")
    for param in important_params:
        try:
            value = vehicle.parameters.get(param, None)
            if value is not None:
                print(f"  {param}: {value}")
        except:
            pass
    
    # ========================================
    # SUMMARY
    # ========================================
    print("\n" + "="*70)
    print("  DIAGNOSTIC SUMMARY")
    print("="*70)
    
    print("\n✓ Completed:")
    print("  1. Basic status check")
    print("  2. Mode verification")
    print("  3. MAVLink message send test")
    print("  4. Sustained velocity command test")
    print("  5. RC override check")
    print("  6. Parameter check")
    
    print("\nNext steps:")
    print("  - If test 4 worked: Your setup is fine, issue is in simulation code")
    print("  - If test 4 failed: Check SITL console for specific error messages")
    print("  - If messages not reaching SITL: Check telemetry configuration")
    
    vehicle.close()
    print("\n✓ Connection closed")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='ElevateXY Advanced Diagnostic')
    parser.add_argument('--connect', required=True, help='Connection string')
    parser.add_argument('--baud', type=int, default=57600, help='Baud rate')
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("  IMPORTANT: Run this while drone is ARMED and AIRBORNE")
    print("="*70)
    print("\nThis diagnostic will:")
    print("  - Check your connection")
    print("  - Verify GUIDED mode")
    print("  - Send test velocity commands")
    print("  - Tell you exactly what's wrong")
    print("\nMake sure your drone is:")
    print("  ✓ Armed")
    print("  ✓ Hovering (taken off)")
    print("  ✓ Safe to move around")
    
    response = input("\nReady to proceed? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled")
        sys.exit(0)
    
    advanced_diagnostic(args.connect, args.baud)

if __name__ == "__main__":
    main()
