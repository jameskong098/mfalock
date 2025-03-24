import face_recognition
import cv2
from picamera2 import Picamera2
import numpy as np

known_image = face_recognition.load_image_file("yunus2.jpg")
known_encoding = face_recognition.face_encodings(known_image)[0]

picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(main={"size": (640, 480)}))
picam2.start()

while True: 
    frame = picam2.capture_array()

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    face_locations = face_recognition.face_locations(rgb_frame)
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

    for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
        matches = face_recognition.compare_faces([known_encoding], face_encoding)
        name = "Unknown"

        if True in matches: 
            name = "Yunus"
            color = (0, 255, 0)
        else:
            name = "unknown"
            color = (255, 0, 0)

        # Draw rectangle around face
        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
        cv2.putText(frame, name, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    cv2.imshow("Face Recognition", frame)

    if cv2.waitKey(1) & 0xFF == 27:  # Press ESC to exit
        break

picam2.stop()
cv2.destroyAllWindows()