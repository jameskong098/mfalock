# Listener Service for MFA Lock

This directory contains the `listener.py` script, which runs on a separate Raspberry Pi (or other device on the network) to receive authentication status messages from the main `web_server.py`.

## Purpose

The `listener.py` script acts as a simple TCP server. It listens on a specified port for incoming connections. When the main web server (`web_server.py`) processes an authentication attempt (either success or failure), it sends a message ("SUCCESS" or "FAILURE") to this listener service.

**New in this version:**
- The listener now automatically communicates with the Raspberry Pi Pico running `servo_lock.py` via serial (USB).
- When a "SUCCESS" message is received, the listener sends an `unlock` command to the Pico, waits 5 seconds, then sends a `lock` command to re-lock the servo.
- The Pico must be running `servo_lock.py` and connected via USB (usually `/dev/ttyACM0`).

The `handle_message` function within `listener.py` implements these actions. For example:
- **On "SUCCESS":** Sends `unlock` to the Pico, waits, then sends `lock`.
- **On "FAILURE":** (No servo action by default, but you can add your own logic.)

## Configuration

- **`LISTENER_HOST`**: Set to `'0.0.0.0'` to listen on all available network interfaces on the device running the listener.
- **`LISTENER_PORT`**: The port number the listener server will bind to. This **must** match the `LISTENER_PI_PORT` configured in `web_server.py`. The default is `8080`.
- **`/dev/ttyACM0`**: The default serial port for the Pico. Change this in `listener.py` if your Pico appears on a different port.

## Finding the Listener Pi's IP Address

The main web server needs the IP address of the device running `listener.py` to send messages to it. Here are common ways to find the IP address of your Raspberry Pi:

1.  **Using the `hostname` command (on the Pi):**
    Open a terminal on the Raspberry Pi and run:
    ```bash
    hostname -I
    ```
    This command usually prints the IP address(es) assigned to the Pi's network interfaces (e.g., `192.168.1.105`). Take the primary IP address relevant to your local network.

2.  **Checking your Router's Interface:**
    Log in to your router's web administration page (usually accessible via an address like `192.168.1.1` or `192.168.0.1`). Look for a section listing "Connected Devices," "DHCP Clients," or similar. Find your Raspberry Pi in the list (it might be identified by its hostname, often `raspberrypi` by default) and note its assigned IP address.

3.  **Using a Network Scanner:**
    Tools like `nmap` (on Linux/macOS/Windows) or mobile apps like Fing can scan your local network and list connected devices with their IP addresses. You can identify the Pi by its hostname or MAC address.
    Example using `nmap` (replace `192.168.1.0/24` with your network range):
    ```bash
    nmap -sn 192.168.1.0/24
    ```

## Updating the Web Server

Once you have the IP address of the device running the listener, you **must** update the `LISTENER_PI_IP` constant in `/Users/jameskong/Documents/mfalock/web_UI/web_server.py`:

```python
# In web_server.py
# ...
LISTENER_PI_IP = "YOUR_LISTENER_PI_IP_ADDRESS" # Replace with the actual IP
LISTENER_PI_PORT = 8080
# ...
```

## Pico Setup

- Flash or run `servo_lock.py` on your Pico. It will listen for `lock` and `unlock` commands over USB serial.
- The Pico should be connected to the listener Pi via USB before starting the listener.

## Running the Listener

1.  Ensure Python 3 and the `pyserial` package are installed:
    ```bash
    pip install pyserial
    ```
2.  Connect the Pico to the Pi via USB and ensure `servo_lock.py` is running on the Pico.
3.  Navigate to the `listener` directory in a terminal.
4.  Run the script:
    ```bash
    python listener.py
    ```
5.  The script will log messages to the console, including serial communication with the Pico. Keep this script running in the background (e.g., using `screen`, `tmux`, or as a systemd service) for the system to function correctly.
