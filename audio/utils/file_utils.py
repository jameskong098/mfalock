import os

def list_audio_files(directory):
	return [f for f in os.listdir(directory) if f.endswith('.wav')]

if __name__ == "__main__":
	print (list_audio_files("../data"))
