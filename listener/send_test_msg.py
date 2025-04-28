import socket
import sys

HOST = '172.20.102.83'  # or the IP address of the listener server
PORT = 8080         # must match LISTENER_PORT in listener.py

print("Press Enter to send an unlock/lock test message to the listener server. Press Ctrl+C to exit.")

try:
    while True:
        input("Press Enter to send test message...")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            s.sendall(b"SUCCESS\n")
        print("Test message sent (SUCCESS). The servo should unlock, then lock after a designated number of seconds.")
except KeyboardInterrupt:
    print("\nExiting test client.")
    sys.exit(0)
