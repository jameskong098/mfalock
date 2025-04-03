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
import sys
import json
import os

pin_sensor = Pin(26, mode=Pin.IN, pull=Pin.PULL_UP)

# Define the default custom pattern - only used if no custom pattern provided
# Each step is a tuple: ("action", "duration")
# "action" can be "tap" or "hold"
# "duration" is the minimum duration for "hold" or 0 for "tap"
DEFAULT_PATTERN = [("tap", 0), ("hold", 1000), ("tap", 0)]

# Start with default pattern, will try to override with custom settings
custom_pattern = DEFAULT_PATTERN

# Function to load pattern from JSON file
def load_pattern_from_file(filepath):
    try:
        # Check if file exists
        try:
            stat = os.stat(filepath)
            if stat[6] == 0:  # Size is 0
                print(f"Pattern file is empty: {filepath}")
                return None
        except OSError:
            print(f"Pattern file not found: {filepath}")
            return None
            
        # Open and read the file
        with open(filepath, 'r') as f:
            data = json.load(f)
            
        # Extract pattern from the data
        if 'pattern' in data and isinstance(data['pattern'], list) and len(data['pattern']) > 0:
            # Convert the JSON format to tuple format
            pattern = []
            for step in data['pattern']:
                if isinstance(step, dict) and 'action' in step and 'duration' in step:
                    pattern.append((step['action'], step['duration']))
            
            if len(pattern) > 0:
                print(f"Loaded pattern from {filepath} with {len(pattern)} steps")
                return pattern
                
        print("No valid pattern found in file")
        return None
    except Exception as e:
        print(f"Error loading pattern from file: {e}")
        return None

# Priority 1: Try to load from custom_pattern.json
pattern_file_path = "custom_pattern.json"
file_pattern = load_pattern_from_file(pattern_file_path)
if file_pattern:
    custom_pattern = file_pattern
    print("Using pattern from custom_pattern.json")

# Priority 2: Check if a custom pattern was provided as an argument (overrides file)
if len(sys.argv) > 1:
    try:
        # Parse the argument as JSON
        pattern_arg = sys.argv[1]
        pattern_data = json.loads(pattern_arg)
        
        # Convert to the expected format
        if isinstance(pattern_data, list):
            arg_pattern = []
            for step in pattern_data:
                if isinstance(step, dict) and "action" in step and "duration" in step:
                    arg_pattern.append((step["action"], step["duration"]))
            
            if arg_pattern:
                custom_pattern = arg_pattern
                print(f"Using provided command-line pattern with {len(custom_pattern)} steps")
            
    except Exception as e:
        print(f"Error parsing pattern argument: {e}")
        
# If we still don't have a valid pattern, log that we're using the default
if custom_pattern == DEFAULT_PATTERN:
    print("Using built-in default pattern")

print(f"Active pattern: {custom_pattern}")

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
        timeout_message_printed = False  # Reset timeout message flag
    elif current_step == 0:
        timeout_message_printed = False  # Reset flag when pattern is reset
    
    # Sleep a bit to save power
    time.sleep_ms(10)