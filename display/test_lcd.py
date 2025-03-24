from displayhatmini import DisplayHATMini
from PIL import Image, ImageDraw, ImageFont
import time

# Create the buffer first
width = DisplayHATMini.WIDTH
height = DisplayHATMini.HEIGHT
buffer = Image.new("RGB", (width, height))
draw = ImageDraw.Draw(buffer)

# Pass buffer into DisplayHATMini
display = DisplayHATMini(buffer)
font = ImageFont.load_default()

# Initial state
system_locked = False

def draw_ui():
    # Clear the existing buffer
    draw.rectangle((0, 0, width, height), fill=(0, 0, 0))

    # Draw Lock button
    draw.rectangle((10, height - 50, width // 2 - 10, height - 10), fill=(50, 50, 50))
    draw.text((20, height - 40), "🔒 Lock", font=font, fill=(255, 255, 255))

    # Draw Unlock button
    draw.rectangle((width // 2 + 10, height - 50, width - 10, height - 10), fill=(50, 50, 50))
    draw.text((width // 2 + 20, height - 40), "🔓 Unlock", font=font, fill=(255, 255, 255))

    # Draw status
    status = "System is LOCKED" if system_locked else "System is UNLOCKED"
    color = (255, 0, 0) if system_locked else (0, 255, 0)
    draw.text((20, 20), status, font=font, fill=color)

    # Push updated buffer to screen
    display.display()

# Set a soft white backlight
display.set_led(0.05, 0.05, 0.05)

# Initial draw
draw_ui()

# Main loop
while True:
    if display.read_button(display.BUTTON_A):
        system_locked = True
        draw_ui()
        time.sleep(0.2)  # Debounce

    elif display.read_button(display.BUTTON_B):
        system_locked = False
        draw_ui()
        time.sleep(0.2)  # Debounce

    time.sleep(0.05)
