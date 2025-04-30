# Pico Sensors

This directory contains MicroPython code for various sensors and actuators connected to a Raspberry Pi Pico, primarily focused on building components for a multi-factor authentication lock system.

## Integrated Sensor Controller (`all_sensors.py`)

This is the main script that integrates multiple sensor inputs and manages the system state based on which sensor is currently active.

**Purpose:** To monitor different input methods (touch patterns, rotary angle changes) and switch between them dynamically. This allows the system to respond to whichever sensor the user interacts with first.

**Features:**

*   **Multi-Sensor Integration:** Currently integrates:
    *   Touch Pattern Lock (using GPIO 26)
    *   Rotary Angle Sensor (using ADC Pin 28 / GP28)
*   **State Management:** The script operates in different states:
    *   `idle`: Waiting for sensor input.
    *   `touch`: Actively processing input from the touch sensor.
    *   `rotary`: Actively processing input from the rotary angle sensor.
*   **Dynamic Switching:** Automatically switches from `idle` to the state corresponding to the first sensor that detects significant input.
*   **Timeout:** If a sensor is active but receives no further input for a defined period (`SENSOR_TIMEOUT`), the system returns to the `idle` state.
*   **Touch Pattern Loading:** The touch pattern lock can use:
    1.  A pattern defined in `custom_pattern.json` (if it exists).
    2.  A pattern passed as a JSON string via command-line argument.
    3.  A built-in default pattern (`[("tap", 0), ("hold", 1000), ("tap", 0)]`).
*   **Sensor Debouncing/Smoothing:** Includes basic debouncing for the touch sensor and a moving average filter for the rotary sensor to improve reliability.

**Hardware:**

*   Raspberry Pi Pico
*   Capacitive Touch Sensor (connected to GP26)
*   Rotary Angle Sensor / Potentiometer (connected to GP28/ADC2)

**Usage:**

1.  Ensure the required sensor scripts (or their logic integrated into `all_sensors.py`) and any necessary configuration files (like `custom_pattern.json`) are present on the Pico.
2.  Upload `all_sensors.py` to the Pico.
3.  Run the script (e.g., using Thonny or `mpremote`).
4.  The script will print its status and wait for input from either the touch sensor or the rotary angle sensor. Interact with a sensor to activate its mode.

## Subdirectories

*   **`rotary_angle/`**: Contains standalone code (`rotary_angle_sensor.py`) specifically for reading and reporting the angle from the rotary sensor, along with its own README detailing setup and usage.
*   **`servo_motor/`**: Contains a `SERVO` class (`servo.py`) and a test script (`servo_test.py`) for controlling a standard hobby servo motor. Includes a README for setup.
*   **`touch/`**: Contains standalone code (`touch_lock.py`) for the touch pattern lock mechanism, along with its own README. Note that the logic in `all_sensors.py` is based on this but integrated with other sensors.

