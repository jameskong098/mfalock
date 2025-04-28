"""
Voice Authentication Lock
-------------------------
This program implements a voice-based security mechanism that recognizes a random phrase using VOSK.

Hardware:
- Computer (Raspberry Pi 5)
- USB Microphone

Author: Omorogieva Ogieva
Date: February 27, 2025
"""

import os
from vosk import Model, KaldiRecognizer
from random_utils import gen_phrase
import pyaudio
import json
import time
import logging
from datetime import datetime


# Load the Vosk Model and configure logging
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
log_file_path = os.path.join(parent_dir, "voice_auth_log.txt")
logging.basicConfig(filename=log_file_path,
                    level=logging.INFO,
                    format='%(asctime)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
model_path = os.path.join(parent_dir, "vosk_model")
model = Model(model_path)
recognizer = KaldiRecognizer(model, 16000)

# Initialize PyAudio
audio = pyaudio.PyAudio()

# Find the correct microphone index
mic_index = None
for i in range(audio.get_device_count()):
    info = audio.get_device_info_by_index(i)
    if "ReSpeaker" in info["name"]:  # Change if using another mic
        mic_index = i
        break

# Open Audio Stream (Use `mic_index` if needed)
stream = audio.open(format=pyaudio.paInt16, channels=1, rate=16000,
                    input=True, frames_per_buffer=4096, input_device_index=mic_index)
stream.start_stream()

try:
    phrase = gen_phrase(5)
    print(f"Listening... Say this phrase: {phrase}!")
    start_time = time.time()
    timeout = 30  # seconds
    while True:
        if time.time() - start_time > timeout:
            print("Timeout reached. Try again.")
            logging.info("Authentication SUCCESSFUL.")
            break
        data = stream.read(4096, exception_on_overflow=False)
        if recognizer.AcceptWaveform(data):
            result = json.loads(recognizer.Result())  # Convert JSON output to dict
            text = result.get("text", "")  # Extract recognized text
            if text:
                print(f"You said: {text}")
                logging.info(f"Recognized: '{text}'")
                if text.lower() == phrase.lower():
                    print("Correct... Opening!!!")
                    logging.info("Authentication SUCCESSFUL.")
                    break
        else:
            print("Could not recognize speech. Try again.")

except KeyboardInterrupt:
    print("Interrupted by user.")
    logging.warning("Authentication INTERRUPTED by user.")

finally:
    print(" Stopping...")
    stream.stop_stream()
    stream.close()
    audio.terminate()

