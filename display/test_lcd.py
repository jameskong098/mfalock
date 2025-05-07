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

socket_url = f"http://{SOCKET_SERVER_IP}:{SOCKET_SERVER_PORT}" 
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
# Possible screens: "set_password", "confirm", "home", "keypad", "facial_recognition", "voice_recognition" # Added voice_recognition
# Initial screen determined after loading settings
current_screen = "home" # Default to home, will change if password needed

menu_options = [
    "Facial Recognition",
    "Voice Recognition",
    "Touch Password",
    "Rotary Authentication",
    "Keypad Authentication"
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

def draw_message_on_home(message):
    """Draws the home screen and overlays a message."""
    draw_home_screen() # Draw the standard home screen first
    text_width, text_height = draw.textsize(message, font=font)
    x = (width - text_width) / 2
    y = (height - text_height) / 2
    # Draw a semi-transparent background for the message for better visibility
    rect_x0 = x - 10
    rect_y0 = y - 5
    rect_x1 = x + text_width + 10
    rect_y1 = y + text_height + 5
    # Ensure rectangle coordinates are within screen bounds
    rect_x0 = max(0, rect_x0)
    rect_y0 = max(0, rect_y0)
    rect_x1 = min(width, rect_x1)
    rect_y1 = min(height, rect_y1)

    draw.rectangle((rect_x0, rect_y0, rect_x1, rect_y1), fill=(50, 50, 50, 200)) # Dark semi-transparent
    draw.text((x, y), message, font=font, fill=(255, 255, 0)) # Yellow text
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

""" VOICE RECOGNITION SCREENS """
def draw_voice_recognition_start_screen(): # Removed phrase argument
    """Displays a generic listening message."""
    draw.rectangle((0, 0, width, height), fill=(0, 0, 0))
    draw.text((10, 5), "Please say the phrase", font=font, fill=(255, 255, 255))
    draw.text((10, 30), "shown on the web interface.", font=font, fill=(255, 255, 255))

    draw.text((10, height - 35), "Listening...", font=font, fill=(255, 255, 0))
    draw.text((10, height - 20), "Press Y to Cancel", font=font, fill=(180, 180, 180))
    display.display()

def draw_voice_recognition_listening_screen():
    """Indicates the system is actively listening (can be combined or separate)."""
    # This might be integrated into the start screen or shown briefly
    draw.rectangle((0, 0, width, height), fill=(0, 0, 0))
    draw.text((20, 20), "Listening for voice...", font=font, fill=(255, 255, 0))
    draw.text((10, height - 20), "Press Y to Cancel", font=font, fill=(180, 180, 180))
    display.display()

def draw_voice_recognition_success_screen():
    """Shows a success message for voice recognition."""
    draw.rectangle((0, 0, width, height), fill=(0, 0, 0))
    draw.text((20, 20), "Voice Recognition Successful", font=font, fill=(0, 255, 0))
    draw.text((10, height - 20), "Press Y to Return", font=font, fill=(180, 180, 180))
    display.display()

def draw_voice_recognition_failure_screen():
    """Shows a failure message for voice recognition."""
    draw.rectangle((0, 0, width, height), fill=(0, 0, 0))
    draw.text((20, 20), "Voice Recognition Failed", font=font, fill=(255, 0, 0))
    draw.text((10, height - 20), "Press Y to Return", font=font, fill=(180, 180, 180))
    display.display()

def draw_voice_recognition_timeout_screen():
    """Shows a timeout message for voice recognition."""
    draw.rectangle((0, 0, width, height), fill=(0, 0, 0))
    draw.text((20, 20), "Voice Recognition Timeout", font=font, fill=(255, 165, 0)) # Orange color
    draw.text((10, height - 20), "Press Y to Return", font=font, fill=(180, 180, 180))
    display.display()
""" END VOICE RECOGNITION SCREENS """


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

"""
LCD SCREENS FOR Rotary Authentication
"""
def draw_Rotary_screen():

    draw.rectangle((0, 0, width, height), fill=(0, 0, 0))
    draw.text((20, 20), "START TURNING", font=font, fill=(0, 255, 255))
    draw.text((10, height - 20), "Press Y to Cancel", font=font, fill=(180, 180, 180))
    display.display()
def draw_rotary_error_screen():
    """
    shows an error screen for Rotary.
    """
    draw.rectangle((0, 0, width, height), fill=(0, 0, 0))
    draw.text((20, 20), "Rotary Authentication Failed", font=font, fill=(255, 0, 0))
    draw.text((10, height - 20), "Press Y to Return", font=font, fill=(180, 180, 180))
    display.display()
def draw_rotary_success_screen():
    """
    shows a success screen for Rotary.
    """
    draw.rectangle((0, 0, width, height), fill=(0, 0, 0))
    draw.text((20, 20), "Rotary Successful", font=font, fill=(0, 255, 0))
    draw.text((10, height - 20), "Press Y to Return", font=font, fill=(180, 180, 180))
    display.display()

def draw_rotary_timeout_screen():
    """Shows a timeout message for Rotary."""
    draw.rectangle((0, 0, width, height), fill=(0, 0, 0))
    draw.text((20, 20), "Rotary Timeout", font=font, fill=(255, 165, 0)) # Orange color
    draw.text((10, height - 20), "Press Y to Return", font=font, fill=(180, 180, 180))
    display.display()

"""
LCD SCREENS FOR Tap Pattern
"""
def draw_tap_screen():

    draw.rectangle((0, 0, width, height), fill=(0, 0, 0))
    draw.text((20, 20), "START TAPPING", font=font, fill=(0, 255, 255))
    draw.text((10, height - 20), "Press Y to Cancel", font=font, fill=(180, 180, 180))
    display.display()
def draw_tap_error_screen():
    """
    shows an error screen for Rotary.
    """
    draw.rectangle((0, 0, width, height), fill=(0, 0, 0))
    draw.text((20, 20), "Tap pattern Auth Failed", font=font, fill=(255, 0, 0))
    draw.text((10, height - 20), "Press Y to Return", font=font, fill=(180, 180, 180))
    display.display()
def draw_tap_success_screen():
    """
    shows a success screen for Rotary.
    """
    draw.rectangle((0, 0, width, height), fill=(0, 0, 0))
    draw.text((20, 20), "Tap pattern Successful", font=font, fill=(0, 255, 0))
    draw.text((10, height - 20), "Press Y to Return", font=font, fill=(180, 180, 180))
    display.display()

def draw_tap_timeout_screen():
    """Shows a timeout message for Rotary."""
    draw.rectangle((0, 0, width, height), fill=(0, 0, 0))
    draw.text((20, 20), "Tap Pattern Timeout", font=font, fill=(255, 165, 0)) # Orange color
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


# --- Voice Recognition Starter Function ---
def start_voice_recognition(script_path, timeout=35):
    """
    Starts the voice recognition script, captures the phrase and result.
    Sends the phrase via Socket.IO.

    Args:
        script_path (str): Path to the voice recognition Python script (audio_utils.py).
        timeout (int): Timeout in seconds for the entire process.

    Returns:
        tuple: (result, phrase)
               result: "SUCCESS", "FAILURE", "TIMEOUT", or "ERROR"
               phrase: The phrase generated by the script, or None.
    """
    global voice_process
    phrase = None
    result = "ERROR"  

    try:
        print(f"Starting voice recognition:")
        print(f"  - Script path: {script_path}")
        print(f"  - Timeout: {timeout} seconds")
        print(f"  - Script exists: {os.path.exists(script_path)}")

        command = ["python3", script_path]
        print(f"Executing command: {' '.join(command)}")

        voice_process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1, 
            universal_newlines=True
        )

        start_time = time.time()
        script_output_processed = False
        stdout_lines = []
        stderr_lines = []

        # Non-blocking read from stdout and stderr
        while True:
            # Check for overall timeout for the voice recognition process
            if time.time() - start_time > timeout:
                if voice_process.poll() is None:  # If process is still running
                    print("Voice recognition script exceeded main timeout. Terminating.")
                    voice_process.terminate() # Try to terminate gracefully
                    try:
                        # Wait a short moment for termination
                        voice_process.wait(timeout=1.0)
                    except subprocess.TimeoutExpired:
                        print("Process did not terminate gracefully, killing.")
                        voice_process.kill() # Force kill if terminate fails
                    
                    # After kill/terminate, try to get remaining output
                    # This might still raise if pipes are broken, hence the try-except
                    try:
                        stdout_rem, stderr_rem = voice_process.communicate()
                        if stdout_rem: stdout_lines.extend(stdout_rem.splitlines())
                        if stderr_rem: stderr_lines.extend(stderr_rem.splitlines())
                    except ValueError: # Handles "I/O operation on closed file" if communicate is called on an already closed pipe
                        print("Error communicating with process after timeout/kill, pipes might be closed.")
                        
                if not script_output_processed: result = "TIMEOUT"
                break # Exit the loop on timeout

            # Read a line from stdout without blocking indefinitely
            # This requires making stdout non-blocking or using select, which is complex.
            # A simpler approach for line-by-line processing with a timeout is to
            # let the Popen object manage its streams and use communicate() with a timeout,
            # but that doesn't allow immediate processing of "PHRASE:".
            # So, we stick to readline but must be careful.

            try:
                line = voice_process.stdout.readline()
            except ValueError: # Can happen if the pipe is closed unexpectedly
                print("ValueError reading stdout, process might have terminated.")
                break


            if line:
                line = line.strip()
                stdout_lines.append(line) # Store all stdout for later full log if needed
                # print(f"Voice Script STDOUT: {line}") # Already printing specific lines

                if line.startswith("PHRASE:"):
                    phrase = line.replace("PHRASE:", "").strip()
                    print(f"Extracted phrase: {phrase}")
                    try:
                        if sio.connected:
                             sio.emit('voice_phrase_update', {'phrase': phrase})
                             print("Emitted voice_phrase_update with phrase.")
                        else:
                            print("Cannot emit voice_phrase_update, Socket.IO not connected.")
                    except Exception as e:
                        print(f"Failed to send voice_phrase_update socket event: {e}")
                elif line.startswith("PARTIAL_RECOGNIZED_TEXT:"):
                    partial_text = line.replace("PARTIAL_RECOGNIZED_TEXT:", "").strip()
                    # print(f"Partial text: {partial_text}") # For debugging
                    try:
                        if sio.connected:
                            sio.emit('recognized_speech_input', {'text': partial_text})
                            # print(f"Emitted partial recognized speech: {partial_text}") # Can be too verbose
                        # else: # Optional: log if not connected
                            # print("Socket.IO not connected, cannot emit partial speech.")
                    except Exception as e:
                        print(f"Failed to send partial recognized_speech_input: {e}")
                elif line.startswith("FINAL_RECOGNIZED_TEXT:"):
                    final_text = line.replace("FINAL_RECOGNIZED_TEXT:", "").strip()
                    # print(f"Final text: {final_text}") # For debugging
                    try:
                        if sio.connected:
                            sio.emit('recognized_speech_input', {'text': final_text})
                            # print(f"Emitted final recognized speech: {final_text}")
                        # else:
                            # print("Socket.IO not connected, cannot emit final speech.")
                    except Exception as e:
                        print(f"Failed to send final recognized_speech_input: {e}")
                elif line == "VOICE - SUCCESS":
                    result = "SUCCESS"
                    script_output_processed = True
                elif line == "VOICE - FAILURE":
                    result = "FAILURE"
                    script_output_processed = True
                elif line == "VOICE - TIMEOUT":
                    result = "TIMEOUT"
                    script_output_processed = True
                elif line == "VOICE - ERROR":
                    result = "ERROR"
                    script_output_processed = True
            
            # Check if the process has ended
            if voice_process.poll() is not None:
                # Process has ended, read any remaining output from stdout
                # This is important because readline() might miss the last lines if no newline
                try:
                    for remaining_line in voice_process.stdout: # Reads until EOF
                        if remaining_line:
                            remaining_line = remaining_line.strip()
                            stdout_lines.append(remaining_line)
                            print(f"Voice Script STDOUT (remaining): {remaining_line}")
                            # Check for result lines again in remaining output
                            if remaining_line == "VOICE - SUCCESS": result = "SUCCESS"; script_output_processed = True
                            elif remaining_line == "VOICE - FAILURE": result = "FAILURE"; script_output_processed = True
                            elif remaining_line == "VOICE - TIMEOUT": result = "TIMEOUT"; script_output_processed = True
                            elif remaining_line == "VOICE - ERROR": result = "ERROR"; script_output_processed = True
                except ValueError:
                     print("ValueError reading remaining stdout, process might have terminated abruptly.")
                break # Exit the loop as process has finished

        # After the loop (due to timeout or process end), ensure process is cleaned up
        if voice_process.poll() is None: # If still running (e.g. loop broke for other reasons)
            print("Process still running after loop, terminating.")
            voice_process.terminate()
            try:
                voice_process.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                voice_process.kill()

        # Capture all stderr output at the end
        # This is safer than trying to read it line-by-line if it's not line-buffered
        try:
            stderr_output = voice_process.stderr.read()
            if stderr_output:
                stderr_lines.extend(stderr_output.strip().splitlines())
                print(f"Voice Script Full STDERR:\n{stderr_output.strip()}")
        except ValueError:
            print("ValueError reading stderr at the end, pipes might be closed.")

        # Clear recognized text on UI after processing finishes, regardless of outcome
        try:
            if sio.connected:
                sio.emit('recognized_speech_input', {'text': ''})
                print("Emitted empty recognized_speech_input to clear UI.")
        except Exception as e:
            print(f"Failed to send clearing recognized_speech_input: {e}")

        if stderr_lines and not script_output_processed and result == "ERROR":
            print("Considering stderr as indication of error as no explicit result was processed.")
            # result remains "ERROR"

        print(f"Voice recognition finished. Determined Result: {result}, Phrase: {phrase}")
        return result, phrase

    except Exception as e:
        print(f"Error starting/managing voice recognition process: {e}")
        if voice_process and voice_process.poll() is None:
            voice_process.kill()
            # Attempt to communicate to free up resources, but might fail if already errored
            try:
                voice_process.communicate()
            except:
                pass
        return "ERROR", phrase
    finally:
        if voice_process: # Ensure stderr is closed
            if voice_process.stderr:
                voice_process.stderr.close()
            if voice_process.stdout: # Ensure stdout is closed
                voice_process.stdout.close()
        voice_process = None

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

# Global variable for the voice process
voice_process = None

# Initialize Socket.IO client
sio = socketio.Client(logger=False, engineio_logger=False) # Set logger to True for debugging if needed
has_connected = False
#socket to lsiten for rotary and touch events
# Add this handler to process any authentication event

@sio.event
def auth_event(data):
    """Handle all authentication events"""
    global current_screen
    
    status = data.get('status', '').lower()
    method = data.get('method', 'Unknown')
    
    print(f"Received auth_event: {method} - {status}")
    
    # Only handle touch and rotary here (other methods have their own handlers)
    if method in ['Touch Pattern', 'Rotary Input']:
        if status == 'success':
            # Show success screen
            if method == 'Touch Pattern':
                draw_tap_success_screen()
                time.sleep(2)
                draw_home_screen()
            else:  # Rotary Input
                draw_rotary_success_screen()
            
            time.sleep(2)
            
            # Return to home
            current_screen = "home"
            emit_lcd_mode_change(current_screen)
            draw_home_screen()
        elif status == 'failure':
            # Show failure message
            draw_error_screen(f"{method} Failed!")
            time.sleep(2)
            draw_home_screen()
            # Stay on current screen or return to home based on your preference

@sio.event
def connect():
    global has_connected
    print("LCD client: Connection established with web server")
    has_connected = True
    # Emit initial mode once connected and home screen is assumed to be active
    # Ensure current_screen is defined before calling this
    if 'current_screen' in globals() and current_screen:
        emit_lcd_mode_change(current_screen)
    else:
        emit_lcd_mode_change("home") # Default to home/idle

@sio.event
def connect_error(data):
    global has_connected
    print(f"LCD client: The connection failed! Data: {data}")
    has_connected = False

@sio.event
def disconnect():
    global has_connected
    print("LCD client: Disconnected!")
    has_connected = False

def emit_lcd_mode_change(new_mode_internal):
    if not has_connected:
        # print("LCD client: Not connected, cannot emit mode change.") # Optional log
        return
    try:
        ui_mode = "idle"  # Default to idle
        if new_mode_internal == "home":
            ui_mode = "idle"
        elif new_mode_internal == "keypad":
            ui_mode = "keypad"
        elif new_mode_internal == "facial_recognition":
            ui_mode = "facial_recognition"
        elif new_mode_internal == "voice_recognition":
            ui_mode = "voice_recognition"
        # Add other mappings for current_screen values if needed (e.g., set_password)

        print(f"LCD client: Emitting lcd_mode_update. Internal: '{new_mode_internal}', UI: '{ui_mode}'")
        sio.emit('lcd_mode_update', {'mode': ui_mode})
    except Exception as e:
        print(f"LCD client: Failed to send lcd_mode_update event: {e}")

# ... (rest of your functions like draw_home_screen, start_facial_recognition, etc.)

# Before your main loop, attempt to connect
try:
    print("LCD client: Attempting to connect to web server...")
    sio.connect('http://localhost:8080', wait_timeout=10) # Adjust address if needed
except socketio.exceptions.ConnectionError as e:
    print(f"LCD client: Could not connect to web server at http://localhost:8080 - {e}")
    # Optionally can decide if the script should exit or continue without web server comms

# Initialize current_screen before the loop and emit initial state if not done in connect handler
current_screen = "home"
# ... any other initializations ...
draw_home_screen()
# If not connected yet, the connect handler will emit the mode.
# If already connected (e.g. quick restart), emit here.
if has_connected:
    emit_lcd_mode_change(current_screen)


while True:
    if not sio.connected and not has_connected: # Attempt to reconnect if connection was lost
        try:
            print("LCD client: Attempting to reconnect to web server...")
            sio.connect('http://localhost:8080', wait_timeout=5)
        except socketio.exceptions.ConnectionError:
            print("LCD client: Reconnect failed. Will try again later.")
            time.sleep(5) # Wait before next reconnect attempt
            continue # Skip the rest of the loop iteration

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
            if selected == "Touch Password":
                draw_tap_screen()
                time.sleep(2)
                draw_home_screen()
            elif selected == "Rotary Authentication":
                draw_Rotary_screen()
                time.sleep(2)
                draw_home_screen()
            elif selected == "Keypad Authentication":
                current_screen = "keypad"
                entered_digits = "" # Reset digits when entering keypad screen
                keypad_index = 0
                try: # Emit keypad_update when screen is entered
                    sio.emit('keypad_update', {'digits': entered_digits})
                except Exception as e:
                    print(f"Error emitting initial keypad_update: {e}")
                emit_lcd_mode_change(current_screen) 
                draw_keypad_screen()

                
            elif selected == "Facial Recognition":
                current_screen = "Facial_recognition"
                emit_lcd_mode_change(current_screen) 
                draw_facial_recognition_screen()
                time.sleep(1)  # Give 1 second to show loading screen

                # Start facial recognition and capture result
                # Pass the path to the script and imagelist.txt
                project_root = os.path.dirname(os.path.dirname(__file__))
                script_path = os.path.join(project_root, "camera", "face_recognition_code.py")
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
                            'status': 'failure', # Standardized
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
                            'status': 'failure', # Standardized
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
                emit_lcd_mode_change(current_screen) 
                draw_home_screen()
            elif selected == "Voice Recognition":
                current_screen = "Voice_recognition"
                print(current_screen)
                emit_lcd_mode_change(current_screen) 
                draw_voice_recognition_start_screen() 

                project_root = os.path.dirname(os.path.dirname(__file__))
                script_path = os.path.join(project_root, "audio", "utils", "audio_utils.py")

                # Start voice recognition and capture result
                result, phrase = start_voice_recognition(script_path, 35) # 35s timeout

                # Handle result: Draw screen and emit auth_event
                if result == "SUCCESS":
                    draw_voice_recognition_success_screen()
                    try:
                        sio.emit('auth_event', {
                            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                            'status': 'success',
                            'message': 'Access granted: Voice matched',
                            'method': 'Voice Recognition',
                            'user': 'User',
                            'location': 'Main Entrance',
                            'details': f'Correct phrase spoken: {phrase if phrase else "N/A"}'
                        })
                        print("Sent 'success' auth_event for voice recognition.")
                    except Exception as e:
                        print(f"Failed to send success socket event for voice: {e}")
                elif result == "FAILURE":
                    draw_voice_recognition_failure_screen()
                    try:
                        sio.emit('auth_event', {
                            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                            'status': 'failure', # Standardized
                            'message': 'Access denied: Voice mismatch or not recognized',
                            'method': 'Voice Recognition',
                            'user': 'User',
                            'location': 'Main Entrance',
                            'details': f'Incorrect phrase or no match. Expected phrase (if available): {phrase if phrase else "N/A"}'
                        })
                        print("Sent 'failure' auth_event for voice recognition (mismatch).")
                    except Exception as e:
                        print(f"Failed to send failure socket event for voice: {e}")
                elif result == "TIMEOUT":
                    draw_voice_recognition_timeout_screen()
                    try:
                        sio.emit('auth_event', {
                            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                            'status': 'failure', # Standardized to lowercase
                            'message': 'Access denied: Voice recognition timed out',
                            'method': 'Voice Recognition',
                            'user': 'User',
                            'location': 'Main Entrance',
                            'details': f'Timeout waiting for voice input. Expected phrase (if available): {phrase if phrase else "N/A"}'
                        })
                        print("Sent 'failure' auth_event for voice recognition (timeout).")
                    except Exception as e:
                        print(f"Failed to send timeout socket event for voice: {e}")
                else:  # ERROR case
                    draw_error_screen("Voice Recog Error!") # Generic error screen
                    try:
                        sio.emit('auth_event', {
                            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                            'status': 'failure', # Standardized to lowercase
                            'message': 'Access denied: Voice recognition script error',
                            'method': 'Voice Recognition',
                            'user': 'User',
                            'location': 'Main Entrance',
                            'details': f'Error in voice recognition process. Expected phrase (if available): {phrase if phrase else "N/A"}'
                        })
                        print("Sent 'failure' auth_event for voice recognition (script error).")
                    except Exception as e:
                        print(f"Failed to send error socket event for voice: {e}")
                
                # Clear the displayed phrase on the web UI after attempt
                try:
                    sio.emit('display_voice_phrase', {'phrase': ''})
                    sio.emit('recognized_speech_input', {'text': ''}) # Clear recognized text
                except Exception as e:
                    print(f"Failed to clear voice phrase on web UI: {e}")

                # Wait for Y press or timeout to return home
                wait_start_time = time.time()
                returned_home = False
                while time.time() - wait_start_time < 5: # Wait up to 5 seconds on result screen
                     if display.read_button(display.BUTTON_Y):
                         current_screen = "home"
                         emit_lcd_mode_change(current_screen) 
                         draw_home_screen()
                         returned_home = True
                         break
                     time.sleep(0.1) # Non-blocking sleep
                if not returned_home:
                    current_screen = "home"
                    emit_lcd_mode_change(current_screen) 
                    draw_home_screen()

            time.sleep(0.2) # Debounce X button

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
            
            # Emit keypad_update after digit change
            try:
                sio.emit('keypad_update', {'digits': entered_digits})
            except Exception as e:
                print(f"Error emitting keypad_update: {e}")

            if len(entered_digits) == 4:
                if entered_digits == user_password and password_Set:
                    print("Keypad Authentication Successful")
                    draw_keypad_success_screen() 
                    sio.emit('auth_event', {
                        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                        'status': 'success',
                        'message': 'Access granted: Keypad match',
                        'method': 'Keypad',
                        'user': 'User',
                        'location': 'Main Entrance',
                        'details': 'Correct PIN entered'
                    })
                    time.sleep(2) # Show success screen for 2 seconds
                    entered_digits = "" # Reset digits
                    keypad_index = 0    # Reset keypad selection
                    current_screen = "home" # Go to home screen
                    emit_lcd_mode_change(current_screen)
                    draw_home_screen()
                else:
                    print("Keypad Authentication Failed")
                    draw_error_screen("Incorrect PIN")
                    sio.emit('auth_event', {
                        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                        'status': 'failure', # Standardized
                        'message': 'Access denied: Wrong PIN',
                        'method': 'Keypad',
                        'user': 'User',
                        'location': 'Main Entrance',
                        'details': 'Wrong PIN entered'
                    })
                    time.sleep(2) # Show error for 2 seconds
                    entered_digits = "" # Reset digits for retry
                    draw_keypad_screen() # Redraw keypad for another attempt
            else: # Not 4 digits yet, just update the display
                draw_keypad_screen()
            time.sleep(0.2)

        elif display.read_button(display.BUTTON_Y):  # Return to home
            print("pressed Y to return")
            entered_digits = ""
            keypad_index = 0
            current_screen = "home"
            emit_lcd_mode_change(current_screen) 
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
            # Emit keypad_update after digit change in set_password screen as well
            # This is for consistency, though web UI might not display it during setup
            try:
                sio.emit('keypad_update', {'digits': entered_digits})
            except Exception as e:
                print(f"Error emitting keypad_update from set_password: {e}")
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
                    emit_lcd_mode_change(current_screen)
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
    elif current_screen == "Facial_recognition":
        if display.read_button(display.BUTTON_Y):
            if face_process and face_process.poll() is None:
                face_process.terminate()
                face_process = None
            current_screen = "home"
            emit_lcd_mode_change(current_screen)
            draw_home_screen()
            time.sleep(0.2)
    elif current_screen == "Voice_recognition":
        print("Voice recognition screen active")
        # Handle cancellation while the voice script is running OR while on result screen
        if display.read_button(display.BUTTON_Y):
            print("starting cancelation for voice recognition")
            if voice_process and voice_process.poll() is None:
                print("Cancelling voice recognition script...")
                voice_process.kill() 
                try:
                    voice_process.communicate(timeout=1) # Attempt to get remaining output
                except subprocess.TimeoutExpired:
                    print("Timeout during communicate after kill in Y press.")
                except ValueError:
                    print("ValueError during communicate after kill in Y press (pipes closed).")
                voice_process = None
                try:
                    if sio.connected:
                        sio.emit('auth_event', {
                            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                            'status': 'cancelled',
                            'message': 'Voice recognition cancelled by user',
                            'method': 'Voice Recognition',
                            'user': 'User',
                            'location': 'Main Entrance',
                            'details': 'User pressed cancel button during operation.'
                        })
                        sio.emit('display_voice_phrase', {'phrase': ''}) 
                        sio.emit('recognized_speech_input', {'text': ''}) # Clear recognized text on cancel
                        print("Sent 'cancelled' auth_event for voice recognition.")
                    else:
                        print("Cannot emit events - Socket.IO not connected")
                except Exception as e:
                    print(f"Failed to send cancel socket event for voice: {e}")
            
            # If Y is pressed on the result screen, it will also bring back to home
            print("Returning to home screen from voice recognition.")
            current_screen = "home"
            emit_lcd_mode_change(current_screen)
            draw_home_screen()
            time.sleep(0.2) # Debounce Y button

    time.sleep(0.05)
