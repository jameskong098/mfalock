from vosk import Model, KaldiRecognizer
import pyaudio
import json
import random_utils
from audio.utils.random_utils import gen_phrase

# Load the Vosk Model (Ensure "vosk_model" folder is in the same directory)
model = Model("vosk_model")
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

print("Listening... Speak now!")
phrase = gen_phrase()

try:
    while True:
        data = stream.read(4096, exception_on_overflow=False)
        if recognizer.AcceptWaveform(data):
            result = json.loads(recognizer.Result())  # Convert JSON output to dict
            text = result.get("text", "")  # Extract recognized text
            if text:
                print(f"You said: {text}")
                if text == phrase:

                    print("Correct... Opening!!!")
except KeyboardInterrupt:
    print(" Stopping...")
    stream.stop_stream()
    stream.close()
    audio.terminate()

