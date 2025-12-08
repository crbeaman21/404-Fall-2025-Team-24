#!/usr/bin/env python3
"""
ElevateXY Simulation with Pynput Global Keyboard Capture
Captures keyboard input regardless of window focus
"""

import time
import threading
import cv2
import numpy as np
from dronekit import connect, VehicleMode
from pymavlink import mavutil

# Pynput for global keyboard capture
try:
    from pynput import keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False
    print("⚠️  Installing pynput...")
    import subprocess
    subprocess.run(['pip3', 'install', 'pynput', '--break-system-packages'], check=False)
    try:
        from pynput import keyboard
        PYNPUT_AVAILABLE = True
        print("✓ Pynput installed successfully")
    except:
        print("❌ Could not install pynput")

class DroneParams:
    """Flight mode parameters"""
    STD_GND_SPEED = 3.0
    STD_VZ_SPEED = 0.5
    STD_YAW_RATE = 30
    
    ECO_GND_SPEED = 2.0
    ECO_VZ_SPEED = 0.35
    ECO_YAW_RATE = 20
    
    PERF_GND_SPEED = 4.5
    PERF_VZ_SPEED = 0.75
    PERF_YAW_RATE = 45

class GridZone:
    TOP_LEFT = 0
    TOP_CENTER = 1
    TOP_RIGHT = 2
    CENTER_LEFT = 3
    CENTER = 4
    CENTER_RIGHT = 5
    BOTTOM_LEFT = 6
    BOTTOM_CENTER = 7
    BOTTOM_RIGHT = 8

class ElevateXYPynput:
    def __init__(self, connection_string='/dev/ttyUSB0', baud=57600):
        """Initialize with pynput keyboard listener"""
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
        
        # Control
        self.autonomous_enabled = False
        self.flight_mode = "standard"
        self.keys_pressed = set()  # Currently pressed keys
        
        self.update_speeds()
        
        # Command sending
        self.command_thread = None
        self.command_active = False
        self.current_vx = 0
        self.current_vy = 0
        self.current_vz = 0
        self.current_yaw = 0
        
        # Keyboard listener
        self.keyboard_listener = None
        
        # Grid zones
        self.setup_grid_zones()
        
    def setup_grid_zones(self):
        """Setup 3x3 grid"""
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
        else:
            self.move_speed = DroneParams.STD_GND_SPEED
            self.vertical_speed = DroneParams.STD_VZ_SPEED
            self.yaw_rate = DroneParams.STD_YAW_RATE
    
    def connect_drone(self):
        """Connect to drone"""
        try:
            print(f"Connecting to: {self.connection_string}")
            self.vehicle = connect(self.connection_string, baud=self.baud,
                                 wait_ready=False, timeout=60)
            print("✓ Connected")
            time.sleep(3)
            
            # Switch to GUIDED
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
        paths = [
            os.path.expanduser('~/opencv_cascades/haarcascade_frontalface_default.xml'),
            '/usr/share/opencv/haarcascades/haarcascade_frontalface_default.xml',
            '/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml',
        ]
        
        for path in paths:
            if os.path.exists(path):
                self.face_cascade = cv2.CascadeClassifier(path)
                if not self.face_cascade.empty():
                    print(f"✓ Face detection ready")
                    return True
        
        print("⚠️  Face detection not available")
        return False
    
    def start_camera(self):
        """Start camera"""
        try:
            self.cap = cv2.VideoCapture(0)
            if self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
                self.camera_active = True
                print("✓ Camera started")
                return True
        except:
            pass
        return False
    
    def start_command_sender(self):
        """Start command sender thread"""
        self.command_active = True
        self.command_thread = threading.Thread(target=self._command_loop, daemon=True)
        self.command_thread.start()
        print("✓ Command sender started (10Hz)")
    
    def _command_loop(self):
        """Send commands at 10Hz"""
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
            
            time.sleep(0.1)
    
    def set_velocity(self, vx, vy, vz, yaw=0):
        """Set velocity"""
        self.current_vx = vx
        self.current_vy = vy
        self.current_vz = vz
        self.current_yaw = yaw
    
    def on_press(self, key):
        """Handle key press - called by pynput"""
        try:
            # Get key character
            if hasattr(key, 'char') and key.char:
                k = key.char.lower()
            else:
                k = str(key).replace('Key.', '')
            
            # Add to pressed keys
            self.keys_pressed.add(k)
            
            # Handle special keys
            if k == 'space':
                self.autonomous_enabled = not self.autonomous_enabled
                mode = "AUTONOMOUS" if self.autonomous_enabled else "MANUAL"
                print(f"\n{'='*60}")
                print(f"{mode} MODE")
                print(f"{'='*60}\n")
                if not self.autonomous_enabled:
                    self.set_velocity(0, 0, 0, 0)
                return
            
            elif k == '1':
                self.flight_mode = "eco"
                self.update_speeds()
                print("Flight mode: ECO")
                return
            
            elif k == '2':
                self.flight_mode = "standard"
                self.update_speeds()
                print("Flight mode: STANDARD")
                return
            
            elif k == '3':
                self.flight_mode = "performance"
                self.update_speeds()
                print("Flight mode: PERFORMANCE")
                return
            
            elif k == 't' and self.vehicle:
                if self.vehicle.armed:
                    print("Taking off...")
                    self.vehicle.simple_takeoff(3.0)
                return
            
            elif k == 'l' and self.vehicle:
                print("Landing...")
                self.vehicle.mode = VehicleMode("LAND")
                self.autonomous_enabled = False
                return
            
            elif k == 'r' and self.vehicle:
                print("RTL...")
                self.vehicle.mode = VehicleMode("RTL")
                self.autonomous_enabled = False
                return
            
            elif k == 'esc':
                print("ESC pressed - exiting...")
                self.cleanup()
                return False  # Stop listener
            
            # Process movement (manual mode only)
            if not self.autonomous_enabled:
                self.process_manual_keys()
                
        except Exception as e:
            print(f"Key press error: {e}")
    
    def on_release(self, key):
        """Handle key release - called by pynput"""
        try:
            if hasattr(key, 'char') and key.char:
                k = key.char.lower()
            else:
                k = str(key).replace('Key.', '')
            
            # Remove from pressed keys
            self.keys_pressed.discard(k)
            
            # Update movement if in manual mode
            if not self.autonomous_enabled:
                self.process_manual_keys()
                
        except:
            pass
    
    def process_manual_keys(self):
        """Process currently pressed keys"""
        if not self.vehicle or not self.vehicle.armed:
            return
        
        vx = vy = vz = yaw = 0
        
        # Movement
        if 'w' in self.keys_pressed:
            vx = self.move_speed
            print(f"Manual: FORWARD ({vx:.1f} m/s)")
        if 's' in self.keys_pressed:
            vx = -self.move_speed
            print(f"Manual: BACKWARD ({vx:.1f} m/s)")
        if 'a' in self.keys_pressed:
            vy = -self.move_speed
            print(f"Manual: LEFT ({vy:.1f} m/s)")
        if 'd' in self.keys_pressed:
            vy = self.move_speed
            print(f"Manual: RIGHT ({vy:.1f} m/s)")
        
        # Altitude
        if 'q' in self.keys_pressed:
            vz = -self.vertical_speed
            print(f"Manual: UP ({vz:.1f} m/s)")
        if 'e' in self.keys_pressed:
            vz = self.vertical_speed
            print(f"Manual: DOWN ({vz:.1f} m/s)")
        
        # Yaw
        if 'left' in self.keys_pressed:
            yaw = -np.radians(self.yaw_rate)
            print(f"Manual: YAW LEFT")
        if 'right' in self.keys_pressed:
            yaw = np.radians(self.yaw_rate)
            print(f"Manual: YAW RIGHT")
        
        self.set_velocity(vx, vy, vz, yaw)
    
    def start_keyboard_listener(self):
        """Start pynput keyboard listener"""
        if not PYNPUT_AVAILABLE:
            print("❌ Pynput not available")
            return False
        
        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        )
        self.keyboard_listener.start()
        print("✓ Global keyboard listener started")
        print("   Keys captured system-wide - no window focus needed!")
        return True
    
    def get_face_zone(self, x, y):
        """Get zone for face position"""
        for zone, (x1, y1, x2, y2) in self.zones.items():
            if x1 <= x < x2 and y1 <= y < y2:
                return zone
        return GridZone.CENTER
    
    def detect_face(self, frame):
        """Detect face"""
        if not self.face_cascade:
            return None
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.05, minNeighbors=6,
            minSize=(50, 50), flags=cv2.CASCADE_SCALE_IMAGE
        )
        
        if len(faces) > 0:
            largest = max(faces, key=lambda f: f[2] * f[3])
            x, y, w, h = largest
            
            self.face_center = (x + w // 2, y + h // 2)
            self.face_zone = self.get_face_zone(self.face_center[0], self.face_center[1])
            self.face_detected = True
            
            return largest
        
        self.face_detected = False
        return None
    
    def calculate_autonomous_commands(self):
        """Calculate autonomous movement"""
        if not self.face_detected or self.face_zone == GridZone.CENTER:
            self.set_velocity(0, 0, 0, 0)
            return
        
        vx = vy = vz = 0
        
        if self.face_zone in [GridZone.TOP_LEFT, GridZone.CENTER_LEFT, GridZone.BOTTOM_LEFT]:
            vy = -self.move_speed
        elif self.face_zone in [GridZone.TOP_RIGHT, GridZone.CENTER_RIGHT, GridZone.BOTTOM_RIGHT]:
            vy = self.move_speed
        
        if self.face_zone in [GridZone.TOP_LEFT, GridZone.TOP_CENTER, GridZone.TOP_RIGHT]:
            vz = -self.vertical_speed
        elif self.face_zone in [GridZone.BOTTOM_LEFT, GridZone.BOTTOM_CENTER, GridZone.BOTTOM_RIGHT]:
            vz = self.vertical_speed
        
        self.set_velocity(vx, vy, vz, 0)
    
    def draw_interface(self, frame, face_rect=None):
        """Draw interface"""
        h, w = frame.shape[:2]
        
        cv2.putText(frame, "ElevateXY - Pynput Control", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        mode_text = "AUTONOMOUS" if self.autonomous_enabled else "MANUAL"
        mode_color = (0, 255, 0) if self.autonomous_enabled else (0, 165, 255)
        cv2.putText(frame, f"{mode_text} | {self.flight_mode.upper()}", 
                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, mode_color, 2)
        
        # Show armed status
        if self.vehicle:
            armed_text = "ARMED" if self.vehicle.armed else "DISARMED"
            armed_color = (0, 255, 0) if self.vehicle.armed else (0, 0, 255)
            cv2.putText(frame, armed_text, (10, 90),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, armed_color, 2)
        
        if self.autonomous_enabled:
            col_width = w // 3
            row_height = h // 3
            
            for i in range(1, 3):
                cv2.line(frame, (col_width * i, 0), (col_width * i, h), (100, 100, 100), 2)
                cv2.line(frame, (0, row_height * i), (w, row_height * i), (100, 100, 100), 2)
            
            center = self.zones[GridZone.CENTER]
            cv2.rectangle(frame, (center[0], center[1]), (center[2], center[3]), (0, 255, 0), 2)
            
            cx, cy = w // 2, h // 2
            cv2.line(frame, (cx - 30, cy), (cx + 30, cy), (0, 255, 0), 2)
            cv2.line(frame, (cx, cy - 30), (cx, cy + 30), (0, 255, 0), 2)
            
            if face_rect is not None:
                x, y, w_box, h_box = face_rect
                color = (0, 255, 0) if self.face_zone == GridZone.CENTER else (0, 255, 255)
                cv2.rectangle(frame, (x, y), (x + w_box, y + h_box), color, 2)
        else:
            cv2.putText(frame, "WASD: Move | QE: Alt | Arrows: Yaw | ESC: Exit", 
                       (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return frame
    
    def run(self):
        """Run simulation"""
        print("\n" + "="*70)
        print("  ELEVATEXY - PYNPUT GLOBAL KEYBOARD CAPTURE")
        print("="*70)
        print("\n✨ Keys work ANYWHERE - no window focus needed!")
        print("\nControls:")
        print("  W/A/S/D - Forward/Left/Back/Right")
        print("  Q/E - Up/Down")
        print("  Left/Right Arrows - Yaw")
        print("  SPACE - Toggle Autonomous/Manual")
        print("  1/2/3 - Eco/Standard/Performance")
        print("  T - Takeoff | L - Land | R - RTL")
        print("  ESC - Exit")
        print("="*70 + "\n")
        
        if not PYNPUT_AVAILABLE:
            print("❌ Pynput required but not available")
            return
        
        if not self.connect_drone():
            return
        
        self.initialize_face_detection()
        
        if not self.start_camera():
            print("⚠️  Camera not available")
        
        self.start_command_sender()
        
        if not self.start_keyboard_listener():
            return
        
        print("\n✓ System ready!")
        print("✓ Keyboard listener active - press keys anywhere\n")
        
        # Main loop
        try:
            while self.command_active:
                if self.camera_active:
                    ret, frame = self.cap.read()
                    if ret:
                        face_rect = None
                        
                        if self.autonomous_enabled:
                            face_rect = self.detect_face(frame)
                            self.calculate_autonomous_commands()
                        
                        display = self.draw_interface(frame, face_rect)
                        cv2.imshow('ElevateXY', display)
                        
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            break
                else:
                    time.sleep(0.1)
                    
        except KeyboardInterrupt:
            print("\nInterrupted")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Cleanup"""
        print("\nCleaning up...")
        self.command_active = False
        self.camera_active = False
        
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        
        if self.vehicle:
            self.set_velocity(0, 0, 0, 0)
            time.sleep(0.5)
            self.vehicle.close()
        
        if self.cap:
            self.cap.release()
        
        cv2.destroyAllWindows()
        print("✓ Cleanup complete")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='ElevateXY - Pynput')
    parser.add_argument('--connect', default='/dev/ttyUSB0')
    parser.add_argument('--baud', type=int, default=57600)
    
    args = parser.parse_args()
    
    sim = ElevateXYPynput(args.connect, args.baud)
    sim.run()

if __name__ == "__main__":
    main()
