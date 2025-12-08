#!/usr/bin/env python3
"""
ElevateXY Telemetry Arming Script
Optimized for RFD900/3DR Radio telemetry connections via /dev/ttyUSB0
"""

import time
from dronekit import connect, VehicleMode
from pymavlink import mavutil
import sys

class ElevateXYTelemetryArming:
    """Handle arming and battery configuration via telemetry module"""
    
    def __init__(self, vehicle):
        self.vehicle = vehicle
        
    def configure_6s_battery(self):
        """Configure for 6S LiPo battery"""
        print("\n" + "="*60)
        print("  CONFIGURING 6S LiPo BATTERY")
        print("="*60)
        
        try:
            print("\nSetting battery parameters...")
            print("(This may take longer over telemetry...)")
            
            # Battery monitoring - 6S LiPo
            params_to_set = {
                'BATT_MONITOR': 4,           # Analog voltage and current
                'BATT_CAPACITY': 5000,        # 5000mAh
                'BATT_LOW_VOLT': 21.0,       # 3.5V per cell
                'BATT_CRT_VOLT': 18.0,       # 3.0V per cell
                'BATT_LOW_MAH': 1000,        # Low capacity warning
                'BATT_CRT_MAH': 500,         # Critical capacity
            }
            
            for param, value in params_to_set.items():
                try:
                    self.vehicle.parameters[param] = value
                    print(f"  ✓ Set {param} = {value}")
                    time.sleep(0.5)  # Longer delay for telemetry
                except Exception as e:
                    print(f"  ⚠️  Could not set {param}: {e}")
            
            print("\n✓ Battery configured for 6S LiPo")
            print(f"  Nominal: 22.2V (3.7V × 6 cells)")
            print(f"  Low: 21.0V (3.5V × 6 cells)")
            print(f"  Critical: 18.0V (3.0V × 6 cells)")
            
            # Give parameters time to sync
            time.sleep(2)
            
            # Check battery voltage
            if hasattr(self.vehicle, 'battery') and self.vehicle.battery:
                if hasattr(self.vehicle.battery, 'voltage') and self.vehicle.battery.voltage:
                    voltage = self.vehicle.battery.voltage
                    print(f"\n✓ Current battery voltage: {voltage:.1f}V")
                    
                    if voltage < 18.0:
                        print(f"⚠️  WARNING: Battery voltage critically low!")
                        print("   Check physical battery connection")
                    elif voltage >= 20.0:
                        print("✓ Battery voltage good!")
            
        except Exception as e:
            print(f"❌ Error configuring battery: {e}")
    
    def disable_arming_checks(self):
        """Disable safety checks (use carefully!)"""
        print("\n" + "="*60)
        print("  CONFIGURING ARMING CHECKS")
        print("="*60)
        
        try:
            print("Adjusting arming requirements...")
            
            # For real drone, keep most checks enabled
            # Only disable GPS if testing indoors
            self.vehicle.parameters['ARMING_CHECK'] = 1  # Keep basic checks
            time.sleep(0.5)
            
            # For indoor testing without GPS
            # Uncomment this line if you need to fly indoors:
            # self.vehicle.parameters['ARMING_CHECK'] = 0
            
            print("✓ Arming checks configured")
            print("  (Keeping safety checks enabled for real drone)")
            
        except Exception as e:
            print(f"⚠️  Could not modify arming checks: {e}")
    
    def wait_for_armable(self, timeout=30):
        """Wait for vehicle to be armable"""
        print("\nWaiting for vehicle to be armable...")
        print("(EKF initialization can take 10-30 seconds...)")
        
        start_time = time.time()
        last_status = None
        
        while not self.vehicle.is_armable:
            elapsed = time.time() - start_time
            
            if elapsed > timeout:
                print(f"❌ Timeout after {timeout}s")
                return False
            
            # Show status updates
            status = self.vehicle.system_status.state
            if status != last_status:
                print(f"  System status: {status}")
                last_status = status
            
            time.sleep(1)
        
        print("✓ Vehicle is armable")
        return True
    
    def check_pre_arm_status(self):
        """Check and display pre-arm status"""
        print("\n" + "-"*60)
        print("  PRE-ARM STATUS CHECK")
        print("-"*60)
        
        print(f"Mode: {self.vehicle.mode.name}")
        print(f"Armed: {self.vehicle.armed}")
        print(f"Armable: {self.vehicle.is_armable}")
        print(f"System Status: {self.vehicle.system_status.state}")
        
        # Battery
        if hasattr(self.vehicle, 'battery') and self.vehicle.battery:
            if hasattr(self.vehicle.battery, 'voltage') and self.vehicle.battery.voltage:
                print(f"Battery Voltage: {self.vehicle.battery.voltage:.1f}V")
            if hasattr(self.vehicle.battery, 'level') and self.vehicle.battery.level:
                print(f"Battery Level: {self.vehicle.battery.level}%")
            if hasattr(self.vehicle.battery, 'current') and self.vehicle.battery.current:
                print(f"Battery Current: {self.vehicle.battery.current:.1f}A")
        
        # GPS
        if hasattr(self.vehicle, 'gps_0'):
            print(f"GPS: {self.vehicle.gps_0.fix_type} (Sats: {self.vehicle.gps_0.satellites_visible})")
        
        # EKF
        if hasattr(self.vehicle, 'ekf_ok'):
            print(f"EKF Status: {'OK' if self.vehicle.ekf_ok else 'NOT READY'}")
        
        print("-"*60)
    
    def arm_vehicle(self, guided=True):
        """Arm the vehicle"""
        print("\n" + "="*60)
        print("  ARMING VEHICLE")
        print("="*60)
        
        # Check if already armed
        if self.vehicle.armed:
            print("✓ Vehicle is already armed!")
            return True
        
        # Check pre-arm status
        self.check_pre_arm_status()
        
        # Wait for vehicle to be armable
        if not self.wait_for_armable():
            print("\n⚠️  Vehicle not armable.")
            print("\nPossible issues:")
            print("  1. EKF not initialized (wait longer)")
            print("  2. GPS not locked (need outdoor or disable GPS check)")
            print("  3. Battery voltage too low")
            print("  4. RC not calibrated")
            
            response = input("\nTry to arm anyway? (y/n): ")
            if response.lower() != 'y':
                return False
        
        # Switch to GUIDED mode
        if guided:
            print("\nSwitching to GUIDED mode...")
            self.vehicle.mode = VehicleMode("GUIDED")
            
            timeout = 10
            start_time = time.time()
            while self.vehicle.mode.name != "GUIDED":
                if time.time() - start_time > timeout:
                    print("❌ Failed to switch to GUIDED mode")
                    print("   You may need to switch manually")
                    return False
                time.sleep(0.5)
            
            print(f"✓ Mode: {self.vehicle.mode.name}")
        
        # Arm
        print("\nSending arm command...")
        print("(This may take a few seconds over telemetry...)")
        self.vehicle.armed = True
        
        # Wait for arming with status updates
        timeout = 15
        start_time = time.time()
        while not self.vehicle.armed:
            elapsed = time.time() - start_time
            
            if elapsed > timeout:
                print("❌ Failed to arm vehicle")
                print("\nCheck ArduCopter messages for errors")
                return False
            
            print(f"  Waiting for arming... ({int(elapsed)}s)")
            time.sleep(0.5)
        
        print("\n" + "="*60)
        print("  ✓✓✓ VEHICLE ARMED! ✓✓✓")
        print("="*60)
        return True
    
    def takeoff(self, target_altitude=3.0):
        """Takeoff to specified altitude"""
        print("\n" + "="*60)
        print(f"  TAKING OFF TO {target_altitude}m")
        print("="*60)
        
        if not self.vehicle.armed:
            print("❌ Vehicle not armed!")
            return False
        
        if self.vehicle.mode.name != "GUIDED":
            print("Switching to GUIDED mode...")
            self.vehicle.mode = VehicleMode("GUIDED")
            time.sleep(2)
        
        print(f"\nSending takeoff command...")
        self.vehicle.simple_takeoff(target_altitude)
        
        # Monitor altitude
        print("\nClimbing...")
        last_alt = 0
        
        while True:
            current_alt = self.vehicle.location.global_relative_frame.alt
            
            # Only print if altitude changed
            if abs(current_alt - last_alt) > 0.2:
                print(f"  Altitude: {current_alt:.1f}m / {target_altitude}m")
                last_alt = current_alt
            
            # Break when close to target
            if current_alt >= target_altitude * 0.95:
                print(f"\n✓ Reached target altitude: {current_alt:.1f}m")
                break
            
            time.sleep(1)
        
        return True
    
    def full_startup_sequence(self, takeoff_alt=3.0):
        """Complete startup sequence"""
        print("\n" + "="*70)
        print("  ELEVATEXY TELEMETRY STARTUP SEQUENCE")
        print("="*70)
        
        # Configure battery
        self.configure_6s_battery()
        
        # Configure arming
        self.disable_arming_checks()
        
        # Arm
        if not self.arm_vehicle():
            return False
        
        # Takeoff if requested
        if takeoff_alt > 0:
            response = input(f"\nTakeoff to {takeoff_alt}m? (y/n): ")
            if response.lower() == 'y':
                if not self.takeoff(takeoff_alt):
                    return False
        
        print("\n" + "="*70)
        print("  ✓ ELEVATEXY READY FOR OPERATION")
        print("="*70)
        return True

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='ElevateXY Telemetry Arming',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Telemetry module (most common for ElevateXY)
  python3 elevatexy_telemetry_arming.py --connect /dev/ttyUSB0 --baud 57600
  
  # RFD900 (higher baud)
  python3 elevatexy_telemetry_arming.py --connect /dev/ttyUSB0 --baud 115200
  
  # 3DR Radio
  python3 elevatexy_telemetry_arming.py --connect /dev/ttyACM0 --baud 57600

This script will:
1. Connect via telemetry module
2. Configure for 6S LiPo battery
3. Setup arming parameters
4. Arm the vehicle
5. Optionally takeoff

Perfect for ElevateXY with radio telemetry!
        """
    )
    
    parser.add_argument(
        '--connect',
        default='/dev/ttyUSB0',
        help='Serial device (default: /dev/ttyUSB0)'
    )
    
    parser.add_argument(
        '--baud',
        type=int,
        default=57600,
        help='Baud rate (default: 57600)'
    )
    
    parser.add_argument(
        '--no-takeoff',
        action='store_true',
        help='Arm only, do not takeoff'
    )
    
    args = parser.parse_args()
    
    print("="*70)
    print("  ELEVATEXY - TELEMETRY ARMING")
    print("="*70)
    print(f"\nDevice: {args.connect}")
    print(f"Baud rate: {args.baud}")
    
    # Connect
    print("\nConnecting to vehicle via telemetry...")
    print("(This may take 10-30 seconds...)")
    
    try:
        vehicle = connect(args.connect, baud=args.baud, wait_ready=False, timeout=60)
        print("✓ Connected!")
    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Check telemetry module is connected: ls /dev/ttyUSB*")
        print("2. Check baud rate matches telemetry config")
        print("3. Verify telemetry module has power")
        print("4. Try: sudo chmod 666 /dev/ttyUSB0")
        sys.exit(1)
    
    # Wait for vehicle initialization
    print("\nWaiting for vehicle initialization...")
    time.sleep(5)
    
    # Create arming handler
    arming = ElevateXYTelemetryArming(vehicle)
    
    # Show initial status
    arming.check_pre_arm_status()
    
    # Ask for startup sequence
    print("\n" + "="*70)
    print("Options:")
    print("  1. Full startup (configure + arm + takeoff)")
    print("  2. Arm only (no takeoff)")
    print("  3. Status check only (no changes)")
    choice = input("\nSelect option (1/2/3): ").strip()
    
    if choice == '1':
        # Full startup
        takeoff_alt = 3.0
        success = arming.full_startup_sequence(takeoff_alt)
        
        if success:
            print("\n✓ Hovering and ready!")
            print("\nYou can now:")
            print("  - Run your ElevateXY simulation")
            print("  - Send manual commands")
            print("  - Enable autonomous mode")
            
            input("\nPress ENTER to land and exit...")
            
            print("\nLanding...")
            vehicle.mode = VehicleMode("LAND")
            
            while vehicle.armed:
                alt = vehicle.location.global_relative_frame.alt
                print(f"  Altitude: {alt:.1f}m")
                time.sleep(1)
            
            print("✓ Landed and disarmed")
    
    elif choice == '2':
        # Arm only
        arming.configure_6s_battery()
        arming.disable_arming_checks()
        success = arming.arm_vehicle()
        
        if success:
            print("\n✓ Vehicle armed and ready!")
            print("You can now takeoff manually or run ElevateXY simulation")
            input("\nPress ENTER to disarm...")
            
            vehicle.armed = False
            print("✓ Disarmed")
    
    elif choice == '3':
        # Status only
        print("\n✓ Status check complete")
        print("No changes made to vehicle")
    
    else:
        print("Invalid choice")
    
    # Close
    vehicle.close()
    print("\n✓ Connection closed")

if __name__ == "__main__":
    main()
