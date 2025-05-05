import face_recognition
import cv2
from picamera2 import Picamera2
import numpy as np
import os

def detect_known_face(image_list_path="imagelist.txt", timeout=30):
    """
    Run face recognition without displaying anything.
    Returns True if any known face is detected, False if blacklisted face is detected,
    and None if no recognized face is detected.
    
    Args:
        image_list_path (str): Path to text file containing allowed image filenames
        timeout (int): Maximum seconds to attempt detection
    """
    print("[DEBUG] Starting face recognition function")
    # Load known faces from the list
    known_encodings = []
    known_names = []
    
    # Get the directory of the image list file
    base_dir = os.path.dirname(os.path.abspath(image_list_path))
    print(f"[DEBUG] Base directory: {base_dir}")
    print(f"[DEBUG] Image list path: {image_list_path}")
    
    # Load allowed faces
    try:
        with open(image_list_path, 'r') as file:
            image_files = [line.strip() for line in file.readlines()]
            print(f"[DEBUG] Found {len(image_files)} images in list file")
    except Exception as e:
        print(f"[DEBUG] Error opening image list file: {str(e)}")
        return False
        
    for img_file in image_files:
        img_path = os.path.join(base_dir, img_file)
        print(f"[DEBUG] Processing image: {img_path}")
        
        if os.path.exists(img_path):
            try:
                print(f"[DEBUG] Loading image file: {img_path}")
                known_image = face_recognition.load_image_file(img_path)
                print(f"[DEBUG] Finding face encodings in: {img_file}")
                encodings = face_recognition.face_encodings(known_image)
                if encodings:
                    known_encodings.append(encodings[0])
                    known_names.append(img_file)
                    print(f"[DEBUG] Successfully loaded encoding for {img_file}")
                else:
                    print(f"[DEBUG] No face found in {img_file}")
            except Exception as e:
                print(f"[DEBUG] Error loading {img_file}: {str(e)}")
        else:
            print(f"[DEBUG] File not found: {img_path}")
    
    print(f"[DEBUG] Total known face encodings loaded: {len(known_encodings)}")
    if not known_encodings:
        print("[DEBUG] No valid face encodings could be loaded.")
        return False
    
    # Set up camera
    print("[DEBUG] Initializing camera")
    picam2 = Picamera2()
    picam2.configure(picam2.create_preview_configuration(main={"size": (640, 480)}))
    picam2.start()
    print("[DEBUG] Camera started")
    
    import time
    start_time = time.time()
    frame_count = 0
    
    try:
        while time.time() - start_time < timeout:
            # Capture frame
            frame = picam2.capture_array()
            frame_count += 1
            
            if frame_count % 10 == 0:  # Print every 10 frames to avoid console spam
                elapsed = time.time() - start_time
                print(f"[DEBUG] Processed {frame_count} frames, {elapsed:.2f} seconds elapsed")
            
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Detect faces
            print(f"[DEBUG] Detecting faces in frame {frame_count}")
            face_locations = face_recognition.face_locations(rgb_frame)
            print(f"[DEBUG] Found {len(face_locations)} faces in frame")
            
            if face_locations:
                face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
                print(f"[DEBUG] Generated {len(face_encodings)} face encodings")
                
                # Check if any face matches the known faces
                for i, face_encoding in enumerate(face_encodings):
                    # Check allowed faces
                    print(f"[DEBUG] Comparing face {i+1} with {len(known_encodings)} known faces")
                    allowed_matches = face_recognition.compare_faces(known_encodings, face_encoding)
                    
                    if True in allowed_matches:
                        index = allowed_matches.index(True)
                        print(f"[DEBUG] Match found! Face matches with: {known_names[index]}")
                        picam2.stop()
                        print(f"[DEBUG] Camera stopped after successful match")
                        return True
                    else:
                        print(f"[DEBUG] No match found for face {i+1}")
            
    except Exception as e:
        print(f"[DEBUG] Error during face detection: {str(e)}")
    finally:
        # Clean up
        picam2.stop()
        print(f"[DEBUG] Camera stopped. Processed {frame_count} frames in {time.time() - start_time:.2f} seconds")
    
    print("[DEBUG] No matches found within timeout period")
    return None

if __name__ == "__main__":
    print("[DEBUG] Starting main program")
    result = detect_known_face()
    if result is True:
        print("SUCCESS")
    elif result is False:
        print("FAILURE")
    else:
        print("TIMEOUT")
    print("[DEBUG] Program completed")