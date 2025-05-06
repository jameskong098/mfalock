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
    # Output the phrase in a specific format for parsing
    print(f"PHRASE: {phrase}")
    # print(sd.query_devices()) # Optional: Keep for debugging if needed
    start_time = time.time()
    recognized_text = ""
    final_result_reported = False # Flag to ensure only one final result is printed

    while True:
        current_time = time.time()
        if current_time - start_time > timeout:
            if not final_result_reported:
                print("VOICE - TIMEOUT") # Use specific output for timeout
                logging.info("Authentication TIMED OUT.")
                final_result_reported = True
            break

        try:
            data = q.get(timeout=0.5) # Shorter timeout for queue get
            if recognizer.AcceptWaveform(data.tobytes()):
                result = json.loads(recognizer.Result())  # Convert JSON output to dict
                text = result.get("text", "")  # Extract recognized text
                if text:
                    recognized_text = text # Store the last recognized text
                    print(f"You said: {text}") # Keep this for logging/debugging
                    logging.info(f"Recognized: '{text}'")
                    if text.lower() == phrase.lower():
                        if not final_result_reported:
                            print("VOICE - SUCCESS")
                            logging.info("Authentication SUCCESSFUL.")
                            final_result_reported = True
                        break # Exit loop on success
                    # else: # Don't immediately print failure, wait for timeout or final result
                    #     print("VOICE - FAILURE") # Avoid printing failure on intermediate results
            # else:
                # Partial results can be accessed here if needed
                # partial_result = json.loads(recognizer.PartialResult())
                # print(f"Partial: {partial_result.get('partial', '')}")
                # pass

        except queue.Empty:
            # No data in the queue, continue loop check timeout
            continue
        except Exception as e:
            logging.error(f"Error during recognition loop: {e}")
            if not final_result_reported:
                print("VOICE - ERROR") # Indicate an error occurred
                final_result_reported = True
            break

    # After loop finishes (timeout, success, or error), check if success was achieved
    if not final_result_reported:
        if recognized_text.lower() == phrase.lower():
             # This case should ideally be caught inside the loop, but as a fallback
             print("VOICE - SUCCESS")
             logging.info("Authentication SUCCESSFUL.")
        else:
             print("VOICE - FAILURE") # Print failure if loop ended without success
             logging.info(f"Authentication FAILED. Expected '{phrase}', Got '{recognized_text}'")

except KeyboardInterrupt:
    print("Interrupted by user.")
    logging.warning("Authentication INTERRUPTED by user.")
    print("VOICE - FAILURE") # Treat interrupt as failure

except Exception as e:
    logging.error(f"An error occurred: {e}")
    print(f"An error occurred: {e}")
    print("VOICE - ERROR") # Indicate a script-level error

finally:
    print(" Stopping...")
    if 'stream' in locals() and stream:
        try:
            stream.stop()
            stream.close()
        except Exception as e:
            logging.error(f"Error closing stream: {e}")
    print("Stream closed.")

