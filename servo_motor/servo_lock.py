from machine import Pin
from servo import SERVO
import sys
import select
from utime import sleep

servo = SERVO(Pin(26))  # GPIO26 = A0

# 🔄 Reset servo to starting position (unlock) at boot
servo.turn(45)
sleep(1)

while True:
    if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
        command = sys.stdin.readline().strip()
        print("Received:", command)

        if command == "lock":
            servo.turn(90)
        elif command == "unlock":
            servo.turn(-90)

        sleep(1)
    else:
        sleep(0.1)
