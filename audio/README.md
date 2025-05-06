# Audio Module for MFA Lock

## Purpose

The Audio module is responsible for handling voice-based authentication within the MFA Lock system. It allows users to authenticate by speaking a dynamically generated phrase.

## Main Script

-   `utils/audio_utils.py`: This is the core script that manages the voice authentication process.

## Functionality

The `audio_utils.py` script performs the following key functions:

1.  **Challenge Phrase Generation**:
    *   Generates a random, simple phrase that the user must speak for authentication.

2.  **Communication with Display Controller & Web UI**:
    *   The generated phrase is sent to the main display controller script (`display/test_lcd.py`).
    *   The display controller then emits this phrase via Socket.IO, allowing the web UI (`web_UI/static/js/dashboard.js`) to display it to the user.

3.  **Audio Capture**:
    *   Captures audio input from the connected microphone when the voice authentication mode is active.

4.  **Speech-to-Text and Verification**:
    *   Converts the captured spoken audio into text.
    *   Compares the recognized text against the original challenge phrase.

5.  **Outcome Reporting**:
    *   Reports the result of the authentication attempt (e.g., "VOICE - SUCCESS", "VOICE - FAILURE", "VOICE - TIMEOUT", "VOICE - ERROR") back to the calling script (`display/test_lcd.py`).

## Integration

-   **Initiation**: The voice authentication process is initiated from the `display/test_lcd.py` script when the user selects "Voice Recognition" from the device's menu.
-   **LCD & Web UI Updates**:
    *   `display/test_lcd.py` uses the result from `audio_utils.py` to update the LCD screen (e.g., show success/failure messages).
    *   It also emits an `auth_event` via Socket.IO to `web_UI/web_server.py`, which then broadcasts it to all connected web clients. This updates the dashboard with the authentication attempt.
    *   The challenge phrase itself is displayed on the web UI through a `display_voice_phrase` Socket.IO event chain originating from `audio_utils.py` -> `test_lcd.py` -> `web_server.py` -> `dashboard.js`.
-   **Listener Pi**: Successful voice authentications are communicated to a designated listener Pi by `web_UI/web_server.py`.

## Dependencies

The `audio_utils.py` script relies on external libraries for:

-   Audio capture (e.g., PyAudio).
-   Speech-to-text processing (e.g., SpeechRecognition library with an engine like CMU Sphinx, Google Speech Recognition, etc.).
-   Random phrase generation.

*(Specific libraries and their versions should be detailed in a `requirements.txt` file or similar within the project's audio or root directory).*

## Setup and Configuration

-   **Microphone**: A functional microphone must be connected to the device running the `audio_utils.py` script (typically the Raspberry Pi with the display). Ensure the microphone is correctly configured at the OS level.
-   **Speech Recognition Engine**: Depending on the chosen speech-to-text engine, API keys or model files might need to be configured or downloaded. For offline engines like CMU Sphinx, language models are required.
-   **Environment Variables**: Any API keys or specific configurations might be managed through environment variables (see `.env` file in the project root).
