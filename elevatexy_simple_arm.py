#!/usr/bin/env python3
"""
ElevateXY Simple Arming Script
Just arms the drone - no parameter changes
Assumes battery and parameters are already configured
"""

import time
from dronekit import connect, VehicleMode
import sys

class SimpleArming:
    """Simple arming handler - no parameter modifications"""
    
    def __init__(self, vehicle):
        self.vehicle = vehicle
    
    def check_status(self):
        """Display current vehicle status"""
        print("\n" + "-"*60)
        print("  VEHICLE STATUS")
        print("-"*60)
        
        print(f"Mode: {self.vehicle.mode.name}")
        print(f"Armed: {self.vehicle.armed}")
        print(f"Armable: {self.vehicle.is_armable}")
        print(f"System Status: {self.vehicle.system_status.state}")
        
        # Battery
        if hasattr(self.vehicle, 'battery') and self.vehicle.battery:
            if hasattr(self.vehicle.battery, 'voltage') and self.vehicle.battery.voltage:
                voltage = self.vehicle.battery.voltage
                print(f"Battery Voltage: {voltage:.1f}V")
                
                # Color code voltage
                if voltage >= 22.0:
                    status = "GOOD"
                elif voltage >= 21.0:
                    status = "LOW"
                else:
                    status = "CRITICAL"
                print(f"Battery Status: {status}")
                
            if hasattr(self.vehicle.battery, 'level') and self.vehicle.battery.level:
                print(f"Battery Level: {self.vehicle.battery.level}%")
        
        # GPS
        if hasattr(self.vehicle, 'gps_0'):
            fix_type = self.vehicle.gps_0.fix_type
            sats = self.vehicle.gps_0.satellites_visible
            print(f"GPS: Fix Type {fix_type} ({sats} satellites)")
            
            if fix_type >= 3:
                print("GPS Status: GOOD (3D Fix)")
            elif fix_type == 2:
                print("GPS Status: 2D Fix (may not be sufficient)")
            else:
                print("GPS Status: NO FIX")
        
        # EKF
        if hasattr(self.vehicle, 'ekf_ok'):
            ekf_status = "OK" if self.vehicle.ekf_ok else "NOT READY"
            print(f"EKF Status: {ekf_status}")
        
        print("-"*60)
    
    def wait_for_armable(self, timeout=30):
        """Wait for vehicle to be armable"""
        print("\nWaiting for vehicle to be armable...")
        
        start_time = time.time()
        last_status = None
        
        while not self.vehicle.is_armable:
            elapsed = time.time() - start_time
            
            if elapsed > timeout:
                print(f"\n❌ Timeout after {timeout}s")
                print("\nVehicle is not armable. Possible reasons:")
                print("  - EKF not initialized (wait longer)")
                print("  - GPS not locked (need outdoor or disable GPS check)")
                print("  - Battery voltage too low")
                print("  - Pre-arm checks failing")
                print("\nCheck your ground station for specific errors.")
                return False
            
            # Show status updates
            status = self.vehicle.system_status.state
            if status != last_status:
                print(f"  System status: {status} ({int(elapsed)}s)")
                last_status = status
            
            time.sleep(1)
        
        print("✓ Vehicle is armable")
        return True
    
    def arm_vehicle(self, guided=True, force=False):
        """Arm the vehicle"""
        print("\n" + "="*60)
        print("  ARMING VEHICLE")
        print("="*60)
        
        # Check if already armed
        if self.vehicle.armed:
            print("✓ Vehicle is already armed!")
            return True
        
        # Show current status
        self.check_status()
        
        # Wait for armable if not forcing
        if not force:
            if not self.wait_for_armable():
                response = input("\nTry to arm anyway? (y/n): ")
                if response.lower() != 'y':
                    return False
        
        # Switch to GUIDED mode if requested
        if guided:
            print("\nSwitching to GUIDED mode...")
            self.vehicle.mode = VehicleMode("GUIDED")
            
            # Wait for mode change
            timeout = 10
            start_time = time.time()
            while self.vehicle.mode.name != "GUIDED":
                if time.time() - start_time > timeout:
                    print("⚠️  Failed to switch to GUIDED mode")
                    print("   Trying to arm in current mode instead...")
                    guided = False  # Disable guided mode requirement
                    break
                time.sleep(0.5)
            
            if guided:
                print(f"✓ Mode: {self.vehicle.mode.name}")
        
        # Arm
        print("\nSending arm command...")
        print(f"Arming in {self.vehicle.mode.name} mode...")
        self.vehicle.armed = True
        
        # Wait for arming
        timeout = 15
        start_time = time.time()
        while not self.vehicle.armed:
            elapsed = time.time() - start_time
            
            if elapsed > timeout:
                print("❌ Failed to arm vehicle")
                print("\nCheck for error messages in your ground station.")
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
            
            # Print altitude changes
            if abs(current_alt - last_alt) > 0.2:
                print(f"  Altitude: {current_alt:.1f}m / {target_altitude}m")
                last_alt = current_alt
            
            # Break when close to target
            if current_alt >= target_altitude * 0.95:
                print(f"\n✓ Reached target altitude: {current_alt:.1f}m")
                break
            
            time.sleep(1)
        
        return True
    
    def disarm(self):
        """Disarm the vehicle"""
        print("\nDisarming...")
        self.vehicle.armed = False
        
        # Wait for disarm
        timeout = 5
        start_time = time.time()
        while self.vehicle.armed:
            if time.time() - start_time > timeout:
                print("❌ Failed to disarm")
                return False
            time.sleep(0.5)
        
        print("✓ Disarmed")
        return True
    
    def land(self):
        """Land the vehicle"""
        print("\nLanding...")
        self.vehicle.mode = VehicleMode("LAND")
        
        # Monitor landing
        while self.vehicle.armed:
            alt = self.vehicle.location.global_relative_frame.alt
            print(f"  Altitude: {alt:.1f}m")
            time.sleep(1)
        
        print("✓ Landed and disarmed")
        return True

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='ElevateXY Simple Arming - No Parameter Changes',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Telemetry module
  python3 elevatexy_simple_arm.py --connect /dev/ttyUSB0 --baud 57600
  
  # Network (simulation)
  python3 elevatexy_simple_arm.py --connect udpin:0.0.0.0:14550
  
  # Serial
  python3 elevatexy_simple_arm.py --connect /dev/ttyACM0 --baud 115200

This script ONLY arms the vehicle. It does NOT modify any parameters.
Configure your battery settings and other parameters on your laptop first.

Options:
  --arm-only      Arm and exit (no takeoff)
  --takeoff N     Takeoff to N meters (default: 3.0)
  --force         Skip armable check (use carefully!)
        """
    )
    
    parser.add_argument(
        '--connect',
        required=True,
        help='Connection string (e.g., /dev/ttyUSB0 or udpin:0.0.0.0:14550)'
    )
    
    parser.add_argument(
        '--baud',
        type=int,
        default=57600,
        help='Baud rate for serial connection (default: 57600)'
    )
    
    parser.add_argument(
        '--arm-only',
        action='store_true',
        help='Arm only, do not takeoff'
    )
    
    parser.add_argument(
        '--takeoff',
        type=float,
        default=3.0,
        help='Takeoff altitude in meters (default: 3.0)'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force arming even if not armable'
    )
    
    parser.add_argument(
        '--no-guided',
        action='store_true',
        help='Arm in current mode (do not switch to GUIDED)'
    )
    
    args = parser.parse_args()
    
    print("="*70)
    print("  ELEVATEXY - SIMPLE ARMING (No Parameter Changes)")
    print("="*70)
    print(f"\nConnection: {args.connect}")
    if args.connect.startswith('/dev/'):
        print(f"Baud rate: {args.baud}")
    
    # Connect
    print("\nConnecting to vehicle...")
    
    try:
        if args.connect.startswith('/dev/'):
            vehicle = connect(args.connect, baud=args.baud, wait_ready=False, timeout=60)
        else:
            vehicle = connect(args.connect, wait_ready=False, timeout=60)
        print("✓ Connected!")
    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        print("\nTroubleshooting:")
        if args.connect.startswith('/dev/'):
            print(f"1. Check device exists: ls {args.connect}")
            print(f"2. Check permissions: sudo chmod 666 {args.connect}")
            print("3. Verify baud rate matches telemetry configuration")
        else:
            print("1. Check vehicle/SITL is running")
            print("2. Verify connection string format")
            print("3. Check network connectivity")
        sys.exit(1)
    
    # Wait for initialization
    print("\nWaiting for vehicle initialization...")
    time.sleep(3)
    
    # Create arming handler
    arming = SimpleArming(vehicle)
    
    # Show status
    arming.check_status()
    
    print("\n" + "="*70)
    print("  READY TO ARM")
    print("="*70)
    print("\nThis script will NOT modify any parameters.")
    print("Make sure battery and parameters are configured on your laptop.")
    
    # Ask user
    if args.arm_only:
        # Arm only mode
        print("\nArm-only mode selected")
        if arming.arm_vehicle(guided=not args.no_guided, force=args.force):
            print("\n✓ Vehicle armed!")
            print("You can now run your ElevateXY simulation or send commands.")
            input("\nPress ENTER to disarm and exit...")
            arming.disarm()
    else:
        # Full sequence
        response = input("\nArm and takeoff? (y/n): ")
        
        if response.lower() == 'y':
            # Arm
            if not arming.arm_vehicle(guided=not args.no_guided, force=args.force):
                print("Arming failed!")
                vehicle.close()
                sys.exit(1)
            
            # Takeoff
            print(f"\nTakeoff to {args.takeoff}m?")
            response = input("Press ENTER to takeoff (or 'n' to skip): ")
            
            if response.lower() != 'n':
                arming.takeoff(args.takeoff)
                
                print("\n✓ Hovering and ready!")
                print("You can now run your ElevateXY simulation.")
                
                input("\nPress ENTER to land and exit...")
                arming.land()
            else:
                print("\n✓ Armed and ready (not taking off)")
                input("\nPress ENTER to disarm...")
                arming.disarm()
        else:
            print("\nCancelled - no changes made")
    
    # Close
    vehicle.close()
    print("\n✓ Connection closed")

if __name__ == "__main__":
    main()
