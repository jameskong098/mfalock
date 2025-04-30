import socket
import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file in the root directory
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path, override=True)
    print(f"Loaded environment variables from: {dotenv_path}")
else:
    print(f".env file not found at: {dotenv_path}. Using defaults or expecting environment variables.")

# Retrieve Listener IP and Port from environment variables
HOST = os.getenv("LISTENER_PI_IP")
PORT_STR = os.getenv("LISTENER_PI_PORT", "8080") # Default to "8080" if not set

# Validate LISTENER_PI_IP
if HOST is None:
    print("Error: LISTENER_PI_IP environment variable not set.")
    print("Please define LISTENER_PI_IP in your .env file or environment variables.")
    sys.exit(1)

# Validate and convert LISTENER_PI_PORT
try:
    PORT = int(PORT_STR)
except ValueError:
    print(f"Warning: Invalid LISTENER_PI_PORT value '{PORT_STR}'. Using default port 8080.")
    PORT = 8080

print(f"Attempting to connect to listener at {HOST}:{PORT}")
print("Type a test message to send to the listener server (e.g., 'TOUCH - SUCCESS'). Press Ctrl+C to exit.")

try:
    while True:
        msg = input("Enter test message: ").strip()
        if not msg:
            print("No message entered. Please type a message.")
            continue
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5) # Add a timeout for the connection attempt
                s.connect((HOST, PORT))
                s.sendall((msg + "\n").encode('utf-8'))
            print(f"Test message sent: {msg}")
        except socket.timeout:
            print(f"Error: Connection to {HOST}:{PORT} timed out.")
        except socket.error as e:
            print(f"Error connecting or sending to {HOST}:{PORT}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

except KeyboardInterrupt:
    print("\nExiting test client.")
    sys.exit(0)
