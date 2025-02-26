# MFA Lock

## Multi-Factor Authentication Smart Lock for Dorms

![MFA Lock Logo](https://via.placeholder.com/150?text=MFA+Lock)

## About MFA Lock

Has this ever happened to you? After a long night of coding for CS 142A, you finally make it home, exhausted, barely debating whether brushing your teeth is worth the effort. But as you reach your door, the realization hits—you forgot your key. Locked out, helpless, and half-asleep, you call the lockout assistant, only to wait endlessly while they take their time.

**MFA Lock** is here to make sure this never happens again. Our cutting-edge multi-factor authentication system provides up to six different ways to unlock your door:

- 👤 Face Recognition
- 🔊 Voice Recognition
- 🔢 Keypad Access
- 📱 Mobile Authentication
- 👋 Gesture Unlocking
- 👆 Tap Unlocking

No more waiting in front of your door or relying on slow lockout services. With MFA Lock, your room is always accessible—only to those you trust.

But it doesn't stop there. MFA Lock also lets you:
- Remotely grant access to friends or roommates when you're away
- Monitor who's at your door in real time
- Add multiple trusted users with personalized authentication methods

Even if you've never forgotten your key, MFA Lock enhances your dorm security, keeping your valuables safe from unwanted intruders.

## Project Goals

We created MFA Lock to solve two key problems:
1. **Convenience**: Traditional keys can be easily lost, forgotten, or stolen
2. **Security**: Enhanced protection for your living space and belongings

Our goal is to provide a seamless, keyless entry system that gives users complete control over access to their space, ensuring they never have to deal with the frustration of lost keys or the insecurity of outdated lock systems.

## Team Members

- [Danish Abbasi](https://www.linkedin.com/in/danish-abbasi/)
- [Omorogieva Ogieva](https://www.linkedin.com/in/ogieva/)
- [James Kong](https://www.linkedin.com/in/jamesdemingkong/)
- [Yunus Kocaman](https://www.linkedin.com/in/yunus-kocaman-b372822b5/)

## Technical Details

### Hardware Components
- **Computing**: Raspberry Pi, Raspberry Pi Pico
- **Authentication Sensors**:
  - Raspberry Pi Camera (facial recognition & gestures)
  - Microphone Array (voice recognition)
  - Touch Sensor (secret tap pattern)
- **Lock Mechanism**: Servo motor
- **Display**: Touch screen 3.5" LCD display
- **Additional Hardware**: Connectors, power supply

### Software Components
- OpenCV for computer vision tasks
- MediaPipe for gesture recognition
- face_recognition library for facial identification
- Custom web application for authentication logs
- Mobile app support (future enhancement)

## Project Timeline

| Week | Milestones |
|------|------------|
| 1-3  | Hardware setup, servo mechanism testing, initial UI development |
| 4    | Implementation of authentication methods (gesture, keypad, tap pattern) |
| 5    | Testing, web application integration, logging verification |
| 6    | Mid-project progress report |
| 7    | Final hardware assembly and software integration |

## Authentication Methods

### Facial Recognition
Using the Raspberry Pi Camera and OpenCV, the system will detect and verify authorized faces.

### Voice Recognition
The microphone array captures voice patterns and compares them against stored profiles.

### Gesture-Based Unlocking
Custom hand gestures captured by the camera serve as unique authentication signals.

### Keypad Authentication
A conventional PIN-based system via the touchscreen display.

### Secret Tap Pattern
A personalized sequence of taps detected by touch sensors unlocks the door.

### Mobile Authentication
Convenient unlocking through a secure mobile application.

## References

- [OpenCV](https://opencv.org/)
- [Python face recognition](https://pypi.org/project/face-recognition/)
- [Raspberry Pi documentation](https://www.raspberrypi.org/documentation/)
- [Python speech recognition](https://www.geeksforgeeks.org/python-speech-recognition-module/)

## License

[MIT License](LICENSE)

Copyright (c) 2025 Yunus Kocaman, James Kong, Danish Abbasi, Omorogieva Ogieva