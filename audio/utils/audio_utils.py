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
    print(f"PHRASE: {phrase}", flush=True) 
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
                    print(f"FINAL_RECOGNIZED_TEXT: {text}") # Parsable final result
                    logging.info(f"Recognized: '{text}'")
                    if text.lower() == phrase.lower():
                        if not final_result_reported:
                            print("VOICE - SUCCESS")
                            logging.info("Authentication SUCCESSFUL.")
                            final_result_reported = True
                        break # Exit loop on success
            else:
                # Handle partial results for live feedback
                partial_result_json = recognizer.PartialResult()
                partial_result = json.loads(partial_result_json)
                partial_text = partial_result.get("partial", "")
                if partial_text:
                    print(f"PARTIAL_RECOGNIZED_TEXT: {partial_text}") # Parsable partial result
                    # print(f"Partial: {partial_text}") # Optional: for local debugging

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
        if recognized_text and phrase and recognized_text.lower() == phrase.lower(): # Check if recognized_text and phrase are not None
             # This case should ideally be caught inside the loop, but as a fallback
             print("VOICE - SUCCESS")
             logging.info("Authentication SUCCESSFUL.")
        elif recognized_text is not None and phrase is not None: # Ensure they are not None before comparing
             print("VOICE - FAILURE") # Print failure if loop ended without success
             logging.info(f"Authentication FAILED. Expected '{phrase}', Got '{recognized_text}'")
        else:
            # Handle cases where recognized_text or phrase might be None if loop exited early
            # For example, if timeout occurred before any recognition, or phrase wasn't generated.
            print("VOICE - FAILURE") # Default to failure if specific conditions not met
            logging.info(f"Authentication FAILED. Expected '{phrase if phrase else '[no phrase generated/available]'}', Got '{recognized_text if recognized_text else '[no speech recognized]'}'")

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

