# Rotary Angle Sensor Lock Mechanism
### Author: James Kong

This project implements a rotary angle sensor lock mechanism that simulates a physical circular combination lock using a Raspberry Pi Pico or similar microcontroller. The system continuously monitors the position of a rotary dial and can be integrated into a security system requiring specific angle combinations.

## Hardware Requirements

- Raspberry Pi Pico or compatible microcontroller
- Rotary angle sensor (potentiometer)
- Connecting wires

## Wiring Setup

The rotary angle sensor is connected to analog pin GP28 of the microcontroller.

![Pin Reference](../web_UI/static/images/Pin_Reference.png)

[Will Insert Image of Physical Wire Connection Soon!]

Connect cable to A2 on Pico Shield

## Lock Mechanism Concept

This mechanism monitors the rotation angle of a dial (0-360 degrees), providing the foundation for implementing a combination lock system. By tracking the precise angles, you can build a security system that requires rotating to specific positions in sequence.

## Code Explanation

The code implements several key features:

- **Angle Calculation**: Converts analog readings (0-65535) to degrees (0-360)
- **Moving Average**: Uses a buffer of 10 readings to smooth out sensor fluctuations
- **Change Detection**: Only reports angle changes of 5 degrees or more to reduce noise
- **Continuous Monitoring**: Constantly reads the sensor position at 100Hz (10ms intervals)

Key parameters:
- `threshold`: 5 degrees - Minimum change required to register a new position
- `buffer_size`: 10 readings - Size of the moving average buffer for smoothing

## Usage

1. Upload the `rotary_angle_sensor.py` file to your microcontroller
2. Open a serial monitor to view the angle output
3. Rotate the dial to see the current angle displayed
4. Integrate this into a broader security system by monitoring for specific sequences of angles

## Customization

You can modify the following parameters:
- Adjust `threshold` to make the system more or less sensitive to movement
- Change `buffer_size` to increase or decrease smoothing
- Modify the sampling frequency by changing the sleep duration

## Troubleshooting

- If readings are unstable, try increasing the buffer size for more smoothing
- If response seems delayed, try reducing the buffer size
- Ensure proper connections between the sensor and microcontroller
- Verify the sensor has stable power supply for consistent readings