# Listener Service for MFA Lock

This directory contains the `listener.py` script, which runs on a separate Raspberry Pi (or other device on the network) to receive authentication status messages from the main `web_server.py`.

## Purpose

The `listener.py` script acts as a simple TCP server. It listens on a specified port for incoming connections from the main web server (`web_server.py`). When the web server processes an authentication attempt (either success or failure), it sends a message ("SUCCESS" or "FAILURE") to this listener service.

- The listener automatically copies the necessary `servo.py` file to the connected Raspberry Pi Pico using `mpremote`.
- It then uses `mpremote exec` to directly execute commands on the Pico to control the servo motor via the copied `servo.py`.
- When a "SUCCESS" message is received, the listener executes code on the Pico to unlock the servo, waits for a configured delay, then executes code to re-lock the servo.
- The Pico must be connected via USB for `mpremote` to function.

The `handle_message` function within `listener.py` implements these actions. For example:
- **On "SUCCESS":** Executes unlock code on the Pico, waits, then executes lock code.
- **On "FAILURE":** (No servo action by default, but you can add your own logic.)

## Configuration

Environment variables are loaded from a `.env` file located in the **project root directory** (`mfalock/.env`).

- **`LISTENER_HOST`**: Set to `'0.0.0.0'` to listen on all available network interfaces on the device running the listener.
- **`LISTENER_PORT`**: The port number the listener server will bind to. This **must** match the `LISTENER_PI_PORT` configured in the root `.env` file. The default is `8080`.
- **`ALLOWED_WEB_SERVER_IP`**: The IP address of the main web server Pi. The listener will *only* accept connections from this IP address. This **must** be configured correctly in the root `.env` file.
- **`UNLOCK_TO_LOCK_DELAY`**: The time in seconds the listener waits after unlocking before sending the lock command. Default is 3 seconds.

**Example `.env` file (in `mfalock/`):**
```dotenv
LISTENER_PI_IP=192.168.1.101 # IP of the listener Pi (used by web_server.py)
LISTENER_PORT=8080
ALLOWED_WEB_SERVER_IP=192.168.1.100 # IP of the web server Pi (used by listener.py)
# Add other variables as needed
```

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

Once you have the IP address of the device running the listener, you **must** ensure the `LISTENER_PI_IP` variable is correctly set in the root `.env` file.

```dotenv
# In mfalock/.env
LISTENER_PI_IP="YOUR_LISTENER_PI_IP_ADDRESS" # Replace with the actual IP
LISTENER_PORT=8080 # Ensure this matches the listener's port
ALLOWED_WEB_SERVER_IP="YOUR_WEB_SERVER_IP_ADDRESS" # IP of the machine running web_server.py
```

You also need to ensure the `ALLOWED_WEB_SERVER_IP` in `listener.py` matches the IP address of the Pi running `web_server.py`.

## Pico Setup

- Flash or run `servo_lock.py` on your Pico. It will listen for `lock` and `unlock` commands over USB serial.
- The Pico should be connected to the listener Pi via USB before starting the listener.

## Running the Listener

1.  Ensure Python 3 is installed on the listener Pi.
2.  Install necessary Python packages:
    ```bash
    pip install pyserial # Required by mpremote
    ```
3.  Install `mpremote` if you haven't already:
    ```bash
    pip install mpremote
    ```
4.  Connect the Pico to the listener Pi via USB.
5.  Navigate to the `listener` directory in a terminal.
6.  Run the script:
    ```bash
    python listener.py
    ```
7.  The script will first attempt to copy `servo.py` from the project's `pico_sensors/servo_motor` directory to the Pico. It will then load settings from the root `.env` file and start listening for connections. Keep this script running in the background (e.g., using `screen`, `tmux`, or as a systemd service) for the system to function correctly.

## Multi-Factor Authentication Session Logic

The listener requires multiple unique authentication methods for a successful unlock. The logic is as follows:

- Each session starts when the first authentication message is received.
- You must authenticate with a configurable number of different methods (e.g., VOICE, TOUCH, KEYPAD, etc.) within a set time window.
- If the required number of unique methods is reached (default: 3), the lock will unlock and then re-lock after the configured delay.
- If the session times out before reaching the required count, the session resets and you must start over.
- Duplicate methods within the same session are ignored.
- Only messages in the format "<METHOD> - SUCCESS" or "<METHOD> - FAILURE" are accepted. Malformed messages are ignored and logged.

### Configuration

At the top of `listener.py`, you can adjust these variables:

```
REQUIRED_AUTH_COUNT = 3  # Number of unique authentication methods required
SESSION_TIMEOUT_SECONDS = 30  # Time allowed per session (seconds)
```

Change these values to fit your security and usability needs.

## Testing the Listener (`send_test_msg.py`)

The `send_test_msg.py` script is provided for testing the listener service independently.

- Allows you to manually send any message to the running `listener.py` service, such as `TOUCH - SUCCESS`, `VOICE - FAILURE`, etc.
- Useful for verifying that the listener is running, accepting connections, and triggering the servo unlock/lock sequence correctly via `mpremote` without needing the full web server to be operational.

**How to Use:**

1.  Ensure `listener.py` is running on its designated Pi and configured correctly (especially `ALLOWED_WEB_SERVER_IP`).
2.  Modify the `HOST` variable in `send_test_msg.py` to match the IP address of the Pi running `listener.py`.
3.  The IP address of the machine running `send_test_msg.py` must be the IP address listed in the `ALLOWED_WEB_SERVER_IP` setting within `listener.py`.
4.  Navigate to the `listener` directory in a terminal on the machine where you edited `send_test_msg.py`.
5.  Run the script:
    ```bash
    python send_test_msg.py
    ```
6.  Type your test message (e.g., `TOUCH - SUCCESS`) and press Enter. You can send as many test messages as you like.
7.  Observe the console output of `listener.py` and check if the servo performs the unlock and re-lock actions as expected.
