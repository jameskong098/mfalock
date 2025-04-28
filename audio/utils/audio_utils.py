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
import json
import time
import logging
import sounddevice as sd
import numpy as np
assert np
import queue


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

# Initialize Parameters
samplerate = 16000
blocksize = 4096
channels = 1
dtype = 'int16'
timeout = 30  # seconds
q = queue.Queue()

def audio_callback(indata, frames, time, status):
    if status:
        logging.warning(f"Status: {status}")
    q.put(indata.copy())

# Start stream
stream = sd.InputStream(
    samplerate=samplerate,
    channels=channels,
    blocksize=blocksize,
    dtype=dtype,
    callback=audio_callback
)


try:
    stream.start()
    phrase = gen_phrase(5)
    print(f"Listening... Say this phrase: {phrase}!")
    print(sd.query_devices())
    start_time = time.time()
    while True:
        if time.time() - start_time > timeout:
            print("Timeout reached. Try again.")
            logging.info("Authentication TIMED OUT.")
            break

        try:
            data = q.get(timeout=1)
            if recognizer.AcceptWaveform(data.tobytes()):
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
        except queue.Empty:
            continue

except KeyboardInterrupt:
    print("Interrupted by user.")
    logging.warning("Authentication INTERRUPTED by user.")

finally:
    print(" Stopping...")
    stream.stop()
    stream.close()

