import socket
import sys

HOST = '172.20.102.83'  # or the IP address of the listener server
PORT = 8080         # must match LISTENER_PORT in listener.py

print("Type a test message to send to the listener server (e.g., 'TOUCH - SUCCESS'). Press Ctrl+C to exit.")

try:
    while True:
        msg = input("Enter test message: ").strip()
        if not msg:
            print("No message entered. Please type a message.")
            continue
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            s.sendall((msg + "\n").encode('utf-8'))
        print(f"Test message sent: {msg}")
except KeyboardInterrupt:
    print("\nExiting test client.")
    sys.exit(0)
