"""
MFA Lock Web Server
------------------
This web server provides an interface to communicate with a Raspberry Pi Pico
running the touch sensor security lock. The server:
1. Hosts the web interface
2. Communicates with the Pico over USB serial
3. Provides real-time updates on authentication events

Author: James Kong
Date: March 10, 2025
"""

import os
import sys
import time
import json
import serial
import threading
import logging
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("MFALock")

# Flask app setup
app = Flask(__name__, static_folder='.', static_url_path='')
app.config['SECRET_KEY'] = 'mfalock-secret-key!'
socketio = SocketIO(app)

# Global variables
pico_connected = False
serial_port = None
auth_logs = []

# Pico connection settings
BAUD_RATE = 115200
SERIAL_TIMEOUT = 1.0

def find_pico_port():
    """Look for the Pico's serial port on common platforms"""
    # For macOS
    candidates = [
        '/dev/tty.usbmodem*',
        '/dev/tty.usbserial*',
        # Linux patterns
        '/dev/ttyACM*',
        '/dev/ttyUSB*',
        # Windows patterns (would need different handling)
    ]
    
    import glob
    for pattern in candidates:
        ports = glob.glob(pattern)
        if ports:
            return ports[0]
    
    return None

def setup_pico_connection():
    """Establish connection to the Pico device"""
    global serial_port, pico_connected
    
    port = find_pico_port()
    if not port:
        logger.error("Could not find Pico device. Please check connection.")
        return False
    
    try:
        serial_port = serial.Serial(port, baudrate=BAUD_RATE, timeout=SERIAL_TIMEOUT)
        logger.info(f"Connected to Pico on {port}")
        time.sleep(1)  # Wait for connection to stabilize
        serial_port.write(b"\x03\r\n")  # Ctrl+C to interrupt any running program
        time.sleep(0.5)
        serial_port.write(b"\x04\r\n")  # Ctrl+D to soft reset
        time.sleep(1)
        
        # Clear input buffer
        serial_port.reset_input_buffer()
        
        pico_connected = True
        return True
    except Exception as e:
        logger.error(f"Failed to connect to Pico: {e}")
        return False

def run_touch_lock():
    """Send command to run the touch lock program on the Pico"""
    if not pico_connected or not serial_port:
        logger.error("Pico is not connected. Cannot run touch lock program.")
        return False
    
    try:
        # Run the touch lock Python file
        logger.info("Starting touch lock program on Pico...")
        serial_port.write(b"import touch_lock\r\n")
        return True
    except Exception as e:
        logger.error(f"Failed to run touch lock program: {e}")
        return False

def monitor_pico():
    """Monitor the Pico's serial output for events"""
    global auth_logs
    
    if not pico_connected or not serial_port:
        logger.error("Pico is not connected. Cannot monitor output.")
        return
    
    logger.info("Starting Pico monitoring thread")
    
    while pico_connected:
        try:
            if serial_port.in_waiting > 0:
                line = serial_port.readline().decode('utf-8').strip()
                if line:
                    logger.info(f"Pico: {line}")
                    
                    # Process authentication events
                    if "ACCESS GRANTED" in line:
                        log_entry = {
                            'id': len(auth_logs) + 1,
                            'timestamp': datetime.now().isoformat(),
                            'user': 'User',  # We don't have individual user identification
                            'location': 'Main Entrance',
                            'status': 'success',
                            'details': 'Pattern recognized correctly'
                        }
                        auth_logs.append(log_entry)
                        socketio.emit('auth_event', log_entry)
                    
                    # Detect failed attempts
                    elif any(x in line for x in ["pattern failed", "Pattern timeout", "too short", "Final tap should be quick"]):
                        log_entry = {
                            'id': len(auth_logs) + 1,
                            'timestamp': datetime.now().isoformat(),
                            'user': 'Unknown',
                            'location': 'Main Entrance',
                            'status': 'failure',
                            'details': f'Incorrect pattern: {line}'
                        }
                        auth_logs.append(log_entry)
                        socketio.emit('auth_event', log_entry)
                
            time.sleep(0.1)
        except Exception as e:
            logger.error(f"Error in Pico monitoring: {e}")
            pico_connected = False
            break

def pico_connection_thread():
    """Thread to handle Pico connection and monitoring"""
    if setup_pico_connection():
        if run_touch_lock():
            monitor_pico()
        else:
            logger.error("Failed to start touch lock program")
    else:
        logger.error("Failed to connect to Pico")

@app.route('/')
def index():
    """Serve the main HTML page"""
    return app.send_static_file('index.html')

@app.route('/api/logs')
def get_logs():
    """API endpoint to get authentication logs"""
    return jsonify(auth_logs)

@app.route('/api/status')
def get_status():
    """API endpoint to check system status"""
    return jsonify({
        'pico_connected': pico_connected,
        'auth_success_count': sum(1 for log in auth_logs if log['status'] == 'success'),
        'auth_failure_count': sum(1 for log in auth_logs if log['status'] == 'failure')
    })

@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    logger.info("Client connected to WebSocket")
    emit('status_update', {
        'pico_connected': pico_connected,
        'auth_success_count': sum(1 for log in auth_logs if log['status'] == 'success'),
        'auth_failure_count': sum(1 for log in auth_logs if log['status'] == 'failure')
    })

@app.errorhandler(404)
def page_not_found(e):
    return "404: Page not found", 404

if __name__ == '__main__':
    # Start the Pico connection in a separate thread
    logger.info("Starting MFA Lock Web Server")
    
    # Launch Pico connection thread
    pico_thread = threading.Thread(target=pico_connection_thread, daemon=True)
    pico_thread.start()
    
    # Wait a moment for the Pico connection to initialize
    time.sleep(2)
    
    # Start the web server
    host = '0.0.0.0'  # Accept connections from any IP
    port = 8080
    logger.info(f"Starting web server on http://{host}:{port}")
    socketio.run(app, host=host, port=port, debug=True, use_reloader=False)