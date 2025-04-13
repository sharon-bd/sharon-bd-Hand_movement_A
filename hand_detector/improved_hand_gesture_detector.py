import cv2
import mediapipe as mp
import numpy as np

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
            x, y = int(lm.x * w), int(lm.y * h)
            landmark_points.append((x, y))
        
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
        dx = landmark_points[17][0] - landmark_points[5][0]  # Pinky MCP - Index MCP x-distance
        dy = landmark_points[17][1] - landmark_points[5][1]  # Pinky MCP - Index MCP y-distance
        
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
        normalized_y = 1.0 - (wrist[1] / h)  # Invert so higher hand = lower value
        raw_throttle = normalized_y
        
        # Apply non-linear mapping for better control (squared for more precision at low speeds)
        raw_throttle = raw_throttle ** 1.5  # Exponential curve gives more control
        
        # Apply smoothing and clamp to valid range
        throttle = self.prev_throttle * self.throttle_smoothing + raw_throttle * (1 - self.throttle_smoothing)
        throttle = max(0.0, min(1.0, throttle))  # Clamp to valid range
        self.prev_throttle = throttle
        controls['throttle'] = throttle
        
        # ==================== GESTURE DETECTION ====================
        # Detect gesture based on finger positions
        # First check if fingers are curled (thumb tip closer to wrist than knuckle)
        index_curled = index_tip[1] > index_mcp[1]
        middle_curled = middle_tip[1] > middle_mcp[1]
        ring_curled = ring_tip[1] > ring_mcp[1]
        pinky_curled = pinky_tip[1] > pinky_mcp[1]
        
        # Detect thumb extended (y-coordinate higher than wrist)
        thumb_extended = thumb_tip[1] < wrist[1] - h*0.1  # Thumb must be significantly higher
        
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
        
        # Call the new function to detect stop sign gesture
        stop_sign_gesture = self._detect_stop_sign_gesture(landmark_points, frame)
        
        # Set control commands based on detected gestures
        if stop_sign_gesture:
            controls['gesture_name'] = 'Stop (Traffic Sign)'
            controls['braking'] = True  # Emergency stop with stop sign gesture
            controls['throttle'] = 0.0
            controls['boost'] = False
            self._update_command_stability("STOP")
            
            # Add prominent visualization of stop state
            cv2.putText(
                frame,
                "STOP SIGN DETECTED",
                (frame.shape[1]//2 - 150, 80),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 0, 255),
                2
            )
        elif boost_gesture:
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
    
    # ================== Improved STOP gesture detection ==================
    def _detect_stop_sign_gesture(self, landmark_points, frame):
        """
        Detect STOP sign gesture (open hand like a stop sign).
        Returns True if the gesture is detected, False otherwise.
        """
        h, w, _ = frame.shape
        
        # Key points
        wrist = landmark_points[0]
        thumb_tip = landmark_points[4]
        index_tip = landmark_points[8]
        middle_tip = landmark_points[12]
        ring_tip = landmark_points[16]
        pinky_tip = landmark_points[20]
        
        # Finger bases (joints)
        thumb_mcp = landmark_points[2]
        index_mcp = landmark_points[5]
        middle_mcp = landmark_points[9]
        ring_mcp = landmark_points[13]
        pinky_mcp = landmark_points[17]
        
        # 1. Check that all fingers are extended (not curled)
        # A finger is considered extended if the tip is further from the wrist than the joint
        # Calculate vectors from wrist to joint and from wrist to fingertip
        
        # 1.1 For index, middle, ring and pinky fingers
        finger_extended = []
        
        for tip, mcp in [(index_tip, index_mcp), 
                         (middle_tip, middle_mcp), 
                         (ring_tip, ring_mcp), 
                         (pinky_tip, pinky_mcp)]:
            # Distance from wrist to fingertip
            dist_tip = np.sqrt((tip[0] - wrist[0])**2 + (tip[1] - wrist[1])**2)
            # Distance from wrist to joint
            dist_mcp = np.sqrt((mcp[0] - wrist[0])**2 + (mcp[1] - wrist[1])**2)
            # Finger is extended if tip is further than joint
            finger_extended.append(dist_tip > dist_mcp * 1.2)  # Requires finger to be extended at least 20% more than joint
        
        # 1.2 For thumb (special case)
        thumb_dist_tip = np.sqrt((thumb_tip[0] - wrist[0])**2 + (thumb_tip[1] - wrist[1])**2)
        thumb_dist_mcp = np.sqrt((thumb_mcp[0] - wrist[0])**2 + (thumb_mcp[1] - wrist[1])**2)
        thumb_extended = thumb_dist_tip > thumb_dist_mcp
        
        # 2. Check that the hand is open and raised
        all_fingers_extended = all(finger_extended) and thumb_extended
        
        # 3. Check that fingers are spread at a reasonable distance from each other
        # Calculate distances between adjacent fingers
        finger_tips = [index_tip, middle_tip, ring_tip, pinky_tip]
        finger_spacings = []
        
        for i in range(len(finger_tips) - 1):
            spacing = np.sqrt((finger_tips[i][0] - finger_tips[i+1][0])**2 + 
                             (finger_tips[i][1] - finger_tips[i+1][1])**2)
            finger_spacings.append(spacing)
        
        # Fingers should be at similar distances from each other
        if len(finger_spacings) > 1:
            min_spacing = min(finger_spacings)
            max_spacing = max(finger_spacings)
            fingers_evenly_spaced = (max_spacing < min_spacing * 2.0)  # Spacings roughly equal
        else:
            fingers_evenly_spaced = True
        
        # Add debug info if needed
        if self.debug_mode:
            cv2.putText(frame, f"All Fingers Extended: {all_fingers_extended}", 
                       (10, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
            cv2.putText(frame, f"Fingers Spaced: {fingers_evenly_spaced}", 
                       (10, 260), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
            
            # Add info about each finger's extension
            fingers = ["Index", "Middle", "Ring", "Pinky", "Thumb"]
            extensions = finger_extended + [thumb_extended]
            for i, (finger, extended) in enumerate(zip(fingers, extensions)):
                color = (0, 255, 0) if extended else (0, 0, 255)
                cv2.putText(frame, f"{finger}: {extended}", 
                           (w - 150, 30 + i*20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        # STOP gesture is detected if all fingers are extended and reasonably spaced
        stop_gesture_detected = all_fingers_extended and fingers_evenly_spaced
        
        return stop_gesture_detected
        
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
