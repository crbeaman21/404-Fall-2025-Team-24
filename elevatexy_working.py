#!/usr/bin/env python3
"""
ElevateXY - Final Working Manual Control
Uses FORCE ARM to bypass throttle check
"""

import time
from dronekit import connect, VehicleMode
from pymavlink import mavutil

class ElevateXYFinal:
    def __init__(self):
        self.vehicle = None
        self.speed = 2.0
        
    def connect(self):
        """Connect to drone"""
        print("🔌 Connecting...")
        self.vehicle = connect('/dev/ttyUSB0', baud=57600, wait_ready=False, timeout=30)
        
        print("⏳ Waiting for telemetry...")
        self.vehicle.wait_ready('mode', 'armed', timeout=10)
        
        print("✅ Connected!")
        print(f"   Mode: {self.vehicle.mode.name}")
        print(f"   GPS: {self.vehicle.gps_0.satellites_visible} sats")
        print(f"   Battery: {self.vehicle.battery.voltage:.1f}V\n")
        return True
    
    def arm_and_takeoff(self, altitude=2.0):
        """Arm with FORCE and takeoff"""
        print("⚠️  SAFETY CHECK")
        print("-" * 50)
        print("   - Propellers attached?")
        print("   - Area clear?")
        print("   - Ready to fly?")
        print()
        
        response = input("Continue? (yes/no): ").strip().lower()
        if response != 'yes':
            print("Cancelled\n")
            return False
        
        # Set GUIDED
        print("\n📍 Setting GUIDED mode...")
        self.vehicle.mode = VehicleMode("GUIDED")
        time.sleep(3)
        
        # ARM with FORCE parameter
        print("🔧 Arming (using force parameter)...")
        
        msg = self.vehicle.message_factory.command_long_encode(
            self.vehicle._master.target_system,
            self.vehicle._master.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,      # confirmation
            1,      # param1: 1=arm
            21196,  # param2: 21196=force (bypass throttle check)
            0, 0, 0, 0, 0
        )
        self.vehicle.send_mavlink(msg)
        self.vehicle.flush()
        
        # Wait for arm
        for i in range(10):
            time.sleep(1)
            if self.vehicle.armed:
                print("✅ ARMED!\n")
                break
            print(f"   Waiting... {i+1}s")
        
        if not self.vehicle.armed:
            print("❌ Failed to arm\n")
            return False
        
        # Takeoff
        print(f"🚁 Taking off to {altitude}m...")
        self.vehicle.simple_takeoff(altitude)
        
        while True:
            alt = self.vehicle.location.global_relative_frame.alt
            print(f"   Altitude: {alt:.1f}m / {altitude}m")
            
            if alt >= altitude * 0.95:
                print("✅ Target altitude reached!\n")
                break
            
            time.sleep(1)
        
        return True
    
    def set_velocity(self, vx, vy, vz):
        """Send velocity command"""
        msg = self.vehicle.message_factory.set_position_target_local_ned_encode(
            0, 0, 0,
            mavutil.mavlink.MAV_FRAME_BODY_NED,
            0b0000111111000111,
            0, 0, 0, vx, vy, vz, 0, 0, 0, 0, 0
        )
        self.vehicle.send_mavlink(msg)
    
    def move(self, direction, duration=2):
        """Move in direction"""
        moves = {
            'w': (self.speed, 0, 0, "Forward"),
            's': (-self.speed, 0, 0, "Backward"),
            'a': (0, -self.speed, 0, "Left"),
            'd': (0, self.speed, 0, "Right"),
            'q': (0, 0, -0.5, "Up"),
            'e': (0, 0, 0.5, "Down")
        }
        
        if direction in moves:
            vx, vy, vz, desc = moves[direction]
            print(f"{desc} {duration}s... ", end='', flush=True)
            self.set_velocity(vx, vy, vz)
            time.sleep(duration)
            self.set_velocity(0, 0, 0)
            print("Done")
    
    def land(self):
        """Land"""
        print("\n🛬 Landing...")
        self.vehicle.mode = VehicleMode("LAND")
        
        while self.vehicle.armed:
            alt = self.vehicle.location.global_relative_frame.alt
            print(f"   Altitude: {alt:.1f}m")
            time.sleep(1)
        
        print("✅ Landed\n")
    
    def status(self):
        """Show status"""
        print("\n" + "="*50)
        print(f"Mode:     {self.vehicle.mode.name}")
        print(f"Armed:    {self.vehicle.armed}")
        print(f"Altitude: {self.vehicle.location.global_relative_frame.alt:.1f}m")
        print(f"Battery:  {self.vehicle.battery.voltage:.1f}V")
        print("="*50 + "\n")
    
    def run(self):
        """Interactive control"""
        print("="*60)
        print("ELEVATEXY MANUAL CONTROL")
        print("="*60)
        print("\nCommands:")
        print("  arm     - Arm and takeoff to 2m")
        print("  w/s/a/d - Move")
        print("  q/e     - Up/Down")
        print("  land    - Land")
        print("  status  - Show status")
        print("  quit    - Exit")
        print("="*60 + "\n")
        
        try:
            while True:
                cmd = input("ElevateXY> ").strip().lower()
                
                if cmd in ['quit', 'exit']:
                    if self.vehicle.armed:
                        print("Landing first...")
                        self.land()
                    break
                
                elif cmd == 'arm':
                    self.arm_and_takeoff(2.0)
                
                elif cmd in ['w', 's', 'a', 'd', 'q', 'e']:
                    self.move(cmd)
                
                elif cmd == 'land':
                    self.land()
                
                elif cmd == 'status':
                    self.status()
                
                elif cmd == '':
                    continue
                
                else:
                    print(f"Unknown: {cmd}")
        
        except KeyboardInterrupt:
            print("\n\nInterrupted!")
            if self.vehicle.armed:
                self.land()
        
        finally:
            self.vehicle.close()
            print("Closed\n")

def main():
    print("\n🚁 ElevateXY - Working Manual Control")
    print("   (Uses force arm to bypass throttle check)\n")
    
    drone = ElevateXYFinal()
    
    if drone.connect():
        drone.run()

if __name__ == "__main__":
    main()
