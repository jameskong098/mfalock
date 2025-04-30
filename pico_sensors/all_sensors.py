"""
Integrated Sensor Controller
----------------------------
This program integrates multiple sensors and switches between them based on detected input.

Current sensors:
- Touch Pattern Lock (GPIO 26)
- Rotary Angle Sensor (ADC Pin 28)

Author: James Kong
"""

from machine import Pin, ADC
import time
import sys
import json
import os

# === Configuration ===
# Sensor selection thresholds
ROTARY_CHANGE_THRESHOLD = 10  # Minimum angle change to activate rotary sensor mode
TOUCH_ACTIVATION_THRESHOLD = 1  # Touch sensor is binary (1 = touched)

# Timeout settings
SENSOR_TIMEOUT = 5000  # ms - time before returning to idle if no activity

# === Initialize Sensors ===
# Touch sensor
touch_sensor = Pin(26, mode=Pin.IN, pull=Pin.PULL_UP)

# Rotary angle sensor
rotary_adc = ADC(Pin(28))

# === State Management ===
# Possible states: "idle", "touch", "rotary"
current_state = "idle"
last_activity_time = 0

# === Sensor State Variables ===
# Touch sensor pattern variables
DEFAULT_PATTERN = [("tap", 0), ("hold", 1000), ("tap", 0)]
custom_pattern = DEFAULT_PATTERN
current_pattern_step = 0
touch_last_value = 0
touch_start_time = 0
touch_last_tap_time = 0
touch_debounce_time = 50
touch_max_tap_interval = 500
touch_is_holding = False
touch_timeout_message_printed = False

# Rotary sensor variables
rotary_prev_angle = -1
rotary_threshold = 5
rotary_buffer_size = 10
rotary_readings = [0] * rotary_buffer_size
rotary_index = 0

def load_touch_pattern_from_file(filepath):
    """Load the touch pattern from a JSON file"""
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

def initialize_touch_sensor():
    """Load touch sensor pattern and initialize variables"""
    global custom_pattern
    
    # Priority 1: Try to load from custom_pattern.json
    pattern_file_path = "custom_pattern.json"
    file_pattern = load_touch_pattern_from_file(pattern_file_path)
    if file_pattern:
        custom_pattern = file_pattern
        print("Using pattern from custom_pattern.json")

    # Priority 2: Check if a custom pattern was provided as an argument
    if len(sys.argv) > 1:
        try:
            pattern_arg = sys.argv[1]
            pattern_data = json.loads(pattern_arg)
            
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
            
    if custom_pattern == DEFAULT_PATTERN:
        print("Using built-in default pattern")

    print(f"Active pattern: {custom_pattern}")

def read_rotary_angle():
    """Read and process the rotary angle sensor value"""
    global rotary_readings, rotary_index
    
    # Read the current analog value
    current_value = rotary_adc.read_u16()
    
    # Add to moving average buffer
    rotary_readings[rotary_index] = current_value
    rotary_index = (rotary_index + 1) % rotary_buffer_size
    
    # Calculate moving average
    avg_value = sum(rotary_readings) // rotary_buffer_size
    
    # Convert to 12-bit and calculate angle
    adc_12bit = avg_value >> 4 
    angle = (adc_12bit / 4095) * 360
    
    return round(angle)

def check_touch_sensor():
    """Check the touch sensor and update state if needed"""
    global current_state, touch_last_value, last_activity_time
    
    current_value = touch_sensor.value()
    
    # Detect change in touch state (with debounce)
    if current_value != touch_last_value:
        time.sleep_ms(touch_debounce_time)  # Debounce
        # Re-read to confirm
        if current_value == touch_sensor.value():
            # Touch started
            if current_value == 1:
                if current_state != "touch":
                    print("Touch sensor activated")
                    current_state = "touch"
                    last_activity_time = time.ticks_ms()
                    reset_touch_state()
            
            touch_last_value = current_value
    
    return current_state == "touch"

def check_rotary_sensor():
    """Check the rotary sensor and update state if needed"""
    global current_state, rotary_prev_angle, last_activity_time
    
    current_angle = read_rotary_angle()
    
    # If this is the first reading or there's a significant change
    if rotary_prev_angle == -1 or abs(current_angle - rotary_prev_angle) >= ROTARY_CHANGE_THRESHOLD:
        if current_state != "rotary":
            print("Rotary sensor activated")
            current_state = "rotary"
            last_activity_time = time.ticks_ms()
        rotary_prev_angle = current_angle
        return True
    
    return current_state == "rotary"

def reset_touch_state():
    """Reset the touch sensor state variables"""
    global current_pattern_step, touch_timeout_message_printed
    current_pattern_step = 0
    touch_timeout_message_printed = False

def handle_touch_sensor():
    """Handle the touch sensor loop iteration"""
    global current_pattern_step, touch_last_value, touch_start_time, touch_last_tap_time
    global touch_is_holding, touch_timeout_message_printed, last_activity_time
    
    current_value = touch_sensor.value()
    current_time = time.ticks_ms()
    
    # Check for other sensor activity first
    if check_rotary_sensor():
        return
    
    # Detect touch state change
    if current_value != touch_last_value:
        time.sleep_ms(touch_debounce_time)  # Debounce
        if current_value == touch_sensor.value():
            # Touch started
            if current_value == 1:
                touch_start_time = current_time
                print("Touch started")
                touch_is_holding = True
                last_activity_time = current_time
            # Touch ended
            else:
                tap_duration = time.ticks_diff(current_time, touch_start_time)
                print(f"Touch ended: {tap_duration}ms")
                touch_is_holding = False
                last_activity_time = current_time
                
                # Process the current step in the pattern
                if current_pattern_step < len(custom_pattern):
                    action, duration = custom_pattern[current_pattern_step]
                    
                    if action == "tap" and tap_duration:
                        print(f"Step {current_pattern_step + 1}: Tap detected")
                        current_pattern_step += 1
                    elif action == "hold" and tap_duration >= duration:
                        print(f"Step {current_pattern_step + 1}: Hold detected ({tap_duration}ms)")
                        current_pattern_step += 1
                    else:
                        print(f"Step {current_pattern_step + 1}: Incorrect input, resetting pattern")
                        current_pattern_step = 0
                
                # Check if the pattern is complete
                if current_pattern_step == len(custom_pattern):
                    print("TOUCH - SUCCESS")
                    current_pattern_step = 0  # Reset for the next attempt
                
                touch_last_tap_time = current_time
            
            touch_last_value = current_value
    
    # Reset pattern if too much time passes between actions
    if (current_pattern_step > 0 and not touch_is_holding and touch_last_tap_time > 0 
            and time.ticks_diff(current_time, touch_last_tap_time) > touch_max_tap_interval * 2):
        if not touch_timeout_message_printed:
            print("Pattern timeout, resetting")
            touch_timeout_message_printed = True
        current_pattern_step = 0
    elif current_pattern_step == 0:
        touch_timeout_message_printed = False  # Reset flag when pattern is reset

def handle_rotary_sensor():
    """Handle the rotary sensor loop iteration"""
    global rotary_prev_angle, last_activity_time
    
    current_time = time.ticks_ms()
    
    # Check for touch sensor activity first
    if check_touch_sensor():
        return
    
    # Read the current angle
    current_angle = read_rotary_angle()
    
    # Only print if the angle has changed significantly
    if abs(current_angle - rotary_prev_angle) >= rotary_threshold or rotary_prev_angle == -1:
        print(f"Angle: {current_angle} degrees")
        rotary_prev_angle = current_angle
        last_activity_time = current_time

def check_timeout():
    """Check if the current sensor has timed out from inactivity"""
    global current_state, last_activity_time
    
    if current_state == "idle":
        return
    
    current_time = time.ticks_ms()
    if time.ticks_diff(current_time, last_activity_time) > SENSOR_TIMEOUT:
        print(f"Sensor timeout: returning to idle state")
        current_state = "idle"
        return True
    
    return False

# === Main Program ===
def main():
    print("Starting Integrated Sensor Controller")
    print("-------------------------------------")
    print("Available Sensors:")
    print("- Touch Pattern Lock (GPIO 26)")
    print("- Rotary Angle Sensor (ADC 28)")
    print("-------------------------------------")
    
    # Initialize sensors
    initialize_touch_sensor()
    
    print("System ready - waiting for sensor input...")
    
    # Main loop
    while True:
        # Check timeout for current sensor
        check_timeout()
        
        # If in idle state, check all sensors for activity
        if current_state == "idle":
            if check_touch_sensor():
                pass  # State already updated in check function
            elif check_rotary_sensor():
                pass  # State already updated in check function
        
        # If in touch state, run touch sensor handler
        elif current_state == "touch":
            handle_touch_sensor()
        
        # If in rotary state, run rotary sensor handler
        elif current_state == "rotary":
            handle_rotary_sensor()
        
        # Brief sleep to save power
        time.sleep_ms(10)

if __name__ == "__main__":
    main()