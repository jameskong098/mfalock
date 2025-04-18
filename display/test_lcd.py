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
# Bottom row includes 'Del' for backspace next to '0'
keypad_grid = [
    ['1', '2', '3'],
    ['4', '5', '6'],
    ['7', '8', '9'],
    [' ', '0', 'Del']  # 'Del' for backspace
]

# Now we have 10 digits plus 1 "Del" entry = 11 total
flat_digits = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', 'Del']

keypad_index = 0
entered_digits = ""

# App state
system_locked = False
# Possible screens: "set_password", "confirm", "home", "lock", "keypad"
current_screen = "set_password"  # Start at password setup

menu_options = [
    "Facial Recognition",
    "Voice Recognition",
    "Touch Password",
    "Keypad Authentication",
    "Basic Unlock"
]
menu_index = 0

# Confirmation prompt tracking
confirm_index = 0  # 0 = "Go Back", 1 = "Confirm"
user_password = ""  # Will hold the confirmed password after setup


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
    """
    Keypad screen for authentication (NOT the initial password setup).
    Allows entering up to 4 digits, with 'Del' to erase the last one.
    """
    draw.rectangle((0, 0, width, height), fill=(0, 0, 0))
    draw.text((10, 5), "A: Left | X: Right | B: Select", font=font, fill=(180, 180, 180))
    draw.text((10, 20), "Y: Return to Home", font=font, fill=(100, 100, 100))
    draw.text((10, 40), f"Entered: {entered_digits}", font=font, fill=(255, 255, 0))

    # Draw the keypad
    for i, digit in enumerate(flat_digits):
        row = i // 3
        col = i % 3
        x = 30 + col * 50
        y_keypad = 70 + row * 30
        color = (0, 255, 0) if i == keypad_index else (255, 255, 255)
        draw.text((x, y_keypad), digit, font=font, fill=color)

    display.display()


def draw_set_password_screen():
    """
    Keypad UI for setting a new password at startup.
    Includes 'Del' for backspace. Y = Submit for confirmation.
    """
    draw.rectangle((0, 0, width, height), fill=(0, 0, 0))
    
    line_spacing = 25
    y_text = 5
    
    draw.text((10, y_text), "Enter new password:", font=font, fill=(255, 255, 255))
    y_text += line_spacing
    
    draw.text((10, y_text), "A: Left | X: Right | B: Select", font=font, fill=(180, 180, 180))
    y_text += line_spacing
    
    draw.text((10, y_text), "Y: Submit Password", font=font, fill=(100, 100, 100))
    y_text += line_spacing
    
    draw.text((10, y_text), f"Entered: {entered_digits}", font=font, fill=(255, 255, 0))

    # Draw the keypad lower down for spacing
    for i, digit in enumerate(flat_digits):
        row = i // 3
        col = i % 3
        x = 30 + col * 50
        y_keypad = 100 + row * 30
        color = (0, 255, 0) if i == keypad_index else (255, 255, 255)
        draw.text((x, y_keypad), digit, font=font, fill=color)

    display.display()


def draw_password_confirm_screen():
    """
    Confirmation prompt for the new password:
    user can select "Go Back" or "Confirm".
    """
    confirm_options = ["Go Back", "Confirm"]
    draw.rectangle((0, 0, width, height), fill=(0, 0, 0))
    draw.text((10, 5), "Set Password:", font=font, fill=(255, 255, 255))
    draw.text((10, 20), f"Entered: {entered_digits}", font=font, fill=(255, 255, 0))
    draw.text((10, 40), "Are you sure you want this", font=font, fill=(180, 180, 180))
    draw.text((10, 55), "password?", font=font, fill=(180, 180, 180))
    
    # Draw the confirmation options at the bottom
    option_x_positions = [10, 90]  # Adjust positions as needed
    for idx, option in enumerate(confirm_options):
        color = (0, 255, 0) if idx == confirm_index else (255, 255, 255)
        draw.text((option_x_positions[idx], height - 20), option, font=font, fill=color)
    
    display.display()


def draw_error_screen(error_message):
    """
    Briefly shows an error message on a black background.
    """
    draw.rectangle((0, 0, width, height), fill=(0, 0, 0))
    draw.text((10, height // 2), error_message, font=font, fill=(255, 0, 0))
    display.display()
    time.sleep(1)  # Display error for 1 second


# Set backlight
display.set_led(0.05, 0.05, 0.05)

# Draw the initial screen (set password)
draw_set_password_screen()

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
            selected_digit = flat_digits[keypad_index]
            if selected_digit == "Del":
                if len(entered_digits) > 0:
                    entered_digits = entered_digits[:-1]
            else:
                if len(entered_digits) < 4:
                    entered_digits += selected_digit
            draw_keypad_screen()
            time.sleep(0.2)

        elif display.read_button(display.BUTTON_Y):  # Return to home
            entered_digits = ""
            keypad_index = 0
            current_screen = "home"
            draw_home_screen()
            time.sleep(0.2)

    elif current_screen == "set_password":
        # The initial password setup screen
        if display.read_button(display.BUTTON_A):  # Move left
            keypad_index = (keypad_index - 1) % len(flat_digits)
            draw_set_password_screen()
            time.sleep(0.2)

        elif display.read_button(display.BUTTON_X):  # Move right
            keypad_index = (keypad_index + 1) % len(flat_digits)
            draw_set_password_screen()
            time.sleep(0.2)

        elif display.read_button(display.BUTTON_B):  # Select digit
            selected_digit = flat_digits[keypad_index]
            if selected_digit == "Del":
                # Backspace
                if len(entered_digits) > 0:
                    entered_digits = entered_digits[:-1]
            else:
                # Add digit if under 4 characters
                if len(entered_digits) < 4:
                    entered_digits += selected_digit
            draw_set_password_screen()
            time.sleep(0.2)

        elif display.read_button(display.BUTTON_Y):  # Submit password
            # Require exactly 4 digits to proceed
            if len(entered_digits) == 4:
                current_screen = "confirm"
                confirm_index = 0
                draw_password_confirm_screen()
            else:
                # Show an error, then go back to set_password screen
                draw_error_screen("You must enter a 4-digit password!")
                draw_set_password_screen()

            time.sleep(0.2)

    elif current_screen == "confirm":
        # Confirmation prompt for the newly entered password
        if display.read_button(display.BUTTON_A):  # Move left
            confirm_index = (confirm_index - 1) % 2
            draw_password_confirm_screen()
            time.sleep(0.2)

        elif display.read_button(display.BUTTON_X):  # Move right
            confirm_index = (confirm_index + 1) % 2
            draw_password_confirm_screen()
            time.sleep(0.2)

        elif display.read_button(display.BUTTON_B):  # Choose "Go Back" or "Confirm"
            if confirm_index == 1:
                # "Confirm" selected
                user_password = entered_digits
                print("Password set to:", user_password)
                # Reset for normal usage
                entered_digits = ""
                keypad_index = 0
                current_screen = "home"
                draw_home_screen()
            else:
                # "Go Back" selected
                current_screen = "set_password"
                draw_set_password_screen()
            time.sleep(0.2)

    time.sleep(0.05)
