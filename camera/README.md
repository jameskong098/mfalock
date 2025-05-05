

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

