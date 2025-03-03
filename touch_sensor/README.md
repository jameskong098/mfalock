# Touch Sensor Lock Pattern
### Author: James Kong

This project implements a touch-sensitive lock mechanism using a capacitive sensor connected to a Raspberry Pi Pico or similar microcontroller. The lock requires a specific pattern of touches to grant access.

## Hardware Requirements

- Raspberry Pi Pico or compatible microcontroller
- Capacitive touch sensor
- Connecting wires

## Wiring Setup

The touch sensor is connected to GP26 of the microcontroller with the ground and power wires in the GND and 3V3(OUT)

![Touch Sensor Wiring](../assets/touch_setup.png)

### Pin Reference

For reference, here is the pinout diagram for the Raspberry Pi Pico:

![Pin Reference](../assets/Pin_Reference.png)

## Pattern Recognition

The current access pattern is:
1. Double tap (two quick touches in succession)
2. Long hold (touch and hold for at least 1 second)
3. Single tap (one quick touch)

When this pattern is correctly performed, the system will output "ACCESS GRANTED".

## Code Explanation

The code uses a state machine approach to detect the pattern:

- **State 0**: Waiting for double tap
- **State 1**: Waiting for long hold
- **State 2**: Waiting for single tap

Key parameters in the code:
- `debounce_time`: 50ms - Prevents false readings from sensor fluctuations
- `max_tap_interval`: 500ms - Maximum time allowed between taps in a sequence
- `min_hold_duration`: 1000ms - Minimum duration required for a "long hold"

## Usage

1. Upload the `test.py` file to your microcontroller
2. Touch the sensor according to the pattern described above
3. The console will output debug information showing your progress through the pattern
4. When the correct pattern is detected, "ACCESS GRANTED" will be displayed

## Customization

You can modify the following parameters to adjust sensitivity:

- Change `max_tap_interval` to allow more or less time between taps
- Adjust `min_hold_duration` to require a longer or shorter hold
- Modify the pattern detection code to create different patterns

## Troubleshooting

- If touches aren't being detected, check your wiring connections
- If pattern detection is unreliable, try adjusting the debounce time
- For false positives, you may need to increase the minimum hold duration
