
import face_recognition
import cv2
from picamera2 import Picamera2
import numpy as np
import os

def detect_known_face(image_list_path="imagelist.txt", blacklist_path="blacklist.txt", timeout=30):
    """
    Run face recognition without displaying anything.
    Returns True if any known face is detected, False if blacklisted face is detected,
    and None if no recognized face is detected.
    
    Args:
        image_list_path (str): Path to text file containing allowed image filenames
        blacklist_path (str): Path to text file containing blacklisted image filenames
        timeout (int): Maximum seconds to attempt detection
    """
    # Load known faces from the list
    known_encodings = []
    known_names = []
    # blacklist_encodings = []
    # blacklist_names = []
    
    # Get the directory of the image list file
    base_dir = os.path.dirname(os.path.abspath(image_list_path))
    
    # Load allowed faces
    with open(image_list_path, 'r') as file:
        image_files = [line.strip() for line in file.readlines()]
        
    for img_file in image_files:
        img_path = os.path.join(base_dir, img_file)
        if os.path.exists(img_path):

            try:
                known_image = face_recognition.load_image_file(img_path)
                encodings = face_recognition.face_encodings(known_image)
                if encodings:
                    known_encodings.append(encodings[0])
                    known_names.append(img_file)
                    print(f"Loaded encoding for {img_file}")
                else:
                    print(f"No face found in {img_file}")
            except Exception as e:
                print(f"Error loading {img_file}: {str(e)}")
        else:
            print(f"File not found: {img_path}")
    
    # Load blacklisted faces
    # if os.path.exists(blacklist_path):
    #     with open(blacklist_path, 'r') as file:
    #         blacklist_files = [line.strip() for line in file.readlines()]
            
    #     for img_file in blacklist_files:
    #         img_path = os.path.join(base_dir, img_file)
    #         if os.path.exists(img_path):
    #             try:
    #                 blacklist_image = face_recognition.load_image_file(img_path)
    #                 encodings = face_recognition.face_encodings(blacklist_image)
    #                 if encodings:
    #                     blacklist_encodings.append(encodings[0])
    #                     blacklist_names.append(img_file)
    #                     print(f"Loaded blacklist encoding for {img_file}")
    #                 else:
    #                     print(f"No face found in blacklisted {img_file}")
    #             except Exception as e:
    #                 print(f"Error loading blacklisted {img_file}: {str(e)}")
    #         else:
    #             print(f"Blacklist file not found: {img_path}")
    
    if not known_encodings:
        print("No valid face encodings could be loaded.")
        return False
    
    # Set up camera
    picam2 = Picamera2()
    picam2.configure(picam2.create_preview_configuration(main={"size": (640, 480)}))
    picam2.start()
    
    import time
    start_time = time.time()
    
    try:
        while time.time() - start_time < timeout:
            # Capture frame
            frame = picam2.capture_array()
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Detect faces
            face_locations = face_recognition.face_locations(rgb_frame)
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            
            # Check if any face matches the known faces or blacklisted faces
            for face_encoding in face_encodings:
                # First check if face is blacklisted
                # if blacklist_encodings:
                #     blacklist_matches = face_recognition.compare_faces(blacklist_encodings, face_encoding)
                #     if True in blacklist_matches:
                #         picam2.stop()
                #         index = blacklist_matches.index(True)
                #         print(f"Matched with blacklisted face: {blacklist_names[index]}")
                #         return False
                
                # Then check allowed faces
                allowed_matches = face_recognition.compare_faces(known_encodings, face_encoding)
                if True in allowed_matches:
                    picam2.stop()
                    index = allowed_matches.index(True)
                    print(f"Matched with allowed face: {known_names[index]}")
                    return True
                
    finally:
        # Clean up
        picam2.stop()
    
    return None

if __name__ == "__main__":
    result = detect_known_face()
    if result is True:
        print("SUCCESS")
    elif result is False:
        print("FAILURE")
    else:
        print("TIMEOUT")