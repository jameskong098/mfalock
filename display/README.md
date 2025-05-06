# Display Setup

## Installation

1.  Enable SPI interface:
    ```bash
    sudo raspi-config nonint do_spi 0
    ```
2.  Ensure you have created and activated a virtual environment (see [../README.md](../README.md)).
3.  Install required Python packages:
    ```bash
    pip3 install displayhatmini rpi-lgpio pillow
    ```

## Troubleshooting

**Error:** `RuntimeError: Cannot determine SOC peripheral base address.`

This error can occur due to conflicting GPIO library versions.

**Cause:** Sometimes, system-wide installations conflict with virtual environment installations. Attempting `pip uninstall lgpio` might show:

```
Found existing installation : lgpio 0.2.2.0
Not uninstalling lgpio at /usr/lib/python3/dist-packages, outside environment /home/yxh/Documents/mfalock/venv/
Can't uninstall 'lgpio'. No files were found to uninstall.
```

**Solution:** Remove the system-wide package:

```bash
sudo apt remove --purge python3-lgpio
```

## LCD Control Script (`test_lcd.py`)

The `test_lcd.py` script is designed to manage the Display HAT Mini, providing a user interface for authentication method selection and execution.

### Key Functionalities

*   UI navigation using Display HAT Mini buttons (A, B, X, Y).
*   Initial password setup for keypad authentication, stored in `web_UI/settings.json`.
*   Selection and initiation of authentication methods:
    *   Facial Recognition (invokes `camera/face_recognition_code.py`).
    *   Voice Recognition (invokes `audio/utils/audio_utils.py`).
    *   Keypad Authentication (on-device PIN entry).
    *   Placeholders/messages for Touch and Rotary (as these are handled by Pico via `web_server.py`).
*   Displaying results (success, failure, timeout, error) for each method.
*   Socket.IO communication with `web_server.py` to:
    *   Send authentication results (`auth_event`).
    *   Update the web UI on the current LCD mode (`lcd_mode_update`).
    *   Send keypad digits (`keypad_update`).
    *   Send the voice recognition challenge phrase (`voice_phrase_update`) to the web UI.
    *   Clear the voice phrase on the web UI.

### Running the Script

To run the script, use the following command:

```bash
python display/test_lcd.py
```

### Configuration Dependencies

The script relies on environment variables (e.g., `ALLOWED_WEB_SERVER_IP`, `LISTENER_PI_PORT`) defined in the root `.env` file for Socket.IO connection. It also interacts with `web_UI/settings.json` for keypad password storage.