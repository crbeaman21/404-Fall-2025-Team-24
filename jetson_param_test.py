from dronekit import connect
import time

print("Connecting to vehicle from Jetson...")
vehicle = connect('/dev/ttyUSB0', baud=57600, wait_ready=True, source_system=42)
print("Connected! Current mode:", vehicle.mode.name)

# Pick a parameter that definitely exists in SITL:
PARAM_NAME = 'SIM_BATT_VOLTAGE'

old = vehicle.parameters.get(PARAM_NAME, None)
print(f"Old {PARAM_NAME}:", old)

# Set a weird, obvious value so we can recognize it
new_value = 23.45
print(f"Setting {PARAM_NAME} to {new_value}...")
vehicle.parameters[PARAM_NAME] = new_value

# Give it a moment to send
time.sleep(3)

print("Done. Disconnecting.")
vehicle.close()
