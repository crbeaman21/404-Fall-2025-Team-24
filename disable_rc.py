#!/usr/bin/env python3
"""
ElevateXY - Disable RC Failsafe Requirement
Allows arming without RC transmitter
"""

import time
from dronekit import connect

def disable_rc_requirement():
    print("="*70)
    print("DISABLE RC FAILSAFE REQUIREMENT")
    print("="*70)
    print()
    print("This will set parameters to allow arming WITHOUT RC transmitter")
    print()
    print("⚠️  WARNING: This removes a safety feature!")
    print("   Only do this if:")
    print("   - You're testing indoors in controlled environment")
    print("   - You have another way to stop the drone (power disconnect)")
    print("   - You understand the risks")
    print()
    
    response = input("Continue? (yes/no): ").strip().lower()
    if response != 'yes':
        print("\nCancelled")
        return
    
    print("\n🔌 Connecting...")
    vehicle = connect('/dev/ttyUSB0', baud=57600, wait_ready=False, timeout=30)
    
    print("⏳ Waiting for connection...")
    vehicle.wait_ready('mode', timeout=10)
    print("✅ Connected\n")
    
    print("📥 Downloading parameters (this may take 30-60 seconds)...")
    print("   Please wait...\n")
    
    try:
        # Wait for parameters with longer timeout
        vehicle.wait_ready('parameters', timeout=90)
        print("✅ Parameters downloaded!\n")
        
        # Set parameters to disable RC requirement
        print("Setting parameters:")
        print("-" * 70)
        
        params_to_set = {
            'FS_THR_ENABLE': 0,      # Disable throttle failsafe
            'FS_GCS_ENABLE': 0,      # Disable GCS failsafe  
            'ARMING_CHECK': 0,       # Disable all pre-arm checks
        }
        
        for param, value in params_to_set.items():
            try:
                print(f"  Setting {param} = {value}... ", end='', flush=True)
                vehicle.parameters[param] = value
                time.sleep(1)
                
                # Verify
                new_value = vehicle.parameters[param]
                if new_value == value:
                    print("✅")
                else:
                    print(f"⚠️  (got {new_value})")
            except Exception as e:
                print(f"❌ {e}")
        
        print()
        print("="*70)
        print("✅ PARAMETERS SET!")
        print("="*70)
        print()
        print("You can now arm without RC transmitter!")
        print()
        print("Next step: Run this command:")
        print("  python3 elevatexy_working.py")
        print()
        
    except Exception as e:
        print(f"\n❌ Parameter download timeout: {e}")
        print()
        print("The parameter download is timing out.")
        print()
        print("SOLUTION: Use MAVProxy to set parameters:")
        print()
        print("1. Run MAVProxy:")
        print("   mavproxy.py --master=/dev/ttyUSB0 --baudrate=57600")
        print()
        print("2. Wait for parameters to download (1-2 minutes)")
        print()
        print("3. Set these parameters:")
        print("   param set FS_THR_ENABLE 0")
        print("   param set FS_GCS_ENABLE 0")
        print("   param set ARMING_CHECK 0")
        print()
        print("4. Exit MAVProxy")
        print()
        print("5. Then Python should be able to arm!")
        print()
    
    vehicle.close()

if __name__ == "__main__":
    disable_rc_requirement()
