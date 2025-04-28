import time
import socket
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %I:%M:%S %p', 
    handlers=[logging.StreamHandler(sys.stdout)] # Log to standard output
)
logger = logging.getLogger("ListenerPi")

# --- Configuration ---
LISTENER_HOST = '0.0.0.0'  # Listen on all available network interfaces
LISTENER_PORT = 8080     # Port to listen on (must match web_server.py)
# ---------------------

def handle_message(message):
    """
    Process the received message.
    Implement your logic here based on the message content.
    For example, control GPIO pins, display messages, etc.
    """
    logger.info(f"Processing message: {message}")
    if message == "SUCCESS":
        logger.info("Authentication Successful - Performing success action...")
        # Add your success action here (e.g., unlock a door)
    elif message == "FAILURE":
        logger.info("Authentication Failed - Performing failure action...")
        # Add your failure action here (e.g., flash an LED)
    else:
        logger.warning(f"Received unknown message: {message}")

def start_listener_server():
    """Starts the TCP server to listen for authentication events."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Allow reusing the address immediately after the server stops
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server_socket.bind((LISTENER_HOST, LISTENER_PORT))
        server_socket.listen(1) # Listen for one incoming connection at a time
        logger.info(f"Listener server started on {LISTENER_HOST}:{LISTENER_PORT}")

        while True:
            logger.info("Waiting for a connection...")
            try:
                client_socket, addr = server_socket.accept()
                logger.info(f"Connection accepted from {addr}")

                try:
                    # Receive data (up to 1024 bytes)
                    data = client_socket.recv(1024)
                    if data:
                        message = data.decode('utf-8').strip()
                        logger.info(f"Received message: {message}")
                        handle_message(message)
                    else:
                        # Connection closed by client with no data
                        logger.info("Client disconnected without sending data.")

                except socket.error as e:
                    logger.error(f"Error receiving data: {e}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                finally:
                    # Ensure the client connection is closed
                    client_socket.close()
                    logger.info("Client connection closed.")

            except socket.error as e:
                logger.error(f"Error accepting connection: {e}")
                # Optional: add a small delay before retrying to accept
                time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received. Shutting down...")
                break # Exit the loop cleanly

    except socket.error as e:
        logger.error(f"Failed to bind or listen on {LISTENER_HOST}:{LISTENER_PORT}: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
    finally:
        logger.info("Closing server socket.")
        server_socket.close()

if __name__ == "__main__":
    start_listener_server()