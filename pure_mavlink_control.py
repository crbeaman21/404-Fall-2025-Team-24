#!/usr/bin/env python3
"""
ElevateXY - Pure Python Solution
Uses pymavlink directly like MAVProxy does
No DroneKit - just raw MAVLink
"""

import time
from pymavlink import mavutil

class PureMAVLinkControl:
    def __init__(self, connection_string='/dev/ttyUSB0', baud=57600):
        self.connection_string = connection_string
        self.baud = baud
        self.master = None
        self.armed = False
        self.mode = "UNKNOWN"
        
    def connect(self):
        """Connect using pymavlink (like MAVProxy does)"""
        print("🔌 Connecting with pymavlink...")
        print(f"   Device: {self.connection_string}")
        print(f"   Baud: {self.baud}")
        
        # This is EXACTLY what MAVProxy does
        self.master = mavutil.mavlink_connection(
            self.connection_string,
            baud=self.baud,
            source_system=255  # GCS system ID
        )
        
        # Wait for heartbeat
        print("⏳ Waiting for heartbeat...")
        self.master.wait_heartbeat()
        
        print("✅ Connected!")
        print(f"   System ID: {self.master.target_system}")
        print(f"   Component ID: {self.master.target_component}")
        
        # Request data streams
        self.master.mav.request_data_stream_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_DATA_STREAM_ALL,
            4,  # Rate in Hz
            1   # Start
        )
        
        time.sleep(2)
        return True
    
    def set_mode(self, mode_name):
        """Set flight mode"""
        mode_mapping = self.master.mode_mapping()
        
        if mode_name not in mode_mapping:
            print(f"❌ Unknown mode: {mode_name}")
            return False
        
        mode_id = mode_mapping[mode_name]
        
        print(f"📍 Setting mode to {mode_name}...")
        
        self.master.mav.set_mode_send(
            self.master.target_system,
            mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
            mode_id
        )
        
        time.sleep(1)
        return True
    
    def arm(self):
        """Arm the drone - EXACTLY like MAVProxy"""
        print("\n🔧 Arming (MAVProxy method)...")
        
        # This is the EXACT command MAVProxy uses
        self.master.arducopter_arm()
        
        # Wait for response
        print("⏳ Waiting for arm confirmation...")
        
        start = time.time()
        while (time.time() - start) < 10:
            msg = self.master.recv_match(type='COMMAND_ACK', blocking=True, timeout=1)
            
            if msg and msg.command == mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM:
                result = msg.result
                
                if result == mavutil.mavlink.MAV_RESULT_ACCEPTED:
                    print("✅ ARM COMMAND ACCEPTED!")
                    
                    # Wait to actually become armed
                    for i in range(5):
                        time.sleep(1)
                        
                        # Check heartbeat for armed status
                        hb = self.master.recv_match(type='HEARTBEAT', blocking=True, timeout=1)
                        if hb:
                            self.armed = (hb.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED) != 0
                            print(f"   {i+1}s: Armed = {self.armed}")
                            
                            if self.armed:
                                print("\n🎉 MOTORS ARMED!")
                                return True
                    
                    print("\n⚠️  Command accepted but not armed yet")
                    return False
                else:
                    print(f"❌ Arm rejected: {result}")
                    return False
        
        print("❌ No response to arm command")
        return False
    
    def takeoff(self, altitude=2.0):
        """Takeoff to altitude"""
        if not self.armed:
            print("⚠️  Not armed - cannot takeoff")
            return False
        
        print(f"\n🚁 Taking off to {altitude}m...")
        
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
            0,  # confirmation
            0, 0, 0, 0, 0, 0,  # params 1-6
            altitude  # param 7: altitude
        )
        
        # Monitor altitude
        print("⏳ Climbing...")
        while True:
            msg = self.master.recv_match(type='GLOBAL_POSITION_INT', blocking=True, timeout=2)
            
            if msg:
                current_alt = msg.relative_alt / 1000.0  # mm to meters
                print(f"   Altitude: {current_alt:.1f}m / {altitude}m")
                
                if current_alt >= altitude * 0.95:
                    print("✅ Target altitude reached!")
                    return True
            
            time.sleep(0.5)
    
    def set_velocity(self, vx, vy, vz):
        """Set velocity in body frame"""
        if not self.armed:
            return
        
        self.master.mav.set_position_target_local_ned_send(
            0,  # time_boot_ms
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_FRAME_BODY_NED,
            0b0000111111000111,  # type_mask (velocity only)
            0, 0, 0,  # position
            vx, vy, vz,  # velocity
            0, 0, 0,  # acceleration
            0, 0  # yaw, yaw_rate
        )
    
    def land(self):
        """Land"""
        print("\n🛬 Landing...")
        
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_NAV_LAND,
            0,  # confirmation
            0, 0, 0, 0, 0, 0, 0
        )
        
        # Monitor until disarmed
        while self.armed:
            msg = self.master.recv_match(type='HEARTBEAT', blocking=True, timeout=1)
            if msg:
                self.armed = (msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED) != 0
                
                if not self.armed:
                    print("✅ Landed and disarmed")
                    return
            
            time.sleep(0.5)
    
    def run_interactive(self):
        """Interactive control"""
        print("\n" + "="*60)
        print("ELEVATEXY - Pure MAVLink Control")
        print("="*60)
        print("\nCommands:")
        print("  guided   - Set GUIDED mode")
        print("  arm      - Arm motors")
        print("  takeoff  - Takeoff to 2m")
        print("  w/s/a/d  - Move (forward/back/left/right)")
        print("  land     - Land")
        print("  quit     - Exit")
        print("="*60 + "\n")
        
        speed = 2.0
        
        try:
            while True:
                cmd = input("MAVLink> ").strip().lower()
                
                if cmd in ['quit', 'exit']:
                    if self.armed:
                        self.land()
                    break
                
                elif cmd == 'guided':
                    self.set_mode('GUIDED')
                
                elif cmd == 'arm':
                    self.set_mode('GUIDED')
                    time.sleep(2)
                    if self.arm():
                        print("\n✅ Ready to fly!")
                
                elif cmd == 'takeoff':
                    self.takeoff(2.0)
                
                elif cmd == 'w':
                    print("Forward...")
                    self.set_velocity(speed, 0, 0)
                    time.sleep(2)
                    self.set_velocity(0, 0, 0)
                
                elif cmd == 's':
                    print("Backward...")
                    self.set_velocity(-speed, 0, 0)
                    time.sleep(2)
                    self.set_velocity(0, 0, 0)
                
                elif cmd == 'a':
                    print("Left...")
                    self.set_velocity(0, -speed, 0)
                    time.sleep(2)
                    self.set_velocity(0, 0, 0)
                
                elif cmd == 'd':
                    print("Right...")
                    self.set_velocity(0, speed, 0)
                    time.sleep(2)
                    self.set_velocity(0, 0, 0)
                
                elif cmd == 'land':
                    self.land()
                
                elif cmd == '':
                    continue
                
                else:
                    print(f"Unknown: {cmd}")
        
        except KeyboardInterrupt:
            print("\n\nInterrupted!")
            if self.armed:
                self.land()
        
        finally:
            if self.master:
                self.master.close()
                print("✅ Connection closed")

def main():
    print("\n🚁 ElevateXY - Pure MAVLink Control")
    print("   Uses pymavlink directly (like MAVProxy)")
    print()
    
    drone = PureMAVLinkControl()
    
    if drone.connect():
        drone.run_interactive()

if __name__ == "__main__":
    main()
