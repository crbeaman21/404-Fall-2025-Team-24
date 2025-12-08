#!/usr/bin/env python3
"""
ElevateXY Simulation - Enhanced with Power & Current Display
Displays: Battery voltage, current, power consumption, and flight metrics
"""

import cv2
import numpy as np
import time
import threading
import argparse
from dronekit import connect, VehicleMode
from pymavlink import mavutil

# GStreamer Python bindings for Jetson camera
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

class GStreamerCamera:
    """Camera wrapper using GStreamer Python bindings"""
    
    def __init__(self, width=640, height=480, framerate=30):
        Gst.init(None)
        
        self.width = width
        self.height = height
        self.framerate = framerate
        self.frame = None
        self.frame_lock = threading.Lock()
        self.running = False
        
        pipeline_str = (
            f"nvarguscamerasrc sensor-id=0 ! "
            f"video/x-raw(memory:NVMM),width={width},height={height},framerate={framerate}/1,format=NV12 ! "
            f"nvvidconv ! "
            f"video/x-raw,format=BGRx ! "
            f"videoconvert ! "
            f"video/x-raw,format=BGR ! "
            f"appsink name=sink emit-signals=true sync=false max-buffers=1 drop=true"
        )
        
        self.pipeline = Gst.parse_launch(pipeline_str)
        self.appsink = self.pipeline.get_by_name('sink')
        self.appsink.connect('new-sample', self.on_new_sample)
        
    def on_new_sample(self, sink):
        sample = sink.emit('pull-sample')
        if sample:
            buffer = sample.get_buffer()
            caps = sample.get_caps()
            
            height = caps.get_structure(0).get_value('height')
            width = caps.get_structure(0).get_value('width')
            
            result, map_info = buffer.map(Gst.MapFlags.READ)
            if result:
                frame_data = np.frombuffer(map_info.data, dtype=np.uint8)
                frame = frame_data.reshape((height, width, 3))
                
                with self.frame_lock:
                    self.frame = frame.copy()
                
                buffer.unmap(map_info)
        
        return Gst.FlowReturn.OK
    
    def start(self):
        ret = self.pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            return False
        self.running = True
        time.sleep(1)
        return True
    
    def read(self):
        with self.frame_lock:
            if self.frame is not None:
                return True, self.frame.copy()
        return False, None
    
    def release(self):
        self.running = False
        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)
    
    def isOpened(self):
        return self.running

class GridZone:
    """Grid zones for autonomous tracking"""
    TOP_LEFT = 0
    TOP_CENTER = 1
    TOP_RIGHT = 2
    CENTER_LEFT = 3
    CENTER = 4
    CENTER_RIGHT = 5
    BOTTOM_LEFT = 6
    BOTTOM_CENTER = 7
    BOTTOM_RIGHT = 8

class DroneParams:
    """Battery-optimized flight parameters for different modes"""
    # Standard mode parameters
    STD_GND_SPEED = 5.0    # m/s horizontal speed
    STD_VZ_SPEED = 0.5     # m/s vertical speed
    STD_YAW_RATE = 0.5     # radians/sec

    # Eco mode parameters (reduced by 30% to save battery)
    ECO_GND_SPEED = 3.5    # m/s horizontal speed
    ECO_VZ_SPEED = 0.35    # m/s vertical speed
    ECO_YAW_RATE = 0.35    # radians/sec

    # Performance mode parameters (increased by 20% for when needed)
    PERF_GND_SPEED = 6.0   # m/s horizontal speed
    PERF_VZ_SPEED = 0.6    # m/s vertical speed
    PERF_YAW_RATE = 0.6    # radians/sec

    # Battery thresholds
    CRITICAL_BATTERY = 15  # percentage
    LOW_BATTERY = 30       # percentage
    RETURN_HOME_BATTERY = 25  # percentage - auto return threshold

    # Battery simulation parameters (6S LiPo)
    BATTERY_VOLTAGE_FULL = 25.2   # 6S LiPo fully charged (4.2V per cell)
    BATTERY_VOLTAGE_NOMINAL = 22.2  # 6S LiPo nominal (3.7V per cell)
    BATTERY_VOLTAGE_LOW = 21.0    # 6S LiPo low (3.5V per cell)
    BATTERY_VOLTAGE_CRITICAL = 18.0  # 6S LiPo critical (3.0V per cell)
    
    # Power consumption estimates (for visualization)
    HOVER_POWER = 100  # Watts (approximate hover power)
    MOVE_POWER_MULTIPLIER = 1.5  # Additional power when moving

class ManualDroneController:
    """Manual drone control with keyboard"""
    def __init__(self, vehicle, flight_mode="standard"):
        self.vehicle = vehicle
        self.flight_mode = flight_mode
        
        self.vx = 0
        self.vy = 0
        self.vz = 0
        self.yaw_rate_cmd = 0
        
        # Set speeds based on mode
        self.update_speeds()
    
    def update_speeds(self):
        """Update speeds based on current flight mode"""
        if self.flight_mode == "eco":
            self.move_speed = DroneParams.ECO_GND_SPEED
            self.vertical_speed = DroneParams.ECO_VZ_SPEED
            self.yaw_rate = np.degrees(DroneParams.ECO_YAW_RATE)
        elif self.flight_mode == "performance":
            self.move_speed = DroneParams.PERF_GND_SPEED
            self.vertical_speed = DroneParams.PERF_VZ_SPEED
            self.yaw_rate = np.degrees(DroneParams.PERF_YAW_RATE)
        else:  # standard
            self.move_speed = DroneParams.STD_GND_SPEED
            self.vertical_speed = DroneParams.STD_VZ_SPEED
            self.yaw_rate = np.degrees(DroneParams.STD_YAW_RATE)
    
    def set_flight_mode(self, mode):
        """Change flight mode and update speeds"""
        self.flight_mode = mode
        self.update_speeds()
        
    def set_forward(self, speed):
        self.vx = speed
    
    def set_backward(self, speed):
        self.vx = -speed
    
    def set_left(self, speed):
        self.vy = -speed
    
    def set_right(self, speed):
        self.vy = speed
    
    def set_up(self, speed):
        self.vz = -speed
    
    def set_down(self, speed):
        self.vz = speed
    
    def stop_all(self):
        self.vx = 0
        self.vy = 0
        self.vz = 0
        self.yaw_rate_cmd = 0
    
    def send_command(self):
        if not self.vehicle or not self.vehicle.armed:
            return
        
        try:
            msg = self.vehicle.message_factory.set_position_target_local_ned_encode(
                0, 0, 0,
                mavutil.mavlink.MAV_FRAME_BODY_NED,
                0b0000111111000111,
                0, 0, 0,
                self.vx, self.vy, self.vz,
                0, 0, 0,
                0, self.yaw_rate_cmd
            )
            self.vehicle.send_mavlink(msg)
            
            if abs(self.vx) > 0 or abs(self.vy) > 0:
                print(f"DEBUG: Sending Vel VX:{self.vx:.1f} VY:{self.vy:.1f}")

        except Exception as e:
            print(f"Manual command error: {e}")

class ElevateXYSimulation:
    def __init__(self, connection_string, baud=57600):
        """Initialize ElevateXY simulation system"""
        self.vehicle = None
        self.connection_string = connection_string
        self.baud = baud
        
        # Camera
        self.cap = None
        self.camera_active = False
        self.frame_width = 640
        self.frame_height = 480
        
        # Face detection
        self.face_cascade = None
        self.face_detected = False
        self.face_zone = GridZone.CENTER
        self.face_center = (self.frame_width // 2, self.frame_height // 2)
        
        # Grid zones
        self.setup_grid_zones()
        
        # Control
        self.autonomous_enabled = False
        self.manual_control = None
        self.flight_mode = "standard"
        self.last_command_time = time.time()
        self.command_interval = 0.1
        
        # Deadzone
        self.deadzone_horizontal = 80
        self.deadzone_vertical = 60
    
    def setup_grid_zones(self):
        """Define the 3x3 grid zones"""
        col_width = self.frame_width // 3
        row_height = self.frame_height // 3
        
        self.zones = {
            GridZone.TOP_LEFT: (0, 0, col_width, row_height),
            GridZone.TOP_CENTER: (col_width, 0, col_width * 2, row_height),
            GridZone.TOP_RIGHT: (col_width * 2, 0, self.frame_width, row_height),
            
            GridZone.CENTER_LEFT: (0, row_height, col_width, row_height * 2),
            GridZone.CENTER: (col_width, row_height, col_width * 2, row_height * 2),
            GridZone.CENTER_RIGHT: (col_width * 2, row_height, self.frame_width, row_height * 2),
            
            GridZone.BOTTOM_LEFT: (0, row_height * 2, col_width, self.frame_height),
            GridZone.BOTTOM_CENTER: (col_width, row_height * 2, col_width * 2, self.frame_height),
            GridZone.BOTTOM_RIGHT: (col_width * 2, row_height * 2, self.frame_width, self.frame_height)
        }
        
        self.zone_names = {
            GridZone.TOP_LEFT: "Top Left",
            GridZone.TOP_CENTER: "Top Center",
            GridZone.TOP_RIGHT: "Top Right",
            GridZone.CENTER_LEFT: "Center Left",
            GridZone.CENTER: "CENTER",
            GridZone.CENTER_RIGHT: "Center Right",
            GridZone.BOTTOM_LEFT: "Bottom Left",
            GridZone.BOTTOM_CENTER: "Bottom Center",
            GridZone.BOTTOM_RIGHT: "Bottom Right"
        }
    
    def initialize_face_detection(self):
        """Initialize face detection cascade"""
        import os
        cascade_paths = [
            os.path.expanduser('~/opencv_cascades/haarcascade_frontalface_default.xml'),
            '/usr/share/opencv/haarcascades/haarcascade_frontalface_default.xml',
            '/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml',
        ]
        
        for path in cascade_paths:
            if os.path.exists(path):
                self.face_cascade = cv2.CascadeClassifier(path)
                if not self.face_cascade.empty():
                    print(f"✓ Loaded face cascade from: {path}")
                    return True
        
        print("✗ Failed to load face cascade")
        return False
    
    def start_camera(self):
        """Start camera using GStreamer"""
        print("Initializing camera...")
        
        try:
            self.cap = GStreamerCamera(self.frame_width, self.frame_height, 30)
            
            if not self.cap.start():
                return False
            
            for i in range(20):
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    print(f"✓ CSI Camera opened successfully ({frame.shape})")
                    self.camera_active = True
                    return True
                time.sleep(0.1)
            
            return False
            
        except Exception as e:
            print(f"✗ Camera initialization failed: {e}")
            return False
    
    def connect_sitl(self):
        """Connect to SITL or real drone"""
        try:
            print(f"Connecting to: {self.connection_string}")
            self.vehicle = connect(self.connection_string, baud=self.baud, 
                                 wait_ready=False, timeout=60)
            
            # Initialize manual controller
            self.manual_control = ManualDroneController(
                self.vehicle, 
                self.flight_mode
            )
            
            print("✓ Vehicle connected")
            return True
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            return False
    
    def set_flight_mode(self, mode):
        """Set flight mode"""
        self.flight_mode = mode
        if self.manual_control:
            self.manual_control.set_flight_mode(mode)
        print(f"Flight mode: {mode.upper()}")
    
    def arm_drone(self, check_armable=True, timeout=30):
        """Arm the drone"""
        if not self.vehicle:
            print("No vehicle connected")
            return False
        
        if check_armable:
            print("Checking if vehicle is armable...")
            start = time.time()
            while not self.vehicle.is_armable and (time.time() - start) < timeout:
                print(f"  Waiting for vehicle to be armable... ({int(time.time()-start)}s)")
                time.sleep(1)
            
            if not self.vehicle.is_armable:
                print("✗ Vehicle not armable after timeout")
                return False
        
        print("Setting GUIDED mode...")
        self.vehicle.mode = VehicleMode("GUIDED")
        time.sleep(1)
        
        print("Arming motors...")
        self.vehicle.armed = True
        
        start = time.time()
        while not self.vehicle.armed and (time.time() - start) < timeout:
            print(f"  Waiting for arming... ({int(time.time()-start)}s)")
            time.sleep(1)
        
        if self.vehicle.armed:
            print("✓ Vehicle ARMED")
            return True
        else:
            print("✗ Failed to arm")
            return False
    
    def get_face_zone(self, face_center_x, face_center_y):
        """Determine which zone the face is in"""
        for zone, (x1, y1, x2, y2) in self.zones.items():
            if x1 <= face_center_x < x2 and y1 <= face_center_y < y2:
                return zone
        return GridZone.CENTER
    
    def calculate_drone_commands(self, zone, face_center):
        """Calculate drone movement commands for autonomous mode"""
        vx = vy = vz = yaw_rate = 0.0
        
        face_x, face_y = face_center
        center_x = self.frame_width // 2
        center_y = self.frame_height // 2
        
        offset_x = face_x - center_x
        offset_y = face_y - center_y
        
        # Get current speed settings
        if self.flight_mode == "eco":
            move_speed = DroneParams.ECO_GND_SPEED
            vert_speed = DroneParams.ECO_VZ_SPEED
        elif self.flight_mode == "performance":
            move_speed = DroneParams.PERF_GND_SPEED
            vert_speed = DroneParams.PERF_VZ_SPEED
        else:
            move_speed = DroneParams.STD_GND_SPEED
            vert_speed = DroneParams.STD_VZ_SPEED
        
        # Horizontal movement
        if zone in [GridZone.TOP_LEFT, GridZone.CENTER_LEFT, GridZone.BOTTOM_LEFT]:
            if abs(offset_x) > self.deadzone_horizontal:
                vy = -move_speed
        elif zone in [GridZone.TOP_RIGHT, GridZone.CENTER_RIGHT, GridZone.BOTTOM_RIGHT]:
            if abs(offset_x) > self.deadzone_horizontal:
                vy = move_speed
        
        # Vertical movement
        if zone in [GridZone.TOP_LEFT, GridZone.TOP_CENTER, GridZone.TOP_RIGHT]:
            if abs(offset_y) > self.deadzone_vertical:
                vz = -vert_speed
        elif zone in [GridZone.BOTTOM_LEFT, GridZone.BOTTOM_CENTER, GridZone.BOTTOM_RIGHT]:
            if abs(offset_y) > self.deadzone_vertical:
                vz = vert_speed
        
        return vx, vy, vz, yaw_rate
    
    def send_velocity_command(self, vx, vy, vz, yaw_rate=0):
        """Send velocity command to drone"""
        if not self.vehicle or not self.vehicle.armed:
            return
        
        try:
            msg = self.vehicle.message_factory.set_position_target_local_ned_encode(
                0, 0, 0,
                mavutil.mavlink.MAV_FRAME_BODY_NED,
                0b0000111111000111,
                0, 0, 0,
                vx, vy, vz,
                0, 0, 0,
                0, yaw_rate
            )
            self.vehicle.send_mavlink(msg)
        except Exception as e:
            print(f"Command error: {e}")
    
    def stop_movement(self):
        """Stop all drone movement"""
        self.send_velocity_command(0, 0, 0, 0)
        if self.manual_control:
            self.manual_control.stop_all()
    
    def detect_and_track(self, frame):
        """Detect face and determine tracking commands"""
        if not self.face_cascade:
            return None
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.05,
            minNeighbors=6,
            minSize=(50, 50),
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        
        if len(faces) > 0:
            largest_face = max(faces, key=lambda f: f[2] * f[3])
            x, y, w, h = largest_face
            
            self.face_center = (x + w // 2, y + h // 2)
            self.face_detected = True
            self.face_zone = self.get_face_zone(self.face_center[0], self.face_center[1])
            
            if self.autonomous_enabled and (time.time() - self.last_command_time) > self.command_interval:
                if self.face_zone != GridZone.CENTER:
                    vx, vy, vz, yaw_rate = self.calculate_drone_commands(
                        self.face_zone, self.face_center
                    )
                    self.send_velocity_command(vx, vy, vz, yaw_rate)
                else:
                    self.stop_movement()
                
                self.last_command_time = time.time()
            
            return largest_face
        else:
            self.face_detected = False
            if self.autonomous_enabled:
                self.stop_movement()
        
        return None
    
    def handle_manual_control(self, key):
        """Handle manual control keyboard input"""
        if not self.manual_control or not self.vehicle:
            return
        
        self.manual_control.stop_all()
        
        # WASD for horizontal movement
        if key == ord('w'):
            self.manual_control.set_forward(self.manual_control.move_speed)
        elif key == ord('a'):
            self.manual_control.set_left(self.manual_control.move_speed)
        elif key == ord('d'):
            self.manual_control.set_right(self.manual_control.move_speed)
        
        # Arrow keys for vertical
        elif key == 82:  # Up arrow
            self.manual_control.set_up(self.manual_control.vertical_speed)
        elif key == 84:  # Down arrow
            self.manual_control.set_down(self.manual_control.vertical_speed)
        
        if not self.autonomous_enabled:
            self.manual_control.send_command()
    
    def draw_power_panel(self, frame):
        """Draw simple power monitoring panel on frame"""
        h, w = frame.shape[:2]
        
        # Get current voltage and current directly from vehicle
        voltage = None
        current = None
        
        if hasattr(self.vehicle, 'battery') and self.vehicle.battery:
            if hasattr(self.vehicle.battery, 'voltage'):
                voltage = self.vehicle.battery.voltage
            if hasattr(self.vehicle.battery, 'current'):
                current = self.vehicle.battery.current
        
        if voltage is None or current is None:
            return frame
        
        # Calculate instantaneous power
        power = voltage * abs(current)
        
        # Panel background (semi-transparent)
        panel_height = 110
        panel_width = 220
        panel_x = w - panel_width - 10
        panel_y = 10
        
        overlay = frame.copy()
        cv2.rectangle(overlay, (panel_x, panel_y), 
                     (panel_x + panel_width, panel_y + panel_height),
                     (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        
        # Panel border
        cv2.rectangle(frame, (panel_x, panel_y),
                     (panel_x + panel_width, panel_y + panel_height),
                     (0, 255, 0), 2)
        
        # Title
        cv2.putText(frame, "POWER MONITOR", (panel_x + 10, panel_y + 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        y_offset = panel_y + 50
        line_height = 25
        
        # Voltage
        volt_color = self.get_voltage_color(voltage)
        cv2.putText(frame, f"Voltage: {voltage:.2f}V", 
                   (panel_x + 10, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, volt_color, 1)
        y_offset += line_height
        
        # Current
        cv2.putText(frame, f"Current: {abs(current):.2f}A", 
                   (panel_x + 10, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        y_offset += line_height
        
        # Power
        power_color = self.get_power_color(power)
        cv2.putText(frame, f"Power:   {power:.1f}W", 
                   (panel_x + 10, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, power_color, 1)
        
        return frame
    
    def get_voltage_color(self, voltage):
        """Get color based on voltage level"""
        if voltage >= DroneParams.BATTERY_VOLTAGE_NOMINAL:
            return (0, 255, 0)  # Green
        elif voltage >= DroneParams.BATTERY_VOLTAGE_LOW:
            return (0, 255, 255)  # Yellow
        elif voltage >= DroneParams.BATTERY_VOLTAGE_CRITICAL:
            return (0, 165, 255)  # Orange
        else:
            return (0, 0, 255)  # Red
    
    def get_power_color(self, power):
        """Get color based on power consumption"""
        if power < 150:
            return (0, 255, 0)  # Green (low power)
        elif power < 300:
            return (0, 255, 255)  # Yellow (medium power)
        else:
            return (0, 165, 255)  # Orange (high power)
    
    def get_battery_level_color(self, level):
        """Get color based on battery level"""
        if level >= DroneParams.LOW_BATTERY:
            return (0, 255, 0)  # Green
        elif level >= DroneParams.RETURN_HOME_BATTERY:
            return (0, 255, 255)  # Yellow
        elif level >= DroneParams.CRITICAL_BATTERY:
            return (0, 165, 255)  # Orange
        else:
            return (0, 0, 255)  # Red
    
    def draw_interface(self, frame, face_rect=None):
        """Draw complete interface with power monitoring"""
        h, w = frame.shape[:2]
        
        # Draw power panel on right side
        frame = self.draw_power_panel(frame)
        
        # Draw grid (only in autonomous mode)
        if self.autonomous_enabled:
            col_width = w // 3
            row_height = h // 3
            
            cv2.line(frame, (col_width, 0), (col_width, h), (100, 100, 100), 2)
            cv2.line(frame, (col_width * 2, 0), (col_width * 2, h), (100, 100, 100), 2)
            cv2.line(frame, (0, row_height), (w, row_height), (100, 100, 100), 2)
            cv2.line(frame, (0, row_height * 2), (w, row_height * 2), (100, 100, 100), 2)
            
            # Highlight center zone
            center_zone = self.zones[GridZone.CENTER]
            cv2.rectangle(frame, 
                         (center_zone[0], center_zone[1]),
                         (center_zone[2], center_zone[3]),
                         (0, 255, 0), 2)
            
            # Draw center crosshair
            center_x, center_y = w // 2, h // 2
            cv2.line(frame, (center_x - 30, center_y), (center_x + 30, center_y), (0, 255, 0), 2)
            cv2.line(frame, (center_x, center_y - 30), (center_x, center_y + 30), (0, 255, 0), 2)
            cv2.circle(frame, (center_x, center_y), 50, (0, 255, 0), 2)
        
        # Draw face detection
        if self.autonomous_enabled and face_rect is not None:
            x, y, w_rect, h_rect = face_rect
            color = (0, 255, 0) if self.face_zone == GridZone.CENTER else (0, 255, 255)
            cv2.rectangle(frame, (x, y), (x + w_rect, y + h_rect), color, 2)
            cv2.circle(frame, self.face_center, 5, (0, 0, 255), -1)
            
            center_x, center_y = self.frame_width // 2, self.frame_height // 2
            cv2.line(frame, self.face_center, (center_x, center_y), (255, 0, 0), 2)
            
            zone_name = self.zone_names[self.face_zone]
            cv2.putText(frame, zone_name, (x, y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        # Status overlay (top-left)
        cv2.putText(frame, "ElevateXY - Power Monitoring", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Flight mode
        mode_colors = {
            "eco": (0, 255, 0),
            "standard": (0, 255, 255),
            "performance": (0, 165, 255)
        }
        mode_color = mode_colors.get(self.flight_mode, (255, 255, 255))
        cv2.putText(frame, f"Mode: {self.flight_mode.upper()}", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, mode_color, 2)
        
        # Control mode
        control_text = "AUTONOMOUS" if self.autonomous_enabled else "MANUAL"
        control_color = (0, 255, 0) if self.autonomous_enabled else (0, 165, 255)
        cv2.putText(frame, f"Control: {control_text}", (10, 90),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, control_color, 2)
        
        # Armed status
        if self.vehicle:
            armed_text = "ARMED" if self.vehicle.armed else "DISARMED"
            armed_color = (0, 0, 255) if self.vehicle.armed else (150, 150, 150)
            cv2.putText(frame, armed_text, (10, 120),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, armed_color, 2)
            
            # Altitude
            if hasattr(self.vehicle.location, 'global_relative_frame'):
                alt = self.vehicle.location.global_relative_frame.alt
                cv2.putText(frame, f"Alt: {alt:.1f}m", (10, 150),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # Ground speed
            if hasattr(self.vehicle, 'groundspeed'):
                speed = self.vehicle.groundspeed
                cv2.putText(frame, f"Speed: {speed:.1f}m/s", (10, 175),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Instructions (bottom)
        y_offset = h - 60
        if self.autonomous_enabled:
            if self.face_detected:
                cv2.putText(frame, "Face: TRACKING", (10, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            else:
                cv2.putText(frame, "Face: SEARCHING", (10, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        else:
            cv2.putText(frame, "Keys: W,A,D=Move | Up/Down=Alt", (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            cv2.putText(frame, "1=Eco | 2=Std | 3=Perf | SPACE=Auto", (10, y_offset + 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        return frame
    
    def run(self):
        """Main loop"""
        print("\n" + "="*60)
        print("ElevateXY - POWER MONITORING SIMULATION")
        print("Jetson Camera + Laptop SITL")
        print("="*60)
        
        # Initialize face detection
        if not self.initialize_face_detection():
            print("Warning: Face detection unavailable")
        
        # Start camera
        if not self.start_camera():
            print("Error: Camera failed")
            return
        
        # Connect to SITL
        if not self.connect_sitl():
            print("Error: SITL connection failed")
            return
        
        print("\nControls:")
        print("  FLIGHT MODES:")
        print("    1         - ECO Mode (battery efficient)")
        print("    2         - STANDARD Mode (balanced)")
        print("    3         - PERFORMANCE Mode (high speed)")
        print("  CONTROL MODES:")
        print("    SPACE     - Toggle Manual ↔ Autonomous")
        print("  MANUAL CONTROLS:")
        print("    W / A / D - Forward / Left / Right")
        print("    UP/DOWN   - Altitude")
        print("  OTHER:")
        print("    X         - ARM drone")
        print("    T         - Takeoff")
        print("    L         - Land")
        print("    Q         - Quit")
        print("="*60 + "\n")
        
        print(f"Ready! Current mode: {self.flight_mode.upper()}\n")
        
        try:
            while self.camera_active:
                ret, frame = self.cap.read()
                if not ret or frame is None:
                    continue
                
                face_rect = None
                if self.autonomous_enabled:
                    face_rect = self.detect_and_track(frame)
                
                display_frame = self.draw_interface(frame, face_rect)
                
                cv2.imshow('ElevateXY - Power Monitoring', display_frame)
                
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q'):
                    break
                    
                # Flight mode changes
                elif key == ord('1'):
                    self.set_flight_mode("eco")
                elif key == ord('2'):
                    self.set_flight_mode("standard")
                elif key == ord('3'):
                    self.set_flight_mode("performance")
                
                # Control mode toggle
                elif key == ord(' '):
                    self.autonomous_enabled = not self.autonomous_enabled
                    status = "AUTONOMOUS" if self.autonomous_enabled else "MANUAL"
                    print(f"\n{'='*60}")
                    print(f"CONTROL MODE: {status}")
                    print(f"{'='*60}\n")
                    if not self.autonomous_enabled:
                        self.stop_movement()
                
                # ARM command
                elif key == ord('x') or key == ord('X'):
                    print("\nArm command received!")
                    self.arm_drone(check_armable=True, timeout=30)
                
                elif key == ord('t'):
                    if self.vehicle and self.vehicle.armed:
                        if self.vehicle.mode.name != 'GUIDED':
                             print("Setting GUIDED mode for takeoff...")
                             self.vehicle.mode = VehicleMode("GUIDED")
                             time.sleep(1)
                        print("Takeoff command sent (Target: 3m)")
                        self.vehicle.simple_takeoff(3.0)
                
                elif key == ord('l'):
                    if self.vehicle:
                        print("Landing...")
                        self.vehicle.mode = VehicleMode("LAND")
                        self.autonomous_enabled = False
                
                elif key != 255:
                    if not self.autonomous_enabled:
                        self.handle_manual_control(key)
        
        except KeyboardInterrupt:
            print("\nInterrupted")
        
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Cleanup"""
        print("\nCleaning up...")
        self.autonomous_enabled = False
        self.camera_active = False
        
        if self.vehicle:
            self.stop_movement()
            self.vehicle.close()
        
        if self.cap:
            self.cap.release()
        
        cv2.destroyAllWindows()
        print("✓ Cleanup complete")

def main():
    parser = argparse.ArgumentParser(
        description='ElevateXY Simulation with Power Monitoring',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  # For simulation (network):
  python3 elevatexy_simulation_power.py --connect tcp:192.168.1.100:14550

  # For real drone (USB):
  python3 elevatexy_simulation_power.py --connect /dev/ttyUSB0 --baud 57600
        """
    )
    
    parser.add_argument(
        '--connect',
        required=True,
        help='Connection string (e.g., tcp:192.168.1.100:14550 or /dev/ttyUSB0)'
    )
    
    parser.add_argument(
        '--baud',
        type=int,
        default=57600,
        help='Baud rate for serial connection (default: 57600)'
    )
    
    args = parser.parse_args()
    
    if args.connect.startswith('/dev/'):
        print(f"ElevateXY - Real Drone Mode with Power Monitoring")
        print(f"Connecting to: {args.connect} @ {args.baud} baud")
    else:
        print(f"ElevateXY Simulation Mode with Power Monitoring")
        print(f"Connecting to: {args.connect}")
    
    sim = ElevateXYSimulation(args.connect, baud=args.baud)
    sim.run()

if __name__ == "__main__":
    main()
