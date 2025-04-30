# Audio Utilities

This directory contains utility modules for audio processing, file handling, and random phrase generation used within the MFA Lock application.

## Modules

*   **`audio_utils.py`**: Contains functions related to audio recording, processing, and potentially voice activity detection or feature extraction. It likely interacts with libraries like `sounddevice` and `vosk`.
*   **`file_utils.py`**: Provides helper functions for managing files, such as saving or loading audio data or logs.
*   **`random_utils.py`**: Includes functions for generating random phrases, likely used for voice authentication challenges. See [`random_utils.py`](/Users/jameskong/Documents/mfalock/audio/utils/random_utils.py) for the word list and functions.

## Dependencies

These utilities rely on several Python packages listed in the main [`requirements.txt`](/Users/jameskong/Documents/mfalock/requirements.txt) file in the root directory. Ensure all dependencies are installed using:

```bash
pip install -r ../../requirements.txt
```

### System Dependencies

Additionally, libraries like `sounddevice` require system-level audio libraries. On Debian-based systems (like Ubuntu), you need to install PortAudio. Run the following command **before** installing the Python requirements:

```bash
sudo apt update && sudo apt install libportaudio2 libportaudiocpp0 portaudio19-dev
```

This ensures that the necessary audio I/O capabilities are available on your system.