### 1. Install System Packages

```bash
sudo apt update && sudo apt upgrade -y

sudo apt install -y \
  cmake build-essential \
  libjpeg-dev libtiff5-dev libpng-dev \
  libavcodec-dev libavformat-dev libswscale-dev \
  libv4l-dev libxvidcore-dev libx264-dev \
  libatlas-base-dev gfortran libhdf5-dev \
  libopenblas-dev liblapack-dev \
  libgtk-3-dev libboost-all-dev \
  python3-dev python3-pip python3-venv \
  libcamera-dev
```

### 2. Camera Code Overview

The camera functionality is primarily handled by `face_recognition_code.py`. This script is responsible for:
- Accessing the Raspberry Pi camera (Picamera2).
- Capturing video frames.
- Detecting faces in the frames.
- Comparing detected faces against a known set of faces.

The known faces are managed through the `camera/faces/imagelist.txt` file. This text file contains a list of filenames (e.g., `user1.jpg`, `user2.png`) corresponding to images stored in the `camera/faces/` directory. The `face_recognition_code.py` script reads this list to load the encodings of known individuals.

**Integration with the System:**

1.  **`display/test_lcd.py` (Display & Main Control Script):**
    *   When "Facial Recognition" is selected from the LCD menu, `test_lcd.py` launches `face_recognition_code.py` as a subprocess.
    *   It passes the path to `imagelist.txt` as an argument to the facial recognition script.
    *   `test_lcd.py` waits for `face_recognition_code.py` to complete and reads its standard output, which will be "SUCCESS", "FAILURE", or "TIMEOUT".
    *   Based on this result, `test_lcd.py` updates the LCD screen and sends an authentication event (success or failure) to the `web_UI/web_server.py` via Socket.IO.

2.  **`web_UI/` (Web Interface):**
    *   The web interface (specifically `web_UI/templates/users.html` and its corresponding JavaScript, interacting with `web_UI/web_server.py`) allows users to manage the approved faces.
    *   Users can upload new face images. Upon upload, the image is saved to the `camera/faces/` directory, and its filename is added to `imagelist.txt` by `web_server.py`.
    *   The web UI also displays the list of currently approved faces and allows for their removal, which updates `imagelist.txt` and can optionally delete the image file.

This setup allows the facial recognition module to operate independently for processing, while the main application (`test_lcd.py`) controls its execution and the web UI provides a convenient way to manage the database of known faces.

 3. Create a Python virtual environment (with system site packages)
 ```bash

    cd ~/Desktop/mfalock
    python3 -m venv --system-site-packages mfa_env
    source mfa_env/bin/activate
```

4. Install Python packages (inside the environment)
```bash 
    pip install wheel
    pip install numpy opencv-python dlib face_recognition
    pip install "python-socketio[client]" pillow pyserial
```

5. Install displayhatmini
``` bash 
    pip install displayhatmini
```

6. Install Picamera2 (for capturing frames
``` bash 
    sudo apt install -y python3-libcamera python3-kms++
    sudo apt install -y libcamera-apps
```
7. Handle GPIO Runtime Error (displayhatmini buffer issue fix)
If you see: RuntimeError: Cannot determine SOC peripheral base address, it's because your script uses RPi.GPIO, but you're not running as root.

You must run with sudo and keep virtual env access:
```bash 
export PYTHONPATH=/home/<your-username>/<your-env-name>/lib/python3.11/site-packages
sudo -E /home/<your-username>/<your-env-name>/bin/python <path-to-your-script>/test_lcd.py
```

8. Run the app
```bash
export PYTHONPATH=/home/pi/mfa_env/lib/python3.11/site-packages
sudo -E /home/pi/mfa_env/bin/python /home/pi/Desktop/mfalock/display/test_lcd.py
```
9. If you have problem regarding numpy running on different version that isnt compatible with facial recognition, do the following: 
```bash
sudo apt update 
sudo apt install libcap-dev -y

pip install --upgrade --no-cache-dir --force-reinstall numpy simplejpeg face_recognition picamera2
```


