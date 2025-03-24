from machine import Pin, UART
from utime import sleep
from servo import SERVO

servo = SERVO(Pin(20))
uart = UART(0, baudrate=9600, tx=Pin(0), rx=Pin(1))

while True:
    if uart.any():
        raw = uart.readline()
        if raw is not None:
            try:
                command = str(raw, 'utf-8').strip()  # Equivalent to decode()
                print("Received:", command)

                if command == "lock":
                    servo.turn(90)
                elif command == "unlock":
                    servo.turn(-90)
            except Exception as e:
                print("Error parsing command:", e)
    sleep(0.1)
