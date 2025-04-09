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


# Load the Vosk Model (Ensure "vosk_model" folder is in the same directory)
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
model_path = os.path.join(parent_dir, "vosk_model")
model = Model(model_path)
recognizer = KaldiRecognizer(model, 16000)

# Initialize PyAudio
audio = pyaudio.PyAudio()

# Find the correct microphone index (useful for ReSpeaker Mic Array)
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

phrase = gen_phrase(5)
print(f"Listening... Say this phrase: {phrase}!")


try:
    while True:
        data = stream.read(4096, exception_on_overflow=False)
        if recognizer.AcceptWaveform(data):
            result = json.loads(recognizer.Result())  # Convert JSON output to dict
            text = result.get("text", "")  # Extract recognized text
            if text:
                print(f"You said: {text}")
                if text.lower() == phrase.lower():
                    print("Correct... Opening!!!")
except KeyboardInterrupt:
    print(" Stopping...")
    stream.stop_stream()
    stream.close()
    audio.terminate()

