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
import glob
import threading
import logging
import subprocess
import pickle
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit
import uuid
import tempfile

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("MFALock")

# Flask app setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'mfalock-secret-key!'
socketio = SocketIO(app)

# Global variables
pico_connected = False
pico_process = None
LOG_FILE_PATH = "auth_logs.json" 
SETTINGS_FILE_PATH = "settings.json"

def load_logs():
    """Load logs from the log file."""
    if os.path.exists(LOG_FILE_PATH):
        with open(LOG_FILE_PATH, 'r') as file:
            return json.load(file)
    return []

def save_logs(logs):
    """Save logs to the log file."""
    with open(LOG_FILE_PATH, 'w') as file:
        json.dump(logs, file, indent=4)

def load_settings():
    """Load settings from the settings file."""
    if os.path.exists(SETTINGS_FILE_PATH):
        with open(SETTINGS_FILE_PATH, 'r') as file:
            return json.load(file)
    return {
        'securityLevel': 'high',
        'notificationEmail': '',
        'notifySuccess': False,
        'notifyFailure': True,
        'customPattern': [{"action": "tap", "duration": 0}, {"action": "hold", "duration": 1000}, {"action": "tap", "duration": 0}]
    }

def save_settings(settings):
    """Save settings to the settings file."""
    with open(SETTINGS_FILE_PATH, 'w') as file:
        json.dump(settings, file, indent=4)

auth_log_entries = load_logs()
settings = load_settings()

def setup_pico_connection():
    """Establish connection to the Pico device using mpremote"""
    global pico_connected
    pico_id = "2e8a:0005"  # Pico USB device ID
    
    # Check if Pico is available
    result = subprocess.run(
        ["mpremote", "connect", "list"], 
        capture_output=True, 
        text=True
    )

    if pico_id not in result.stdout:
        logger.error("Could not find Pico device. Please check connection.")
        pico_connected = False
        return False
    
    logger.info("Pico device detected")
    pico_connected = True
    return True
  
def check_and_copy_touch_lock():
    """Check if touch_lock.py exists on the Pico, and copy it if not present"""
    global pico_connected
    
    if not pico_connected:
        logger.error("Pico is not connected. Cannot check for touch_lock.py.")
        return False
    
    try:
        # Always copy the latest version of touch_lock.py to the Pico
        logger.info("Copying touch_lock.py to Pico...")
        
        # Get the path to touch_lock.py in the touch directory
        touch_lock_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "touch",
            "touch_lock.py"
        )
        
        if not os.path.exists(touch_lock_path):
            logger.error(f"Cannot find source file at {touch_lock_path}")
            return False
        
        # Delete the existing touch_lock.py file on the Pico if it exists
        delete_result = subprocess.run(
            ["mpremote", "rm", ":touch_lock.py"],
            capture_output=True,
            text=True
        )
        
        if delete_result.returncode != 0 and "No such file or directory" not in delete_result.stderr:
            logger.error(f"Failed to delete existing touch_lock.py: {delete_result.stderr}")
            return False
        
        # Copy the file to the Pico
        copy_result = subprocess.run(
            ["mpremote", "cp", touch_lock_path, ":touch_lock.py"],
            capture_output=True,
            text=True
        )
        
        if copy_result.returncode != 0:
            logger.error(f"Failed to copy touch_lock.py: {copy_result.stderr}")
            return False
        
        logger.info("Successfully copied touch_lock.py to Pico")
        return True
    except Exception as e:
        logger.error(f"Error checking or copying touch_lock.py: {e}")
        return False

def run_touch_lock():
    """Send command to run the touch lock program on the Pico asynchronously."""
    if not pico_connected:
        logger.error("Pico is not connected. Cannot run touch lock program.")
        return False
    
    try:
        # Run the touch lock Python file using mpremote
        logger.info("Starting touch lock program on Pico...")
        subprocess.run(
            ["mpremote", "exec", "import touch_lock"], 
            check=True
        )
        return True
    except Exception as e:
        logger.error(f"Failed to run touch lock program: {e}")
        return False

def monitor_pico():
    """Monitor the Pico's output for events using mpremote"""
    global auth_log_entries, pico_process, pico_connected
    
    if not pico_connected:
        logger.error("Pico is not connected. Cannot monitor output.")
        return
    
    logger.info("Starting Pico monitoring thread")
    
    try:
        # Start mpremote in repl mode and capture its output
        pico_process = subprocess.Popen(
            ["mpremote", "repl", "--escape-non-printable"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # Emit status update to clients
        socketio.emit('status_update', {
            'pico_connected': pico_connected,
            'auth_success_count': sum(1 for log in auth_log_entries if log['status'] == 'success'),
            'auth_failure_count': sum(1 for log in auth_log_entries if log['status'] == 'failure')
        })
        
        # Read output line by line
        while pico_connected and pico_process.poll() is None:
            line = pico_process.stdout.readline().strip()
            if line:
                logger.info(f"Pico: {line}")
                
                # Process authentication events
                if "ACCESS GRANTED" in line:
                    log_entry = {
                        'id': str(uuid.uuid4()),
                        'timestamp': datetime.now().isoformat(),
                        'user': 'User',
                        'location': 'Main Entrance',
                        'status': 'success',
                        'details': 'Pattern recognized correctly'
                    }
                    auth_log_entries.append(log_entry)
                    save_logs(auth_log_entries)
                    socketio.emit('auth_event', log_entry)
                
                # Detect failed attempts
                elif "timeout" in line:
                    log_entry = {
                        'id': str(uuid.uuid4()),
                        'timestamp': datetime.now().isoformat(),
                        'user': 'Unknown',
                        'location': 'Main Entrance',
                        'status': 'failure',
                        'details': f'Incorrect pattern: {line}'
                    }
                    auth_log_entries.append(log_entry)
                    save_logs(auth_log_entries)
                    socketio.emit('auth_event', log_entry)
            
            time.sleep(0.1)
    except Exception as e:
        logger.error(f"Error in Pico monitoring: {e}")
        pico_connected = False
        
        # Emit disconnection status to clients
        socketio.emit('status_update', {
            'pico_connected': pico_connected,
            'auth_success_count': sum(1 for log in auth_log_entries if log['status'] == 'success'),
            'auth_failure_count': sum(1 for log in auth_log_entries if log['status'] == 'failure')
        })
    finally:
        if pico_process and pico_process.poll() is None:
            pico_process.terminate()
            pico_process = None

def pico_connection_thread():
    """Thread to handle Pico connection and monitoring"""
    global pico_connected
    reconnection_interval = 1  # seconds between reconnection attempts
    
    while True:
        # Check connection status - whether initially connected or reconnected
        was_connected = pico_connected
        
        # Check if Pico is connected
        current_connected = setup_pico_connection()
        
        # If connection status changed, notify clients
        if current_connected != was_connected:
            pico_connected = current_connected
            logger.info(f"Pico connection status changed: {'Connected' if pico_connected else 'Disconnected'}")
            socketio.emit('status_update', {
                'pico_connected': pico_connected,
                'auth_success_count': sum(1 for log in auth_log_entries if log['status'] == 'success'),
                'auth_failure_count': sum(1 for log in auth_log_entries if log['status'] == 'failure')
            })
        
        # If connected, set up and monitor the Pico
        if pico_connected:
            logger.info("Pico connected. Setting up touch lock...")
            if check_and_copy_touch_lock():
                try:
                    # Check if a custom pattern file exists and copy it to the Pico
                    pattern_file_path = os.path.join(
                        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "touch",
                        "custom_pattern.json"
                    )
                    
                    if os.path.exists(pattern_file_path):
                        logger.info("Found existing custom pattern file, copying to Pico...")
                        copy_result = subprocess.run(
                            ["mpremote", "cp", pattern_file_path, ":custom_pattern.json"],
                            capture_output=True,
                            text=True
                        )
                        
                        if copy_result.returncode == 0:
                            logger.info("Successfully copied custom pattern file to Pico")
                        else:
                            logger.error(f"Failed to copy custom pattern file: {copy_result.stderr}")
                    else:
                        logger.info("No custom pattern file found, Pico will use default pattern")
                    
                    # Create a launcher script that runs touch_lock in the background
                    pattern_json = json.dumps(settings['customPattern'])
                    launcher_script = (
                        f'import _thread\n'
                        f'import json\n'
                        f'pattern_arg = \'{pattern_json}\'\n'
                        f'def run_touch_lock(arg):\n'
                        f'    __import__("touch_lock", None, None, [], 0)\n'
                        f'try: _thread.start_new_thread(run_touch_lock, (pattern_arg,))\n'
                        f'except Exception as e: print("Error starting touch_lock:", e)'
                    )
                    
                    logger.info("Creating background job to run touch_lock")
                    subprocess.run(["mpremote", "exec", launcher_script], check=True, timeout=2)
                    
                    logger.info("Starting to monitor Pico output...")
                    monitor_pico()
                except Exception as e:
                    logger.error(f"Failed to start touch lock program: {e}")
                    pico_connected = False
                    socketio.emit('status_update', {
                        'pico_connected': False,
                        'auth_success_count': sum(1 for log in auth_log_entries if log['status'] == 'success'),
                        'auth_failure_count': sum(1 for log in auth_log_entries if log['status'] == 'failure')
                    })
            else:
                logger.error("Failed to check or copy touch_lock.py to Pico")
                pico_connected = False
                socketio.emit('status_update', {
                    'pico_connected': False,
                    'auth_success_count': sum(1 for log in auth_log_entries if log['status'] == 'success'),
                    'auth_failure_count': sum(1 for log in auth_log_entries if log['status'] == 'failure')
                })
        else:
            logger.warning(f"No Pico detected. Will retry in {reconnection_interval} seconds...")
        
        # Sleep before next connection check
        time.sleep(reconnection_interval)

# Route handlers for different pages
@app.route('/')
def index():
    """Redirect to the dashboard"""
    return render_template('dashboard.html')

@app.route('/dashboard')
def dashboard():
    """Serve the dashboard page"""
    return render_template('dashboard.html')

@app.route('/auth_logs')
def auth_logs():
    """Serve the logs page"""
    return render_template('auth_logs.html')

@app.route('/how_it_works')
def how_it_works():
    """Serve the how it works page"""
    return render_template('how_it_works.html')

@app.route('/settings')
def settings_page():  # Renamed from "settings" to "settings_page"
    """Serve the settings page"""
    return render_template('settings.html')

@app.route('/users')
def users():
    """Serve the users page"""
    return render_template('users.html')

@app.route('/api/logs')
def get_logs():
    """API endpoint to get authentication logs"""
    return jsonify(auth_log_entries)

@app.route('/api/logs/<string:log_id>', methods=['DELETE'])
def delete_log(log_id):
    """API endpoint to delete a specific log by its ID"""
    global auth_log_entries
    # Find the log with the given ID
    log_to_delete = next((log for log in auth_log_entries if log['id'] == log_id), None)
    if log_to_delete:
        # Remove the log from the list
        auth_log_entries = [log for log in auth_log_entries if log['id'] != log_id]
        save_logs(auth_log_entries)
        logger.info(f"Deleted log with ID {log_id}")
        return jsonify({'status': 'success', 'message': f'Log with ID {log_id} deleted'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'Log not found'}), 404

@app.route('/api/settings', methods=['GET', 'POST'])
def handle_settings():
    """API endpoint to get or update settings"""
    global settings
    
    if request.method == 'GET':
        return jsonify(settings)
    elif request.method == 'POST':
        try:
            # Process settings update
            updated_settings = request.json
            if updated_settings is None:
                logger.error("No JSON data received in settings update")
                return jsonify({'status': 'error', 'message': 'No JSON data received'}), 400
            
            # Make a copy of current settings and update it
            current_settings = settings.copy() if isinstance(settings, dict) else {}
            current_settings.update(updated_settings)
            settings = current_settings
            save_settings(settings)
            
            # Save and update the custom pattern if it was changed
            if 'customPattern' in updated_settings:
                custom_pattern = updated_settings['customPattern']
                pattern_saved = save_pattern_to_json(custom_pattern)
                
                # If Pico is connected, try to update the pattern on the device
                pattern_updated = False
                if pico_connected:
                    try:
                        pattern_updated = update_touch_lock_pattern(custom_pattern)
                    except Exception as e:
                        logger.error(f"Error updating pattern on device: {e}")
                
                # Return detailed status
                return jsonify({
                    'status': 'success',
                    'pattern_saved': pattern_saved,
                    'pattern_updated_on_device': pattern_updated if pico_connected else None,
                    'pico_connected': pico_connected
                })
            
            logger.info(f"Updated settings: {settings}")
            return jsonify({'status': 'success'})
        except Exception as e:
            logger.error(f"Error handling settings: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
        

# Route to handle image uploads
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'picture' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file part'}), 400
    file = request.files['picture']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No selected file'}), 400
    if file:
        # Save the uploaded image
        upload_folder = os.path.join('camera', 'faces')
        os.makedirs(upload_folder, exist_ok=True)  # Ensure the upload folder exists
        image_path = os.path.join(upload_folder, file.filename)
        print(image_path)
        file.save(image_path)

        # Save the file path to a pickle file
        pickle_file = os.path.join(upload_folder, 'uploaded_images.pkl')
        try:
            if os.path.exists(pickle_file):
                with open(pickle_file, 'rb') as f:
                    uploaded_images = pickle.load(f)
            else:
                uploaded_images = []

            uploaded_images.append(image_path)

            with open(pickle_file, 'wb') as f:
                pickle.dump(uploaded_images, f)

            return jsonify({'status': 'success'})
            # return jsonify({'status': 'success', 'message': 'File uploaded successfully', 'path': image_path}), 200
        except Exception as e:
            logger.error(f"Error saving to pickle file: {e}")
            return jsonify({'status': 'error', 'message': 'Failed to save file path'}), 500
        
# Function to transfer a file to the Pico via mpremote
# def transfer_file_to_pi(local_path, remote_path, pi_ip, username, apssword):
#     try: 
#         ssh = paramiko.SSHClient()  


def update_touch_lock_pattern(custom_pattern):
    """Update the touch_lock.py file with the new custom pattern and restart it"""
    global pico_connected
    
    # Save the pattern to a JSON file first
    pattern_file_path = save_pattern_to_json(custom_pattern)
    
    if not pico_connected:
        logger.error("Pico is not connected. Cannot update touch lock pattern.")
        return False
    
    try:
        # Get the path to the touch_lock.py file
        touch_lock_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "touch",
            "touch_lock.py"
        )
        
        if not os.path.exists(touch_lock_path):
            logger.error(f"Cannot find source file at {touch_lock_path}")
            return False
        
        # Perform a complete reboot of the Pico - this is more reliable than soft reset
        logger.info("Performing complete reboot of the Pico...")
        
        # First attempt a clean shutdown of any running processes
        try:
            subprocess.run(
                ["mpremote", "exec", "import machine; machine.reset()"],
                capture_output=True,
                text=True,
                timeout=2
            )
        except Exception as e:
            logger.warning(f"Machine reset attempt: {e}")
        
        # Wait for a moment
        time.sleep(2)
        
        # Now do a hard reset via the tool
        logger.info("Hard resetting Pico...")
        subprocess.run(
            ["mpremote", "reset"],
            capture_output=True,
            text=True
        )
        
        # Wait for Pico to reconnect with a longer timeout
        logger.info("Waiting for Pico to reconnect after reset...")
        reconnect_attempts = 0
        max_attempts = 15  # Increased from 10
        reconnected = False
        
        while reconnect_attempts < max_attempts and not reconnected:
            time.sleep(2)  # Increased wait time between attempts
            reconnect_attempts += 1
            
            logger.info(f"Reconnection attempt {reconnect_attempts}/{max_attempts}...")
            
            # Check if Pico is connected
            result = subprocess.run(
                ["mpremote", "connect", "list"], 
                capture_output=True, 
                text=True
            )
            
            if "2e8a:0005" in result.stdout:
                logger.info("Pico reconnected successfully")
                reconnected = True
                # Extra stabilization time
                logger.info("Allowing Pico to fully stabilize...")
                time.sleep(4)  # Longer stabilization time
            else:
                logger.warning("Pico not yet reconnected, waiting...")
        
        if not reconnected:
            logger.error("Failed to reconnect to Pico after reset")
            return False
        
        # Verify connection is still active
        verify_result = subprocess.run(
            ["mpremote", "connect", "list"], 
            capture_output=True, 
            text=True
        )
        
        if "2e8a:0005" not in verify_result.stdout:
            logger.error("Pico connection unstable after reconnection")
            return False
            
        # Clear out any boot.py or main.py that might be auto-starting touch_lock
        logger.info("Ensuring no auto-start scripts are present...")
        try:
            subprocess.run(["mpremote", "rm", ":boot.py"], capture_output=True, text=True)
        except:
            pass
        try:
            subprocess.run(["mpremote", "rm", ":main.py"], capture_output=True, text=True)
        except:
            pass
        
        # Clean copy of touch_lock.py to the Pico
        logger.info("Copying fresh touch_lock.py to Pico...")
        try:
            # Delete existing file first
            subprocess.run(["mpremote", "rm", ":touch_lock.py"], capture_output=True, text=True)
            time.sleep(0.5)
            
            # Copy the file
            copy_result = subprocess.run(
                ["mpremote", "cp", touch_lock_path, ":touch_lock.py"],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info("Successfully copied touch_lock.py to Pico")
        except Exception as e:
            logger.error(f"Failed to copy touch_lock.py: {e}")
            return False
        
        # Copy the custom pattern file
        logger.info("Copying custom_pattern.json to Pico...")
        try:
            copy_result = subprocess.run(
                ["mpremote", "cp", pattern_file_path, ":custom_pattern.json"],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info("Successfully copied custom_pattern.json to Pico")
        except Exception as e:
            logger.error(f"Failed to copy custom_pattern.json: {e}")
            return False
        
        # Wait to ensure files are fully written
        time.sleep(1)
        
        # Start touch_lock with a clean environment
        logger.info("Starting touch_lock with new pattern...")
        launcher_script = (
            f'import gc\n'
            f'gc.collect()\n'
            f'import sys\n'
            f'# Clear any modules that might be loaded\n'
            f'for name in list(sys.modules):\n'
            f'    if name != "sys" and name != "gc":\n'
            f'        del sys.modules[name]\n'
            f'import _thread\n'
            f'def run_touch_lock():\n'
            f'    # Import with fresh state\n'
            f'    __import__("touch_lock")\n'
            f'try:\n'
            f'    _thread.start_new_thread(run_touch_lock, ())\n'
            f'    print("Touch lock started with fresh state")\n'
            f'except Exception as e:\n'
            f'    print(f"Error starting touch_lock: {{e}}")\n'
        )
        
        # Execute the launcher script
        try:
            result = subprocess.run(
                ["mpremote", "exec", launcher_script], 
                capture_output=True,
                text=True,
                timeout=3
            )
            if "Touch lock started with fresh state" in result.stdout:
                logger.info("Successfully started touch_lock with new pattern")
            else:
                logger.warning(f"Unexpected output when starting touch_lock: {result.stdout}")
        except Exception as e:
            logger.error(f"Error executing launcher script: {e}")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Error updating touch_lock pattern: {e}")
        return False

def save_pattern_to_json(custom_pattern):
    """Save the custom pattern to a JSON file"""
    try:
        # Path to save the pattern file
        pattern_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "touch"
        )
        pattern_file_path = os.path.join(pattern_dir, "custom_pattern.json")
        
        # Ensure the directory exists
        os.makedirs(pattern_dir, exist_ok=True)
        
        # Format the pattern for saving - only include the user's custom pattern
        pattern_data = {
            "pattern": custom_pattern,
            "created_at": datetime.now().isoformat()
            # No default_pattern key
        }
        
        # Write the pattern to the file (completely overwrite)
        with open(pattern_file_path, 'w') as f:
            json.dump(pattern_data, f, indent=4)
        
        logger.info(f"Custom pattern saved to {pattern_file_path}")
        return pattern_file_path
    except Exception as e:
        logger.error(f"Error saving pattern to JSON: {e}")
        return None

@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    logger.info("Client connected to WebSocket")
    emit('status_update', {
        'pico_connected': pico_connected,
        'auth_success_count': sum(1 for log in auth_log_entries if log['status'] == 'success'),
        'auth_failure_count': sum(1 for log in auth_log_entries if log['status'] == 'failure')
    })

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

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
