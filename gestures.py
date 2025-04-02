# gestures.py - Enhanced hand gesture detection

import cv2
import numpy as np
import mediapipe as mp

class HandGestureDetector:
    def __init__(self, max_hands=1, min_detection_confidence=0.7):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            max_num_hands=max_hands, 
            min_detection_confidence=min_detection_confidence
        )
        self.mp_draw = mp.solutions.drawing_utils
        
        # Store previous hand positions for motion detection
        self.prev_landmarks = None
        self.gesture_history = []  # Store recent gestures for smoothing
        self.history_size = 5
        
    def process_frame(self, frame):
        """Process a frame and detect hand landmarks."""
        # Convert image to RGB (required by mediapipe)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process the image for hand detection
        self.results = self.hands.process(frame_rgb)
        
        self.frame_shape = frame.shape
        
        # Draw hand landmarks on the frame if hands are detected
        if self.results.multi_hand_landmarks:
            for hand_landmarks in self.results.multi_hand_landmarks:
                self.mp_draw.draw_landmarks(
                    frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
        
        return frame
    
    def get_landmarks(self):
        """Extract landmark positions from detected hands."""
        landmarks_list = []
        
        if self.results.multi_hand_landmarks:
            for hand_landmarks in self.results.multi_hand_landmarks:
                landmarks = []
                for lm in hand_landmarks.landmark:
                    h, w, c = self.frame_shape
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    landmarks.append([cx, cy])
                landmarks_list.append(landmarks)
                
            # Update previous landmarks for motion detection
            self.prev_landmarks = landmarks_list[0] if landmarks_list else None
        else:
            self.prev_landmarks = None
            
        return landmarks_list
    
    def calculate_distance(self, point1, point2):
        """Calculate Euclidean distance between two points."""
        return np.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)
    
    def detect_gestures(self, frame):
        """
        Detect various hand gestures and return control values.
        
        Returns:
            dict: Control values including:
                - speed: float, 0.0 to 5.0
                - direction: int, -1 (left), 0 (straight), 1 (right)
                - braking: bool, True if brake gesture detected
                - boost: bool, True if boost gesture detected
                - gesture_name: str, name of the detected gesture
        """
        # Process frame and get landmarks
        processed_frame = self.process_frame(frame)
        landmarks_list = self.get_landmarks()
        
        # Default control values
        controls = {
            'speed': 0.0,
            'direction': 0,
            'braking': False,
            'boost': False,
            'gesture_name': 'No hand detected'
        }
        
        # If no hands detected, return default controls
        if not landmarks_list:
            return controls, processed_frame
        
        # Use the first hand detected
        landmarks = landmarks_list[0]
        
        # Check for different gestures
        if self.is_fist_gesture(landmarks):
            controls['braking'] = True
            controls['gesture_name'] = 'Fist (Braking)'
            self.draw_gesture_text(processed_frame, "BRAKING!", (255, 0, 0))
            
        elif self.is_stop_gesture(landmarks):
            controls['braking'] = True
            controls['gesture_name'] = 'Stop (Braking)'
            self.draw_gesture_text(processed_frame, "STOP GESTURE - BRAKING!", (255, 0, 0))
            
        elif self.is_boost_gesture(landmarks):
            controls['boost'] = True
            controls['speed'] = 5.0  # Maximum speed
            controls['gesture_name'] = 'Boost (Speed Up)'
            self.draw_gesture_text(processed_frame, "BOOST ACTIVATED!", (0, 255, 0))
            
        else:
            # Normal driving controls based on hand position
            thumb_tip = landmarks[4]
            wrist = landmarks[0]
            index_tip = landmarks[8]
            pinky_tip = landmarks[20]
            
            # Calculate speed based on thumb position (Y-axis)
            distance = wrist[1] - thumb_tip[1]  # Distance between thumb and wrist
            speed_factor = distance / 80  
            controls['speed'] = max(0, min(5, speed_factor))
            
            # Calculate direction based on hand tilt
            direction_delta = index_tip[0] - pinky_tip[0]
            if direction_delta > 30:
                controls['direction'] = 1  # Right
                direction_text = "Right"
            elif direction_delta < -30:
                controls['direction'] = -1  # Left
                direction_text = "Left"
            else:
                controls['direction'] = 0  # Straight
                direction_text = "Forward"
            
            controls['gesture_name'] = f'Driving ({direction_text})'
            
            # Display control values on frame
            cv2.putText(processed_frame, f"Speed: {controls['speed']:.1f}", 
                       (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(processed_frame, f"Direction: {direction_text}", 
                       (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # Add to gesture history for smoothing
        self.gesture_history.append(controls)
        if len(self.gesture_history) > self.history_size:
            self.gesture_history.pop(0)
        
        # Apply smoothing to controls
        return self.smooth_controls(controls), processed_frame
    
    def smooth_controls(self, current_controls):
        """Apply smoothing to controls to prevent jerky movements."""
        if len(self.gesture_history) < 2:
            return current_controls
        
        # Average speed over recent history (excluding current control)
        if not current_controls['braking'] and not current_controls['boost']:
            speed_values = [controls['speed'] for controls in self.gesture_history[:-1]]
            avg_speed = sum(speed_values) / len(speed_values)
            # Weighted average: 70% current + 30% history
            current_controls['speed'] = 0.7 * current_controls['speed'] + 0.3 * avg_speed
        
        # Smooth direction changes
        if not current_controls['braking']:
            # Only change direction if the same direction is held for multiple frames
            direction_values = [controls['direction'] for controls in self.gesture_history[-3:]]
            if len(direction_values) >= 3:
                # If all recent directions are the same, use that direction
                if all(d == direction_values[0] for d in direction_values):
                    current_controls['direction'] = direction_values[0]
        
        return current_controls
    
    def is_fist_gesture(self, landmarks):
        """
        Detect if the hand is making a fist gesture (all fingers closed).
        """
        if len(landmarks) < 21:  # Make sure we have all landmarks
            return False
        
        # Get fingertip and palm landmarks
        thumb_tip = landmarks[4]
        index_tip = landmarks[8]
        middle_tip = landmarks[12]
        ring_tip = landmarks[16]
        pinky_tip = landmarks[20]
        palm_center = landmarks[9]  # Middle of palm
        
        # Get finger base positions
        thumb_mcp = landmarks[2]
        index_mcp = landmarks[5]
        middle_mcp = landmarks[9]
        ring_mcp = landmarks[13]
        pinky_mcp = landmarks[17]
        
        # Calculate palm size to normalize distances
        palm_width = self.calculate_distance(index_mcp, pinky_mcp)
        
        # Check if all fingertips are close to the palm
        # Normalize distances by palm width for scale invariance
        thumb_closed = self.calculate_distance(thumb_tip, palm_center) / palm_width < 0.4
        index_closed = self.calculate_distance(index_tip, index_mcp) / palm_width < 0.45
        middle_closed = self.calculate_distance(middle_tip, middle_mcp) / palm_width < 0.45
        ring_closed = self.calculate_distance(ring_tip, ring_mcp) / palm_width < 0.45
        pinky_closed = self.calculate_distance(pinky_tip, pinky_mcp) / palm_width < 0.45
        
        return index_closed and middle_closed and ring_closed and pinky_closed
    
    def is_stop_gesture(self, landmarks):
        """
        Detect if the hand is making a stop sign gesture (palm facing camera with fingers extended).
        """
        if len(landmarks) < 21:
            return False
        
        # Get key landmark positions
        wrist = landmarks[0]
        thumb_tip = landmarks[4]
        index_tip = landmarks[8]
        middle_tip = landmarks[12]
        ring_tip = landmarks[16]
        pinky_tip = landmarks[20]
        
        # Get finger middle points (for calculating palm orientation)
        index_pip = landmarks[6]  # PIP joint of index finger
        pinky_pip = landmarks[18]  # PIP joint of pinky finger
        
        # Calculate palm size to normalize distances
        palm_width = self.calculate_distance(landmarks[5], landmarks[17])  # Index to pinky MCP
        
        # Check if all fingers are extended
        thumb_extended = self.calculate_distance(thumb_tip, wrist) > 0.5 * palm_width
        index_extended = self.calculate_distance(index_tip, wrist) > 0.8 * palm_width
        middle_extended = self.calculate_distance(middle_tip, wrist) > 0.8 * palm_width
        ring_extended = self.calculate_distance(ring_tip, wrist) > 0.7 * palm_width
        pinky_extended = self.calculate_distance(pinky_tip, wrist) > 0.6 * palm_width
        
        fingers_extended = index_extended and middle_extended and ring_extended and pinky_extended
        
        # Check if fingers are spread apart
        index_middle_spread = self.calculate_distance(index_tip, middle_tip) > 0.2 * palm_width
        middle_ring_spread = self.calculate_distance(middle_tip, ring_tip) > 0.2 * palm_width
        ring_pinky_spread = self.calculate_distance(ring_tip, pinky_tip) > 0.2 * palm_width
        
        fingers_spread = index_middle_spread and middle_ring_spread and ring_pinky_spread
        
        # Check if palm is facing the camera
        palm_facing = self.calculate_distance(index_pip, pinky_pip) > 0.6 * palm_width
        
        return fingers_extended and fingers_spread and palm_facing
    
    def is_boost_gesture(self, landmarks):
        """
        Detect if the hand is making a boost gesture (only index and middle fingers extended).
        """
        if len(landmarks) < 21:
            return False
        
        # Get fingertip, knuckle, and palm landmarks
        thumb_tip = landmarks[4]
        index_tip = landmarks[8]
        middle_tip = landmarks[12]
        ring_tip = landmarks[16]
        pinky_tip = landmarks[20]
        
        thumb_mcp = landmarks[2]  # Thumb MCP
        index_mcp = landmarks[5]  # Index MCP
        middle_mcp = landmarks[9]  # Middle MCP
        ring_mcp = landmarks[13]  # Ring MCP
        pinky_mcp = landmarks[17]  # Pinky MCP
        
        wrist = landmarks[0]
        
        # Calculate palm size to normalize distances
        palm_width = self.calculate_distance(index_mcp, pinky_mcp)
        
        # Check if index and middle fingers are extended
        index_extended = self.calculate_distance(index_tip, index_mcp) > 0.7 * palm_width
        middle_extended = self.calculate_distance(middle_tip, middle_mcp) > 0.7 * palm_width
        
        # Check if other fingers are closed
        thumb_closed = self.calculate_distance(thumb_tip, thumb_mcp) < 0.4 * palm_width
        ring_closed = self.calculate_distance(ring_tip, ring_mcp) < 0.4 * palm_width
        pinky_closed = self.calculate_distance(pinky_tip, pinky_mcp) < 0.4 * palm_width
        
        # Check if index and middle fingers are close together (peace sign)
        fingers_together = self.calculate_distance(index_tip, middle_tip) < 0.3 * palm_width
        
        return index_extended and middle_extended and thumb_closed and ring_closed and pinky_closed and not fingers_together
    
    def draw_gesture_text(self, frame, text, color):
        """Draw large text on frame for gesture notifications."""
        cv2.putText(frame, text, (50, 250), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)