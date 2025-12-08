#!/usr/bin/env python3
"""
ElevateXY Simulation with Tkinter Keyboard Input
Reliable keyboard controls using tkinter like drone_demo.py
"""

import time
import threading
import cv2
import numpy as np
from dronekit import connect, VehicleMode
from pymavlink import mavutil

# Tkinter for keyboard input
try:
    import tkinter as tk
    from tkinter import ttk
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False
    print("⚠️  Tkinter not available")

# DroneParams class
class DroneParams:
    """Flight mode parameters"""
    # Standard mode
    STD_GND_SPEED = 3.0    # m/s
    STD_VZ_SPEED = 0.5     # m/s
    STD_YAW_RATE = 30      # deg/s
    
    # Eco mode (30% slower)
    ECO_GND_SPEED = 2.0
    ECO_VZ_SPEED = 0.35
    ECO_YAW_RATE = 20
    
    # Performance mode (50% faster)
    PERF_GND_SPEED = 4.5
    PERF_VZ_SPEED = 0.75
    PERF_YAW_RATE = 45

# GridZone class
class GridZone:
    """Grid zones for face tracking"""
    TOP_LEFT = 0
    TOP_CENTER = 1
    TOP_RIGHT = 2
    CENTER_LEFT = 3
    CENTER = 4
    CENTER_RIGHT = 5
    BOTTOM_LEFT = 6
    BOTTOM_CENTER = 7
    BOTTOM_RIGHT = 8

class ElevateXYSimulation:
    def __init__(self, connection_string='/dev/ttyUSB0', baud=57600):
        """Initialize ElevateXY simulation with tkinter"""
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
        
        # Control state
        self.autonomous_enabled = False
        self.flight_mode = "standard"
        self.keyboard_state = {}  # Track pressed keys
        
        # Movement parameters
        self.update_speeds()
        
        # Command sending
        self.command_thread = None
        self.command_active = False
        self.current_vx = 0
        self.current_vy = 0
        self.current_vz = 0
        self.current_yaw = 0
        
        # Grid zones
        self.setup_grid_zones()
        
        # Tkinter
        self.root = None
        self.status_label = None
        
        # Camera thread
        self.camera_thread = None
        
    def update_speeds(self):
        """Update speeds based on flight mode"""
        if self.flight_mode == "eco":
            self.move_speed = DroneParams.ECO_GND_SPEED
            self.vertical_speed = DroneParams.ECO_VZ_SPEED
            self.yaw_rate = DroneParams.ECO_YAW_RATE
        elif self.flight_mode == "performance":
            self.move_speed = DroneParams.PERF_GND_SPEED
            self.vertical_speed = DroneParams.PERF_VZ_SPEED
            self.yaw_rate = DroneParams.PERF_YAW_RATE
        else:  # standard
            self.move_speed = DroneParams.STD_GND_SPEED
            self.vertical_speed = DroneParams.STD_VZ_SPEED
            self.yaw_rate = DroneParams.STD_YAW_RATE
    
    def setup_grid_zones(self):
        """Define 3x3 grid zones"""
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
    
    def connect_drone(self):
        """Connect to drone"""
        try:
            print(f"Connecting to: {self.connection_string}")
            self.vehicle = connect(self.connection_string, baud=self.baud,
                                 wait_ready=False, timeout=60)
            print("✓ Connected to drone")
            time.sleep(3)
            
            # Ensure GUIDED mode
            if self.vehicle.mode.name != "GUIDED":
                print("Switching to GUIDED mode...")
                self.vehicle.mode = VehicleMode("GUIDED")
                time.sleep(2)
                print(f"Mode: {self.vehicle.mode.name}")
            
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def initialize_face_detection(self):
        """Initialize face cascade"""
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
                    print(f"✓ Loaded face cascade: {path}")
                    return True
        
        print("⚠️  Face cascade not found")
        return False
    
    def start_camera(self):
        """Start USB camera"""
        try:
            self.cap = cv2.VideoCapture(0)
            if self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
                self.camera_active = True
                print("✓ Camera started")
                return True
        except Exception as e:
            print(f"❌ Camera failed: {e}")
        return False
    
    def start_command_sender(self):
        """Start continuous command sending thread"""
        self.command_active = True
        self.command_thread = threading.Thread(target=self._command_loop, daemon=True)
        self.command_thread.start()
        print("✓ Command sender started (10Hz)")
    
    def _command_loop(self):
        """Background thread sending commands at 10Hz"""
        while self.command_active:
            if self.vehicle and self.vehicle.armed:
                try:
                    msg = self.vehicle.message_factory.set_position_target_local_ned_encode(
                        0, 0, 0,
                        mavutil.mavlink.MAV_FRAME_BODY_NED,
                        0b0000111111000111,
                        0, 0, 0,
                        self.current_vx, self.current_vy, self.current_vz,
                        0, 0, 0,
                        0, self.current_yaw
                    )
                    self.vehicle.send_mavlink(msg)
                except Exception as e:
                    print(f"Command error: {e}")
            
            time.sleep(0.1)  # 10Hz
    
    def set_velocity(self, vx, vy, vz, yaw=0):
        """Set velocity command (will be sent continuously)"""
        self.current_vx = vx
        self.current_vy = vy
        self.current_vz = vz
        self.current_yaw = yaw
    
    def stop_movement(self):
        """Stop all movement"""
        self.set_velocity(0, 0, 0, 0)
    
    def key_press(self, event):
        """Handle key press - called by tkinter"""
        key = event.keysym
        self.keyboard_state[key] = True
        
        # Mode switching
        if key == 'space':
            self.autonomous_enabled = not self.autonomous_enabled
            mode = "AUTONOMOUS" if self.autonomous_enabled else "MANUAL"
            print(f"\n{'='*60}")
            print(f"{mode} MODE")
            print(f"{'='*60}\n")
            if not self.autonomous_enabled:
                self.stop_movement()
            self.update_status_display()
        
        elif key == '1':
            self.flight_mode = "eco"
            self.update_speeds()
            print("Flight mode: ECO")
            self.update_status_display()
        
        elif key == '2':
            self.flight_mode = "standard"
            self.update_speeds()
            print("Flight mode: STANDARD")
            self.update_status_display()
        
        elif key == '3':
            self.flight_mode = "performance"
            self.update_speeds()
            print("Flight mode: PERFORMANCE")
            self.update_status_display()
        
        elif key == 't' and self.vehicle:
            if self.vehicle.armed:
                print("Taking off...")
                self.vehicle.simple_takeoff(3.0)
        
        elif key == 'l' and self.vehicle:
            print("Landing...")
            self.vehicle.mode = VehicleMode("LAND")
            self.autonomous_enabled = False
        
        elif key == 'r' and self.vehicle:
            print("RTL...")
            self.vehicle.mode = VehicleMode("RTL")
            self.autonomous_enabled = False
        
        # Manual control (only if not autonomous)
        if not self.autonomous_enabled:
            self.process_manual_control()
    
    def key_release(self, event):
        """Handle key release - called by tkinter"""
        key = event.keysym
        if key in self.keyboard_state:
            self.keyboard_state[key] = False
        
        # Stop movement when keys released (manual mode only)
        if not self.autonomous_enabled:
            movement_keys = ['w', 'a', 's', 'd', 'q', 'e', 'Up', 'Down', 'Left', 'Right']
            if key in movement_keys:
                # Check if any movement keys still pressed
                if not any(self.keyboard_state.get(k, False) for k in movement_keys):
                    self.stop_movement()
    
    def process_manual_control(self):
        """Process current keyboard state for manual control"""
        if not self.vehicle or not self.vehicle.armed:
            return
        
        vx = vy = vz = yaw = 0
        
        # WASD for horizontal movement
        if self.keyboard_state.get('w', False):
            vx = self.move_speed
        if self.keyboard_state.get('s', False):
            vx = -self.move_speed
        if self.keyboard_state.get('a', False):
            vy = -self.move_speed
        if self.keyboard_state.get('d', False):
            vy = self.move_speed
        
        # Q/E for altitude
        if self.keyboard_state.get('q', False):
            vz = -self.vertical_speed
        if self.keyboard_state.get('e', False):
            vz = self.vertical_speed
        
        # Arrow keys for yaw
        if self.keyboard_state.get('Left', False):
            yaw = -np.radians(self.yaw_rate)
        if self.keyboard_state.get('Right', False):
            yaw = np.radians(self.yaw_rate)
        
        # Set the velocity
        self.set_velocity(vx, vy, vz, yaw)
    
    def get_face_zone(self, x, y):
        """Determine which zone the face is in"""
        for zone, (x1, y1, x2, y2) in self.zones.items():
            if x1 <= x < x2 and y1 <= y < y2:
                return zone
        return GridZone.CENTER
    
    def detect_face(self, frame):
        """Detect face in frame"""
        if not self.face_cascade:
            return None
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.05, minNeighbors=6,
            minSize=(50, 50), flags=cv2.CASCADE_SCALE_IMAGE
        )
        
        if len(faces) > 0:
            # Get largest face
            largest = max(faces, key=lambda f: f[2] * f[3])
            x, y, w, h = largest
            
            self.face_center = (x + w // 2, y + h // 2)
            self.face_zone = self.get_face_zone(self.face_center[0], self.face_center[1])
            self.face_detected = True
            
            return largest
        
        self.face_detected = False
        return None
    
    def calculate_autonomous_commands(self):
        """Calculate commands based on face position"""
        if not self.face_detected or self.face_zone == GridZone.CENTER:
            self.stop_movement()
            return
        
        vx = vy = vz = 0
        
        # Horizontal
        if self.face_zone in [GridZone.TOP_LEFT, GridZone.CENTER_LEFT, GridZone.BOTTOM_LEFT]:
            vy = -self.move_speed
        elif self.face_zone in [GridZone.TOP_RIGHT, GridZone.CENTER_RIGHT, GridZone.BOTTOM_RIGHT]:
            vy = self.move_speed
        
        # Vertical
        if self.face_zone in [GridZone.TOP_LEFT, GridZone.TOP_CENTER, GridZone.TOP_RIGHT]:
            vz = -self.vertical_speed
        elif self.face_zone in [GridZone.BOTTOM_LEFT, GridZone.BOTTOM_CENTER, GridZone.BOTTOM_RIGHT]:
            vz = self.vertical_speed
        
        self.set_velocity(vx, vy, vz, 0)
    
    def draw_interface(self, frame, face_rect=None):
        """Draw interface on frame"""
        h, w = frame.shape[:2]
        
        # Title
        cv2.putText(frame, "ElevateXY - Tkinter Control", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Mode
        mode_text = "AUTONOMOUS" if self.autonomous_enabled else "MANUAL"
        mode_color = (0, 255, 0) if self.autonomous_enabled else (0, 165, 255)
        cv2.putText(frame, f"Mode: {mode_text} | {self.flight_mode.upper()}", 
                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, mode_color, 2)
        
        # Draw grid in autonomous mode
        if self.autonomous_enabled:
            col_width = w // 3
            row_height = h // 3
            
            # Grid lines
            for i in range(1, 3):
                cv2.line(frame, (col_width * i, 0), (col_width * i, h), (100, 100, 100), 2)
                cv2.line(frame, (0, row_height * i), (w, row_height * i), (100, 100, 100), 2)
            
            # Center zone
            center = self.zones[GridZone.CENTER]
            cv2.rectangle(frame, (center[0], center[1]), (center[2], center[3]), (0, 255, 0), 2)
            
            # Crosshair
            cx, cy = w // 2, h // 2
            cv2.line(frame, (cx - 30, cy), (cx + 30, cy), (0, 255, 0), 2)
            cv2.line(frame, (cx, cy - 30), (cx, cy + 30), (0, 255, 0), 2)
            cv2.circle(frame, (cx, cy), 50, (0, 255, 0), 2)
            
            # Draw face
            if face_rect is not None:
                x, y, w_box, h_box = face_rect
                color = (0, 255, 0) if self.face_zone == GridZone.CENTER else (0, 255, 255)
                cv2.rectangle(frame, (x, y), (x + w_box, y + h_box), color, 2)
                cv2.circle(frame, self.face_center, 5, (0, 0, 255), -1)
                
                zone_name = self.zone_names[self.face_zone]
                cv2.putText(frame, zone_name, (x, y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        else:
            # Show manual controls
            cv2.putText(frame, "WASD: Move | QE: Alt | Arrows: Yaw", 
                       (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return frame
    
    def camera_loop(self):
        """Camera processing loop"""
        while self.camera_active:
            try:
                ret, frame = self.cap.read()
                if not ret:
                    continue
                
                face_rect = None
                
                # Autonomous mode - detect face
                if self.autonomous_enabled:
                    face_rect = self.detect_face(frame)
                    self.calculate_autonomous_commands()
                
                # Draw interface
                display = self.draw_interface(frame, face_rect)
                
                # Show frame
                cv2.imshow('ElevateXY Simulation', display)
                
                # Handle CV2 window close
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    self.cleanup()
                    break
                    
            except Exception as e:
                print(f"Camera error: {e}")
                break
    
    def update_status_display(self):
        """Update tkinter status display"""
        if not self.status_label or not self.vehicle:
            return
        
        try:
            mode = "AUTONOMOUS" if self.autonomous_enabled else "MANUAL"
            status = f"Mode: {self.vehicle.mode.name} | Armed: {self.vehicle.armed} | Control: {mode} | Flight: {self.flight_mode.upper()}"
            
            if hasattr(self.vehicle, 'location'):
                alt = self.vehicle.location.global_relative_frame.alt
                status += f" | Alt: {alt:.1f}m"
            
            self.status_label.config(text=status)
        except:
            pass
    
    def update_status_loop(self):
        """Periodic status update"""
        if self.command_active:
            self.update_status_display()
            if self.root:
                self.root.after(1000, self.update_status_loop)
    
    def run(self):
        """Run the simulation with tkinter GUI"""
        print("\n" + "="*70)
        print("  ELEVATEXY SIMULATION - TKINTER INPUT")
        print("="*70)
        
        if not GUI_AVAILABLE:
            print("❌ Tkinter not available")
            return
        
        # Connect drone
        if not self.connect_drone():
            return
        
        # Initialize face detection
        self.initialize_face_detection()
        
        # Start camera
        if not self.start_camera():
            print("⚠️  Camera not available - manual control only")
        
        # Start command sender
        self.start_command_sender()
        
        # Create tkinter GUI
        self.root = tk.Tk()
        self.root.title("ElevateXY - Tkinter Control")
        self.root.geometry("600x400")
        
        # Status frame
        status_frame = ttk.Frame(self.root, padding=10)
        status_frame.pack(fill=tk.X)
        
        self.status_label = ttk.Label(status_frame, 
            text=f"Mode: {self.vehicle.mode.name} | Armed: {self.vehicle.armed}")
        self.status_label.pack()
        
        # Controls frame
        control_frame = ttk.LabelFrame(self.root, text="Controls", padding=10)
        control_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        controls_text = """KEYBOARD CONTROLS:
        
Manual Mode (default):
  W/A/S/D - Forward/Left/Back/Right
  Q/E - Up/Down
  Left/Right Arrows - Yaw Left/Right

Flight Modes:
  1 - Eco Mode
  2 - Standard Mode
  3 - Performance Mode

Mode Toggle:
  SPACE - Toggle Autonomous/Manual

Commands:
  T - Takeoff
  L - Land
  R - Return to Launch

Autonomous Mode:
  Position your face in camera view
  Drone will center on your face automatically
  
Press Q in video window to quit"""
        
        control_label = ttk.Label(control_frame, text=controls_text, justify=tk.LEFT)
        control_label.pack()
        
        # Button frame
        button_frame = ttk.Frame(self.root, padding=10)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="Takeoff", 
                  command=lambda: self.vehicle.simple_takeoff(3.0) if self.vehicle and self.vehicle.armed else None).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Land",
                  command=lambda: setattr(self.vehicle, 'mode', VehicleMode("LAND")) if self.vehicle else None).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="RTL",
                  command=lambda: setattr(self.vehicle, 'mode', VehicleMode("RTL")) if self.vehicle else None).pack(side=tk.LEFT, padx=5)
        
        # Bind keyboard events
        self.root.bind('<KeyPress>', self.key_press)
        self.root.bind('<KeyRelease>', self.key_release)
        self.root.focus_set()
        
        # Start camera thread
        if self.camera_active:
            self.camera_thread = threading.Thread(target=self.camera_loop, daemon=True)
            self.camera_thread.start()
        
        # Start status updates
        self.root.after(1000, self.update_status_loop)
        
        print("\n✓ ElevateXY Simulation Ready!")
        print("Focus on the tkinter window for keyboard input")
        print("="*70 + "\n")
        
        # Run tkinter main loop
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            pass
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        print("\nCleaning up...")
        self.command_active = False
        self.camera_active = False
        
        if self.vehicle:
            self.stop_movement()
            self.vehicle.close()
        
        if self.cap:
            self.cap.release()
        
        cv2.destroyAllWindows()
        
        if self.root:
            try:
                self.root.destroy()
            except:
                pass
        
        print("✓ Cleanup complete")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='ElevateXY Simulation - Tkinter')
    parser.add_argument('--connect', default='/dev/ttyUSB0', help='Connection string')
    parser.add_argument('--baud', type=int, default=57600, help='Baud rate')
    
    args = parser.parse_args()
    
    sim = ElevateXYSimulation(args.connect, args.baud)
    sim.run()

if __name__ == "__main__":
    main()
