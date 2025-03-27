import serial
from displayhatmini import DisplayHATMini
from PIL import Image, ImageDraw, ImageFont
import time
import os

# Display setup
width = DisplayHATMini.WIDTH
height = DisplayHATMini.HEIGHT
buffer = Image.new("RGB", (width, height))
draw = ImageDraw.Draw(buffer)

display = DisplayHATMini(buffer)
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)

# Keypad config (flattened index-based navigation)
keypad_grid = [
    ['1', '2', '3'],
    ['4', '5', '6'],
    ['7', '8', '9'],
    [' ', '0', ' ']  # Padding for alignment
]
flat_digits = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']
keypad_index = 0
entered_digits = ""

# App state
system_locked = False
current_screen = "home"

menu_options = [
    "Facial Recognition",
    "Voice Recognition",
    "Touch Password",
    "Keypad Authentication",
    "Basic Unlock"
]
menu_index = 0

def draw_home_screen():
    draw.rectangle((0, 0, width, height), fill=(0, 0, 0))
    draw.text((20, 5), "Select Authentication:", font=font, fill=(255, 255, 255))

    for i, option in enumerate(menu_options):
        y = 25 + i * 20
        color = (0, 255, 0) if i == menu_index else (255, 255, 255)
        draw.text((10, y), f"{'> ' if i == menu_index else '  '}{option}", font=font, fill=color)

    draw.text((10, height - 15), "Use A/B to scroll | X to select", font=font, fill=(100, 100, 100))
    display.display()

def draw_lock_screen():
    draw.rectangle((0, 0, width, height), fill=(0, 0, 0))
    status = "System is LOCKED" if system_locked else "System is UNLOCKED"
    color = (255, 0, 0) if system_locked else (0, 255, 0)
    draw.text((20, 20), status, font=font, fill=color)
    draw.text((20, 50), "A to Lock | B to Unlock", font=font, fill=(180, 180, 180))
    draw.text((10, height - 15), "Press Y to return to Home", font=font, fill=(100, 100, 100))
    display.display()

def draw_keypad_screen():
    draw.rectangle((0, 0, width, height), fill=(0, 0, 0))
    draw.text((10, 5), "A: Left | X: Right | B: Select", font=font, fill=(180, 180, 180))
    draw.text((10, 20), "Y: Return to Home", font=font, fill=(100, 100, 100))
    draw.text((10, 40), f"Entered: {entered_digits}", font=font, fill=(255, 255, 0))

    for i, digit in enumerate(flat_digits):
        row = i // 3
        col = i % 3
        x = 30 + col * 50
        y = 70 + row * 30
        color = (0, 255, 0) if i == keypad_index else (255, 255, 255)
        draw.text((x, y), digit, font=font, fill=color)

    display.display()

# Set backlight
display.set_led(0.05, 0.05, 0.05)

# Draw initial screen
draw_home_screen()

while True:
    if current_screen == "home":
        if display.read_button(display.BUTTON_A):
            menu_index = (menu_index - 1) % len(menu_options)
            draw_home_screen()
            time.sleep(0.2)

        elif display.read_button(display.BUTTON_B):
            menu_index = (menu_index + 1) % len(menu_options)
            draw_home_screen()
            time.sleep(0.2)

        elif display.read_button(display.BUTTON_X):
            selected = menu_options[menu_index]
            if selected == "Basic Unlock":
                current_screen = "lock"
                draw_lock_screen()
            elif selected == "Keypad Authentication":
                current_screen = "keypad"
                draw_keypad_screen()
            time.sleep(0.2)

    elif current_screen == "lock":
        if display.read_button(display.BUTTON_A):
            system_locked = True
            try:
                with serial.Serial("/dev/ttyACM0", 9600, timeout=1) as ser:
                    ser.write(b"lock\n")
            except Exception as e:
                print("Error sending lock:", e)
            draw_lock_screen()
            time.sleep(0.2)

        elif display.read_button(display.BUTTON_B):
            system_locked = False
            try:
                with serial.Serial("/dev/ttyACM0", 9600, timeout=1) as ser:
                    ser.write(b"unlock\n")
            except Exception as e:
                print("Error sending unlock:", e)
            draw_lock_screen()
            time.sleep(0.2)

        elif display.read_button(display.BUTTON_Y):
            current_screen = "home"
            draw_home_screen()
            time.sleep(0.2)

    elif current_screen == "keypad":
        if display.read_button(display.BUTTON_A):  # Move left
            keypad_index = (keypad_index - 1) % len(flat_digits)
            draw_keypad_screen()
            time.sleep(0.2)

        elif display.read_button(display.BUTTON_X):  # Move right
            keypad_index = (keypad_index + 1) % len(flat_digits)
            draw_keypad_screen()
            time.sleep(0.2)

        elif display.read_button(display.BUTTON_B):  # Select digit
            if len(entered_digits) < 4:
                entered_digits += flat_digits[keypad_index]
                draw_keypad_screen()
            time.sleep(0.2)

        elif display.read_button(display.BUTTON_Y):  # Return to home
            entered_digits = ""
            keypad_index = 0
            current_screen = "home"
            draw_home_screen()
            time.sleep(0.2)

    time.sleep(0.05)
