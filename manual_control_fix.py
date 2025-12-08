#!/usr/bin/env python3
"""
ElevateXY Manual Control Fix
Adds continuous command sending for telemetry connections
"""

# ISSUE: Manual control commands not reaching SITL
# CAUSE: Commands need to be sent continuously, not just on keypress
# FIX: Add a command sending thread that sends at 10Hz

import threading
import time
from dronekit import VehicleMode
from pymavlink import mavutil

class ContinuousCommandSender:
    """Sends velocity commands continuously at 10Hz"""
    
    def __init__(self, vehicle):
        self.vehicle = vehicle
        self.active = False
        self.thread = None
        
        # Current command state
        self.vx = 0
        self.vy = 0
        self.vz = 0
        self.yaw_rate = 0
        
        # Lock for thread safety
        self.lock = threading.Lock()
    
    def set_velocity(self, vx, vy, vz, yaw_rate=0):
        """Set the velocity command to send"""
        with self.lock:
            self.vx = vx
            self.vy = vy
            self.vz = vz
            self.yaw_rate = yaw_rate
    
    def _send_loop(self):
        """Background thread that sends commands at 10Hz"""
        while self.active:
            if self.vehicle and self.vehicle.armed:
                with self.lock:
                    vx, vy, vz, yaw = self.vx, self.vy, self.vz, self.yaw_rate
                
                try:
                    msg = self.vehicle.message_factory.set_position_target_local_ned_encode(
                        0, 0, 0,
                        mavutil.mavlink.MAV_FRAME_BODY_NED,
                        0b0000111111000111,
                        0, 0, 0,
                        vx, vy, vz,
                        0, 0, 0,
                        0, yaw
                    )
                    self.vehicle.send_mavlink(msg)
                except Exception as e:
                    print(f"Command send error: {e}")
            
            time.sleep(0.1)  # 10Hz
    
    def start(self):
        """Start the command sender thread"""
        if not self.active:
            self.active = True
            self.thread = threading.Thread(target=self._send_loop, daemon=True)
            self.thread.start()
            print("✓ Continuous command sender started (10Hz)")
    
    def stop(self):
        """Stop the command sender thread"""
        self.active = False
        if self.thread:
            self.thread.join(timeout=1.0)
        print("✓ Continuous command sender stopped")

# INSTRUCTIONS TO FIX YOUR elevatexy_simulation.py:
#
# 1. Add this class to the top of your file
#
# 2. In the ElevateXYSimulation.__init__() method, add:
#    self.command_sender = None
#
# 3. In the connect_sitl() method, after connecting, add:
#    self.command_sender = ContinuousCommandSender(self.vehicle)
#    self.command_sender.start()
#
# 4. Replace the ManualDroneController.send_command() method with:
#    def send_command(self, command_sender):
#        if command_sender:
#            command_sender.set_velocity(self.vx, self.vy, self.vz, self.yaw_rate_cmd)
#
# 5. In handle_manual_control(), change:
#    self.manual_control.send_command()
#    to:
#    self.command_sender.set_velocity(
#        self.manual_control.vx,
#        self.manual_control.vy,
#        self.manual_control.vz,
#        self.manual_control.yaw_rate_cmd
#    )
#
# 6. In cleanup(), add:
#    if self.command_sender:
#        self.command_sender.stop()

print(__doc__)
print("\nTo use this fix, integrate the ContinuousCommandSender class into your simulation.")
print("See instructions in the comments above.")
