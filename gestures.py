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
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        # Store previous hand positions for motion detection
        self.prev_landmarks = None
        self.gesture_history = []  # Store recent gestures for smoothing
        self.history_size = 5
        
        # Control state with improved smoothing
        self.prev_steering = 0
        self.prev_throttle = 0
        self.steering_smoothing = 0.6  # Higher value for smoother steering
        self.throttle_smoothing = 0.5  # Throttle smoothing
        
        # Add state flags for gestures
        self.braking_active = False
        self.boost_active = False
        
        # Frame counter for stabilization
        self.stable_frames_required = 3  # Number of frames required before changing status
        self.brake_stable_count = 0
        self.boost_stable_count = 0
        
        # Add class for marking relevant parts on screen
        self.debug_mode = True
        
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
                    frame, 
                    hand_landmarks, 
                    self.mp_hands.HAND_CONNECTIONS,
                    self.mp_drawing_styles.get_default_hand_landmarks_style(),
                    self.mp_drawing_styles.get_default_hand_connections_style())
        
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
                - steering: float, -1.0 (left) to 1.0 (right)
                - throttle: float, 0.0 to 1.0
                - braking: bool, True if brake gesture detected
                - boost: bool, True if boost gesture detected
        """
        # Process frame and get landmarks
        processed_frame = self.process_frame(frame)
        landmarks_list = self.get_landmarks()
        
        # Default control values with higher default values
        controls = {
            'steering': 0.0,  # -1.0 (full left) to 1.0 (full right)
            'throttle': 0.2,  # Default small throttle value so car moves
            'braking': False,
            'boost': False,
            'gesture_name': 'No hand detected'
        }
        
        # If no hands detected, update boost and brake status
        if not landmarks_list:
            # If no hand detected, cancel boost and check if braking
            self.boost_active = False
            self.boost_stable_count = 0
            
            # Gradually reset braking
            if self.brake_stable_count > 0:
                self.brake_stable_count -= 1
            else:
                self.braking_active = False
                
            controls['braking'] = self.braking_active
            return controls, processed_frame
        
        # Use the first hand detected
        landmarks = landmarks_list[0]
        
        # Extract hand positions for improved control detection
        wrist_pos = landmarks[0]
        thumb_tip = landmarks[4]
        index_tip = landmarks[8]
        middle_tip = landmarks[12]
        ring_tip = landmarks[16]
        pinky_tip = landmarks[20]
        
        # Get finger base positions
        index_mcp = landmarks[5]
        middle_mcp = landmarks[9]
        ring_mcp = landmarks[13]
        pinky_mcp = landmarks[17]
        
        h, w, _ = self.frame_shape
        
        # Calculate steering based on hand angle
        dx = middle_tip[0] - wrist_pos[0]
        dy = middle_tip[1] - wrist_pos[1]
        
        # Calculate hand angle in degrees
        hand_angle = np.degrees(np.arctan2(dy, dx))
        
        # Debug visualization for hand angle
        if self.debug_mode:
            # Convert landmarks to pixel coordinates
            wrist_px = (wrist_pos[0], wrist_pos[1])
            middle_px = (middle_tip[0], middle_tip[1])
            
            # Draw line showing hand orientation
            cv2.line(processed_frame, wrist_px, middle_px, (0, 255, 255), 2)
            
            # Show angle text
            cv2.putText(processed_frame, f"Angle: {hand_angle:.1f}", 
                       (10, 280), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        # Improved steering calculation - mapped to -1 to 1 range
        raw_steering = 0.0
        
        # Hand angle ranges for improved steering control
        if -45 <= hand_angle <= 45:  # Horizontal right hand
            # Map -45..45 degrees to 0..1 (right turn)
            raw_steering = hand_angle / 45.0
        elif hand_angle > 135 or hand_angle < -135:  # Horizontal left hand
            # Map 135..180/-180..-135 degrees to -1..0 (left turn)
            if (hand_angle > 0):
                raw_steering = (hand_angle - 180) / 45.0
            else:
                raw_steering = (hand_angle + 180) / 45.0
        else:
            # Vertical hand (approximate straight)
            raw_steering = 0.0
        
        # Apply non-linear mapping for finer control near center
        raw_steering = np.sign(raw_steering) * (raw_steering ** 2)
        
        # Apply smoothing for more stable steering
        steering = self.prev_steering * self.steering_smoothing + raw_steering * (1 - self.steering_smoothing)
        self.prev_steering = steering
        controls['steering'] = steering
        
        # Calculate throttle based on hand height (higher hand = more throttle)
        # Convert y position to normalized value (1.0 - y gives higher throttle when hand is higher)
        raw_throttle = 1.0 - (wrist_pos[1] / h)
        
        # Apply non-linear mapping for better control
        raw_throttle = raw_throttle ** 1.5  # Exponential curve
        
        # Limit throttle to valid range and apply smoothing
        raw_throttle = max(0.0, min(1.0, raw_throttle))
        throttle = self.prev_throttle * self.throttle_smoothing + raw_throttle * (1 - self.throttle_smoothing)
        self.prev_throttle = throttle
        controls['throttle'] = throttle
        
        # Detect braking - check if fingers are curled (fist)
        index_curled = index_tip[1] > index_mcp[1]
        middle_curled = middle_tip[1] > middle_mcp[1]
        ring_curled = ring_tip[1] > ring_mcp[1]
        pinky_curled = pinky_tip[1] > pinky_mcp[1]
        
        # Calculate fist (all fingers curled)
        fist_detected = index_curled and middle_curled and ring_curled and pinky_curled
        
        # Update brake stable counter
        if fist_detected:
            self.brake_stable_count = min(self.stable_frames_required, self.brake_stable_count + 1)
            if self.brake_stable_count >= self.stable_frames_required:
                self.braking_active = True
                controls['gesture_name'] = 'Fist (Braking)'
                self.draw_gesture_text(processed_frame, "BRAKING!", (255, 0, 0))
        else:
            # Gradually reduce stability counter
            if self.brake_stable_count > 0:
                self.brake_stable_count -= 1
            else:
                self.braking_active = False
        
        controls['braking'] = self.braking_active
        
        # Detect boost - check if thumb is up and others are curled
        thumb_extended = thumb_tip[1] < wrist_pos[1]  # Thumb is higher than wrist
        
        boost_detected = thumb_extended and index_curled and middle_curled and ring_curled and pinky_curled
        
        # Update boost stable counter
        if boost_detected:
            self.boost_stable_count = min(self.stable_frames_required, self.boost_stable_count + 1)
            if self.boost_stable_count >= self.stable_frames_required:
                self.boost_active = True
                controls['boost'] = True
                controls['throttle'] = 1.0  # Maximum throttle
                controls['gesture_name'] = 'Boost (Speed Up)'
                self.draw_gesture_text(processed_frame, "BOOST ACTIVATED!", (0, 255, 0))
        else:
            # Gradually reduce stability counter
            if self.boost_stable_count > 0:
                self.boost_stable_count -= 1
            else:
                self.boost_active = False
        
        controls['boost'] = self.boost_active
        
        # If neither braking nor boosting, check for stop gesture
        if not self.braking_active and not self.boost_active and self.is_stop_gesture(landmarks):
            controls['braking'] = True
            controls['gesture_name'] = 'Stop (Braking)'
            self.draw_gesture_text(processed_frame, "STOP GESTURE - BRAKING!", (255, 0, 0))
        
        # Add visualization of controls
        self._add_control_visualization(processed_frame, controls)
        
        return controls, processed_frame
    
    def _add_control_visualization(self, frame, controls):
        """Add visual indicators of the current controls to the frame."""
        h, w, _ = frame.shape
        
        # Draw background panel for controls
        panel_height = 150
        panel_y = h - panel_height - 10
        cv2.rectangle(frame, (10, panel_y), (250, h - 10), (230, 230, 230), -1)
        cv2.rectangle(frame, (10, panel_y), (250, h - 10), (0, 0, 0), 1)
        
        # Draw steering indicator
        steering = controls['steering']
        cv2.putText(frame, "Steering:", (20, panel_y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        
        steer_center_x = 130
        steer_width = 100
        steer_y = panel_y + 30
        
        # Steering box
        cv2.rectangle(frame, 
                      (steer_center_x - steer_width//2, steer_y - 15), 
                      (steer_center_x + steer_width//2, steer_y + 15), 
                      (200, 200, 200), -1)
        cv2.rectangle(frame, 
                      (steer_center_x - steer_width//2, steer_y - 15), 
                      (steer_center_x + steer_width//2, steer_y + 15), 
                      (0, 0, 0), 1)
        
        # Steering indicator
        steer_pos = int(steer_center_x + steering * steer_width/2)
        cv2.circle(frame, (steer_pos, steer_y), 10, (0, 0, 255), -1)
        
        # Draw throttle indicator
        throttle = controls['throttle']
        cv2.putText(frame, "Throttle:", (20, panel_y + 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        
        throttle_x = 130
        throttle_height = 50
        throttle_width = 30
        throttle_y = panel_y + 50
        
        # Throttle box
        cv2.rectangle(frame, 
                     (throttle_x, throttle_y), 
                     (throttle_x + throttle_width, throttle_y + throttle_height), 
                     (200, 200, 200), -1)
        cv2.rectangle(frame, 
                     (throttle_x, throttle_y), 
                     (throttle_x + throttle_width, throttle_y + throttle_height), 
                     (0, 0, 0), 1)
        
        # Throttle fill
        filled_height = int(throttle_height * throttle)
        cv2.rectangle(frame, 
                     (throttle_x, throttle_y + throttle_height - filled_height), 
                     (throttle_x + throttle_width, throttle_y + throttle_height), 
                     (0, 255, 0), -1)
        
        # Draw brake and boost indicators
        brake_color = (0, 0, 255) if controls['braking'] else (200, 200, 200)
        cv2.circle(frame, (50, panel_y + 120), 15, brake_color, -1)
        cv2.putText(frame, "Brake", (30, panel_y + 140), cv2.FONT_HERSHEY_SIMPLEX, 0.6, brake_color, 2)
        
        boost_color = (255, 165, 0) if controls['boost'] else (200, 200, 200)
        cv2.circle(frame, (120, panel_y + 120), 15, boost_color, -1)
        cv2.putText(frame, "Boost", (100, panel_y + 140), cv2.FONT_HERSHEY_SIMPLEX, 0.6, boost_color, 2)
    
    def smooth_controls(self, current_controls):
        """Apply smoothing to controls to prevent jerky movements."""
        if len(self.gesture_history) < 2:
            return current_controls
        
        # Average speed over recent history (excluding current control)
        if not current_controls['braking'] and not current_controls['boost']:
            speed_values = [controls['speed'] for controls in self.gesture_history[:-1]]
            avg_speed = sum(speed_values) / len(speed_values) if speed_values else 0
            # Weighted average: 90% current + 10% history (changed from 70/30)
            current_controls['speed'] = 0.9 * current_controls['speed'] + 0.1 * avg_speed
        
        # Smooth direction changes
        if not current_controls['braking']:
            # Only check the last 2 frames instead of 3 for faster direction response
            direction_values = [controls['direction'] for controls in self.gesture_history[-2:]]
            if len(direction_values) >= 2:
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

class EnhancedHandGestureDetector:
    """Enhanced class to detect hand gestures and convert them to car control signals."""
    
    def __init__(self):
        """Initialize the hand gesture detector with MediaPipe."""
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,  # Track only one hand for simplicity
            min_detection_confidence=0.6,  # Increased from 0.4 for more reliable detection
            min_tracking_confidence=0.5    # Increased from 0.4 for better tracking
        )
        self.mp_draw = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        # Control state with improved smoothing
        self.prev_steering = 0
        self.prev_throttle = 0
        self.steering_smoothing = 0.5  # Balanced value for stable but responsive steering
        self.throttle_smoothing = 0.4  # Slightly faster response for throttle
        
        # State tracking for gesture stability
        self.gesture_history = []
        self.history_size = 5
        self.last_command = None
        self.command_stability_count = 0
        self.stability_threshold = 3  # Require this many consistent readings
        
        # Debug and display options
        self.debug_mode = True
        
    def detect_gestures(self, frame):
        """
        Detect hand gestures in the given frame and return control signals.
        
        Args:
            frame: CV2 image frame
            
        Returns:
            controls: Dictionary with control values (steering, throttle, braking, boost)
            processed_frame: Frame with visualization of detected hands and controls
        """
        try:
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Process the frame with MediaPipe
            results = self.hands.process(rgb_frame)
            
            # Default controls
            controls = {
                'steering': 0.0,     # -1.0 (full left) to 1.0 (full right)
                'throttle': 0.0,     # 0.0 to 1.0
                'braking': False,
                'boost': False,
                'gesture_name': 'No hand detected',
                'speed': 0.0,        # For compatibility with Car.update()
                'direction': 0.0     # For compatibility with Car.update()
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
                    controls = self._extract_controls_from_landmarks(hand_landmarks, frame, controls)
            else:
                # Reset stability counter when no hand detected
                self.command_stability_count = 0
                
            # Add visualization of current controls to the frame
            self._add_control_visualization(frame, controls)
            
            # Add speed and direction mappings for compatibility with the Car class
            controls['speed'] = controls['throttle']
            controls['direction'] = controls['steering']
            
            return controls, frame
        except Exception as e:
            print(f"Error in gesture detection: {e}")
            return {
                'steering': 0.0,
                'throttle': 0.0,
                'braking': False,
                'boost': False,
                'gesture_name': 'Error',
                'speed': 0.0,
                'direction': 0.0
            }, frame
    
    def _extract_controls_from_landmarks(self, landmarks, frame, controls):
        """
        Extract control values from hand landmarks with improved detection.
        """
        # Convert landmarks to more accessible format
        h, w, c = frame.shape
        landmark_points = []
        for lm in landmarks.landmark:
            # Ensure x, y are real numbers (not complex)
            x, y = float(lm.x * w), float(lm.y * h)
            landmark_points.append((int(x), int(y)))
        
        # Get key points
        wrist = landmark_points[0]
        thumb_tip = landmark_points[4]
        index_tip = landmark_points[8]
        middle_tip = landmark_points[12]
        ring_tip = landmark_points[16]
        pinky_tip = landmark_points[20]
        
        # Get MCP (knuckle) positions for detecting finger curling
        thumb_mcp = landmark_points[2]
        index_mcp = landmark_points[5]
        middle_mcp = landmark_points[9]
        ring_mcp = landmark_points[13]
        pinky_mcp = landmark_points[17]
        
        # ==================== STEERING DETECTION ====================
        # Calculate hand rotation for steering
        # Using index and pinky base for more stable steering detection
        dx = float(landmark_points[17][0] - landmark_points[5][0])  # Pinky MCP - Index MCP x-distance
        dy = float(landmark_points[17][1] - landmark_points[5][1])  # Pinky MCP - Index MCP y-distance
        
        # Calculate angle of hand rotation
        hand_angle = np.degrees(np.arctan2(dy, dx))
        
        # Map angle to steering value
        # Neutral hand orientation (fingers pointing up) is around -90 degrees
        # We'll map -135° to -45° (90° range) to our full steering range
        if -135 <= hand_angle <= -45:
            # Normalize to -1 to 1 steering range
            # -135° maps to -1 (full left), -90° to 0 (center), -45° to 1 (full right)
            raw_steering = (hand_angle + 90) / 45
        else:
            # If hand is rotated extremely, use max values
            raw_steering = -1 if hand_angle < -135 else 1
        
        # Apply smoothing for more stable steering
        steering = self.prev_steering * self.steering_smoothing + raw_steering * (1 - self.steering_smoothing)
        steering = max(-1.0, min(1.0, steering))  # Clamp to valid range
        self.prev_steering = steering
        controls['steering'] = steering
        
        # Draw steering indicator line on frame if in debug mode
        if self.debug_mode:
            steer_start = wrist
            steer_length = 100
            steer_angle_rad = np.radians(hand_angle)
            steer_end = (
                int(steer_start[0] + steer_length * np.cos(steer_angle_rad)),
                int(steer_start[1] + steer_length * np.sin(steer_angle_rad))
            )
            cv2.line(frame, steer_start, steer_end, (0, 255, 255), 2)
            cv2.putText(frame, f"Angle: {hand_angle:.1f}", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.putText(frame, f"Steering: {steering:.2f}", (10, 60), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        # ==================== THROTTLE DETECTION ====================
        # Detect throttle based on overall hand height (y-position)
        # Lower hand position = more throttle
        normalized_y = 1.0 - (float(wrist[1]) / float(h))  # Invert so higher hand = lower value
        raw_throttle = normalized_y
        
        # Apply non-linear mapping for better control (squared for more precision at low speeds)
        raw_throttle = float(raw_throttle ** 1.5)  # Exponential curve gives more control
        
        # Apply smoothing and clamp to valid range
        throttle = self.prev_throttle * self.throttle_smoothing + raw_throttle * (1 - self.throttle_smoothing)
        throttle = max(0.0, min(1.0, throttle))  # Clamp to valid range
        self.prev_throttle = throttle
        controls['throttle'] = throttle
        
        # ==================== GESTURE DETECTION ====================
        # Detect gesture based on finger positions
        # First check if fingers are curled (thumb tip closer to wrist than knuckle)
        index_curled = float(index_tip[1]) > float(index_mcp[1])
        middle_curled = float(middle_tip[1]) > float(middle_mcp[1])
        ring_curled = float(ring_tip[1]) > float(ring_mcp[1])
        pinky_curled = float(pinky_tip[1]) > float(pinky_mcp[1])
        
        # Detect thumb extended (y-coordinate higher than wrist)
        thumb_extended = float(thumb_tip[1]) < float(wrist[1]) - float(h*0.1)  # Thumb must be significantly higher
        
        # Detect fist (all fingers curled)
        fist_detected = index_curled and middle_curled and ring_curled and pinky_curled
        
        # Detect stop gesture (all fingers extended and spread)
        # We use open palm = stop
        all_fingers_extended = not (index_curled or middle_curled or ring_curled or pinky_curled)
        
        # Detect specialized gestures
        # Detect boost gesture (thumb up, all other fingers curled)
        boost_gesture = thumb_extended and index_curled and middle_curled and ring_curled and pinky_curled
        
        # Detect braking gesture (fist)
        brake_gesture = fist_detected and not thumb_extended
        
        # Set control commands based on detected gestures
        if boost_gesture:
            controls['gesture_name'] = 'Boost'
            controls['boost'] = True
            controls['throttle'] = 1.0  # Full throttle when boosting
            self._update_command_stability("FORWARD_BOOST")
        elif brake_gesture:
            controls['gesture_name'] = 'Brake'
            controls['braking'] = True
            controls['throttle'] = 0.0  # No throttle when braking
            self._update_command_stability("STOP")
        elif all_fingers_extended:
            controls['gesture_name'] = 'Stop'
            controls['braking'] = True  # Emergency stop with open palm
            controls['throttle'] = 0.0
            self._update_command_stability("STOP")
        else:
            # Regular driving with steering and throttle
            if abs(steering) > 0.3:  # Significant steering
                if steering < -0.3:
                    controls['gesture_name'] = 'Turning Left'
                    self._update_command_stability("LEFT")
                else:
                    controls['gesture_name'] = 'Turning Right'
                    self._update_command_stability("RIGHT")
            else:
                controls['gesture_name'] = 'Forward'
                self._update_command_stability("FORWARD")
                
        # Draw detected gesture name at the top of the frame
        cv2.putText(frame, f"Gesture: {controls['gesture_name']}", 
                   (frame.shape[1]//2 - 100, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
        return controls
        
    def _update_command_stability(self, command):
        """Track command stability to avoid jitter in command sending."""
        if command == self.last_command:
            self.command_stability_count += 1
        else:
            self.last_command = command
            self.command_stability_count = 1
            
    def get_stable_command(self):
        """Get the current command only if it's stable enough."""
        if self.command_stability_count >= self.stability_threshold:
            return self.last_command
        return None
    
    def _add_control_visualization(self, frame, controls):
        """Add visual indicators of the current controls to the frame."""
        h, w, _ = frame.shape
        
        # Draw background panel for controls
        panel_height = 120
        panel_y = h - panel_height - 10
        panel_width = 250
        cv2.rectangle(frame, (10, panel_y), (panel_width + 10, h - 10), (230, 230, 230), -1)
        cv2.rectangle(frame, (10, panel_y), (panel_width + 10, h - 10), (0, 0, 0), 1)
        
        # Draw steering indicator
        steering = controls['steering']
        cv2.putText(frame, "Steering:", (20, panel_y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        
        steer_center_x = 130
        steer_width = 100
        steer_y = panel_y + 30
        
        # Steering box
        cv2.rectangle(frame, 
                      (steer_center_x - steer_width//2, steer_y - 15), 
                      (steer_center_x + steer_width//2, steer_y + 15), 
                      (200, 200, 200), -1)
        cv2.rectangle(frame, 
                      (steer_center_x - steer_width//2, steer_y - 15), 
                      (steer_center_x + steer_width//2, steer_y + 15), 
                      (0, 0, 0), 1)
        
        # Steering indicator
        steer_pos = int(steer_center_x + steering * steer_width/2)
        cv2.circle(frame, (steer_pos, steer_y), 10, (0, 0, 255), -1)
        
        # Draw throttle indicator
        throttle = controls['throttle']
        cv2.putText(frame, "Throttle:", (20, panel_y + 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        
        throttle_x = 130
        throttle_height = 50
        throttle_width = 30
        throttle_y = panel_y + 50
        
        # Throttle box
        cv2.rectangle(frame, 
                     (throttle_x, throttle_y), 
                     (throttle_x + throttle_width, throttle_y + throttle_height), 
                     (200, 200, 200), -1)
        cv2.rectangle(frame, 
                     (throttle_x, throttle_y), 
                     (throttle_x + throttle_width, throttle_y + throttle_height), 
                     (0, 0, 0), 1)
        
        # Throttle fill
        filled_height = int(throttle_height * throttle)
        cv2.rectangle(frame, 
                     (throttle_x, throttle_y + throttle_height - filled_height), 
                     (throttle_x + throttle_width, throttle_y + throttle_height), 
                     (0, 255, 0), -1)
        
        # Draw brake and boost indicators
        brake_color = (0, 0, 255) if controls['braking'] else (200, 200, 200)
        cv2.circle(frame, (50, panel_y + 110), 15, brake_color, -1)
        cv2.putText(frame, "Brake", (30, panel_y + 140), cv2.FONT_HERSHEY_SIMPLEX, 0.6, brake_color, 2)
        
        boost_color = (255, 165, 0) if controls['boost'] else (200, 200, 200)
        cv2.circle(frame, (120, panel_y + 110), 15, boost_color, -1)
        cv2.putText(frame, "Boost", (100, panel_y + 140), cv2.FONT_HERSHEY_SIMPLEX, 0.6, boost_color, 2)
        
        # Add stability indicator
        stability_x = panel_width - 40
        cv2.putText(frame, f"Stability: {self.command_stability_count}/{self.stability_threshold}", 
                   (stability_x - 80, panel_y + 110), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)