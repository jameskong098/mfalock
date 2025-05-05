# MFA Lock

## 🔒 Multi-Factor Authentication Smart Lock for Dorms

## About MFA Lock

Has this ever happened to you? After a long night of coding for CS 142A, you finally make it home, exhausted, barely debating whether brushing your teeth is worth the effort. But as you reach your door, the realization hits—you forgot your key. Locked out, helpless, and half-asleep, you call the lockout assistant, only to wait endlessly while they take their time.

**MFA Lock** is here to make sure this never happens again. Our cutting-edge multi-factor authentication system provides multiple ways to unlock your door:

- 👤 Face Recognition (via Camera)
- 🔊 Voice Recognition (via Microphone Array)
- 👋 Gesture Unlocking (via Camera)
- 👆 Secret Tap Pattern (via Pico Touch Sensor)
- 🔄 Rotary Angle Sequence (via Pico Rotary Sensor)
- 🔢 Keypad Access (via Touchscreen Display)

No more waiting in front of your door or relying on slow lockout services. With MFA Lock, your room is always accessible—only to those you trust.

But it doesn't stop there. MFA Lock also lets you:
- Monitor who's at your door in real time via the Web UI
- Review historical access logs
- Configure authentication methods
- (Future) Remotely grant access to friends or roommates
- (Future) Add multiple trusted users with personalized authentication methods

Even if you've never forgotten your key, MFA Lock enhances your dorm security, keeping your valuables safe from unwanted intruders.

## Project Goals

We created MFA Lock to solve two key problems:
1. **Convenience**: Traditional keys can be easily lost, forgotten, or stolen.
2. **Security**: Enhanced protection for your living space and belongings using multiple authentication factors.

Our goal is to provide a seamless, keyless entry system that gives users complete control over access to their space, ensuring they never have to deal with the frustration of lost keys or the insecurity of outdated lock systems.

## Team Members

- [Danish Abbasi](https://www.linkedin.com/in/danish-abbasi/)
- [Omorogieva Ogieva](https://www.linkedin.com/in/ogieva/)
- [James Kong](https://www.linkedin.com/in/jamesdemingkong/)
- [Yunus Kocaman](https://www.linkedin.com/in/yunus-kocaman-b372822b5/)

## Architecture Overview

The MFA Lock system utilizes a distributed architecture involving two Raspberry Pi devices and connected peripherals:

1.  **Raspberry Pi 1 (Web Server & Sensor Hub):**
    *   Runs the main Flask web application (`web_UI/web_server.py`).
    *   Provides a web interface for monitoring, configuration, and viewing logs.
    *   Connects directly to sensors like the Raspberry Pi Camera (for face/gesture recognition) and a Microphone Array (for voice recognition).
    *   Communicates via USB/Serial with a Raspberry Pi Pico running `pico_sensors/all_sensors.py`. This Pico handles inputs from the Touch Sensor and Rotary Angle Sensor.
    *   Processes authentication attempts based on inputs from various sensors.
    *   Sends authentication status messages (e.g., "TOUCH - SUCCESS", "VOICE - FAILURE") over the network to Raspberry Pi 2.

2.  **Raspberry Pi 2 (Listener & Actuator Controller):**
    *   Runs the `listener/listener.py` TCP server.
    *   Listens for authentication status messages from Raspberry Pi 1.
    *   Second Pico is connected to the physical lock mechanism (Servo Motor).
    *   Upon receiving a valid sequence of successful authentication messages from Pi 1 (based on configured multi-factor requirements), Pi 2 uses `mpremote` to command its connected Pico to activate the servo motor, unlocking the door.

**Communication Flow:**

```
User -> Sensor (Camera, Mic, Touch, Rotary, Keypad) -> Pi 1 (Web Server) -> Authentication Logic -> Network Message -> Pi 2 (Listener) -> Pico (Servo Control) -> Servo Motor -> Lock Unlocks
```

## Project Components

This repository is organized into the following directories:

*   **`audio/`**: Contains Python scripts and utilities for voice recognition.
    *   `utils/`: Helper modules for audio recording, file handling, and random phrase generation for voice challenges.
    *   `vosk_model/`: Pre-trained Vosk model for offline speech recognition.
*   **`camera/`**: Includes scripts for facial recognition (`face_recognition.py`) using OpenCV and the `face_recognition` library. Stores known face images in `faces/`.
*   **`display/`**: Contains code related to the touchscreen LCD display (e.g., `test_lcd.py`). *[Potentially for keypad input or status display]*
*   **`listener/`**: Houses the `listener.py` server that runs on Raspberry Pi 2. It receives authentication messages from the web server and controls the lock servo via its connected Pico. Includes a test script (`send_test_msg.py`).
*   **`pico_sensors/`**: Contains MicroPython code for the Raspberry Pi Picos.
    *   `all_sensors.py`: The primary script for the Pico connected to Pi 1, integrating touch and rotary sensor inputs and managing the active sensor state.
    *   `rotary_angle/`: Standalone code and README for the rotary angle sensor.
    *   `servo_motor/`: Code (`servo.py`) and README for controlling the servo motor (used by the Pico connected to Pi 2).
    *   `touch/`: Standalone code and README for the touch pattern lock mechanism.
*   **`web_UI/`**: The core Flask web application.
    *   `web_server.py`: The main Flask server script handling web requests, WebSocket communication, sensor interaction (via Pico and direct connections), authentication logic, and communication with the listener Pi.
    *   `static/`: Contains CSS, JavaScript, and images for the web interface.
    *   `templates/`: HTML templates for the web pages (Dashboard, Logs, Settings, etc.).
*   **`touch/`**: Stores the `custom_pattern.json` file, which defines the secret tap pattern if customized via the Web UI.
*   **Root Directory:**
    *   `requirements.txt`: Lists Python dependencies for the Raspberry Pi components.
    *   `auth_logs.json`: Stores historical authentication logs generated by the web server.
    *   `settings.json`: Stores system settings configured via the Web UI (e.g., touch pattern, rotary sequence).
    *   `README.md`: This file.

## Technical Details

### Hardware Components
- **Computing**: 2x Raspberry Pi, 2x Raspberry Pi Pico
- **Authentication Sensors**:
  - Raspberry Pi Camera (facial recognition & gestures) - Connected to Pi 1
  - Microphone Array (voice recognition) - Connected to Pi 1
  - Capacitive Touch Sensor (secret tap pattern) - Connected to Pico on Pi 1
  - Rotary Angle Sensor (color/angle sequence) - Connected to Pico on Pi 1
- **Lock Mechanism**: Servo motor - Connected to Pico on Pi 2
- **Display**: Touch screen 3.5" LCD display - Connected to Pi 1 (*Optional/Planned*)
- **Additional Hardware**: Connectors, power supplies, network connection (for Pi 1 <-> Pi 2 communication)

### Software Components
- **Operating System**: Raspberry Pi OS (or similar Linux distribution) on Raspberry Pis, MicroPython on Picos.
- **Main Application**: Python 3, Flask, Flask-SocketIO, pyserial, python-dotenv.
- **Computer Vision**: OpenCV, MediaPipe, face_recognition.
- **Voice Recognition**: Vosk (offline), sounddevice, numpy.
- **Pico Communication**: `mpremote`.
- **Web Frontend**: HTML, CSS, JavaScript.

## Authentication Methods Implemented

### Facial Recognition
Using the Raspberry Pi Camera and `face_recognition` library via `camera/face_recognition.py`, the system detects and verifies authorized faces stored in `camera/faces/`.

### Voice Recognition
The microphone array captures voice patterns. `audio/utils/audio_utils.py` likely handles recording, and Vosk performs offline speech-to-text for command/phrase verification.

### Gesture-Based Unlocking
*(Implementation details might be within `camera/` using OpenCV/MediaPipe - Needs verification)* Custom hand gestures captured by the camera serve as unique authentication signals.

### Secret Tap Pattern
A personalized sequence of taps and holds detected by the touch sensor connected to the Pico (running `pico_sensors/all_sensors.py`). The pattern is configurable via the Web UI (`web_UI/`) and stored in `touch/custom_pattern.json` or `web_UI/settings.json`.

### Rotary Angle Sequence
A sequence of colors/angles selected using the rotary angle sensor connected to the Pico (running `pico_sensors/all_sensors.py`). The sequence is configurable via the Web UI (`web_UI/`) and stored in `web_UI/settings.json`.

### Keypad Authentication
*(Planned)* A conventional PIN-based system potentially using the touchscreen display.

### Mobile Authentication
*(Planned)* Convenient unlocking through the web interface or a dedicated mobile application.

## Setup & Running

1.  **Hardware:** Connect sensors, Picos, and Pis as described in the Architecture section and component READMEs (`pico_sensors/`, `web_UI/`, `listener/`).
2.  **Software Dependencies:**
    *   **IMPORTANT:** First, follow the setup instructions in [camera/README.md](./camera/README.md) to correctly install dependencies for the camera and facial recognition, especially `dlib` and `face_recognition`. These can have complex build requirements.
    *   After completing the camera setup, install the remaining Python packages from `requirements.txt` on both Raspberry Pis: `pip install -r requirements.txt`.
    *   Install system dependencies (like PortAudio for `sounddevice`) if needed. Install `mpremote` on both Pis.
3.  **Pico Code:** Upload `pico_sensors/all_sensors.py` to the Pico connected to Pi 1. Upload `pico_sensors/servo_motor/servo.py` (or ensure the listener copies it) to the Pico connected to Pi 2.
4.  **Configuration:** Create a `.env` file in the project root (`mfalock/`) on *both* Raspberry Pis. Configure `LISTENER_PI_IP`, `LISTENER_PORT`, and `ALLOWED_WEB_SERVER_IP` correctly based on your network setup. See `web_UI/README.md` and `listener/README.md` for details.
5.  **Run Listener (Pi 2):** Navigate to `listener/` and run `python listener.py`. Keep it running.
6.  **Run Web Server (Pi 1):** Navigate to `web_UI/` and run `python web_server.py`.
7.  **Access Web UI:** Open a browser on a device on the same network and go to `http://<IP_ADDRESS_OF_PI_1>:8080`.

## References

- [OpenCV](https://opencv.org/)
- [Python face recognition](https://pypi.org/project/face-recognition/)
- [Raspberry Pi documentation](https://www.raspberrypi.org/documentation/)
- [Vosk Offline Speech Recognition](https://alphacephei.com/vosk/)
- [Flask](https://flask.palletsprojects.com/)
- [Flask-SocketIO](https://flask-socketio.readthedocs.io/)
- [mpremote](https://docs.micropython.org/en/latest/reference/mpremote.html)

## License

[MIT License](LICENSE)

Copyright (c) 2025 Yunus Kocaman, James Kong, Danish Abbasi, Omorogieva Ogieva