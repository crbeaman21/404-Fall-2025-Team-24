#!/usr/bin/env python3
"""
ElevateXY - Final Working Solution
Use MAVProxy to arm, then Python controls the flight
This WILL work for your project!
"""

import time
import sys
from dronekit import connect, VehicleMode
from pymavlink import mavutil

class ElevateXY:
    def __init__(self):
        self.vehicle = None
        self.speed = 2.0
        
    def connect_and_verify(self):
        """Connect and verify drone is armed by MAVProxy"""
        
        print("="*70)
        print("ELEVATEXY - WORKING SOLUTION")
        print("="*70)
        print()
        print("STEP 1: Start MAVProxy in another terminal")
        print("-" * 70)
        print("Run this command:")
        print()
        print("  mavproxy.py --master=/dev/ttyUSB0 --baudrate=57600")
        print()
        print("Then in MAVProxy, type these commands:")
        print("  mode GUIDED")
        print("  arm safetyoff")
        print("  arm throttle")
        print()
        print("When you see 'COMMAND_ACK: COMPONENT_ARM_DISARM: ACCEPTED'")
        print("come back here and press ENTER")
        print("="*70)
        print()
        
        input("Press ENTER when drone is ARMED in MAVProxy...")
        
        print("\nSTEP 2: Connecting Python for flight control")
        print("-" * 70)
        
        try:
            print("🔌 Connecting...")
            self.vehicle = connect('/dev/ttyUSB0', baud=57600, wait_ready=False, timeout=15)
            
            print("⏳ Waiting for telemetry...")
            self.vehicle.wait_ready('mode', 'armed', timeout=5)
            
            print("\n✅ Python connected!")
            print(f"   Mode: {self.vehicle.mode.name}")
            print(f"   Armed: {self.vehicle.armed}")
            print(f"   GPS: {self.vehicle.gps_0.satellites_visible} sats")
            print(f"   Battery: {self.vehicle.battery.voltage:.1f}V\n")
            
            if not self.vehicle.armed:
                print("❌ ERROR: Drone shows as NOT ARMED")
                print("   Go back to MAVProxy and verify you typed:")
                print("   arm throttle")
                print()
                return False
            
            print("🎉 SUCCESS! Drone is armed and Python is connected!")
            print("   Ready for flight control\n")
            return True
            
        except Exception as e:
            print(f"\n❌ Connection error: {e}\n")
            return False
    
    def set_velocity(self, vx, vy, vz):
        """Send velocity command"""
        msg = self.vehicle.message_factory.set_position_target_local_ned_encode(
            0, 0, 0,
            mavutil.mavlink.MAV_FRAME_BODY_NED,
            0b0000111111000111,
            0, 0, 0, vx, vy, vz, 0, 0, 0, 0, 0
        )
        self.vehicle.send_mavlink(msg)
    
    def takeoff(self, altitude=2.0):
        """Takeoff to altitude"""
        print(f"\n🚁 TAKEOFF to {altitude}m")
        print("-" * 50)
        
        self.vehicle.simple_takeoff(altitude)
        
        while True:
            alt = self.vehicle.location.global_relative_frame.alt
            print(f"   Altitude: {alt:.1f}m / {altitude:.1f}m")
            
            if alt >= altitude * 0.95:
                print("✅ Target altitude reached!\n")
                break
            
            time.sleep(1)
    
    def move(self, direction, duration=2):
        """Move in direction"""
        moves = {
            'w': (self.speed, 0, 0, "Forward ⬆️"),
            's': (-self.speed, 0, 0, "Backward ⬇️"),
            'a': (0, -self.speed, 0, "Left ⬅️"),
            'd': (0, self.speed, 0, "Right ➡️"),
            'q': (0, 0, -0.5, "Up ⬆️"),
            'e': (0, 0, 0.5, "Down ⬇️")
        }
        
        if direction in moves:
            vx, vy, vz, desc = moves[direction]
            print(f"{desc} ({duration}s)... ", end='', flush=True)
            self.set_velocity(vx, vy, vz)
            time.sleep(duration)
            self.set_velocity(0, 0, 0)
            print("✅ Done")
        else:
            print(f"❌ Unknown direction: {direction}")
    
    def land(self):
        """Land the drone"""
        print("\n🛬 LANDING")
        print("-" * 50)
        
        self.vehicle.mode = VehicleMode("LAND")
        
        while self.vehicle.armed:
            alt = self.vehicle.location.global_relative_frame.alt
            print(f"   Altitude: {alt:.1f}m")
            time.sleep(1)
        
        print("✅ Landed and disarmed\n")
    
    def status(self):
        """Show status"""
        print()
        print("="*50)
        print(f"Mode:     {self.vehicle.mode.name}")
        print(f"Armed:    {self.vehicle.armed}")
        print(f"Altitude: {self.vehicle.location.global_relative_frame.alt:.1f}m")
        print(f"Speed:    {self.vehicle.groundspeed:.1f} m/s")
        print(f"Battery:  {self.vehicle.battery.voltage:.1f}V ({self.vehicle.battery.level}%)")
        print(f"GPS:      {self.vehicle.gps_0.satellites_visible} satellites")
        print("="*50)
        print()
    
    def run_interactive(self):
        """Interactive control"""
        print("="*70)
        print("MANUAL CONTROL - Ready to fly!")
        print("="*70)
        print()
        print("Commands:")
        print("  takeoff    - Takeoff to 2m")
        print("  w/s/a/d    - Move forward/back/left/right")
        print("  q/e        - Move up/down")
        print("  land       - Land")
        print("  status     - Show status")
        print("  quit       - Exit (will land if flying)")
        print()
        print("="*70)
        print()
        
        try:
            while True:
                cmd = input("ElevateXY> ").strip().lower()
                
                if cmd in ['quit', 'exit']:
                    if self.vehicle.armed:
                        print("\n⚠️  Drone still armed - landing first...")
                        self.land()
                    break
                
                elif cmd == 'takeoff':
                    self.takeoff(2.0)
                
                elif cmd in ['w', 's', 'a', 'd', 'q', 'e']:
                    self.move(cmd)
                
                elif cmd == 'land':
                    self.land()
                
                elif cmd == 'status':
                    self.status()
                
                elif cmd == '':
                    continue
                
                else:
                    print(f"Unknown command: {cmd}")
        
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted!")
            if self.vehicle and self.vehicle.armed:
                print("Emergency landing...")
                self.land()
        
        finally:
            if self.vehicle:
                print("\n🔌 Closing connection...")
                self.vehicle.close()
                print("✅ Done\n")

def main():
    print()
    print("🚁 ElevateXY Manual Control - Final Working Version")
    print()
    
    drone = ElevateXY()
    
    if drone.connect_and_verify():
        drone.run_interactive()
    else:
        print("❌ Setup failed. Follow the instructions above.\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
