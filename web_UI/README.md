# MFA Lock Web UI
### Author: James Kong

A web-based interface for the Multi-Factor Authentication Smart Lock system.

## Overview

This web server provides an interface to monitor and control the MFA Lock, a touch-sensitive security system built with a Raspberry Pi Pico microcontroller. The web UI offers:

- Real-time authentication monitoring
- Historical access logs
- Interactive demonstration of the touch pattern
- System settings configuration

## Features

- **Dashboard** - View system status and authentication statistics
- **Authentication Logs** - Review detailed access logs with filtering capabilities
- **How It Works** - Interactive demonstration of the authentication pattern
- **Settings** - Configure system parameters and notification preferences
- **Real-time Updates** - WebSocket integration for live status updates

## Prerequisites

- Python 3.7 or higher
- Raspberry Pi Pico with the touch sensor program installed
- Required Python packages (see Installation)

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/jameskong098/mfalock.git
    cd mfalock/web_UI
    ```

2. Install the required packages:
    ```bash
    pip install flask flask-socketio pyserial
    ```

## Configuration

The web server is pre-configured with default settings. You can modify the following parameters in `web_server.py` if needed:

- `LOG_FILE_PATH` (default: `auth_logs.json`) - Path to the authentication logs file
- Web server port (default: 8080)

## Hardware Setup

Ensure the touch sensor is connected to the Raspberry Pi Pico correctly. Refer to the diagram below for proper wiring:

![Touch Sensor Setup](static/images/touch_setup.png)

- Connect the capacitive touch sensor to GPIO pin 26 on the Pico.
- Ensure all connections are secure and the sensor is functioning properly before starting the server.

## Running the Server

1. Connect your Raspberry Pi Pico to your computer via USB.

2. Ensure the `touch_lock.py` file is available on the Pico. The server will automatically copy the latest version if needed.

3. Start the web server:
    ```bash
    python web_server.py
    ```

4. Open a web browser and navigate to:
    ```
    http://localhost:8080
    ```
    
    Or to access from another device on the same network:
    ```
    http://[your-computer-ip]:8080

    ```

    Use `172.20.102.83` on Brandeis eduroam

## Troubleshooting

### Pico Connection Issues

If the server cannot connect to the Pico:

1. Check that the Pico is properly connected via USB.
2. Verify the `touch_lock.py` file is loaded on the Pico. The server will attempt to copy it automatically.
3. Ensure no other programs are using the serial port.
4. Try disconnecting and reconnecting the Pico.

### Web Interface Issues

If the web interface is not responding:

1. Check that the server is running without errors.
2. Ensure your firewall allows connections on port 8080.
3. Try a different web browser.
4. Clear your browser cache.

## API Endpoints

- `/api/logs` - Get authentication logs
- `/api/logs/<log_id>` (DELETE) - Delete a specific log by its ID
- `/api/settings` - Get or update system settings

## Real-Time Updates

The web UI uses WebSocket integration (via Flask-SocketIO) to provide real-time updates for:

- Authentication events (success or failure)
- Pico connection status
- Authentication statistics (success and failure counts)

## Pages

- **Dashboard**: Displays system status, authentication statistics, and live authentication events.
- **Authentication Logs**: Allows users to view and filter historical access logs.
- **How It Works**: Provides an interactive demonstration of the touch pattern required for authentication.
- **Settings**: Enables configuration of system parameters, such as security level and notification preferences.

## System Requirements

- **Hardware**:
  - Raspberry Pi Pico
  - Capacitive touch sensor connected to GPIO pin 26
- **Software**:
  - Python 3.7 or higher
  - Flask, Flask-SocketIO, and PySerial libraries
  - `mpremote` for communication with the Pico

## Additional Notes

- The server automatically monitors the Pico's output for authentication events and updates the logs in real time.
- The `touch_lock.py` file is copied to the Pico if it is not already present or if an updated version is available.
