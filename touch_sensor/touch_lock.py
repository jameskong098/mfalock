"""
Touch Sensor Pattern Lock
-------------------------
This program implements a touch-based security mechanism that recognizes a specific pattern:
- Double tap
- Long hold (at least 1 second)
- Single tap

When the correct pattern is entered, the system grants access.

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

# Pattern: double tap + long hold + single tap

pattern_buffer = []
last_value = 0
touch_start_time = 0
last_tap_time = 0
debounce_time = 50  # 50ms debounce to prevent false readings
max_tap_interval = 500  # Maximum time between taps (500ms)
min_hold_duration = 1000  # Minimum hold duration (1s)
tap_count = 0
pattern_state = 0  # 0: waiting for double tap, 1: waiting for hold, 2: waiting for single tap
in_sequence = False
is_holding = False

# Add a flag to track if timeout message has been printed
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
                
                # State machine for pattern detection
                if pattern_state == 0:  # Waiting for double tap
                    # First tap or continuing a sequence
                    if last_tap_time == 0 or time.ticks_diff(current_time, last_tap_time) <= max_tap_interval:
                        tap_count += 1
                        print(f"Double tap progress: {tap_count}/2")
                        
                        # Check if double tap completed
                        if tap_count == 2:
                            print("Double tap complete, now waiting for long hold")
                            pattern_state = 1
                            tap_count = 0
                    else:
                        # Reset if too much time between taps
                        print("Tap timeout, resetting double tap sequence")
                        tap_count = 1
                        print(f"Double tap progress: {tap_count}/2")
                
                elif pattern_state == 1:  # Waiting for long hold
                    # Check if the hold was long enough
                    if tap_duration >= min_hold_duration:
                        print(f"Long hold complete ({tap_duration}ms), now waiting for single tap")
                        pattern_state = 2
                        last_tap_time = current_time  # Update last_tap_time to start timing for the next state
                    else:
                        print(f"Hold too short ({tap_duration}ms), pattern failed")
                        pattern_state = 0
                        tap_count = 0
                        timeout_message_printed = False
                
                elif pattern_state == 2:  # Waiting for final single tap
                    # Check if this is a quick tap (not another long hold)
                    if tap_duration < min_hold_duration:
                        print("Single tap detected, pattern complete!")
                        print("ACCESS GRANTED")
                        
                        # Reset pattern detection
                        pattern_state = 0
                        tap_count = 0
                        timeout_message_printed = False
                    else:
                        print("Final tap should be quick, not a hold")
                        pattern_state = 0
                        tap_count = 0
                        timeout_message_printed = False
                
                last_tap_time = current_time
            
            last_value = current_value
    
    # Reset pattern if too much time passes between actions
    if not is_holding and last_tap_time > 0 and time.ticks_diff(current_time, last_tap_time) > max_tap_interval * 2:
        # Only reset if we're still waiting for pattern completion
        if pattern_state < 2 and tap_count < 2:
            if not timeout_message_printed:
                print("Pattern timeout, resetting")
                timeout_message_printed = True
            pattern_state = 0
            tap_count = 0
        elif pattern_state == 1 or pattern_state == 2:
            if not timeout_message_printed:
                print("Pattern timeout while waiting for long hold or single tap, resetting")
                timeout_message_printed = True
            pattern_state = 0
            tap_count = 0
    
    # Sleep a bit to save power
    time.sleep_ms(10)
