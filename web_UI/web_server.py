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
import paramiko
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit
import uuid
import tempfile
import socket

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
current_sensor_mode = "idle"  
LOG_FILE_PATH = "auth_logs.json" 
SETTINGS_FILE_PATH = "settings.json"

# Add WebSocket route to handle manual auth events from the browser
@socketio.on('auth_event')
def handle_auth_event(data):
    """Handle authentication events sent from the browser"""
    global auth_log_entries
    
    # Ensure the data has a timestamp
    if 'timestamp' not in data:
        data['timestamp'] = datetime.now().isoformat()
    
    # Ensure the data has an ID
    if 'id' not in data:
        data['id'] = str(uuid.uuid4())
    
    # Add the event to our logs
    auth_log_entries.append(data)
    save_logs(auth_log_entries)
    
    # Broadcast the event to all clients
    socketio.emit('auth_event', data)
    logger.info(f"Auth event received from client: {data['status']} - {data['message']}")

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
        'customPattern': [{"action": "tap", "duration": 0}, {"action": "hold", "duration": 1000}, {"action": "tap", "duration": 0}],
        'colorSequence': ['red', 'blue', 'green', 'yellow']  # Default color sequence
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
  

def check_and_copy_all_sensors():
    """Check if all_sensors.py exists on the Pico, and copy it if not present"""
    global pico_connected
    
    if not pico_connected:
        logger.error("Pico is not connected. Cannot check for all_sensors.py.")
        return False
    
    try:
        # Always copy the latest version of all_sensors.py to the Pico
        logger.info("Copying all_sensors.py to Pico...")
        
        # Get the path to all_sensors.py
        all_sensors_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            "pico_sensors",
            "all_sensors.py"
        )
        
        if not os.path.exists(all_sensors_path):
            logger.error(f"Cannot find source file at {all_sensors_path}")
            return False
        
        # Delete the existing all_sensors.py file on the Pico if it exists
        delete_result = subprocess.run(
            ["mpremote", "rm", ":all_sensors.py"],
            capture_output=True,
            text=True
        )
        
        if delete_result.returncode != 0 and "No such file or directory" not in delete_result.stderr:
            logger.error(f"Failed to delete existing all_sensors.py: {delete_result.stderr}")
            return False
        
        # Copy the file to the Pico
        copy_result = subprocess.run(
            ["mpremote", "cp", all_sensors_path, ":all_sensors.py"],
            capture_output=True,
            text=True
        )
        
        if copy_result.returncode != 0:
            logger.error(f"Failed to copy all_sensors.py: {copy_result.stderr}")
            return False
        
        logger.info("Successfully copied all_sensors.py to Pico")
        return True
    except Exception as e:
        logger.error(f"Error checking or copying all_sensors.py: {e}")
        return False

def run_all_sensors():
    """Send command to run the all sensors program on the Pico asynchronously."""
    if not pico_connected:
        logger.error("Pico is not connected. Cannot run all sensors program.")
        return False
    
    try:
        # Run the all sensors Python file using mpremote
        logger.info("Starting all sensors program on Pico...")
        subprocess.run(
            ["mpremote", "exec", "import all_sensors"], 
            check=True
        )
        return True
    except Exception as e:
        logger.error(f"Failed to run all sensors program: {e}")
        return False

def monitor_pico():
    """Monitor the Pico's output for events using mpremote"""
    global auth_log_entries, pico_process, pico_connected
    global current_sensor_mode  
    
    if not pico_connected:
        logger.error("Pico is not connected. Cannot monitor output.")
        return
    
    logger.info("Starting Pico monitoring thread")
    current_sensor_mode = "idle"  
    
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
                
                # Detect sensor mode changes
                if "Touch sensor activated" in line:
                    prev_mode = current_sensor_mode
                    current_sensor_mode = "touch"
                    logger.info(f"Sensor mode changed from {prev_mode} to {current_sensor_mode}")
                    socketio.emit('sensor_mode_change', {'mode': current_sensor_mode})
                
                elif "Rotary sensor activated" in line:
                    prev_mode = current_sensor_mode
                    current_sensor_mode = "rotary"
                    logger.info(f"Sensor mode changed from {prev_mode} to {current_sensor_mode}")
                    socketio.emit('sensor_mode_change', {'mode': current_sensor_mode})
                
                elif "Sensor timeout: returning to idle state" in line:
                    prev_mode = current_sensor_mode
                    current_sensor_mode = "idle"
                    logger.info(f"Sensor mode changed from {prev_mode} to {current_sensor_mode}")
                    socketio.emit('sensor_mode_change', {'mode': current_sensor_mode})
                
                # Process rotary sensor data
                elif "Angle:" in line and current_sensor_mode == "rotary":
                    try:
                        angle = int(line.split("Angle:")[1].split("degrees")[0].strip())
                        socketio.emit('rotary_update', {'angle': angle})
                    except Exception as e:
                        logger.error(f"Error parsing rotary angle: {e}")
                
                # Process authentication events
                elif "ACCESS GRANTED" in line:
                    log_entry = {
                        'id': str(uuid.uuid4()),
                        'timestamp': datetime.now().isoformat(),
                        'user': 'User',
                        'location': 'Main Entrance',
                        'status': 'success',
                        'message': 'Access granted: Touch pattern recognized correctly',
                        'details': f'Touch pattern recognized',
                        'method': 'Touch Pattern' if current_sensor_mode == 'touch' else 'Rotary Input' if current_sensor_mode == 'rotary' else 'Unknown'
                    }
                    auth_log_entries.append(log_entry)
                    save_logs(auth_log_entries)
                    socketio.emit('auth_event', log_entry)
                
                # Detect failed attempts
                elif "timeout" in line or "Incorrect input" in line:
                    log_entry = {
                        'id': str(uuid.uuid4()),
                        'timestamp': datetime.now().isoformat(),
                        'user': 'Unknown',
                        'location': 'Main Entrance',
                        'status': 'failure',
                        'message': 'Access denied: Incorrect touch pattern',
                        'details': f'Incorrect touch pattern: {line}',
                        'method': 'Touch Pattern' if current_sensor_mode == 'touch' else 'Rotary Input' if current_sensor_mode == 'rotary' else 'Unknown'
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
            logger.info("Pico connected. Setting up all sensors...")
            if check_and_copy_all_sensors():
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
                    
                    # Create a launcher script that runs all_sensors in the background
                    pattern_json = json.dumps(settings['customPattern'])
                    launcher_script = (
                        f'import _thread\n'
                        f'import json\n'
                        f'pattern_arg = \'{pattern_json}\'\n'
                        f'def run_all_sensors(arg):\n'
                        f'    all_sensors = __import__("all_sensors", None, None, [], 0)\n'
                        f'    all_sensors.main()\n'
                        f'try: _thread.start_new_thread(run_all_sensors, (pattern_arg,))\n'
                        f'except Exception as e: print("Error starting run_all_sensors", e)'
                    )
                    
                    logger.info("Creating background job to run all_sensors")
                    subprocess.run(["mpremote", "exec", launcher_script], check=True, timeout=2)
                    
                    
                    logger.info("Starting to monitor Pico output...")
                    monitor_pico()
                except Exception as e:
                    logger.error(f"Failed to start all sensors program: {e}")
                    pico_connected = False
                    socketio.emit('status_update', {
                        'pico_connected': False,
                        'auth_success_count': sum(1 for log in auth_log_entries if log['status'] == 'success'),
                        'auth_failure_count': sum(1 for log in auth_log_entries if log['status'] == 'failure')
                    })
            else:
                logger.error("Failed to check or copy all_sensors.py to Pico")
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
            
            # Track if we need to restart all_sensors
            restart_all_sensors = False
            pattern_saved = False
            color_sequence_saved = False
            
            # Save and update the custom pattern if it was changed
            if 'customPattern' in updated_settings:
                custom_pattern = updated_settings['customPattern']
                pattern_saved = save_pattern_to_json(custom_pattern)
                restart_all_sensors = True
            
            # Save and update the color sequence if it was changed
            if 'colorSequence' in updated_settings:
                color_sequence = updated_settings['colorSequence']
                color_sequence_saved = save_color_sequence_to_json(color_sequence)
                restart_all_sensors = True
            
            # If Pico is connected and we need to restart, do it once for all changes
            pattern_updated = False
            if restart_all_sensors and pico_connected:
                try:
                    pattern_updated = update_sensor_pattern()
                except Exception as e:
                    logger.error(f"Error updating sensors on device: {e}")
            
            # Return detailed status
            return jsonify({
                'status': 'success',
                'pattern_saved': pattern_saved,
                'color_sequence_saved': color_sequence_saved,
                'pattern_updated_on_device': pattern_updated if pico_connected else None,
                'pico_connected': pico_connected
            })
            
        except Exception as e:
            logger.error(f"Error handling settings: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
        
#blacklist images upload 
@app.route('/blacklist', methods=['POST'])
def upload_file():
    if 'picture' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file part'}), 400
    file = request.files['picture']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No selected file'}), 400
    if file:
        # Save the uploaded image locally
        upload_folder = os.path.join('camera', 'faces')
        os.makedirs(upload_folder, exist_ok=True)  # Ensure the upload folder exists
        image_path = os.path.join(upload_folder, file.filename)
        file.save(image_path)

    filename_log = os.path.join('camera','faces', 'blacklist.txt')
    with open(filename_log, 'a') as f:
        f.write(file.filename + '\n')

    logger.info(f"Image saved locally at: {image_path}")

# Route to handle approved  image uploads
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'picture' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file part'}), 400
    file = request.files['picture']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No selected file'}), 400
    if file:
        # Save the uploaded image locally
        upload_folder = os.path.join('camera', 'faces')
        os.makedirs(upload_folder, exist_ok=True)  # Ensure the upload folder exists
        image_path = os.path.join(upload_folder, file.filename)
        file.save(image_path)

    filename_log = os.path.join('camera','faces', 'imagelist.txt')
    with open(filename_log, 'a') as f:
        f.write(file.filename + '\n')

    logger.info(f"Image saved locally at: {image_path}")
    
    # NOTE: This code is for transferring the image to a Raspberry Pi. We no longer needed this because we decided to run the web server on the Raspberry Pi.  
    # try:
    #     # Define remote path on the Raspberry Pi
    #     raspberry_pi_ip = '172.20.231.165'
    #     username = 'yunus'
    #     password = 'yunus'
    #     remote_path = f'/home/yunus/fac-rec-env/{file.filename}'

    #     remote_list_path = f'/home/yunus/fac-rec-env/imagelist.txt'

        
    #     # Transfer the image directly to the Raspberry Pi
    #     transfer_status, message = transfer_file_to_pi(image_path, remote_path, raspberry_pi_ip, username, password)
    #     list_transfer_status, list_message = transfer_file_to_pi(filename_log, remote_list_path, raspberry_pi_ip, username, password)

        
    #     if transfer_status and list_transfer_status:
    #         logger.info("Image transfer successful")
    #         return jsonify({
    #             'status': 'success', 
    #             'message': 'Image and image list uploaded and transferred successfully',
    #             'path': image_path
    #         })
    #     else:
    #         logger.error(f"Image transfer failed: {message}, {list_message}")
    #         return jsonify({
    #             'status': 'partial_success', 
    #             'message': f'Image uploaded locally but transfer failed: {message}, {list_message}',
    #             'path': image_path
    #         }), 207
            

    # except Exception as e:
    #     logger.error(f"Error during image upload process: {e}")
    #     return jsonify({'status': 'error', 'message': f'Failed to process image: {str(e)}'}), 500


# Function to transfer a file to the Raspberry Pi via SSH/SFTP
def transfer_file_to_pi(local_path, remote_path, pi_ip, username, password):
    """
    Transfer a file to the Raspberry Pi and verify the transfer
    
    Returns:
        tuple: (success_status, message)
    """
    ssh = None
    sftp = None
    
    try: 
        # Log connection attempt
        logger.info(f"Connecting to Raspberry Pi at {pi_ip}...")
        
        # Set up SSH client
        ssh = paramiko.SSHClient()  
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Connect with timeout
        ssh.connect(
            pi_ip, 
            username=username, 
            password=password,
            timeout=10  # 10 second timeout
        )
        logger.info("SSH connection established")
         
        # Open SFTP session
        sftp = ssh.open_sftp()
        
        # Ensure remote directory exists
        remote_dir = os.path.dirname(remote_path)
        try:
            # Try to create the directory (will fail if it exists, which is fine)
            stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {remote_dir}")
            exit_status = stdout.channel.recv_exit_status()
            if exit_status != 0:
                logger.warning(f"mkdir command returned non-zero exit status: {exit_status}")
        except Exception as e:
            logger.warning(f"Error ensuring remote directory exists: {e}")
        
        # Get local file size for verification
        local_size = os.path.getsize(local_path)
        logger.info(f"Local image size: {local_size} bytes")
        
        # Transfer the file
        logger.info(f"Transferring image {local_path} to {remote_path}...")
        sftp.put(local_path, remote_path)
        
        # Verify the transfer by checking file existence and size
        try:
            # Check if file exists and get its size
            remote_stat = sftp.stat(remote_path)
            remote_size = remote_stat.st_size
            logger.info(f"Remote image size: {remote_size} bytes")
            
            if remote_size == local_size:
                return True, "Image transferred and verified successfully"
            else:
                return False, f"Size mismatch: Local {local_size} bytes, Remote {remote_size} bytes"
                
        except FileNotFoundError:
            return False, "Image not found on remote system after transfer"
            
    except paramiko.AuthenticationException:
        return False, "Authentication failed. Check username and password."
    except paramiko.SSHException as e:
        return False, f"SSH connection error: {str(e)}"
    except socket.timeout:
        return False, "Connection timed out. Check IP address and network."
    except Exception as e:
        return False, f"Error: {str(e)}"
    finally:
        # Clean up
        if sftp:
            sftp.close()
        if ssh:
            ssh.close()


def update_sensor_pattern():
    """Update the sensor settings on the Pico and restart the sensors"""
    global pico_connected
    
    # Ensure we have the pattern and color sequence files
    pattern_file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "touch",
        "custom_pattern.json"
    )
    
    color_sequence_file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "rotary",
        "color_sequence.json"
    )
    
    if not pico_connected:
        logger.error("Pico is not connected. Cannot update sensors.")
        return False
    
    try:
        # Perform a complete reboot of the Pico
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
        
        # Hard reset via the tool
        logger.info("Hard resetting Pico...")
        subprocess.run(
            ["mpremote", "reset"],
            capture_output=True,
            text=True
        )
        
        # Wait for Pico to reconnect
        logger.info("Waiting for Pico to reconnect after reset...")
        reconnect_attempts = 0
        max_attempts = 15
        reconnected = False
        
        while reconnect_attempts < max_attempts and not reconnected:
            time.sleep(2)
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
                time.sleep(4)
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
            
        # Clear out any boot.py or main.py that might be auto-starting
        logger.info("Ensuring no auto-start scripts are present...")
        try:
            subprocess.run(["mpremote", "rm", ":boot.py"], capture_output=True, text=True)
        except:
            pass
        try:
            subprocess.run(["mpremote", "rm", ":main.py"], capture_output=True, text=True)
        except:
            pass
        
        # Get the path to the all_sensors.py file
        all_sensors_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "pico_sensors",
            "all_sensors.py"
        )
        
        # Copy all_sensors.py to the Pico
        if os.path.exists(all_sensors_path):
            logger.info("Copying fresh all_sensors.py to Pico...")
            try:
                # Delete existing file first
                subprocess.run(["mpremote", "rm", ":all_sensors.py"], capture_output=True, text=True)
                time.sleep(0.5)
                
                # Copy the file
                copy_result = subprocess.run(
                    ["mpremote", "cp", all_sensors_path, ":all_sensors.py"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                logger.info("Successfully copied all_sensors.py to Pico")
            except Exception as e:
                logger.error(f"Failed to copy all_sensors.py: {e}")
                return False
        else:
            logger.error(f"Cannot find source file at {all_sensors_path}")
            return False
        
        # Copy the custom pattern file if it exists
        if os.path.exists(pattern_file_path):
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
        
        # Copy the color sequence file if it exists
        if os.path.exists(color_sequence_file_path):
            logger.info("Copying color_sequence.json to Pico...")
            try:
                copy_result = subprocess.run(
                    ["mpremote", "cp", color_sequence_file_path, ":color_sequence.json"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                logger.info("Successfully copied color_sequence.json to Pico")
            except Exception as e:
                logger.error(f"Failed to copy color_sequence.json: {e}")
        
        # Wait to ensure files are fully written
        time.sleep(1)
        
        # Start all_sensors with a clean environment
        logger.info("Starting all_sensors with new settings...")
        launcher_script = (
            f'import gc\n'
            f'gc.collect()\n'
            f'import sys\n'
            f'# Clear any modules that might be loaded\n'
            f'for name in list(sys.modules):\n'
            f'    if name != "sys" and name != "gc":\n'
            f'        del sys.modules[name]\n'
            f'import _thread\n'
            f'def run_all_sensors():\n'
            f'    # Import with fresh state\n'
            f'    all_sensors = __import__("all_sensors")\n'
            f'    all_sensors.main()\n'
            f'try:\n'
            f'    _thread.start_new_thread(run_all_sensors, ())\n'
            f'    print("All sensors started with fresh state")\n'
            f'except Exception as e:\n'
            f'    print(f"Error starting all_sensors: {{e}}")\n'
        )
        
        # Execute the launcher script
        try:
            result = subprocess.run(
                ["mpremote", "exec", launcher_script], 
                capture_output=True,
                text=True,
                timeout=3
            )
            if "All sensors started with fresh state" in result.stdout:
                logger.info("Successfully started all_sensors with new settings")
                return True
            else:
                logger.warning(f"Unexpected output when starting all_sensors: {result.stdout}")
                return False
        except Exception as e:
            logger.error(f"Error executing launcher script: {e}")
            return False
        
    except Exception as e:
        logger.error(f"Error updating sensor settings: {e}")
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

def save_color_sequence_to_json(color_sequence):
    """Save the color sequence to settings.json"""
    try:
        # Update the color sequence in settings
        settings['colorSequence'] = color_sequence
        save_settings(settings)
        
        # Create a separate color sequence JSON file for the Pico
        color_sequence_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "rotary"
        )
        color_sequence_file_path = os.path.join(color_sequence_dir, "color_sequence.json")
        
        # Ensure the directory exists
        os.makedirs(color_sequence_dir, exist_ok=True)
        
        # Format the color sequence for saving
        sequence_data = {
            "sequence": color_sequence,
            "created_at": datetime.now().isoformat()
        }
        
        # Write the color sequence to the file
        with open(color_sequence_file_path, 'w') as f:
            json.dump(sequence_data, f, indent=4)
        
        logger.info(f"Color sequence saved to {color_sequence_file_path}")
        return color_sequence_file_path
    except Exception as e:
        logger.error(f"Error saving color sequence to JSON: {e}")
        return None

def update_audio():
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

@app.route('/api/sensor_mode')
def get_sensor_mode():
    """API endpoint to get the current sensor mode"""
    global current_sensor_mode
    return jsonify({'mode': current_sensor_mode})

if __name__ == '__main__':
    # Start the Pico connection in a separate thread
    logger.info("Starting MFA Lock Web Server")
    
    # Launch Pico connection thread
    pico_thread = threading.Thread(target=pico_connection_thread, daemon=True)
    pico_thread.start()
    
    # Wait a moment for the Pico connection to initialize
    time.sleep(3)
    
    # Start the web server
    host = '0.0.0.0'  # Accept connections from any IP
    port = 8080
    logger.info(f"Starting web server on http://{host}:{port}")
    socketio.run(app, host=host, port=port, debug=True, use_reloader=False)
