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

3. Install the required packages:
    ```bash
    pip install flask flask-socketio pyserial
    ```

## Configuration

The web server is pre-configured with default settings. You can modify the following parameters in `web_server.py` if needed:

- `BAUD_RATE` (default: 115200) - Serial communication speed with the Pico
- `SERIAL_TIMEOUT` (default: 1.0) - Timeout for serial communication
- Web server port (default: 8080)

## Running the Server

1. Connect your Raspberry Pi Pico to your computer via USB

2. Ensure the touch_lock.py file is available on the Pico

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

## Troubleshooting

### Pico Connection Issues

If the server cannot connect to the Pico:

1. Check that the Pico is properly connected via USB
2. Verify the touch_lock.py file is loaded on the Pico
3. Ensure no other programs are using the serial port
4. Try disconnecting and reconnecting the Pico

### Web Interface Issues

If the web interface is not responding:

1. Check that the server is running without errors
2. Ensure your firewall allows connections on port 8080
3. Try a different web browser
4. Clear your browser cache

## API Endpoints

- `/api/logs` - Get authentication logs
- `/api/status` - Get system status
- `/api/settings` - Get or update settings
