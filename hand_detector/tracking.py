import cv2
import mediapipe as mp

class HandDetector:
    def __init__(self, mode=False, max_hands=2, detection_con=0.5, track_con=0.5):
        self.mode = mode
        self.max_hands = max_hands
        # Increase detection confidence for more stability
        self.detection_con = detection_con
        # Increase tracking confidence for better response
        self.track_con = track_con
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(self.mode, self.max_hands, self.detection_con, self.track_con)
        self.mp_draw = mp.solutions.drawing_utils
        self.prev_landmarks = []

    def find_hands(self, img, draw=True):
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.results = self.hands.process(img_rgb)
        if self.results.multi_hand_landmarks:
            for hand_lms in self.results.multi_hand_landmarks:
                if draw:
                    self.mp_draw.draw_landmarks(img, hand_lms, self.mp_hands.HAND_CONNECTIONS)
        return img

    def find_position(self, img, hand_no=0, draw=True):
        landmark_list = []
        h, w, c = img.shape
        
        if self.results.multi_hand_landmarks:
            try:
                my_hand = self.results.multi_hand_landmarks[hand_no]
                for id, lm in enumerate(my_hand.landmark):
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    landmark_list.append([id, cx, cy])
                    if draw:
                        cv2.circle(img, (cx, cy), 7, (255, 0, 255), cv2.FILLED)
            except IndexError:
                # Handle case when hand_no is out of range
                pass
                
        # Add position smoothing to reduce jitter
        if len(landmark_list) > 0 and hasattr(self, 'prev_landmarks') and len(self.prev_landmarks) > 0:
            for i in range(len(landmark_list)):
                if i < len(self.prev_landmarks):
                    # Apply smoothing (80% current position, 20% previous position)
                    landmark_list[i][1] = int(0.8 * landmark_list[i][1] + 0.2 * self.prev_landmarks[i][1])
                    landmark_list[i][2] = int(0.8 * landmark_list[i][2] + 0.2 * self.prev_landmarks[i][2])
        
        # Store current landmarks for next frame
        self.prev_landmarks = landmark_list.copy()
        
        return landmark_list
    
    # Add a new method to detect movement speed
    def calculate_movement(self, current_pos, prev_pos):
        if not prev_pos or not current_pos:
            return 0
            
        # Calculate distance between current and previous positions
        dx = current_pos[1] - prev_pos[1]
        dy = current_pos[2] - prev_pos[2]
        distance = (dx**2 + dy**2)**0.5
        return distance