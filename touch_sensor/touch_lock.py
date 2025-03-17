"""
Touch Sensor Pattern Lock
-------------------------
This program implements a touch-based security mechanism that recognizes a custom pattern.

Hardware:
- Microcontroller (Raspberry Pi Pico or similar)
- Touch sensor connected to GPIO pin 26
- Internal pull-up resistor enabled

Author: James Kong
Date: February 27, 2025
"""

from machine import Pin
import time

pin_sensor = Pin(26, mode=Pin.IN, pull=Pin.PULL_UP)

# Define the custom pattern
# Each step is a tuple: ("action", "duration")
# "action" can be "tap" or "hold"
# "duration" is the minimum duration for "hold" or 0 for "tap"
#custom_pattern = [("tap", 0), ("tap", 0), ("hold", 1000), ("tap", 0)]
custom_pattern = [("tap", 0), ("hold", 1000), ("tap", 0)]

# Pattern state variables
current_step = 0
last_value = 0
touch_start_time = 0
last_tap_time = 0
debounce_time = 50  # 50ms debounce to prevent false readings
max_tap_interval = 500  # Maximum time between taps (500ms)
is_holding = False
timeout_message_printed = False

while True:
    current_value = pin_sensor.value()
    current_time = time.ticks_ms()
    
    # Detect touch state change
    if current_value != last_value:
        time.sleep_ms(debounce_time)  # Debounce
        # Re-read to confirm
        if current_value == pin_sensor.value():
            # Touch started
            if current_value == 1:
                touch_start_time = current_time
                print("Touch started")
                is_holding = True
            # Touch ended
            else:
                tap_duration = time.ticks_diff(current_time, touch_start_time)
                print(f"Touch ended: {tap_duration}ms")
                is_holding = False
                
                # Process the current step in the pattern
                if current_step < len(custom_pattern):
                    action, duration = custom_pattern[current_step]
                    
                    if action == "tap" and tap_duration:
                        print(f"Step {current_step + 1}: Tap detected")
                        current_step += 1
                    elif action == "hold" and tap_duration >= duration:
                        print(f"Step {current_step + 1}: Hold detected ({tap_duration}ms)")
                        current_step += 1
                    else:
                        print(f"Step {current_step + 1}: Incorrect input, resetting pattern")
                        current_step = 0
                
                # Check if the pattern is complete
                if current_step == len(custom_pattern):
                    print("Custom pattern complete!")
                    print("ACCESS GRANTED")
                    current_step = 0  # Reset for the next attempt
                
                last_tap_time = current_time
            
            last_value = current_value
    
    # Reset pattern if too much time passes between actions
    if current_step > 0 and not is_holding and last_tap_time > 0 and time.ticks_diff(current_time, last_tap_time) > max_tap_interval * 2:
        if not timeout_message_printed:
            print("Pattern timeout, resetting")
            timeout_message_printed = True
        current_step = 0
    
    # Sleep a bit to save power
    time.sleep_ms(10)
