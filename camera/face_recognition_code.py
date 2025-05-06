import face_recognition
import cv2
from picamera2 import Picamera2
import numpy as np
import os
import argparse
import sys # Import sys

def detect_known_face(image_list_path="imagelist.txt", timeout=30):
    """
    Run face recognition without displaying anything.
    Returns True if any known face is detected, False if blacklisted face is detected,
    and None if no recognized fasce is detected.
    
    Args:
        image_list_path (str): Path to text file containing allowed image filenames
        timeout (int): Maximum seconds to attempt detection
    """
    # --- Send DEBUG messages to stderr ---
    print("[DEBUG] Starting face recognition function", file=sys.stderr)
    # Load known faces from the list
    known_encodings = []
    known_names = []
    
    # Get the directory of thesimage list file
    base_dir = os.path.dirname(os.path.abspath(image_list_path))
    print(f"[DEBUG] Base directory: {base_dir}", file=sys.stderr)
    print(f"[DEBUG] Image list path: {image_list_path}", file=sys.stderr)
    
    # Load allowed faces
    try:
        with open(image_list_path, 'r') as file:
            image_files = [line.strip() for line in file.readlines()]
            print(f"[DEBUG] Found {len(image_files)} images in list file", file=sys.stderr)
    except Exception as e:
        print(f"[DEBUG] Error opening image list file: {str(e)}", file=sys.stderr)
        return False # Keep return values as they are
        
    for img_file in image_files:
        img_path = os.path.join(base_dir, img_file)
        print(f"[DEBUG] Processing image: {img_path}", file=sys.stderr)
        
        if os.path.exists(img_path):
            try:
                print(f"[DEBUG] Loading image file: {img_path}", file=sys.stderr)
                known_image = face_recognition.load_image_file(img_path)
                print(f"[DEBUG] Finding face encodings in: {img_file}", file=sys.stderr)
                encodings = face_recognition.face_encodings(known_image)
                if encodings:
                    known_encodings.append(encodings[0])
                    known_names.append(img_file)
                    print(f"[DEBUG] Successfully loaded encoding for {img_file}", file=sys.stderr)
                else:
                    print(f"[DEBUG] No face found in {img_file}", file=sys.stderr)
            except Exception as e:
                print(f"[DEBUG] Error loading {img_file}: {str(e)}", file=sys.stderr)
        else:
            print(f"[DEBUG] File not found: {img_path}", file=sys.stderr)
    
    print(f"[DEBUG] Total known face encodings loaded: {len(known_encodings)}", file=sys.stderr)
    if not known_encodings:
        print("[DEBUG] No valid face encodings could be loaded.", file=sys.stderr)
        return False # Keep return values as they are
    
    # Set up camera
    print("[DEBUG] Initializing camera", file=sys.stderr)
    picam2 = Picamera2()
    picam2.configure(picam2.create_preview_configuration(main={"size": (640, 480)}))
    picam2.start()
    print("[DEBUG] Camera started", file=sys.stderr)
    
    import time
    start_time = time.time()
    frame_count = 0
    match_found = False # Flag added
    
    try:
        while time.time() - start_time < timeout:
            # Capture frame
            frame = picam2.capture_array()
            frame_count += 1
            
            if frame_count % 10 == 1:  # Process every 10 frames (1, 11, 21...) and print status
                elapsed = time.time() - start_time
                print(f"[DEBUG] Processed {frame_count} frames, {elapsed:.2f} seconds elapsed", file=sys.stderr)
                # Detect faces only on processed frames
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                print(f"[DEBUG] Detecting faces in frame {frame_count}", file=sys.stderr)
                face_locations = face_recognition.face_locations(rgb_frame, model='hog') # Use hog for speed
                print(f"[DEBUG] Found {len(face_locations)} faces in frame", file=sys.stderr)
                
                if face_locations:
                    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
                    print(f"[DEBUG] Generated {len(face_encodings)} face encodings", file=sys.stderr)
                    
                    # Check if any face matches the known faces
                    for i, face_encoding in enumerate(face_encodings):
                        # Check allowed faces
                        print(f"[DEBUG] Comparing face {i+1} with {len(known_encodings)} known faces", file=sys.stderr)
                        allowed_matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=0.55) # Adjust tolerance if needed
                        
                        if True in allowed_matches:
                            index = allowed_matches.index(True)
                            print(f"[DEBUG] Match found! Face matches with: {known_names[index]}", file=sys.stderr)
                            match_found = True # Set flag
                            break # Exit inner loop
                        else:
                            print(f"[DEBUG] No match found for face {i+1}", file=sys.stderr)
                if match_found:
                    break # Exit outer loop (while) if match found
            else:
                 time.sleep(0.01) # Small sleep if skipping frame processing
            
    except Exception as e:
        print(f"[DEBUG] Error during face detection: {str(e)}", file=sys.stderr)
        match_found = False # Ensure failure on error
    finally:
        # Clean up
        picam2.stop()
        print(f"[DEBUG] Camera stopped. Processed {frame_count} frames in {time.time() - start_time:.2f} seconds", file=sys.stderr)
    
    # --- Determine final result based on flag and timeout ---
    if match_found:
        print("[DEBUG] Match found within timeout period", file=sys.stderr)
        return True
    elif time.time() - start_time >= timeout:
         print("[DEBUG] No matches found within timeout period", file=sys.stderr)
         return None # Indicate timeout explicitly
    else:
         print("[DEBUG] No matches found (detection loop finished early or error occurred)", file=sys.stderr)
         return False # Indicate failure


if __name__ == "__main__":
    # --- Add Argument Parsing ---
    parser = argparse.ArgumentParser(description="Detect known faces using PiCamera.")
    parser.add_argument('--imagelist', type=str, required=True,
                        help='Path to the text file containing known image filenames.')
    parser.add_argument('--timeout', type=int, default=30,
                        help='Timeout in seconds for detection.')
    args = parser.parse_args()
    # --- End Argument Parsing ---

    print("[DEBUG] Starting main program", file=sys.stderr)
    # Pass the parsed arguments to the function
    result = detect_known_face(image_list_path=args.imagelist, timeout=args.timeout)

    # --- Output the result clearly to STDOUT for the calling script ---
    if result is True:
        print("SUCCESS") # Print exactly "SUCCESS" to STDOUT
    elif result is False:
        print("FAILURE") # Print exactly "FAILURE" to STDOUT
    else: # result is None (timeout)
        print("TIMEOUT") # Print exactly "TIMEOUT" to STDOUT
    # --- End STDOUT output ---

    print("[DEBUG] Program completed", file=sys.stderr)
