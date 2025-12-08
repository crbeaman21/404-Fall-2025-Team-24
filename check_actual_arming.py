#!/usr/bin/env python3
"""
Check if drone can ACTUALLY arm (not just accept command)
"""

from pymavlink import mavutil
import time

def check_actual_arming():
    print("="*70)
    print("ACTUAL ARMING VERIFICATION")
    print("="*70)
    print()
    print("We've been seeing 'ACCEPTED' but never actually arming.")
    print("Let's monitor HEARTBEAT messages to see armed status.")
    print()
    
    master = mavutil.mavlink_connection('/dev/ttyUSB0', baud=57600)
    print("Waiting for heartbeat...")
    master.wait_heartbeat()
    print(f"Connected to system {master.target_system}\n")
    
    print("="*70)
    print("CURRENT STATUS")
    print("="*70)
    
    # Get current status
    msg = master.recv_match(type='HEARTBEAT', blocking=True, timeout=5)
    if msg:
        armed = (msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED) != 0
        mode = msg.custom_mode
        
        print(f"Armed: {armed}")
        print(f"Mode: {mode}")
        print(f"System Status: {msg.system_status}")
        print()
    
    # Now let's look at SYS_STATUS for more details
    print("="*70)
    print("DETAILED SYSTEM STATUS")
    print("="*70)
    
    master.mav.request_data_stream_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_DATA_STREAM_ALL,
        1, 1
    )
    
    # Listen for a few seconds
    print("\nListening for status messages for 5 seconds...")
    print("(Looking for any error or warning messages)\n")
    
    start = time.time()
    messages_seen = []
    
    while (time.time() - start) < 5:
        msg = master.recv_match(blocking=True, timeout=1)
        
        if msg:
            msg_type = msg.get_type()
            
            # Capture interesting messages
            if msg_type == 'STATUSTEXT':
                text = msg.text
                print(f"📢 STATUSTEXT: {text}")
                messages_seen.append(('STATUSTEXT', text))
            
            elif msg_type == 'SYS_STATUS':
                # Check for sensor health issues
                onboard_control = msg.onboard_control_sensors_health
                print(f"ℹ️  Sensors Health: {bin(onboard_control)}")
            
            elif msg_type == 'HEARTBEAT':
                armed = (msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED) != 0
                if armed:
                    print(f"✅ ARMED detected in heartbeat!")
    
    print("\n" + "="*70)
    print("ANALYSIS")
    print("="*70)
    print()
    
    if not messages_seen:
        print("❌ NO STATUSTEXT messages received")
        print()
        print("This means ArduPilot is NOT telling us WHY it won't arm.")
        print()
        print("Possible reasons:")
        print("1. RC receiver issue (already confirmed - RC channels = 0)")
        print("2. Compass/gyro not calibrated")
        print("3. Accelerometer not calibrated")
        print("4. Battery voltage too low for copter")
        print("5. GPS quality not good enough for copter")
        print()
        print("SOLUTION:")
        print("You need to use Mission Planner or QGroundControl to:")
        print("- Calibrate accelerometer")
        print("- Calibrate compass")
        print("- Check 'Messages' tab to see pre-arm errors")
        print()
    
    print("="*70)
    print("MANUAL TEST INSTRUCTIONS")
    print("="*70)
    print()
    print("Let's verify MAVProxy can ACTUALLY arm (not just accept):")
    print()
    print("1. Close this script")
    print("2. Run: mavproxy.py --master=/dev/ttyUSB0 --baudrate=57600")
    print("3. Wait for connection")
    print("4. Type: mode GUIDED")
    print("5. Type: arm throttle")
    print("6. Look for 'ARMED' in the output (not just 'ACCEPTED')")
    print("7. Check if you hear motor beeps or see LED change")
    print()
    print("If MAVProxy also shows 'ACCEPTED' but never arms,")
    print("then this is NOT a Python issue - it's a")
    print("calibration/configuration issue with the drone.")
    print()
    
    master.close()

if __name__ == "__main__":
    check_actual_arming()
