# Servo Motor Control

This directory contains MicroPython code for controlling a standard hobby servo motor connected to a Raspberry Pi Pico.

## Files

- `servo.py`: Contains the `SERVO` class which handles the PWM signal generation required to control the servo's position. It maps angles (0-180 degrees) to the appropriate PWM duty cycle.
- `servo_test.py`: A simple script that demonstrates how to use the `SERVO` class. It initializes the servo on GPIO 26 and sweeps it between two positions (5 and 90 degrees) twice.

## Hardware Setup

- Connect the servo's signal pin to GPIO 26 on the Pico.
- Connect the servo's VCC pin to a suitable power source (e.g., 5V). **Note:** The Pico's 3.3V pin might not provide enough current for some servos; an external 5V supply is often recommended.
- Connect the servo's GND pin to the Pico's GND.

## Usage

### `servo.py`

To use the `SERVO` class in your own MicroPython script:

1.  Ensure `servo.py` is uploaded to your Pico.
2.  Import the necessary modules:
    ```python
    from machine import Pin
    from servo import SERVO
    from utime import sleep
    ```
3.  Create a `SERVO` object, specifying the GPIO pin connected to the servo's signal line:
    ```python
    servo_pin = Pin(26)
    my_servo = SERVO(servo_pin)
    ```
4.  Use the `turn()` method to set the servo's angle (typically 0-180 degrees, but the exact range depends on your servo):
    ```python
    my_servo.turn(0)    # Move to 0 degrees
    sleep(1)
    my_servo.turn(90)   # Move to 90 degrees
    sleep(1)
    my_servo.turn(180)  # Move to 180 degrees
    ```

### `servo_test.py`

To run the test script:

1.  Ensure both `servo.py` and `servo_test.py` are uploaded to your Pico.
2.  Use a tool like `mpremote` to run the test script:
    ```bash
    mpremote run servo_test.py
    ```
    This will cause the servo connected to GPIO 26 to sweep back and forth twice.
