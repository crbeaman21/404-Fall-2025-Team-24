#!/usr/bin/env python3
"""
ElevateXY - Message Capture
Captures STATUSTEXT messages showing WHY arming fails
"""

import time
from dronekit import connect, VehicleMode
from pymavlink import mavutil

def capture_prearm_messages():
    print("="*70)
    print("PREARM MESSAGE CAPTURE")
    print("="*70)
    print("\nThis will show the ACTUAL error messages from ArduPilot\n")
    
    # Connect
    print("🔌 Connecting...")
    vehicle = connect('/dev/ttyUSB0', baud=57600, wait_ready=False, timeout=30)
    
    print("⏳ Waiting for telemetry...")
    vehicle.wait_ready('mode', 'armed', timeout=10)
    
    print("✅ Connected\n")
    
    # Set up message capture
    print("📡 Setting up message listener...")
    print("   Will capture all STATUSTEXT messages\n")
    
    all_messages = []
    prearm_messages = []
    
    # Create a more aggressive message listener
    def message_listener(self, name, msg):
        timestamp = time.strftime("%H:%M:%S")
        
        if name == 'STATUSTEXT':
            text = msg.text
            all_messages.append(f"[{timestamp}] {text}")
            print(f"📢 [{timestamp}] {text}")
            
            if 'PreArm' in text or 'Arm' in text or 'armed' in text:
                prearm_messages.append(text)
        
        elif name == 'COMMAND_ACK':
            result_map = {
                0: "ACCEPTED ✅",
                1: "TEMPORARILY_REJECTED",
                2: "DENIED",
                3: "UNSUPPORTED",
                4: "FAILED",
                5: "IN_PROGRESS"
            }
            result = result_map.get(msg.result, f"UNKNOWN({msg.result})")
            
            if msg.command == mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM:
                ack_msg = f"ARM Command Result: {result}"
                all_messages.append(f"[{timestamp}] {ack_msg}")
                print(f"🔔 [{timestamp}] {ack_msg}")
    
    # Add listener
    vehicle.add_message_listener('STATUSTEXT', message_listener)
    vehicle.add_message_listener('COMMAND_ACK', message_listener)
    
    print("✅ Listener active\n")
    
    # Set GUIDED mode
    print("📍 Setting GUIDED mode...")
    vehicle.mode = VehicleMode("GUIDED")
    
    print("   Waiting 5 seconds for mode change and messages...")
    time.sleep(5)
    
    print(f"   Current mode: {vehicle.mode.name}\n")
    
    # Now try to arm and watch messages
    print("="*70)
    print("ARMING ATTEMPT")
    print("="*70)
    print("\n🔧 Sending arm command...\n")
    
    # Try using direct MAVLink command (like MAVProxy does)
    msg = vehicle.message_factory.command_long_encode(
        vehicle._master.target_system,
        vehicle._master.target_component,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        0,  # confirmation
        1,  # param1: 1=arm, 0=disarm
        0,  # param2: 0=normal arm, 21196=force arm
        0, 0, 0, 0, 0  # unused params
    )
    vehicle.send_mavlink(msg)
    vehicle.flush()
    
    print("Command sent. Listening for 15 seconds...\n")
    
    # Wait and listen
    start = time.time()
    while (time.time() - start) < 15:
        elapsed = int(time.time() - start)
        
        if vehicle.armed:
            print(f"\n✅ ARMED at {elapsed} seconds!")
            break
        
        # Print status every 2 seconds
        if elapsed % 2 == 0 and elapsed > 0:
            print(f"   {elapsed}s: Armed={vehicle.armed}, Mode={vehicle.mode.name}")
        
        time.sleep(0.5)
    
    print("\n" + "="*70)
    print("RESULTS")
    print("="*70)
    
    if vehicle.armed:
        print("\n✅ SUCCESS! Drone armed!")
        print("\nDisarming...")
        vehicle.armed = False
        time.sleep(2)
    else:
        print("\n❌ Failed to arm")
    
    print("\n📋 PreArm/Arm Messages Captured:")
    print("-" * 70)
    if prearm_messages:
        for msg in prearm_messages:
            print(f"  • {msg}")
    else:
        print("  (No PreArm messages captured)")
    
    print("\n📋 All Messages Captured:")
    print("-" * 70)
    if all_messages:
        for msg in all_messages[-20:]:  # Show last 20
            print(f"  {msg}")
    else:
        print("  (No messages captured)")
    
    print("\n💡 Analysis:")
    print("-" * 70)
    
    if not prearm_messages and not all_messages:
        print("❌ PROBLEM: No messages captured at all!")
        print("   This means:")
        print("   1. The message listener isn't working correctly")
        print("   2. OR ArduPilot isn't sending STATUSTEXT messages")
        print("   3. OR there's a communication timing issue")
        print()
        print("   Solution: We need to use MAVProxy's message system")
        print("   Run this instead:")
        print("   mavproxy.py --master=/dev/ttyUSB0 --baudrate=57600")
        print("   Then type: arm throttle")
        print("   You'll see the exact error there")
    
    elif prearm_messages:
        print("✅ Found PreArm messages (see above)")
        print("   These tell you exactly what's wrong")
    
    else:
        print("⚠️  Got messages but no PreArm errors")
        print("   This is unusual - the arm command might not be reaching ArduPilot")
    
    vehicle.close()
    print("\n" + "="*70)

if __name__ == "__main__":
    capture_prearm_messages()
