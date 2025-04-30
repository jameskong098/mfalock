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
import threading
import logging
import subprocess
import paramiko
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_file
from flask_socketio import SocketIO, emit
import uuid
import socket
from dotenv import load_dotenv 

# Load environment variables from .env file in the root directory
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path, override=True)
    print(f"Loaded environment variables from: {dotenv_path}")
else:
    print(f".env file not found at: {dotenv_path}")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %I:%M:%S %p', 
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("MFALock")

# Flask app setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'mfalock-secret-key!'
socketio = SocketIO(app)

LISTENER_PI_IP = os.getenv("LISTENER_PI_IP")

# Check if the environment variable was loaded
if LISTENER_PI_IP is None:
    logger.error("Error: LISTENER_PI_IP environment variable not set.")
    logger.error("Please define LISTENER_PI_IP in your .env file or environment variables.")
    sys.exit(1) 

LISTENER_PI_PORT = int(os.getenv("LISTENER_PI_PORT", 8080)) 

# Global variables
pico_connected = False
pico_process = None
current_sensor_mode = "idle"  
LOG_FILE_PATH = "auth_logs.json" 
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE_PATH = os.path.join(BASE_DIR, "settings.json")

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

    # Check if it's a successful rotary authentication and send to listener
    if data.get('method') == 'Rotary Lock' and data.get('status') == 'success':
        logger.info("Detected successful rotary authentication, sending to listener.")
        send_to_listener("ROTARY - SUCCESS")

def load_logs():
    """Load logs from the log file."""
    if os.path.exists(LOG_FILE_PATH):
        try:
            with open(LOG_FILE_PATH, 'r') as file:
                return json.load(file)
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON from {LOG_FILE_PATH}")
            return []
        except Exception as e:
            logger.error(f"Error loading logs: {e}")
            return []
    return []

def save_logs(logs):
    """Save logs to the log file."""
    try:
        with open(LOG_FILE_PATH, 'w') as file:
            json.dump(logs, file, indent=4)
    except Exception as e:
        logger.error(f"Error saving logs: {e}")

def load_settings():
    """Load settings from the settings file."""
    if os.path.exists(SETTINGS_FILE_PATH):
        try:
            with open(SETTINGS_FILE_PATH, 'r') as file:
                return json.load(file)
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON from {SETTINGS_FILE_PATH}")
        except Exception as e:
            logger.error(f"Error loading settings: {e}")

    # Default settings if file doesn't exist or is invalid
    return {
        'customPattern': [{"action": "tap", "duration": 0}, {"action": "hold", "duration": 1000}, {"action": "tap", "duration": 0}],
        'colorSequence': ['red', 'blue', 'green', 'yellow']
    }

def save_settings(settings):
    """Save settings to the settings file."""
    try:
        with open(SETTINGS_FILE_PATH, 'w') as file:
            json.dump(settings, file, indent=4)
        logger.info(f"Settings saved to {SETTINGS_FILE_PATH}")
    except Exception as e:
        logger.error(f"Error saving settings: {e}")

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

                # --- Touch event emission ---
                if "Touch started" in line:
                    socketio.emit('touch_event', {'action': 'hold_start'})
                elif "Touch ended" in line:
                    # You can parse the duration if you want, e.g. "Touch ended: 1200ms"
                    try:
                        duration = int(line.split("Touch ended:")[1].replace("ms", "").strip())
                        # If it's a quick tap, treat as tap; if longer, treat as hold_end
                        if duration < 500:
                            socketio.emit('touch_event', {'action': 'tap'})
                        else:
                            socketio.emit('touch_event', {'action': 'hold_end', 'duration': duration})
                    except Exception:
                        socketio.emit('touch_event', {'action': 'hold_end'})
                elif "Step 1: Tap detected" in line or "Step 3: Tap detected" in line:
                    socketio.emit('touch_event', {'action': 'tap'})
                elif "Step 2: Hold detected" in line:
                    socketio.emit('touch_event', {'action': 'hold_end'})
                elif "TOUCH - SUCCESS" in line:
                    socketio.emit('touch_event', {'action': 'success'})
                elif "timeout" in line or "Incorrect input" in line:
                    socketio.emit('touch_event', {'action': 'failure'})
                elif "Sensor timeout: returning to idle state" in line:
                    socketio.emit('touch_event', {'action': 'reset'})
                # --- End touch event emission ---

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
                elif "TOUCH - SUCCESS" in line:
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
                    send_to_listener("TOUCH - SUCCESS") 
                
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
                    send_to_listener("FAILURE") 
            
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
    global settings, pico_connected

    if request.method == 'GET':
        return jsonify(settings)
    elif request.method == 'POST':
        try:
            updated_settings_data = request.json
            if updated_settings_data is None:
                logger.error("No JSON data received in settings update")
                return jsonify({'status': 'error', 'message': 'No JSON data received'}), 400

            # Make a copy of current settings and update it
            # Ensure settings is a dict before copying
            current_settings = settings.copy() if isinstance(settings, dict) else load_settings()
            current_settings.update(updated_settings_data)
            settings = current_settings # Update global settings variable
            save_settings(settings) # Save updated settings to settings.json

            # Track if we need to restart all_sensors based on changes
            restart_all_sensors = False
            if 'customPattern' in updated_settings_data or 'colorSequence' in updated_settings_data:
                 # Check if the new pattern/sequence is different from the old one before triggering restart
                 # This requires comparing updated_settings_data with the previous state of settings
                 # For simplicity now, assume any change requires restart if Pico connected
                 restart_all_sensors = True

            pattern_updated_on_device = None # Initialize status

            # If Pico is connected and settings affecting it changed, update the Pico
            if restart_all_sensors and pico_connected:
                logger.info("Relevant settings changed, attempting to update Pico...")
                try:
                    # Pass the relevant settings directly or trigger an update mechanism
                    # For now, just call update_sensor_pattern which restarts the script
                    # In the future, update_sensor_pattern could take settings as an argument
                    update_success = update_sensor_pattern()
                    pattern_updated_on_device = update_success
                    if update_success:
                        logger.info("Successfully updated sensor pattern/sequence on Pico.")
                    else:
                        logger.error("Failed to update sensor pattern/sequence on Pico.")
                except Exception as e:
                    logger.error(f"Error during Pico update process: {e}")
                    pattern_updated_on_device = False


            # Return detailed status
            return jsonify({
                'status': 'success',
                'message': 'Settings saved successfully.',
                # Indicate whether the update attempt was made and its result
                'pattern_updated_on_device': pattern_updated_on_device,
                'pico_connected': pico_connected
            })

        except Exception as e:
            logger.error(f"Error handling settings: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

#remove removed files from approved.txt
@app.route('/api/remove-face', methods=['POST'])
def remove_face():
    data = request.get_json()
    filename = data.get('filename')
    approved_file = 'camera/faces/imagelist.txt'
    face_path = os.path.join('static/faces', filename)

    # Remove from approved.txt
    with open(approved_file, 'r') as f:
        lines = f.readlines()
    with open(approved_file, 'w') as f:
        for line in lines:
            if line.strip() != filename:
                f.write(line)

    # Optionally delete the image
    try:
        os.remove(face_path)
    except Exception as e:
        print(f"Warning: could not delete image file: {e}")

    return jsonify({'status': 'success', 'removed': filename})

#get lsit of approved faces 
@app.route('/api/approved-faces')
def get_approved_faces():
    with open('camera/faces/imagelist.txt', 'r') as f:
        lines = [line.strip() for line in f if line.strip()]
    return jsonify(lines)

# Allows browser to acces images
@app.route('/camera/faces/<path:filename>')
def serve_face_image(filename):
    # Full absolute path
    full_path = os.path.join(os.getcwd(), 'camera', 'faces', filename)
    return send_file(full_path)

#blacklist images upload 
@app.route('/blacklist', methods=['POST'])
def upload_blacklist():
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
def upload_approved():
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
    """Update the sensor settings on the Pico by restarting the main script."""
    global pico_connected

    if not pico_connected:
        logger.error("Pico is not connected. Cannot update sensors.")
        return False

    # Path to the all_sensors.py file on the host machine
    all_sensors_host_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), # Go up two levels from web_UI
        "pico_sensors",
        "all_sensors.py"
    )

    # Path to the settings file on the host machine
    settings_host_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), SETTINGS_FILE_PATH)


    try:
        # Perform a complete reboot of the Pico
        logger.info("Performing complete reboot of the Pico to apply new settings...")

        # Attempt clean reset first
        try:
            subprocess.run(
                ["mpremote", "reset", "--hard"], # Use hard reset directly
                capture_output=True,
                text=True,
                timeout=5 # Increased timeout for reset
            )
            logger.info("Pico hard reset command issued.")
        except subprocess.TimeoutExpired:
             logger.warning("mpremote reset command timed out, Pico might be resetting.")
        except Exception as e:
            logger.warning(f"Error during mpremote reset: {e}")

        # Wait for Pico to potentially reboot and reconnect
        logger.info("Waiting for Pico to reconnect after reset (up to 30s)...")
        reconnect_attempts = 0
        max_attempts = 15 # 15 attempts * 2s sleep = 30s
        reconnected = False

        while reconnect_attempts < max_attempts:
            time.sleep(2) # Wait before checking connection
            reconnect_attempts += 1
            logger.info(f"Reconnection attempt {reconnect_attempts}/{max_attempts}...")

            # Check if Pico is listed
            result = subprocess.run(
                ["mpremote", "connect", "list"],
                capture_output=True,
                text=True
            )

            if "2e8a:0005" in result.stdout: # Pico vendor/product ID
                logger.info("Pico reconnected successfully.")
                reconnected = True
                # Allow extra time for filesystem to stabilize after reconnect
                time.sleep(4)
                break # Exit loop once reconnected
            else:
                logger.warning("Pico not yet detected, waiting...")

        if not reconnected:
            logger.error("Failed to reconnect to Pico after reset.")
            pico_connected = False # Update connection status
            socketio.emit('status_update', {'pico_connected': False}) # Notify clients
            return False

        # Update global connection status if it changed
        if not pico_connected:
             pico_connected = True
             socketio.emit('status_update', {'pico_connected': True})


        # Clear out any auto-start scripts (optional, but good practice)
        logger.info("Ensuring no auto-start scripts (boot.py, main.py) are present...")
        try:
            subprocess.run(["mpremote", "rm", ":boot.py"], capture_output=True, text=True, timeout=3)
        except: pass # Ignore errors if files don't exist
        try:
            subprocess.run(["mpremote", "rm", ":main.py"], capture_output=True, text=True, timeout=3)
        except: pass


        # Copy the main sensor script
        if os.path.exists(all_sensors_host_path):
            logger.info("Copying fresh all_sensors.py to Pico...")
            try:
                # Remove existing file first to ensure clean copy
                subprocess.run(["mpremote", "rm", ":all_sensors.py"], capture_output=True, text=True, timeout=3)
                time.sleep(0.5) # Short pause after delete

                # Copy the file
                copy_result = subprocess.run(
                    ["mpremote", "cp", all_sensors_host_path, ":all_sensors.py"],
                    capture_output=True, text=True, check=True, timeout=10 # Increased timeout for copy
                )
                logger.info("Successfully copied all_sensors.py to Pico.")
            except subprocess.CalledProcessError as e:
                 logger.error(f"Failed to copy all_sensors.py: {e.stderr}")
                 return False
            except subprocess.TimeoutExpired:
                 logger.error("Timeout expired while copying all_sensors.py.")
                 return False
            except Exception as e:
                logger.error(f"Failed to copy all_sensors.py: {e}")
                return False
        else:
            logger.error(f"Cannot find source file at {all_sensors_host_path}")
            return False

        # Copy the settings file
        if os.path.exists(settings_host_path):
            logger.info(f"Copying {SETTINGS_FILE_PATH} to Pico...")
            try:
                # Remove existing file first
                subprocess.run(["mpremote", "rm", f":{SETTINGS_FILE_PATH}"], capture_output=True, text=True, timeout=3)
                time.sleep(0.5)

                # Copy the file
                copy_result = subprocess.run(
                    ["mpremote", "cp", settings_host_path, f":{SETTINGS_FILE_PATH}"],
                    capture_output=True, text=True, check=True, timeout=10
                )
                logger.info(f"Successfully copied {SETTINGS_FILE_PATH} to Pico.")
            except subprocess.CalledProcessError as e:
                 logger.error(f"Failed to copy {SETTINGS_FILE_PATH}: {e.stderr}")
                 return False
            except subprocess.TimeoutExpired:
                 logger.error(f"Timeout expired while copying {SETTINGS_FILE_PATH}.")
                 return False
            except Exception as e:
                logger.error(f"Failed to copy {SETTINGS_FILE_PATH}: {e}")
                return False
        else:
             logger.warning(f"Settings file not found at {settings_host_path}. Pico might use defaults or fail.")


        # Wait briefly for file system operations to complete
        time.sleep(1)

        # Start all_sensors.py using a launcher script to ensure clean execution
        logger.info("Starting all_sensors.py on Pico with new settings...")
        launcher_script = (
            f'import gc, sys, _thread\n'
            f'gc.collect()\n'
            f'# Clear modules except essential ones\n'
            f'for name in list(sys.modules):\n'
            f'    if name not in ("gc", "sys", "_thread", "micropython", "uctypes", "array", "rp2"):\n' # Keep essential builtins
            f'        try:\n'
            f'            del sys.modules[name]\n'
            f'        except KeyError:\n'
            f'            pass\n'
            f'gc.collect()\n'
            f'def run_main():\n'
            f'    try:\n'
            f'        print("Importing all_sensors...")\n'
            f'        all_sensors = __import__("all_sensors")\n'
            f'        print("Running all_sensors.main()...")\n'
            f'        all_sensors.main()\n' # Assuming all_sensors.py has a main() function
            f'        print("all_sensors.main() finished.")\n'
            f'    except Exception as e:\n'
            f'        print(f"Error in run_main: {{e}}")\n'
            f'try:\n'
            f'    print("Starting thread for run_main...")\n'
            f'    _thread.start_new_thread(run_main, ())\n'
            f'    print("Thread started.")\n'
            f'except Exception as e:\n'
            f'    print(f"Error starting thread: {{e}}")\n'
        )

        try:
            # Execute the launcher script using mpremote exec
            result = subprocess.run(
                ["mpremote", "exec", launcher_script],
                capture_output=True,
                text=True,
                timeout=5 # Timeout for starting the script
            )
            logger.info(f"Launcher script stdout:\n{result.stdout}")
            logger.error(f"Launcher script stderr:\n{result.stderr}")

            # Check for success indicators in the output
            if "Thread started." in result.stdout and not result.stderr:
                logger.info("Successfully started all_sensors.py via launcher script.")
                # Start monitoring the output in the existing monitor_pico thread
                # No need to start a new monitor here, the main loop handles it.
                return True
            else:
                logger.error(f"Failed to start all_sensors.py cleanly. Check Pico logs if possible. Output: {result.stdout} {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            logger.error("Timeout expired while executing launcher script on Pico.")
            return False
        except Exception as e:
            logger.error(f"Error executing launcher script on Pico: {e}")
            return False

    except Exception as e:
        logger.error(f"Unexpected error during sensor update process: {e}")
        # Attempt to ensure connection status is accurate
        try:
             result = subprocess.run(["mpremote", "connect", "list"], capture_output=True, text=True, timeout=3)
             if "2e8a:0005" not in result.stdout:
                  pico_connected = False
                  socketio.emit('status_update', {'pico_connected': False})
        except:
             pico_connected = False # Assume disconnected on error
             socketio.emit('status_update', {'pico_connected': False})
        return False

def update_audio():
    return None

def send_to_listener(message):
    """Sends a message to the listener Pi."""
    if not LISTENER_PI_IP:
        logger.warning("Listener Pi IP address is not configured. Cannot send message.")
        return

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(3) # Set a timeout (e.g., 3 seconds)
            logger.info(f"Attempting to connect to listener Pi at {LISTENER_PI_IP}:{LISTENER_PI_PORT}")
            s.connect((LISTENER_PI_IP, LISTENER_PI_PORT))
            s.sendall(message.encode('utf-8'))
            logger.info(f"Sent message '{message}' to listener Pi.")
    except socket.timeout:
        logger.error(f"Connection to listener Pi ({LISTENER_PI_IP}:{LISTENER_PI_PORT}) timed out.")
    except socket.error as e:
        logger.error(f"Could not connect or send to listener Pi ({LISTENER_PI_IP}:{LISTENER_PI_PORT}): {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while sending to listener: {e}")

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
