import cv2
import mediapipe as mp
import numpy as np

class HandGestureDetector:
    """Class to detect hand gestures and convert them to car control signals."""
    
    def __init__(self):
        """Initialize the hand gesture detector with MediaPipe."""
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,  # Track only one hand for simplicity
            min_detection_confidence=0.4,  # Lowered from 0.5 to increase sensitivity
            min_tracking_confidence=0.4    # Lowered from 0.5 to increase sensitivity
        )
        self.mp_draw = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        # Control state
        self.prev_steering = 0
        self.steering_smoothing = 0.3  # Reduced from 0.5 to give more weight to current movements
        
    def detect_gestures(self, frame):
        """
        Detect hand gestures in the given frame and return control signals.
        
        Args:
            frame: CV2 image frame
            
        Returns:
            controls: Dictionary with control values (steering, throttle, braking, boost)
            processed_frame: Frame with visualization of detected hands and controls
        """
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process the frame with MediaPipe
        results = self.hands.process(rgb_frame)
        
        # Default controls
        controls = {
            'steering': 0.0,  # -1.0 (full left) to 1.0 (full right)
            'throttle': 0.0,  # 0.0 to 1.0
            'braking': False,
            'boost': False
        }
        
        # Draw hand landmarks and extract control information
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Draw hand landmarks on the frame
                self.mp_draw.draw_landmarks(
                    frame,
                    hand_landmarks,
                    self.mp_hands.HAND_CONNECTIONS,
                    self.mp_drawing_styles.get_default_hand_landmarks_style(),
                    self.mp_drawing_styles.get_default_hand_connections_style()
                )
                
                # Extract control values from hand landmarks
                controls = self._extract_controls_from_landmarks(hand_landmarks, controls)
        
        # Add visualization of controls to the frame
        self._add_control_visualization(frame, controls)
        
        return controls, frame
    
    def _extract_controls_from_landmarks(self, landmarks, controls):
        """
        Extract control values from hand landmarks.
        
        This function analyzes the position and orientation of the hand
        to determine steering, throttle, braking and boost controls.
        """
        # Get hand positions
        wrist = landmarks.landmark[0]
        thumb_tip = landmarks.landmark[4]
        index_tip = landmarks.landmark[8]
        middle_tip = landmarks.landmark[12]
        ring_tip = landmarks.landmark[16]
        pinky_tip = landmarks.landmark[20]
        
        # Calculate steering based on hand angle
        # Use wrist and middle finger position to determine angle
        dx = middle_tip.x - wrist.x
        dy = middle_tip.y - wrist.y
        
        # Calculate angle in degrees (-180 to 180)
        angle = np.degrees(np.arctan2(dy, dx))
        
        # Convert angle to steering value (-1.0 to 1.0)
        # Adjust these thresholds based on your desired sensitivity
        if -45 <= angle <= 45:  # Right
            steering = (angle + 45) / 90  # 0.0 to 1.0
        elif 45 < angle <= 135:  # Down
            steering = 0.0
        elif -135 <= angle < -45:  # Up
            steering = 0.0
        else:  # Left
            steering = (angle - 180) / 90 if angle > 0 else (angle + 180) / 90  # -1.0 to 0.0
        
        # Apply smoothing to steering
        steering = self.prev_steering * self.steering_smoothing + steering * (1 - self.steering_smoothing)
        self.prev_steering = steering
        controls['steering'] = steering
        
        # Calculate throttle based on hand height (lower hand = more throttle)
        # Normalize to screen space (0.0 to 1.0)
        throttle = 1.0 - wrist.y  # Higher hand position = less throttle
        controls['throttle'] = max(0.0, min(1.0, throttle))
        
        # Detect braking gesture (closed fist - all fingers curled)
        finger_tips_y = [index_tip.y, middle_tip.y, ring_tip.y, pinky_tip.y]
        finger_mcp_y = [landmarks.landmark[5].y, landmarks.landmark[9].y, 
                        landmarks.landmark[13].y, landmarks.landmark[17].y]
        
        # Check if all fingertips are below their MCPs (fingers curled)
        fingers_curled = all(tip_y > mcp_y for tip_y, mcp_y in zip(finger_tips_y, finger_mcp_y))
        if fingers_curled:
            controls['braking'] = True
            controls['throttle'] = 0.0  # No throttle when braking
        
        # Detect boost gesture (thumb extended)
        thumb_extended = thumb_tip.x > landmarks.landmark[2].x  # Thumb tip is to the right of thumb IP
        if thumb_extended and not fingers_curled:
            controls['boost'] = True
        
        return controls
    
    def _add_control_visualization(self, frame, controls):
        """Add visual indicators of the current controls to the frame."""
        h, w, _ = frame.shape
        
        # Draw steering indicator
        steering = controls['steering']
        cv2.line(frame, (w//2, h-50), (w//2, h-20), (200, 200, 200), 2)
        steer_pos = int(w//2 + steering * 100)  # Scale steering to pixels
        cv2.circle(frame, (steer_pos, h-35), 10, (0, 0, 255), -1)
        
        # Draw throttle indicator
        throttle = controls['throttle']
        throttle_h = int(h - 150 - throttle * 100)
        cv2.rectangle(frame, (w-50, h-150), (w-30, h-50), (200, 200, 200), 2)
        cv2.rectangle(frame, (w-50, throttle_h), (w-30, h-50), (0, 255, 0), -1)
        
        # Draw brake and boost indicators
        brake_color = (0, 0, 255) if controls['braking'] else (200, 200, 200)
        cv2.circle(frame, (50, h-50), 15, brake_color, -1)
        cv2.putText(frame, "BRAKE", (30, h-20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, brake_color, 2)
        
        boost_color = (255, 255, 0) if controls['boost'] else (200, 200, 200)
        cv2.circle(frame, (120, h-50), 15, boost_color, -1)
        cv2.putText(frame, "BOOST", (100, h-20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, boost_color, 2)
        
        # Draw instructions
        cv2.putText(frame, "Tilt hand left/right to steer", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, "Raise/lower hand for throttle", (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, "Make a fist to brake", (10, 90), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, "Extend thumb for boost", (10, 120), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
