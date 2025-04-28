from machine import Pin
from servo import SERVO
from utime import sleep

servo = SERVO(Pin(26))  # GPIO26 = A0

for _ in range(2):
    servo.turn(5)   # Move to one extreme
    sleep(1)
    servo.turn(90)  # Move to the other extreme
    sleep(1)

print("Servo test complete.")
