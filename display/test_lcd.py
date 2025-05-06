import serial
from displayhatmini import DisplayHATMini
from PIL import Image, ImageDraw, ImageFont
import time
import os
import subprocess
import socketio
import sys
import json 
from dotenv import load_dotenv
# pip install "python-socketio[client]"

# Load environment variables from .env file in the root directory
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path, override=True)
    print(f"Loaded environment variables from: {dotenv_path}")
else:
    print(f".env file not found at: {dotenv_path}")

# --- Configuration ---
# Get the Web Server IP (which hosts the Socket.IO server) from environment variables
# Assuming the web server runs on the same machine defined by ALLOWED_WEB_SERVER_IP in .env
SOCKET_SERVER_IP = os.getenv("ALLOWED_WEB_SERVER_IP") # Use the IP for the web server device
SOCKET_SERVER_PORT = int(os.getenv("LISTENER_PI_PORT", 8080)) # Use the same port

# Check if the environment variable was loaded
if SOCKET_SERVER_IP is None:
    print("Error: ALLOWED_WEB_SERVER_IP environment variable not set in .env.")
    print("Please define ALLOWED_WEB_SERVER_IP in your .env file.")
    sys.exit(1)
# --- End Configuration ---

# --- Settings File Path ---
# Calculate the path to settings.json relative to this script
script_dir = os.path.dirname(__file__)
project_root = os.path.dirname(script_dir) # Go up one level from 'display'
settings_file_path = os.path.join(project_root, 'web_UI', 'settings.json')
print(f"Settings file path: {settings_file_path}")
# --- End Settings File Path ---


# Display setup
width = DisplayHATMini.WIDTH
height = DisplayHATMini.HEIGHT
buffer = Image.new("RGB", (width, height))
draw = ImageDraw.Draw(buffer)
face_process = None
display = DisplayHATMini(buffer)
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
# used for keypad authentication
password_Set = False
user_password = "" 

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
# Initial screen determined after loading settings
current_screen = "home" # Default to home, will change if password needed

menu_options = [
    "Facial Recognition",
    "Voice Recognition",
    "Touch Password",
    "Rotary Authentication",
    "Keypad Authentication",
    "Basic Unlock"
]
menu_index = 0

# Confirmation prompt tracking
confirm_index = 0  # 0 = "Go Back", 1 = "Confirm"
# --- Password Persistence Functions ---
def load_password_from_settings():
    """Loads the keypad password from settings.json."""
    global user_password, password_Set, current_screen
    try:
        if os.path.exists(settings_file_path):
            with open(settings_file_path, 'r') as f:
                settings_data = json.load(f)
                loaded_password = settings_data.get("keypad_password")
                if loaded_password and len(loaded_password) == 4:
                    user_password = loaded_password
                    password_Set = True
                    print(f"Loaded password from settings: {user_password}")
                    current_screen = "home" # Start at home if password exists
                    return True
                else:
                    print("No valid password found in settings.json or password length is not 4.")
                    current_screen = "set_password" # Force setup if invalid
        else:
            print(f"Settings file not found at {settings_file_path}. User needs to set a password.")
            current_screen = "set_password" # Force setup if file missing
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading settings: {e}. User needs to set a password.")
        current_screen = "set_password" # Force setup on error
    except Exception as e:
        print(f"An unexpected error occurred loading settings: {e}")
        current_screen = "set_password" # Force setup on unexpected error

    password_Set = False
    user_password = ""
    return False

def save_password_to_settings(new_password):
    """Saves the keypad password to settings.json."""
    settings_data = {}
    try:
        # Load existing settings first to avoid overwriting other keys
        if os.path.exists(settings_file_path):
            with open(settings_file_path, 'r') as f:
                try:
                    settings_data = json.load(f)
                except json.JSONDecodeError:
                    print("Warning: settings.json is corrupted. Creating a new one.")
                    settings_data = {} # Start fresh if corrupted

        settings_data["keypad_password"] = new_password

        # Ensure the directory exists before writing
        os.makedirs(os.path.dirname(settings_file_path), exist_ok=True)

        with open(settings_file_path, 'w') as f:
            json.dump(settings_data, f, indent=4)
        print(f"Password saved to {settings_file_path}")
        return True
    except (IOError, OSError) as e:
        print(f"Error saving settings: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred saving settings: {e}")
        return False
# --- End Password Persistence Functions ---


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

def draw_keypad_success_screen():
    """
    shows a success screen for facial recognition.
    """
    draw.rectangle((0, 0, width, height), fill=(0, 0, 0))
    draw.text((20, 20), "Success", font=font, fill=(0, 255, 0))
    draw.text((10, height - 20), "Press Y to Return", font=font, fill=(180, 180, 180))
    display.display()

def draw_error_screen(error_message):
    """
    Briefly shows an error message on a black background.
    """
    draw.rectangle((0, 0, width, height), fill=(0, 0, 0))
    draw.text((10, height // 2), error_message, font=font, fill=(255, 0, 0))
    display.display()
    time.sleep(1)  # Display error for 1 second

"""
LCD SCREENS FOR FACIAL RECOGNITION  
"""
def draw_facial_recognition_screen():
    """
    shows a loading screen for facial recognition.
    """
    draw.rectangle((0, 0, width, height), fill=(0, 0, 0))
    draw.text((20, 20), "Starting Facial Recognition...", font=font, fill=(0, 255, 255))
    draw.text((10, height - 20), "Press Y to Cancel", font=font, fill=(180, 180, 180))
    display.display()
def draw_facial_recognition_error_screen():
    """
    shows an error screen for facial recognition.
    """
    draw.rectangle((0, 0, width, height), fill=(0, 0, 0))
    draw.text((20, 20), "Facial Recognition Failed", font=font, fill=(255, 0, 0))
    draw.text((10, height - 20), "Press Y to Return", font=font, fill=(180, 180, 180))
    display.display()
def draw_facial_recognition_success_screen():
    """
    shows a success screen for facial recognition.
    """
    draw.rectangle((0, 0, width, height), fill=(0, 0, 0))
    draw.text((20, 20), "Facial Recognition Successful", font=font, fill=(0, 255, 0))
    draw.text((10, height - 20), "Press Y to Return", font=font, fill=(180, 180, 180))
    display.display()

# --- Facial Recognition Starter Function ---
def start_facial_recognition(script_path, imagelist_path, timeout=30):
    """
    Starts facial recognition script, captures the result (SUCCESS or FAILURE).

    Args:
        script_path (str): Path to the facial recognition Python script.
        timeout (int): Timeout in seconds to wait for facial recognition to finish.

    Returns:
        str: "SUCCESS", "FAILURE", or "TIMEOUT"
    """
    global face_process
    try:     
        #debugging 
        print(f"Starting facial recognition:")
        print(f"  - Script path: {script_path}")
        print(f"  - Imagelist path: {imagelist_path}")
        print(f"  - Timeout: {timeout} seconds")
        
        # Check if files exist
        print(f"  - Script exists: {os.path.exists(script_path)}")
        print(f"  - Imagelist exists: {os.path.exists(imagelist_path)}")
        
        # Start the facial recognition process
        command = ["python3", script_path, "--imagelist", imagelist_path]
        print(f"Executing command: {' '.join(command)}")
        # Start the facial recognition process

        face_process = subprocess.Popen(
            ["python3", script_path, "--imagelist", imagelist_path],  # FIXED
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        try:
            output, error = face_process.communicate(timeout=timeout)
            output = output.strip()

                 # IMPORTANT: Always print error output for debugging
            if error:
                print(f"ERROR OUTPUT: {error}")
            print(f"STANDARD OUTPUT: {output}")

            if output == "SUCCESS":
                return "SUCCESS"
            else:
                return "FAILURE"

        except subprocess.TimeoutExpired:
            face_process.kill()
            print("Facial recognition timed out.")
            return "TIMEOUT"

    except Exception as e:
        print(f"Error starting facial recognition: {e}")
        return "FAILURE"


""" AUDIO AUTHENTICATION Screens"""

# Set backlight
display.set_led(0.05, 0.05, 0.05)

sio = socketio.Client()
try:
    # Use the loaded IP and Port
    socket_url = f"http://{SOCKET_SERVER_IP}:{SOCKET_SERVER_PORT}"
    print(f"Attempting to connect to Socket.IO server at: {socket_url}")
    sio.connect(socket_url)
    print("Socket.IO connection successful.")
except socketio.exceptions.ConnectionError as e:
    print(f"Socket.IO connection failed: {e}")
    # Optionally decide if the program should exit or continue without socket connection
    # sys.exit(1) # Uncomment to exit if connection fails
except Exception as e:
    print(f"An unexpected error occurred during Socket.IO connection: {e}")
    # sys.exit(1) # Uncomment to exit on other errors

# --- Load Password and Set Initial Screen ---
load_password_from_settings()
# --- End Load Password ---

# Draw the initial screen based on whether password needs setting
if current_screen == "set_password":
    draw_set_password_screen()
elif current_screen == "home":
    draw_home_screen()
# Add other initial screen draws if necessary (e.g., lock screen)
else:
    draw_home_screen() # Default fallback


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

                
            elif selected == "Facial Recognition":
                current_screen = "facial_recognition"
                draw_facial_recognition_screen()
                time.sleep(1)  # Give 1 second to show loading screen

                # Start facial recognition and capture result
                # Pass the path to the script and imagelist.txt
                project_root = os.path.dirname(os.path.dirname(__file__))
                script_path = os.path.join(project_root, "camera", "face_recognition.py")
                imagelist_path = os.path.join(project_root, "camera", "faces", "imagelist.txt")
                
                # Check if the file exists
                if not os.path.exists(imagelist_path):
                    print(f"Warning: imagelist.txt not found at {imagelist_path}")
                    result = "FAILURE"
                else:
                    result = start_facial_recognition(script_path,imagelist_path, 30)

                if result == "SUCCESS":
                    draw_facial_recognition_success_screen()
                    #Sends socket event for successful authentication to webserver.py
                    try:
                        sio.emit('auth_event', {
                            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                            'status': 'success',
                            'message': 'Access granted: Face recognized',
                            'method': 'Facial Recognition',
                            'user': 'User',  # Customize as needed
                            'location': 'Main Entrance',
                            'details': 'Matched with known face'
                        })
                    except Exception as e:
                        print("Failed to send socket event:", e)
                elif result == "FAILURE":
                    draw_facial_recognition_error_screen()
                    try:
                        sio.emit('auth_event', {
                            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                            'status': 'Failure',
                            'message': 'Access Not granted: Unknown face',
                            'method': 'Facial Recognition',
                            'user': 'User',  # Customize as needed
                            'location': 'Main Entrance',
                            'details': 'Did not Match with a known face'
                        })
                    except Exception as e:
                        print("Failed to send socket event:", e)
                elif result == "TIMEOUT":
                    draw_error_screen("Face Recognition Timeout!")
                    try:
                        sio.emit('auth_event', {
                            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                            'status': 'Failure',
                            'message': 'Access not Granted: Timeout',
                            'method': 'Facial Recognition',
                            'user': 'User',  # Customize as needed
                            'location': 'Main Entrance',
                            'details': 'Facial recognition timed out'
                        })
                    except Exception as e:
                        print("Failed to send socket event:", e)

                time.sleep(2)  # Show the success or failure screen briefly
                current_screen = "home"
                draw_home_screen()
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

                    if len(entered_digits) == 4:
                        if entered_digits == user_password and password_Set:
                            print("Keypad Authentication Successful")
                            draw_password_confirm_screen()  # or your custom success screen
                            sio.emit('auth_event', {
                                'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                                'status': 'success',
                                'message': 'Access granted: Keypad match',
                                'method': 'Keypad',
                                'user': 'User',
                                'location': 'Main Entrance',
                                'details': 'Correct PIN entered'
                            })
                        else:
                            print("Keypad Authentication Failed")
                            draw_error_screen("Incorrect PIN")
                            sio.emit('auth_event', {
                                'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                                'status': 'failure',
                                'message': 'Access denied: Wrong PIN',
                                'method': 'Keypad',
                                'user': 'User',
                                'location': 'Main Entrance',
                                'details': 'Wrong PIN entered'
                            })
                        # Reset input after checking
                        time.sleep(2)
                        entered_digits = ""
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
                # Save the new password to settings.json
                if save_password_to_settings(user_password):
                    password_Set = True # Mark password as set
                    # Reset for normal usage
                    entered_digits = ""
                    keypad_index = 0
                    current_screen = "home"
                    draw_home_screen()
                else:
                    # Handle save error - maybe show an error screen?
                    draw_error_screen("Failed to save password!")
                    # Go back to set password screen or stay on confirm?
                    current_screen = "set_password"
                    draw_set_password_screen()

            else:
                # "Go Back" selected
                current_screen = "set_password"
                draw_set_password_screen()
            time.sleep(0.2)
    elif current_screen == "facial_recognition":
        if display.read_button(display.BUTTON_Y):
            if face_process and face_process.poll() is None:
                face_process.terminate()
                face_process = None
            current_screen = "home"
            draw_home_screen()
            time.sleep(0.2)
    time.sleep(0.05)
