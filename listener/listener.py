"""
ListenerPi - TCP Listener for Authentication Events

This script listens for success or failure messages from a web server running on a Raspberry Pi. This program is also 
designed to be run on a Raspberry Pi.
It processes the messages and moves the servo to unlock the lock accordingly.

Author: James Kong
"""

import time
import socket
import logging
import sys
import os
import subprocess
from dotenv import load_dotenv 

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path, override=True)
    print(f"Loaded environment variables from: {dotenv_path}") 
else:
    print(f".env file not found at: {dotenv_path}") 

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %I:%M:%S %p', 
    handlers=[logging.StreamHandler(sys.stdout)] 
)
logger = logging.getLogger("ListenerPi")

# --- Configuration ---
LISTENER_HOST = os.getenv('LISTENER_HOST', '0.0.0.0')
LISTENER_PORT = int(os.getenv('LISTENER_PORT', '8080'))

ALLOWED_WEB_SERVER_IP = os.getenv("ALLOWED_WEB_SERVER_IP")
if ALLOWED_WEB_SERVER_IP is None:
    logger.error("Error: ALLOWED_WEB_SERVER_IP environment variable not set.")
    logger.error("Please define ALLOWED_WEB_SERVER_IP in your listener/.env file or environment variables.")
    sys.exit(1) 

# --- Multi-factor Session Configuration ---
REQUIRED_AUTH_COUNT = 2  # Number of unique authentication methods required
UNLOCK_TO_LOCK_DELAY = 3  # Delay in seconds between unlock and lock commands
SESSION_TIMEOUT_SECONDS = 30  # Time allowed per session (seconds)
# -----------------------------------------


# Session state
session_methods = set()
session_start_time = None

def reset_session():
    global session_methods, session_start_time
    session_methods = set()
    session_start_time = None
    logger.info("Session reset.")

def send_command_to_servo(command):
    """
    Sends a command to the Pico using mpremote exec to directly control the servo.
    """
    logger.info(f"Sending command via mpremote exec: {command}")
    try:
        # Construct the Python code to execute on the Pico
        pico_code = ""
        if command == "unlock":
            # Ensure servo module is imported, Pin is imported, create object, turn
            pico_code = "import servo; from machine import Pin; s = servo.SERVO(Pin(26)); s.turn(5); print('unlock command executed')"
        elif command == "lock":
            # Ensure servo module is imported, Pin is imported, create object, turn
            pico_code = "import servo; from machine import Pin; s = servo.SERVO(Pin(26)); s.turn(90); print('lock command executed')"
        else:
            logger.warning(f"Unknown servo command: {command}")
            return

        # Execute the code on the Pico using mpremote
        result = subprocess.run(
            ["mpremote", "exec", pico_code],
            capture_output=True,
            text=True,
            timeout=5  # Add a timeout
        )

        if result.returncode == 0:
            # Check stdout for confirmation from the Pico print statement
            if f"{command} command executed" in result.stdout:
                 logger.info(f"Successfully executed '{command}' command on Pico.")
                 # logger.debug(f"mpremote output: {result.stdout.strip()}")
            else:
                 logger.warning(f"Executed '{command}' on Pico, but confirmation message not found. Output: {result.stdout.strip()}")

        else:
            logger.error(f"Failed to execute '{command}' command on Pico via mpremote. Error: {result.stderr}")

    except subprocess.TimeoutExpired:
         logger.error(f"Timeout executing '{command}' command on Pico via mpremote.")
    except Exception as e:
        logger.error(f"Error sending command via mpremote exec: {e}")

def handle_message(message):
    """
    Process the received message.
    Supports messages in the format '<METHOD> - SUCCESS' or '<METHOD> - FAILURE'.
    Implements multi-factor session logic.
    """
    global session_methods, session_start_time

    try:
        if ' - ' in message:
            method, status = message.split(' - ', 1)
            method = method.strip().upper()
            status = status.strip().upper()
        else:
            logger.warning(f"Received malformed message: {message}")
            return

        now = time.time()
        # Start or check session
        if session_start_time is None:
            session_start_time = now
            logger.info("New authentication session started.")
        elif now - session_start_time > SESSION_TIMEOUT_SECONDS:
            logger.info("Session timed out. Resetting session.")
            reset_session()
            session_start_time = now

        if status == "SUCCESS":
            if method in session_methods:
                logger.info(f"Method {method} already used in this session. Ignoring.")
            else:
                session_methods.add(method)
                logger.info(f"Authenticated with {method}. Methods this session: {session_methods}")
                if len(session_methods) >= REQUIRED_AUTH_COUNT:
                    logger.info(f"Required {REQUIRED_AUTH_COUNT} unique methods reached. Unlocking.")
                    send_command_to_servo("unlock")
                    time.sleep(UNLOCK_TO_LOCK_DELAY)
                    send_command_to_servo("lock")
                    reset_session()
        elif status == "FAILURE":
            logger.info(f"Authentication Failed via {method}.")
        else:
            logger.warning(f"Received unknown status: {status} in message: {message}")
    except Exception as e:
        logger.error(f"Error parsing message: {e}")

def check_and_copy_servo_files():
    """
    Check and copy servo.py to the Pico using mpremote.
    Always copies the latest version.
    """
    servo_py_src = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pico_sensors", "servo_motor", "servo.py")
    servo_py_dst = ":servo.py"

    if not os.path.exists(servo_py_src):
        logger.error(f"Cannot find source file at {servo_py_src}")
        return # Stop if servo.py is missing

    try:
        # Delete the existing servo.py file on the Pico if it exists
        subprocess.run(["mpremote", "rm", servo_py_dst], capture_output=True, text=True)
        # Copy the servo.py file to the Pico
        result = subprocess.run(["mpremote", "cp", servo_py_src, servo_py_dst], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"Successfully copied servo.py to Pico")
        else:
            logger.error(f"Failed to copy servo.py: {result.stderr}")
    except Exception as e:
        logger.error(f"Error copying servo.py: {e}")

def start_listener_server():
    """Starts the TCP server to listen for authentication events."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Allow reusing the address immediately after the server stops
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server_socket.bind((LISTENER_HOST, LISTENER_PORT))
        server_socket.listen(1) # Listen for one incoming connection at a time
        logger.info(f"Listener server started on {LISTENER_HOST}:{LISTENER_PORT}")
        logger.info(f"Only accepting connections from: {ALLOWED_WEB_SERVER_IP}") # Log allowed IP
        logger.info(f"Unlock delay: {UNLOCK_TO_LOCK_DELAY}s, Required methods: {REQUIRED_AUTH_COUNT}, Session timeout: {SESSION_TIMEOUT_SECONDS}s") # Log other configs

        while True:
            logger.info("Waiting for a connection...")
            client_socket = None 
            try:
                client_socket, addr = server_socket.accept()
                logger.info(f"Connection attempt from {addr}")

                # Check if the incoming connection is from the allowed web server IP
                if addr[0] == ALLOWED_WEB_SERVER_IP:
                    logger.info(f"Connection accepted from allowed IP: {addr[0]}")
                    try:
                        # Receive data (up to 1024 bytes)
                        data = client_socket.recv(1024)
                        if data:
                            message = data.decode('utf-8').strip()
                            handle_message(message)
                        else:
                            # Connection closed by client with no data
                            logger.info("Client disconnected without sending data.")

                    except socket.error as e:
                        logger.error(f"Error receiving data: {e}")
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")
                else:
                    # Reject connection from unexpected IP
                    logger.warning(f"Rejected connection from unexpected IP: {addr[0]}")

            except socket.error as e:
                logger.error(f"Error accepting connection: {e}")
                time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received. Shutting down...")
                break 
            finally:
                # Ensure the client connection is closed
                if client_socket:
                    client_socket.close()
                    logger.info("Client connection closed.")

    except socket.error as e:
        logger.error(f"Failed to bind or listen on {LISTENER_HOST}:{LISTENER_PORT}: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
    finally:
        logger.info("Closing server socket.")
        server_socket.close()

if __name__ == "__main__":
    check_and_copy_servo_files()
    start_listener_server()