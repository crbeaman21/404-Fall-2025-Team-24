# test_jetson_control.py
from dronekit import connect, VehicleMode
import time

print("Connecting...")
vehicle = connect('/dev/ttyUSB0', baud=57600, wait_ready=True, source_system=1)
print("Connected! Mode is", vehicle.mode.name)

print("Changing mode to LOITER...")
vehicle.mode = VehicleMode("LOITER")
vehicle.flush()
time.sleep(3)
print("New mode is", vehicle.mode.name)

vehicle.mode = VehicleMode("GUIDED")
vehicle.armed = True
vehicle.flush()

while not vehicle.armed:
    print(" Waiting for arming...")
    time.sleep(1)

print("Armed! Doing simple_takeoff(2m)")
vehicle.simple_takeoff(2.0)

for i in range(10):
    print(" Alt:", vehicle.location.global_relative_frame.alt)
    time.sleep(1)

vehicle.mode = VehicleMode("LAND")
vehicle.flush()
print("Landing...")
time.sleep(5)
vehicle.close()
