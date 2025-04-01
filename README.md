# Hand Gesture Car Control System

A Python application that allows you to control a virtual car using hand gestures captured through a webcam.

## Overview

This application uses computer vision and machine learning to detect hand movements and translate them into car controls. You can accelerate, brake, and steer the car by moving your hand in front of your webcam.

## Features

- **Real-time hand gesture detection** using MediaPipe
- **Intuitive controls**:
  - Control speed by raising/lowering your thumb
  - Control direction by tilting your hand left or right
- **Dynamic game elements**:
  - Random objects appear on the road
  - Score tracking for objects passed
  - Collision detection with visual feedback
- **Realistic engine sounds** that change with speed
- **Auto-stop safety feature** if no hand is detected
- **Multiple camera support** with camera selection interface

## Requirements

- Python 3.7+
- Webcam
- The following Python packages:
  - opencv-python
  - mediapipe
  - pygame
  - numpy

## Installation

1. Clone this repository or download the files
2. Install required packages:

```bash
pip install -r requirements.txt
```

## How to Use

1. Run the application:

```bash
python app.py
```

2. The system will scan for available cameras and let you select one
3. Two windows will appear:
   - Hand tracking window showing your hand with detection points
   - Game window showing the car and road

### Controls

- **Speed**: Raise your thumb higher to accelerate, lower to slow down
- **Direction**: 
  - Tilt your hand so that your index finger is higher than your pinky to turn left
  - Tilt your hand so that your pinky is higher than your index finger to turn right
  - Keep your fingers at the same level to go straight

### Gameplay

- Random objects will appear on the road
- Navigate around them to increase your score
- Collisions will reduce your score
- The car will automatically slow down if no hand is detected for 3 seconds

## Customization

You can modify various aspects of the game by editing `app.py`:

- Change the road width/position
- Adjust sensitivity of hand controls
- Change car size and appearance
- Modify game scoring system
- Add or modify sound effects

## Troubleshooting

- **Camera not working**: Make sure your webcam is properly connected and not being used by another application
- **No sound**: Check that your system audio is working and not muted
- **Gesture detection issues**: Try adjusting lighting conditions or moving your hand closer to the camera

## Technical Details

- Hand landmark detection using MediaPipe's Hand solution
- PyGame for rendering the car and game elements
- Custom sound synthesis for engine sounds
- Real-time collision detection using AABB (Axis-Aligned Bounding Box) method

## Credits

This project uses the following technologies:
- [MediaPipe](https://mediapipe.dev/) for hand detection
- [OpenCV](https://opencv.org/) for image processing
- [Pygame](https://www.pygame.org/) for game rendering
- [NumPy](https://numpy.org/) for numerical operations

## License

This project is available for educational and personal use.

---

Enjoy controlling your virtual car with hand gestures!
