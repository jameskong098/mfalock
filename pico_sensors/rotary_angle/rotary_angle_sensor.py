from machine import ADC, Pin
import utime

adc = ADC(Pin(28))  

# Initialize previous value to ensure first reading is printed
prev_angle = -1  

# Threshold for considering a change significant (in degrees)
threshold = 5  # Only report changes of 5 degrees or more

# Moving average buffer
buffer_size = 10
readings = [0] * buffer_size
index = 0

print("Rotary Angle Sensor Monitor - Values will print when changed significantly")

while True:
    # Read the current analog value (0-65535 for Pico's ADC)
    current_value = adc.read_u16()
    
    # Add to moving average buffer
    readings[index] = current_value
    index = (index + 1) % buffer_size
    
    # Calculate moving average
    avg_value = sum(readings) // buffer_size
    
    # Convert to 12-bit and calculate angle
    adc_12bit = avg_value >> 4 
    angle = (adc_12bit / 4095) * 360
    
    # Round to nearest integer to reduce minor fluctuations
    rounded_angle = round(angle)
    
    # Only print if the angle has changed significantly
    if abs(rounded_angle - prev_angle) >= threshold or prev_angle == -1:
        print(f"Angle: {rounded_angle} degrees")
        prev_angle = rounded_angle
        
    # Small delay to avoid too frequent readings
    utime.sleep(0.01)