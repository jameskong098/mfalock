from machine import ADC, Pin
import utime

adc = ADC(Pin(26))

# Initialize previous value to ensure first reading is printed
prev_value = -1  

# Threshold for considering a change significant (to handle small fluctuations)
threshold = 50  

print("Rotary Angle Sensor Monitor - Values will print when changed")

while True:
    # Read the current analog value (0-65535 for Pico's ADC)
    current_value = adc.read_u16()

    # Check if the value has changed significantly
    if abs(current_value - prev_value) > threshold or prev_value == -1:
        angle_percentage = (current_value / 65535) * 100
        print(f"Angle: {current_value} (raw), {angle_percentage:.1f}%")
        
        # Update previous value
        prev_value = current_value
    
    # Small delay to avoid too frequent readings
    utime.sleep(0.01)