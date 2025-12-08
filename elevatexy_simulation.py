#!/usr/bin/env python3
"""
ElevateXY Simulation - Jetson Side
Connects to laptop SITL via network/serial, provides camera and AI processing.
MODIFIED FOR SITL CONTROL FIXES
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
    
    def set_yaw_left(self, rate):
        self.yaw_rate_cmd = -np.radians(rate)
    
    def set_yaw_right(self, rate):
        self.yaw_rate_cmd = np.radians(rate)
    
    def stop_all(self):
        self.vx = 0
        self.vy = 0
        self.vz = 0
        self.yaw_rate_cmd = 0
    
    def send_command(self):
        if not self.vehicle or not self.vehicle.armed:
            return
        
        try:
            # IMPORTANT: MAV_FRAME_BODY_NED only works in GUIDED mode!
            msg = self.vehicle.message_factory.set_position_target_local_ned_encode(
                0, 0, 0,
                mavutil.mavlink.MAV_FRAME_BODY_NED,
                0b0000111111000111, # Bitmask: Ignore PosX/Y/Z, AccelX/Y/Z. Use VelX/Y/Z + YawRate
                0, 0, 0, # Pos
                self.vx, self.vy, self.vz, # Velocity
                0, 0, 0, # Accel
                0, self.yaw_rate_cmd # Yaw/YawRate
            )
            self.vehicle.send_mavlink(msg)
            
            # Debug output for verification
            if abs(self.vx) > 0 or abs(self.vy) > 0:
                print(f"DEBUG: Sending Vel VX:{self.vx:.1f} VY:{self.vy:.1f}")

        except Exception as e:
            print(f"Manual command error: {e}")

class ElevateXYSimulation:
    def __init__(self, connection_string, baud=57600):
        """Initialize ElevateXY simulation system"""
        self.vehicle = None
        self.connection_string = connection_string
        self.baud = baud  # Baud rate for serial connections
        
        # Camera setup
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
        
        # Flight mode (eco, standard, performance)
        self.flight_mode = "standard"
        
        # Movement parameters (will be updated based on mode)
        self.move_speed = DroneParams.STD_GND_SPEED
        self.vertical_speed = DroneParams.STD_VZ_SPEED
        self.yaw_rate = np.degrees(DroneParams.STD_YAW_RATE)
        
        # Control mode (manual vs autonomous)
        self.autonomous_enabled = False
        self.manual_control = None
        self.last_command_time = time.time()
        self.command_interval = 0.1
        
        # Deadzone
        self.deadzone_horizontal = 80
        self.deadzone_vertical = 60
        
        # Status tracking
        self.connected = False
        self.last_heartbeat = 0
        
        # Battery simulation
        self.simulated_battery_percent = 100.0
        self.simulated_battery_voltage = DroneParams.BATTERY_VOLTAGE_FULL
        
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
    
    def update_speeds_for_mode(self):
        """Update movement speeds based on current flight mode"""
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
        
        # Update manual controller if it exists
        if self.manual_control:
            self.manual_control.set_flight_mode(self.flight_mode)
    
    def set_flight_mode(self, mode):
        """Set flight mode (eco, standard, performance)"""
        if mode not in ["eco", "standard", "performance"]:
            return
        
        self.flight_mode = mode
        self.update_speeds_for_mode()
        
        mode_colors = {
            "eco": "GREEN",
            "standard": "YELLOW",
            "performance": "RED"
        }
        
        print(f"\n{'='*60}")
        print(f"FLIGHT MODE: {mode.upper()}")
        print(f"Speed: {self.move_speed:.1f} m/s | Vert: {self.vertical_speed:.2f} m/s")
        print(f"Battery: {'Efficient' if mode == 'eco' else 'Balanced' if mode == 'standard' else 'High Drain'}")
        print(f"{'='*60}\n")
    
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
        print("Initializing Jetson camera...")
        
        try:
            self.cap = GStreamerCamera(self.frame_width, self.frame_height, 30)
            
            if not self.cap.start():
                return False
            
            # Wait for first frame
            for i in range(20):
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    print(f"✓ Camera ready ({frame.shape})")
                    self.camera_active = True
                    return True
                time.sleep(0.1)
            
            return False
            
        except Exception as e:
            print(f"✗ Camera failed: {e}")
            return False
    
    def connect_sitl(self):
        """Connect to laptop SITL via network or real drone via serial"""
        try:
            # Determine if this is a serial connection or network connection
            is_serial = self.connection_string.startswith('/dev/')
            
            if is_serial:
                print(f"Connecting to real drone at {self.connection_string}...")
                print(f"Baud rate: {self.baud}")
            else:
                print(f"Connecting to SITL at {self.connection_string}...")
                print("(This connects to your laptop's ArduCopter simulation)")
            
            # FIX: Added source_system=200 to differentiate this script from MAVProxy
            self.vehicle = connect(
                self.connection_string,
                baud=self.baud,
                wait_ready=False,
                timeout=60,
                heartbeat_timeout=30,
                source_system=200 # Unique ID for this script
            )
            
            # Wait for heartbeat
            print("Waiting for heartbeat...")
            start = time.time()
            while not self.vehicle.is_armable and (time.time() - start) < 30:
                time.sleep(0.5)
            
            # Set 6S battery parameters (for real drone, these may already be set)
            try:
                if not is_serial:  # Only set for simulation
                    print("Configuring 6S LiPo battery parameters...")
                    self.vehicle.parameters['BATT_MONITOR'] = 4
                    self.vehicle.parameters['SIM_BATT_VOLTAGE'] = DroneParams.BATTERY_VOLTAGE_NOMINAL
                    self.vehicle.parameters['BATT_CAPACITY'] = 5200
                    print(f"✓ Battery configured: {DroneParams.BATTERY_VOLTAGE_NOMINAL}V (6S LiPo)")
                else:
                    print("✓ Using real drone battery parameters")
            except Exception as e:
                print(f"Note: Could not set battery parameters: {e}")
            
            # Initialize manual controller with flight mode
            self.manual_control = ManualDroneController(
                self.vehicle,
                self.flight_mode
            )
            
            # FIX: Force GUIDED mode immediately so commands work
            print("Switching to GUIDED mode for computer control...")
            self.vehicle.mode = VehicleMode("GUIDED")
            time.sleep(1)

            self.connected = True
            self.last_heartbeat = time.time()
            
            connection_type = "Real Drone" if is_serial else "SITL"
            print(f"✓ Connected to {connection_type}!")
            print(f"  Mode: {self.vehicle.mode.name}")
            print(f"  Armed: {self.vehicle.armed}")
            print(f"  Flight Mode: {self.flight_mode.upper()}")
            
            return True
            
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            if self.connection_string.startswith('/dev/'):
                print("\nTroubleshooting (Real Drone):")
                print("  1. Check USB cable is connected")
                print("  2. Verify device: ls -l /dev/ttyUSB* /dev/ttyACM*")
                print("  3. Check permissions: sudo usermod -a -G dialout $USER")
                print("  4. Try different baud: --baud 115200")
                print("  5. Check flight controller is powered on")
            else:
                print("\nTroubleshooting (Simulation):")
                print("  1. Check laptop SITL is running")
                print("  2. Verify laptop IP address")
                print("  3. Test: ping YOUR_LAPTOP_IP")
                print("  4. Test: telnet YOUR_LAPTOP_IP 14550")
            return False
    
    def get_face_zone(self, face_center_x, face_center_y):
        """Determine which zone the face is in"""
        for zone, (x1, y1, x2, y2) in self.zones.items():
            if x1 <= face_center_x < x2 and y1 <= face_center_y < y2:
                return zone
        return GridZone.CENTER
    
    def calculate_drone_commands(self, zone, face_center):
        """Calculate drone movement commands"""
        vx = vy = vz = yaw_rate = 0.0
        
        face_x, face_y = face_center
        center_x = self.frame_width // 2
        center_y = self.frame_height // 2
        
        offset_x = face_x - center_x
        offset_y = face_y - center_y
        
        # Horizontal
        if zone in [GridZone.TOP_LEFT, GridZone.CENTER_LEFT, GridZone.BOTTOM_LEFT]:
            if abs(offset_x) > self.deadzone_horizontal:
                vy = -self.move_speed
                print("  → Moving LEFT")
        elif zone in [GridZone.TOP_RIGHT, GridZone.CENTER_RIGHT, GridZone.BOTTOM_RIGHT]:
            if abs(offset_x) > self.deadzone_horizontal:
                vy = self.move_speed
                print("  → Moving RIGHT")
        
        # Vertical
        if zone in [GridZone.TOP_LEFT, GridZone.TOP_CENTER, GridZone.TOP_RIGHT]:
            if abs(offset_y) > self.deadzone_vertical:
                vz = -self.vertical_speed
                print("  ↑ Moving UP")
        elif zone in [GridZone.BOTTOM_LEFT, GridZone.BOTTOM_CENTER, GridZone.BOTTOM_RIGHT]:
            if abs(offset_y) > self.deadzone_vertical:
                vz = self.vertical_speed
                print("  ↓ Moving DOWN")
        
        return vx, vy, vz, yaw_rate
    
    def send_velocity_command(self, vx, vy, vz, yaw_rate=0):
        """Send velocity command to simulated drone"""
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
        """Stop all movement"""
        self.send_velocity_command(0, 0, 0, 0)
        if self.manual_control:
            self.manual_control.stop_all()
    
    def detect_and_track(self, frame):
        """Detect face and determine tracking commands"""
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
                    print(f"Face in {self.zone_names[self.face_zone]} - Adjusting")
                else:
                    self.stop_movement()
                    print(f"Face CENTERED - Holding")
                
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
        
        # Ensure we are in GUIDED mode for manual velocity control
        if self.vehicle.mode.name != 'GUIDED':
             print("Warning: Drone not in GUIDED mode. Switching...")
             self.vehicle.mode = VehicleMode("GUIDED")
        
        self.manual_control.stop_all()
        
        # WASD
        if key == ord('w'):
            self.manual_control.set_forward(self.move_speed)
            print("Manual: FORWARD")
        elif key == ord('s'):
            self.manual_control.set_backward(self.move_speed)
            print("Manual: BACKWARD")
        elif key == ord('a'):
            self.manual_control.set_left(self.move_speed)
            print("Manual: LEFT")
        elif key == ord('d'):
            self.manual_control.set_right(self.move_speed)
            print("Manual: RIGHT")
        
        # Arrows
        elif key == 82:  # Up
            self.manual_control.set_up(self.vertical_speed)
            print("Manual: UP")
        elif key == 84:  # Down
            self.manual_control.set_down(self.vertical_speed)
            print("Manual: DOWN")
        elif key == 81:  # Left
            self.manual_control.set_yaw_left(self.yaw_rate)
            print("Manual: YAW LEFT")
        elif key == 83:  # Right
            self.manual_control.set_yaw_right(self.yaw_rate)
            print("Manual: YAW RIGHT")
        
        if not self.autonomous_enabled:
            self.manual_control.send_command()
    
    def draw_interface(self, frame, face_rect=None):
        """Draw interface overlays"""
        h, w = frame.shape[:2]
        
        # Draw grid in autonomous mode
        if self.autonomous_enabled:
            col_width = w // 3
            row_height = h // 3
            
            cv2.line(frame, (col_width, 0), (col_width, h), (100, 100, 100), 2)
            cv2.line(frame, (col_width * 2, 0), (col_width * 2, h), (100, 100, 100), 2)
            cv2.line(frame, (0, row_height), (w, row_height), (100, 100, 100), 2)
            cv2.line(frame, (0, row_height * 2), (w, row_height * 2), (100, 100, 100), 2)
            
            # Center zone
            center_zone = self.zones[GridZone.CENTER]
            cv2.rectangle(frame,
                         (center_zone[0], center_zone[1]),
                         (center_zone[2], center_zone[3]),
                         (0, 255, 0), 2)
            
            # Crosshair
            center_x, center_y = w // 2, h // 2
            cv2.line(frame, (center_x - 30, center_y), (center_x + 30, center_y), (0, 255, 0), 2)
            cv2.line(frame, (center_x, center_y - 30), (center_x, center_y + 30), (0, 255, 0), 2)
            cv2.circle(frame, (center_x, center_y), 50, (0, 255, 0), 2)
        
        # Draw face
        if self.autonomous_enabled and face_rect is not None:
            x, y, w_box, h_box = face_rect
            color = (0, 255, 0) if self.face_zone == GridZone.CENTER else (0, 255, 255)
            cv2.rectangle(frame, (x, y), (x + w_box, y + h_box), color, 2)
            cv2.circle(frame, self.face_center, 5, (0, 0, 255), -1)
            
            center_x, center_y = self.frame_width // 2, self.frame_height // 2
            cv2.line(frame, self.face_center, (center_x, center_y), (255, 0, 0), 2)
            
            zone_name = self.zone_names[self.face_zone]
            cv2.putText(frame, zone_name, (x, y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        # Status overlay
        cv2.putText(frame, "ElevateXY SIMULATION", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Control mode (Manual/Autonomous)
        mode_text = "AUTONOMOUS" if self.autonomous_enabled else "MANUAL"
        mode_color = (0, 255, 0) if self.autonomous_enabled else (0, 165, 255)
        cv2.putText(frame, f"Control: {mode_text}", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, mode_color, 2)
        
        # Flight mode (Eco/Standard/Performance)
        flight_mode_colors = {
            "eco": (0, 255, 0),        # Green
            "standard": (0, 255, 255),  # Yellow
            "performance": (0, 0, 255)  # Red
        }
        flight_color = flight_mode_colors.get(self.flight_mode, (255, 255, 255))
        cv2.putText(frame, f"Flight: {self.flight_mode.upper()}", (10, 90),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, flight_color, 2)
        
        # Speed info
        cv2.putText(frame, f"Speed: {self.move_speed:.1f}m/s", (10, 120),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Connection status
        conn_color = (0, 255, 0) if self.connected else (0, 0, 255)
        conn_text = "CONNECTED" if self.connected else "DISCONNECTED"
        cv2.putText(frame, f"SITL: {conn_text}", (10, 145),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, conn_color, 1)
        
        # Vehicle status
        if self.vehicle:
            mode = self.vehicle.mode.name if self.vehicle.mode else "UNKNOWN"
            armed = "ARMED" if self.vehicle.armed else "DISARMED"
            armed_color = (0, 255, 0) if self.vehicle.armed else (0, 0, 255)
            
            cv2.putText(frame, f"Drone: {mode} | {armed}", (10, 170),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, armed_color, 1)
            
            # Altitude
            if hasattr(self.vehicle, 'location'):
                alt = self.vehicle.location.global_relative_frame.alt
                cv2.putText(frame, f"Alt: {alt:.1f}m", (10, 195),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # Battery voltage (6S)
            if hasattr(self.vehicle, 'battery') and self.vehicle.battery:
                if hasattr(self.vehicle.battery, 'voltage') and self.vehicle.battery.voltage:
                    voltage = self.vehicle.battery.voltage
                    # Color code based on voltage thresholds
                    if voltage >= DroneParams.BATTERY_VOLTAGE_NOMINAL:
                        volt_color = (0, 255, 0)  # Green
                    elif voltage >= DroneParams.BATTERY_VOLTAGE_LOW:
                        volt_color = (0, 255, 255)  # Yellow
                    else:
                        volt_color = (0, 0, 255)  # Red
                    
                    cv2.putText(frame, f"6S Batt: {voltage:.1f}V", (10, 220),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, volt_color, 1)
                
                if hasattr(self.vehicle.battery, 'level') and self.vehicle.battery.level:
                    level = self.vehicle.battery.level
                    cv2.putText(frame, f"Level: {level}%", (10, 245),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Instructions based on mode
        y_offset = h - 60
        if self.autonomous_enabled:
            if self.face_detected:
                cv2.putText(frame, "Face: TRACKING", (10, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            else:
                cv2.putText(frame, "Face: SEARCHING", (10, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        else:
            cv2.putText(frame, "Keys: WASD=Move | Arrows=Alt/Yaw", (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            cv2.putText(frame, "1=Eco | 2=Std | 3=Perf | SPACE=Auto", (10, y_offset + 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        return frame
    
    def run(self):
        """Main loop"""
        print("\n" + "="*60)
        print("ElevateXY - SIMULATION MODE")
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
        print("    1         - ECO Mode (3.5 m/s, battery efficient)")
        print("    2         - STANDARD Mode (5.0 m/s, balanced)")
        print("    3         - PERFORMANCE Mode (6.0 m/s, high speed)")
        print("  ")
        print("  CONTROL MODES:")
        print("    SPACE     - Toggle Manual ↔ Autonomous")
        print("  ")
        print("  MANUAL CONTROLS:")
        print("    W/A/S/D   - Move Forward/Left/Back/Right")
        print("    UP/DOWN   - Altitude Up/Down")
        print("    LEFT/RIGHT- Yaw Left/Right")
        print("  ")
        print("  AUTONOMOUS MODE:")
        print("    [Auto]    - Face tracking enabled")
        print("  ")
        print("  OTHER:")
        print("    T         - Takeoff (if armed)")
        print("    L         - Land")
        print("    Q         - Quit")
        print("="*60 + "\n")
        
        print(f"Ready! Current mode: {self.flight_mode.upper()}")
        print("Arm and takeoff from laptop console, then control from here.\n")
        
        try:
            while self.camera_active:
                ret, frame = self.cap.read()
                if not ret or frame is None:
                    continue
                
                face_rect = None
                if self.autonomous_enabled:
                    face_rect = self.detect_and_track(frame)
                
                display_frame = self.draw_interface(frame, face_rect)
                
                cv2.imshow('ElevateXY Simulation', display_frame)
                
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q'):
                    break
                    
                # Flight mode changes (1, 2, 3)
                elif key == ord('1'):
                    self.set_flight_mode("eco")
                elif key == ord('2'):
                    self.set_flight_mode("standard")
                elif key == ord('3'):
                    self.set_flight_mode("performance")
                
                # Control mode toggle (SPACE)
                elif key == ord(' '):
                    self.autonomous_enabled = not self.autonomous_enabled
                    status = "AUTONOMOUS" if self.autonomous_enabled else "MANUAL"
                    print(f"\n{'='*60}")
                    print(f"CONTROL MODE: {status}")
                    if self.autonomous_enabled:
                        print("Face tracking enabled - Position face in camera view")
                    else:
                        print(f"Manual control - Using {self.flight_mode.upper()} flight mode")
                    print(f"{'='*60}\n")
                    if not self.autonomous_enabled:
                        self.stop_movement()
                
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
        description='ElevateXY Simulation - Jetson Side',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  # For simulation (network):
  python3 elevatexy_simulation.py --connect tcp:192.168.1.100:14550

  # For real drone (USB):
  python3 elevatexy_simulation.py --connect /dev/ttyUSB0 --baud 57600

Replace 192.168.1.100 with your laptop's IP address for simulation.
Use /dev/ttyUSB0 (or /dev/ttyACM0) with --baud for real drone connection.
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
    
    # Build connection string with baud if it's a serial connection
    if args.connect.startswith('/dev/'):
        connection_string = f"{args.connect}"
        print(f"ElevateXY - Real Drone Mode")
        print(f"Connecting to: {args.connect} @ {args.baud} baud")
    else:
        connection_string = args.connect
        print(f"ElevateXY Simulation Mode")
        print(f"Connecting to: {args.connect}")
    
    sim = ElevateXYSimulation(connection_string, baud=args.baud)
    sim.run()

if __name__ == "__main__":
    main()
