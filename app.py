import cv2
import numpy as np
import pygame
import mediapipe as mp
import time
import random
import os  # Add import for the os module

# Initialize hand detection modules
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)
mp_draw = mp.solutions.drawing_utils

# Initialize global variables
car_speed = 0
car_direction = 0  # 0 = straight, -1 = left, 1 = right
car_position = [400, 300]  # Initial car position - centered on screen
road_objects = []  # List to store objects on the road
objects_passed = 0  # Number of objects the car has passed
last_hand_detection_time = time.time()  # Track last time a hand was detected
auto_stopping = False  # Flag to indicate if auto-stopping is in progress
auto_stop_start_time = 0  # When auto-stopping began
engine_sound = None  # Will hold the engine sound object
diesel_idle_sound = None  # Will hold the diesel idle sound
diesel_revving_sound = None  # Will hold the diesel revving sound
current_sound_playing = None  # Tracks which sound is currently playing
collisions = 0  # Track number of collisions
last_collision_time = 0  # Track when the last collision occurred
collision_flash = False  # Flag for visual feedback on collision
sound_muted = False  # Flag to track if sound is muted
mute_button_rect = pygame.Rect(20, 550, 40, 40)  # Position and size of mute button
braking = False  # Flag to indicate if braking is in progress
brake_start_time = 0  # When braking began
original_brake_speed = 0  # Speed before braking started

# Function to detect if thumb is hidden in a fist
def is_thumb_hidden(landmarks):
    """
    Detect if the thumb is hidden in a fist by checking:
    1. All fingertips are close to the palm
    2. The thumb tip is not visible or is very close to the side of the palm
    """
    
    if len(landmarks) < 21:  # Make sure we have all landmarks
        return False
    
    # Get key landmark positions
    thumb_tip = landmarks[4]
    index_tip = landmarks[8]
    middle_tip = landmarks[12]
    ring_tip = landmarks[16]
    pinky_tip = landmarks[20]
    wrist = landmarks[0]
    palm_center = landmarks[9]  # Middle of palm
    
    # Calculate distances from fingertips to palm center
    thumb_palm_dist = calculate_distance(thumb_tip, palm_center)
    index_palm_dist = calculate_distance(index_tip, palm_center)
    middle_palm_dist = calculate_distance(middle_tip, palm_center)
    ring_palm_dist = calculate_distance(ring_tip, palm_center)
    pinky_palm_dist = calculate_distance(pinky_tip, palm_center)
    
    # Calculate palm size to normalize distances (distance from wrist to middle finger base)
    palm_size = calculate_distance(wrist, landmarks[9])
    
    # Normalize distances by palm size
    norm_thumb_dist = thumb_palm_dist / palm_size
    norm_index_dist = index_palm_dist / palm_size
    norm_middle_dist = middle_palm_dist / palm_size
    norm_ring_dist = ring_palm_dist / palm_size
    norm_pinky_dist = pinky_palm_dist / palm_size
    
    # Calculate thumb visibility
    thumb_side_dist = calculate_distance(thumb_tip, landmarks[1])  # Distance to side of palm
    norm_thumb_side_dist = thumb_side_dist / palm_size
    
    # Conditions for a closed fist with hidden thumb:
    # 1. All fingers are close to palm (closed fist)
    fingers_closed = (
        norm_index_dist < 0.5 and
        norm_middle_dist < 0.5 and
        norm_ring_dist < 0.5 and
        norm_pinky_dist < 0.5
    )
    
    # 2. Thumb is very close to side of palm or hidden
    thumb_hidden = norm_thumb_side_dist < 0.3 or norm_thumb_dist < 0.3
    
    return fingers_closed and thumb_hidden

# Function to detect if hand is making a stop sign gesture (palm facing camera)
def is_stop_gesture(landmarks):
    """
    Detect if the hand is making a stop sign gesture (palm facing camera with fingers extended)
    
    A stop sign gesture is characterized by:
    1. All fingers are extended and visible
    2. Fingers are spread apart reasonably
    3. Palm is facing the camera (based on relative positions of landmarks)
    """
    if len(landmarks) < 21:  # Make sure we have all landmarks
        return False
    
    # Get key landmark positions
    wrist = landmarks[0]
    thumb_tip = landmarks[4]
    index_tip = landmarks[8]
    middle_tip = landmarks[12]
    ring_tip = landmarks[16]
    pinky_tip = landmarks[20]
    
    # Get finger middle points (for calculating palm orientation)
    index_pip = landmarks[6]  # Middle point of index finger
    pinky_pip = landmarks[18]  # Middle point of pinky finger
    
    # Calculate palm size to normalize distances
    palm_width = calculate_distance(landmarks[5], landmarks[17])  # Distance between index and pinky MCP
    
    # Check if all fingers are extended (distance from fingertip to wrist should be significant)
    thumb_extended = calculate_distance(thumb_tip, wrist) > 0.5 * palm_width
    index_extended = calculate_distance(index_tip, wrist) > 0.8 * palm_width
    middle_extended = calculate_distance(middle_tip, wrist) > 0.8 * palm_width
    ring_extended = calculate_distance(ring_tip, wrist) > 0.7 * palm_width
    pinky_extended = calculate_distance(pinky_tip, wrist) > 0.6 * palm_width
    
    fingers_extended = thumb_extended and index_extended and middle_extended and ring_extended and pinky_extended
    
    # Check if fingers are spread apart (not in a fist)
    index_middle_spread = calculate_distance(index_tip, middle_tip) > 0.2 * palm_width
    middle_ring_spread = calculate_distance(middle_tip, ring_tip) > 0.2 * palm_width
    ring_pinky_spread = calculate_distance(ring_tip, pinky_tip) > 0.2 * palm_width
    
    fingers_spread = index_middle_spread and middle_ring_spread and ring_pinky_spread
    
    # Check if palm is facing the camera
    # For palm facing camera, the distance between index and pinky PIPs should be significant
    # compared to when the palm is sideways
    palm_facing = calculate_distance(index_pip, pinky_pip) > 0.6 * palm_width
    
    # Return True if all conditions are met
    return fingers_extended and fingers_spread and palm_facing

# Function to calculate distance between two points
def calculate_distance(point1, point2):
    return np.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)

# Function to detect hand gestures
def detect_hand_gestures(frame):
    global car_speed, car_direction, last_hand_detection_time, auto_stopping, auto_stop_start_time, braking, brake_start_time, original_brake_speed
    
    # Convert image to RGB (required by mediapipe)
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Process the image for hand detection
    results = hands.process(frame_rgb)
    
    # If hands are detected
    if results.multi_hand_landmarks:
        # Update the last hand detection time
        last_hand_detection_time = time.time()
        # Reset auto-stopping if a hand is detected
        auto_stopping = False
        
        # Get the first detected hand
        hand_landmarks = results.multi_hand_landmarks[0]
        
        # Draw hand landmarks on the image
        mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
        
        # Extract landmark positions
        landmarks = []
        for lm in hand_landmarks.landmark:
            h, w, c = frame.shape
            cx, cy = int(lm.x * w), int(lm.y * h)
            landmarks.append([cx, cy])
        
        # Check for stop gesture (palm facing camera)
        if is_stop_gesture(landmarks) and car_speed > 0.1:
            # If not already braking, start braking process
            if not braking:
                braking = True
                brake_start_time = time.time()
                original_brake_speed = car_speed
                print("Braking initiated - stop gesture detected")
                
            # Display stop gesture notification
            cv2.putText(frame, "STOP GESTURE DETECTED! BRAKING!", (50, 250), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        else:
            # Check for thumb hidden in fist (alternative braking method)
            is_braking_fist = is_thumb_hidden(landmarks)
            
            if is_braking_fist and car_speed > 0.1:
                # If not already braking, start braking process
                if not braking:
                    braking = True
                    brake_start_time = time.time()
                    original_brake_speed = car_speed
                    print("Braking initiated - thumb hidden in fist")
                    
                # Display braking notification
                cv2.putText(frame, "BRAKING!", (50, 250), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            elif not is_braking_fist and not is_stop_gesture(landmarks):
                # If no braking gesture is detected, stop braking
                braking = False
                
                # Set car speed based on thumb position (Y-axis)
                # The higher the thumb, the greater the speed
                thumb_tip = landmarks[4]
                wrist = landmarks[0]
                
                # Calculate speed with higher sensitivity
                distance = wrist[1] - thumb_tip[1]  # Distance between thumb and wrist
                
                # Increase sensitivity with a factor of 2.5 instead of 200
                speed_factor = distance / 80  
                
                # Limit speed to range 0-5, with minimum threshold
                car_speed = max(0, min(5, speed_factor))
                
                # Set direction based on hand angle
                index_tip = landmarks[8]  # Index finger tip
                pinky_tip = landmarks[20]  # Pinky finger tip
                
                # Calculate difference on X-axis to determine direction
                direction_delta = index_tip[0] - pinky_tip[0]
                
                if direction_delta > 30:
                    car_direction = 1  # Right
                elif direction_delta < -30:
                    car_direction = -1  # Left
                else:
                    car_direction = 0  # Straight
                
                # Add text to display speed and direction
                cv2.putText(frame, f"Speed: {car_speed:.1f}", (50, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                
                direction_text = "Left" if car_direction == -1 else "Right" if car_direction == 1 else "Forward"
                cv2.putText(frame, f"Direction: {direction_text}", (50, 100), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    else:
        # Check if no hand has been detected for more than 3 seconds
        current_time = time.time()
        time_without_hand = current_time - last_hand_detection_time
        
        # Display warning if no hand detected
        if time_without_hand >= 1.0:
            warning_color = (0, 0, 255)  # Red color for warning
            cv2.putText(frame, f"No hand detected for {time_without_hand:.1f}s", 
                        (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, warning_color, 2)
        
        # Start auto-stopping after 3 seconds without hands
        if time_without_hand >= 3.0 and not auto_stopping and car_speed > 0:
            auto_stopping = True
            auto_stop_start_time = current_time
    
    # Handle braking if needed
    if braking:
        current_time = time.time()
        brake_duration = 1.5  # 1.5 seconds to come to a complete stop
        elapsed_time = current_time - brake_start_time
        
        if elapsed_time >= brake_duration:
            # Car has completely stopped
            car_speed = 0
            braking = False
        else:
            # Gradually decrease speed over 1.5 seconds
            # Calculate deceleration factor (0 to 1)
            deceleration_factor = elapsed_time / brake_duration
            # Apply gradual speed reduction
            car_speed = original_brake_speed * (1 - deceleration_factor)
    
    # Handle auto-stopping if needed (only if not already braking)
    if auto_stopping and not braking:
        current_time = time.time()
        stop_duration = 2.0  # 2 seconds to come to a complete stop
        elapsed_time = current_time - auto_stop_start_time
        
        if elapsed_time >= stop_duration:
            # Car has completely stopped
            car_speed = 0
            auto_stopping = False
        else:
            # Gradually decrease speed over 2 seconds
            # Calculate deceleration factor (0 to 1)
            deceleration_factor = elapsed_time / stop_duration
            # Apply gradual speed reduction
            original_speed = car_speed
            car_speed = original_speed * (1 - deceleration_factor)
            
            # Display auto-stopping notification
            cv2.putText(frame, "Auto-stopping: No hand detected", 
                        (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    
    return frame

# Function to update car position
def update_car_position():
    global car_position
    
    # Update car position based on direction only if the car is moving
    if car_speed > 0:
        car_position[0] += car_direction * 5  # Change on X-axis
    # Keep Y position fixed at center of screen
    car_position[1] = 300
    
    # Keep the car within screen boundaries (only horizontal constraint)
    car_position[0] = max(50, min(750, car_position[0]))

# Function to create a new object on the road
def create_road_object():
    # Choose a random type of object (0, 1, or 2)
    object_type = random.randint(0, 2)
    # Set random position on the road (between 320 and 480 on X-axis)
    x_pos = random.randint(320, 480)
    # Object starts at the top of the screen (outside view)
    y_pos = -50
    # Set random color for the object
    color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    
    return {
        'type': object_type,
        'position': [x_pos, y_pos],
        'color': color,
        'passed': False,  # Whether the car has passed this object
        'size': random.randint(10, 30)  # Random size
    }

# Function to update road objects
def update_road_objects():
    global road_objects, objects_passed, collisions, last_collision_time, collision_flash
    
    # Add a new object with certain probability
    if len(road_objects) < 5 and random.random() < 0.02:
        road_objects.append(create_road_object())
    
    # Update position of all objects and check if car has passed them
    for obj in road_objects[:]:
        # Objects move downward relative to car speed
        obj['position'][1] += car_speed * 2
        
        # Check for collision with the car
        car_width = 30
        car_height = 50
        obj_size = obj['size']
        
        # Calculate car boundaries
        car_left = car_position[0] - car_width // 2
        car_right = car_position[0] + car_width // 2
        car_top = car_position[1] - car_height // 2
        car_bottom = car_position[1] + car_height // 2
        
        # Calculate object boundaries (approximate as square for simplicity)
        obj_left = obj['position'][0] - obj_size
        obj_right = obj['position'][0] + obj_size
        obj_top = obj['position'][1] - obj_size
        obj_bottom = obj['position'][1] + obj_size
        
        # Check for collision using simple AABB overlap
        if (car_left < obj_right and car_right > obj_left and
            car_top < obj_bottom and car_bottom > obj_top):
            # Collision detected!
            if time.time() - last_collision_time > 1.0:  # Prevent multiple counts for same collision
                collisions += 1
                last_collision_time = time.time()
                collision_flash = True
                # Remove the object that was hit
                road_objects.remove(obj)
                continue
        
        # Check if car has passed the object
        if not obj['passed'] and obj['position'][1] > car_position[1]:
            # Check if car is close enough to object on X-axis
            if abs(obj['position'][0] - car_position[0]) < 40:
                obj['passed'] = True
                objects_passed += 1
        
        # Remove objects that exit the screen
        if obj['position'][1] > 650:
            road_objects.remove(obj)

# Function to check if a file exists
def file_exists(file_path):
    import os
    return os.path.isfile(file_path)

# Function to update engine sound based on car speed
def update_engine_sound():
    global engine_sound, car_speed, diesel_idle_sound, diesel_revving_sound, current_sound_playing, sound_muted, braking
    
    # If sound is muted, stop any playing sounds and return early
    if sound_muted:
        if pygame.mixer.get_busy():
            pygame.mixer.stop()
            current_sound_playing = None
        return
    
    # Import time explicitly to avoid conflicts with numpy
    import time as py_time
    
    # If no sounds are loaded, return
    if not diesel_idle_sound and not diesel_revving_sound:
        return
    
    # Print debug info periodically (every ~5 seconds)
    if int(py_time.time()) % 5 == 0:
        print(f"Debug - Speed: {car_speed:.1f}, Sound playing: {pygame.mixer.get_busy()}, Muted: {sound_muted}")
        
    # Determine which sound to play based on car speed
    if car_speed <= 0.5:
        # Use idle sound when stopped or moving very slowly
        target_sound = diesel_idle_sound
        target_volume = 0.8
        # More realistic idle variation with speed
        target_pitch = 0.9 + (car_speed * 0.2)  # Smaller pitch change at idle
    else:
        # Use revving sound when moving faster
        target_sound = diesel_revving_sound
        # Volume increases with speed (more pronounced at high speeds)
        target_volume = min(1.0, 0.7 + car_speed * 0.1)
        # More realistic pitch curve - non-linear increase with speed
        target_pitch = 0.8 + (car_speed / 5.0) * (1.0 + car_speed * 0.2)
    
    # Add braking sound effect - reduce volume during braking
    if braking and target_sound == diesel_revving_sound:
        target_volume = max(0.3, target_volume * 0.7)
        
    # If car is completely stopped, fade out any playing sound
    if car_speed <= 0.1:
        if pygame.mixer.get_busy():
            # Just reduce volume instead of stopping
            if current_sound_playing and not sound_muted:
                current_sound_playing.set_volume(0.2)
        return
    
    # Only proceed with sound if not muted
    if sound_muted:
        return
    
    # Check if sound is playing and needs to be changed
    if (target_sound != current_sound_playing or not pygame.mixer.get_busy()) and car_speed > 0.1:
        # Stop current sound if playing
        if pygame.mixer.get_busy() and current_sound_playing:
            current_sound_playing.stop()
            
        # Start new sound
        try:
            target_sound.play(-1)  # -1 means loop indefinitely
            current_sound_playing = target_sound
            print(f"Engine sound {'idle' if target_sound == diesel_idle_sound else 'revving'} started playing")
        except Exception as e:
            print(f"Error playing engine sound: {e}")
    
    # Always update the volume for continuous sound adjustment
    try:
        if current_sound_playing and pygame.mixer.get_busy():
            current_sound_playing.set_volume(target_volume)
        elif car_speed > 0.1 and current_sound_playing and not pygame.mixer.get_busy() and not sound_muted:
            # If sound should be playing but isn't, restart it
            current_sound_playing.play(-1)
            print("Restarting engine sound that stopped unexpectedly")
    except Exception as e:
        print(f"Error setting engine sound volume: {e}")

# Function to draw road objects
def draw_road_objects(screen):
    for obj in road_objects:
        if obj['type'] == 0:
            # Draw circle
            pygame.draw.circle(screen, obj['color'], 
                              (obj['position'][0], obj['position'][1]), 
                              obj['size'])
        elif obj['type'] == 1:
            # Draw square
            rect = pygame.Rect(obj['position'][0] - obj['size']//2, 
                              obj['position'][1] - obj['size']//2,
                              obj['size'], obj['size'])
            pygame.draw.rect(screen, obj['color'], rect)
        else:
            # Draw triangle
            points = [
                (obj['position'][0], obj['position'][1] - obj['size']),
                (obj['position'][0] - obj['size'], obj['position'][1] + obj['size']),
                (obj['position'][0] + obj['size'], obj['position'][1] + obj['size'])
            ]
            pygame.draw.polygon(screen, obj['color'], points)

# Function to draw mute button
def draw_mute_button(screen):
    global sound_muted, mute_button_rect
    
    # Draw button background
    button_color = (200, 50, 50) if sound_muted else (50, 200, 50)
    pygame.draw.rect(screen, button_color, mute_button_rect)
    pygame.draw.rect(screen, (0, 0, 0), mute_button_rect, 2)  # Black border
    
    # Draw speaker icon
    speaker_color = (255, 255, 255)  # White icon
    
    # Draw speaker base
    pygame.draw.rect(screen, speaker_color, 
                    (mute_button_rect.left + 10, mute_button_rect.top + 15, 8, 10))
    
    # Draw speaker cone
    points = [
        (mute_button_rect.left + 18, mute_button_rect.top + 10),
        (mute_button_rect.left + 28, mute_button_rect.top + 5),
        (mute_button_rect.left + 28, mute_button_rect.top + 35),
        (mute_button_rect.left + 18, mute_button_rect.top + 30)
    ]
    pygame.draw.polygon(screen, speaker_color, points)
    
    # Draw X over speaker if muted
    if sound_muted:
        pygame.draw.line(screen, (255, 0, 0), 
                        (mute_button_rect.left + 8, mute_button_rect.top + 8),
                        (mute_button_rect.left + 32, mute_button_rect.top + 32), 3)
        pygame.draw.line(screen, (255, 0, 0), 
                        (mute_button_rect.left + 32, mute_button_rect.top + 8),
                        (mute_button_rect.left + 8, mute_button_rect.top + 32), 3)

# Function to check if mouse clicked on mute button
def check_mute_button_click(pos):
    global sound_muted, mute_button_rect, diesel_idle_sound, diesel_revving_sound, current_sound_playing, car_speed
    
    if mute_button_rect.collidepoint(pos):
        sound_muted = not sound_muted
        
        # When muting, stop all sounds immediately
        if sound_muted:
            pygame.mixer.stop()
            current_sound_playing = None
            print("Sound muted - stopping all sounds")
        # When unmuting, restart the appropriate sound based on car speed
        elif not sound_muted and car_speed > 0.1:
            print("Sound unmuted - restarting engine sound")
            if car_speed <= 0.5 and diesel_idle_sound:
                diesel_idle_sound.play(-1)
                current_sound_playing = diesel_idle_sound
            elif car_speed > 0.5 and diesel_revving_sound:
                diesel_revving_sound.play(-1)
                current_sound_playing = diesel_revving_sound
        
        print(f"Sound {'muted' if sound_muted else 'unmuted'}")
        return True
    return False

# Function to display the car on pygame screen
def draw_car(screen):
    # Draw simple car using a rectangle
    car_color = (255, 0, 0)  # Red
    
    # Change car color temporarily when collision occurs
    global collision_flash
    if collision_flash:
        if time.time() - last_collision_time < 0.3:  # Flash for 0.3 seconds
            car_color = (255, 255, 0)  # Yellow flash
        else:
            collision_flash = False  # Reset flash
    
    car_size = (30, 50)
    car_rect = pygame.Rect(car_position[0] - car_size[0] // 2, 
                          car_position[1] - car_size[1] // 2, 
                          car_size[0], car_size[1])
    pygame.draw.rect(screen, car_color, car_rect)
    
    # Add details to the car
    pygame.draw.rect(screen, (0, 0, 0), 
                    (car_position[0] - car_size[0] // 2 + 5, 
                     car_position[1] - car_size[1] // 2 + 10, 
                     car_size[0] - 10, 15))

# Main function
def main(camera_index=0):
    global engine_sound, diesel_idle_sound, diesel_revving_sound, current_sound_playing, sound_muted
    
    # Initialize sound_muted to False explicitly
    sound_muted = False
    
    # Import time module explicitly to avoid conflicts with numpy
    import time as py_time
    
    # Initialize pygame
    pygame.init()
    
    # Initialize the sound mixer with more robust parameters
    try:
        pygame.mixer.quit()  # First quit any existing mixer
        # Try higher quality audio settings
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
        print("Sound mixer initialized successfully with advanced settings")
    except Exception as e:
        print(f"Error initializing advanced sound mixer: {e}")
        # Fallback to basic sound initialization
        try:
            pygame.mixer.init()
            print("Sound mixer initialized with default settings")
        except Exception as e:
            print(f"Error initializing default sound mixer: {e}")
    
    # Try to set overall volume to maximum
    try:
        pygame.mixer.music.set_volume(1.0)
        print("Set master volume to maximum")
    except:
        print("Could not set master volume")
    
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Car Controlled by Hand Gestures")
    clock = pygame.time.Clock()
    
    # Load diesel engine sounds with multiple fallback options
    sound_loaded = False
    # Update paths to look in Hand_movement directory instead of Hand_directors
    base_paths = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), ''),  # Current script directory
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sounds', ''),
        'c:\\Users\\Sharon\\JohnBryce-python\\Project2\\Hand_movement\\',
        'c:\\Users\\Sharon\\JohnBryce-python\\Project2\\Hand_movement\\sounds\\',
        '.\\',
        '.\\sounds\\'
    ]
    
    # Try to load diesel idle sound
    diesel_idle_files = ['gasoline_idle.wav', 'gasoline_idle.mp3', 'petrol_idle.wav', 'petrol_idle.mp3', 'idle.wav', 'idle.mp3', 'engine_idle.wav', 'diesel_idle.wav']
    
    # Debug: print current directory
    print(f"Current working directory: {os.getcwd()}")
    
    for base_path in base_paths:
        if sound_loaded:
            break
        for file in diesel_idle_files:
            # Use os.path.join for better path handling
            full_path = os.path.join(base_path, file)
            print(f"Trying to load sound from: {full_path}")
            if os.path.isfile(full_path):
                try:
                    diesel_idle_sound = pygame.mixer.Sound(full_path)
                    # Set higher volume for better audibility
                    diesel_idle_sound.set_volume(1.0)
                    print(f"Gasoline idle sound loaded successfully from: {full_path}")
                    sound_loaded = True
                    break
                except Exception as e:
                    print(f"Error loading sound file {full_path}: {e}")
    
    # Try to load diesel revving sound
    sound_loaded = False  # Reset for second sound
    diesel_revving_files = ['gasoline_revving.wav', 'gasoline_revving.mp3', 'petrol_revving.wav', 'petrol_revving.mp3', 'revving.wav', 'revving.mp3', 'engine.wav', 'engine.mp3', 'diesel_revving.wav']
    
    for base_path in base_paths:
        if sound_loaded:
            break
        for file in diesel_revving_files:
            # Try with absolute path first
            full_path = os.path.join(base_path, file)
            print(f"Trying to load sound from: {full_path}")
            if file_exists(full_path):
                try:
                    diesel_revving_sound = pygame.mixer.Sound(full_path)
                    # Set higher volume for better audibility
                    diesel_revving_sound.set_volume(1.0)
                    print(f"Gasoline revving sound loaded successfully from: {full_path}")
                    sound_loaded = True
                    break
                except Exception as e:
                    print(f"Error loading sound file {full_path}: {e}")
    
    # Create default sounds if none were loaded
    if not diesel_idle_sound:
        try:
            print("Creating default gasoline idle sound...")
            # Create a more realistic gasoline engine idle sound
            sample_rate = 44100
            duration = 1.0  # 1 second of sound
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            # Base frequency for idle (higher for gasoline sound)
            base_freq = 120  # Higher pitch for gasoline engines
            
            # Create complex waveform with harmonics for engine idle
            signal = np.zeros_like(t)
            
            # Add fundamental frequency
            signal += 0.3 * np.sin(2 * np.pi * base_freq * t)
            # Add harmonics with different amplitudes - more high-frequency content for gasoline
            signal += 0.25 * np.sin(2 * np.pi * (base_freq * 2) * t)
            signal += 0.2 * np.sin(2 * np.pi * (base_freq * 3) * t)
            signal += 0.15 * np.sin(2 * np.pi * (base_freq * 4) * t)
            signal += 0.1 * np.sin(2 * np.pi * (base_freq * 5) * t)
            signal += 0.08 * np.sin(2 * np.pi * (base_freq * 6) * t)
            
            # Add some random variations to simulate combustion irregularities
            # Gasoline engines have more rapid and crisp variations
            signal += 0.07 * np.random.normal(0, 1, len(t)) * np.sin(2 * np.pi * base_freq * 0.8 * t)
            
            # Add pulsating effect (cylinder firing rhythm)
            # Gasoline engines have more rapid firing rhythms
            pulse_freq = 25  # Higher firing frequency for gasoline
            pulse_mod = 0.15 * np.sin(2 * np.pi * pulse_freq * t)
            signal *= (1 + pulse_mod)
            
            # Apply a smooth envelope to avoid pops/clicks
            envelope = np.ones_like(t)
            attack_samples = int(0.05 * sample_rate)  # 50ms attack
            decay_samples = int(0.05 * sample_rate)   # 50ms decay
            envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
            envelope[-decay_samples:] = np.linspace(1, 0, decay_samples)
            signal *= envelope
            
            # Normalize to float32 range (-1, 1)
            signal = np.clip(signal, -1, 1).astype(np.float32)
            
            # Create buffer with smoother looping
            repeated = np.tile(signal, 4)
            # Create crossfade at the loop points
            crossfade_samples = int(0.1 * sample_rate)  # 100ms crossfade
            for i in range(1, 4):
                loop_point = i * len(signal)
                # Apply crossfade
                fade_out = np.linspace(1, 0, crossfade_samples)
                fade_in = np.linspace(0, 1, crossfade_samples)
                repeated[loop_point-crossfade_samples:loop_point] *= fade_out
                repeated[loop_point:loop_point+crossfade_samples] *= fade_in
                
            buffer = repeated
            
            diesel_idle_sound = pygame.mixer.Sound(buffer)
            diesel_idle_sound.set_volume(1.0)
            print("Default gasoline engine idle sound created successfully")
        except Exception as e:
            print(f"Could not create default idle sound: {e}")
    
    if not diesel_revving_sound:
        try:
            print("Creating default gasoline revving sound...")
            # Create a more realistic gasoline engine revving sound
            sample_rate = 44100
            duration = 1.0
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            # Base frequency for revving (higher than idle - gasoline engines rev higher)
            base_freq = 180
            
            # Create complex waveform with harmonics for engine revving
            signal = np.zeros_like(t)
            
            # Add fundamental frequency
            signal += 0.3 * np.sin(2 * np.pi * base_freq * t)
            
            # Add stronger harmonics for revving sound - gasoline engines have more high-end
            signal += 0.25 * np.sin(2 * np.pi * (base_freq * 2) * t)
            signal += 0.2 * np.sin(2 * np.pi * (base_freq * 3) * t)
            signal += 0.18 * np.sin(2 * np.pi * (base_freq * 4) * t)
            signal += 0.15 * np.sin(2 * np.pi * (base_freq * 5) * t)
            signal += 0.12 * np.sin(2 * np.pi * (base_freq * 6) * t)
            signal += 0.1 * np.sin(2 * np.pi * (base_freq * 7) * t)
            signal += 0.07 * np.sin(2 * np.pi * (base_freq * 8) * t)
            
            # Add some frequency modulation for more realistic engine sound
            fm_freq = 12  # Higher modulation frequency for gasoline
            fm_index = 8  # Stronger modulation index
            fm_mod = np.sin(2 * np.pi * fm_freq * t)
            
            # Apply rising pitch effect - gasoline engines can rev higher
            t_norm = t / duration
            pitch_increase = 1 + 1.2 * t_norm  # Steeper pitch increase
            
            # Apply frequency modulation with increasing pitch
            for i, time in enumerate(t):
                signal[i] += 0.25 * np.sin(2 * np.pi * base_freq * pitch_increase[i] * time + fm_index * fm_mod[i])
            
            # Apply cylinder firing effect
            pulse_freq = 45  # Higher firing frequency for revving gasoline
            pulse_mod = 0.18 * np.sin(2 * np.pi * pulse_freq * t)
            signal *= (1 + pulse_mod)
            
            # Add high frequency components characteristic of gasoline engines
            signal += 0.05 * np.sin(2 * np.pi * 1200 * t) * np.sin(2 * np.pi * 5 * t)  # Valve noise
            
            # Apply a smooth envelope to avoid pops/clicks
            envelope = np.ones_like(t)
            attack_samples = int(0.05 * sample_rate)  # 50ms attack
            decay_samples = int(0.05 * sample_rate)   # 50ms decay
            envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
            envelope[-decay_samples:] = np.linspace(1, 0, decay_samples)
            signal *= envelope
            
            # Normalize to float32 range (-1, 1)
            signal = np.clip(signal, -1, 1).astype(np.float32)
            
            # Create buffer with smoother looping
            repeated = np.tile(signal, 4)
            # Create crossfade at the loop points
            crossfade_samples = int(0.1 * sample_rate)  # 100ms crossfade
            for i in range(1, 4):
                loop_point = i * len(signal)
                # Apply crossfade
                fade_out = np.linspace(1, 0, crossfade_samples)
                fade_in = np.linspace(0, 1, crossfade_samples)
                repeated[loop_point-crossfade_samples:loop_point] *= fade_out
                repeated[loop_point:loop_point+crossfade_samples] *= fade_in
                
            buffer = repeated
            
            diesel_revving_sound = pygame.mixer.Sound(buffer)
            diesel_revving_sound.set_volume(1.0)
            print("Default gasoline engine revving sound created successfully")
        except Exception as e:
            print(f"Could not create default revving sound: {e}")
    
    if not diesel_idle_sound and not diesel_revving_sound:
        print("WARNING: Could not load or create any sound files. Sound will be disabled.")
    
    # Initialize webcam with selected index
    cap = cv2.VideoCapture(camera_index)
    
    # Check if camera opened successfully
    if not cap.isOpened():
        print(f"Error: Cannot open webcam with index {camera_index}!")
        return
    
    print(f"Using camera with index {camera_index}")
    
    running = True
    while running:
        # Handle pygame events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Check if mute button was clicked
                if check_mute_button_click(event.pos):
                    print(f"Sound state changed: {'MUTED' if sound_muted else 'UNMUTED'}")
        
        # Read frame from webcam
        ret, frame = cap.read()
        if not ret:
            print("Error reading frame from camera, trying again...")
            # Try to reinitialize the camera
            cap.release()
            time.sleep(0.5)
            cap = cv2.VideoCapture(camera_index)
            if not cap.isOpened():
                print("Cannot reopen camera, exiting...")
                break
            continue
        
        # Flip the image to act as a mirror
        frame = cv2.flip(frame, 1)
        
        # Detect hand gestures
        frame = detect_hand_gestures(frame)
        
        # Update car position
        update_car_position()
        
        # Update engine sound based on car speed
        update_engine_sound()
        
        # Update road objects
        update_road_objects()
        
        # Draw pygame screen
        screen.fill((255, 255, 255))  # White background
        
        # Draw road/track first (order matters so car appears above road)
        road_color = (200, 200, 200)
        pygame.draw.rect(screen, road_color, (300, 0, 200, 600))
        
        # Draw objects on the road
        draw_road_objects(screen)
        
        # Draw car above the road
        draw_car(screen)
        
        # Display number of objects passed
        font = pygame.font.SysFont(None, 36)
        text = font.render(f"Objects passed: {objects_passed}", True, (0, 0, 0))
        screen.blit(text, (50, 50))
        
        # Display current speed
        speed_text = font.render(f"Speed: {car_speed:.1f}", True, (0, 0, 0))
        screen.blit(speed_text, (50, 100))
        
        # Display collision count
        collision_text = font.render(f"Collisions: {collisions}", True, (255, 0, 0))
        screen.blit(collision_text, (50, 150))
        
        # Display game score (objects passed minus collisions)
        score = max(0, objects_passed - collisions * 2)  # Collisions count double negative
        score_text = font.render(f"Score: {score}", True, (0, 0, 255))
        screen.blit(score_text, (50, 200))
        
        # Draw mute button
        draw_mute_button(screen)
        
        # Display text label for mute button
        font = pygame.font.SysFont(None, 24)
        mute_label = font.render("Sound", True, (0, 0, 0))
        screen.blit(mute_label, (mute_button_rect.left - 5, mute_button_rect.bottom + 5))
        
        # Display braking status if active
        if braking:
            brake_text = font.render("BRAKING!", True, (255, 0, 0))
            screen.blit(brake_text, (50, 250))
        
        # Display webcam frame in separate window
        cv2.imshow("Hand Gesture Detection", frame)
        
        # Update pygame screen
        # Force sound update periodically to ensure continuous playback
        # Use the explicitly imported time module
        if int(py_time.time()) % 2 == 0 and car_speed > 0.1:
            if current_sound_playing and not pygame.mixer.get_busy():
                print("Forcing sound restart - sound stopped unexpectedly")
                current_sound_playing.play(-1)
        
        # Add debug text for mute state on screen
        font = pygame.font.SysFont(None, 24)
        mute_status = font.render(f"Sound: {'MUTED' if sound_muted else 'ON'}", True, (255, 0, 0) if sound_muted else (0, 128, 0))
        screen.blit(mute_status, (mute_button_rect.left + 45, mute_button_rect.top + 10))
        
        # Update pygame screen
        pygame.display.flip()
        
        # Limit to 60 frames per second
        clock.tick(60)
        
        # Exit loop if ESC key is pressed
        if cv2.waitKey(1) == 27:
            running = False
    
    # Cleanup and close
    if diesel_idle_sound or diesel_revving_sound:
        pygame.mixer.stop()
    pygame.mixer.quit()
    cap.release()
    cv2.destroyAllWindows()
    pygame.quit()

def find_available_cameras():
    """Check available camera devices and their indices"""
    available_cameras = []
    for i in range(10):  # Check indices 0-9
        try:
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    print(f"Camera index {i} is working")
                    available_cameras.append(i)
                cap.release()
            else:
                print(f"Camera index {i} is not available")
        except Exception as e:
            print(f"Error with camera index {i}: {e}")
    return available_cameras

def select_camera(available_cameras):
    """Let the user select a camera from the available ones"""
    if not available_cameras:
        return None
    
    if len(available_cameras) == 1:
        print(f"Only one camera found (index {available_cameras[0]}), using it automatically.")
        return available_cameras[0]
    
    print("\nAvailable cameras:")
    for i, cam_idx in enumerate(available_cameras):
        print(f"{i+1}. Camera {cam_idx}")
    
    selection = -1
    while selection < 0 or selection >= len(available_cameras):
        try:
            selection = int(input("Select camera number (1, 2, ...): ")) - 1
            if selection < 0 or selection >= len(available_cameras):
                print("Invalid selection, try again.")
        except ValueError:
            print("Please enter a valid number.")
    
    return available_cameras[selection]

if __name__ == "__main__":
    print("Checking available cameras...")
    cameras = find_available_cameras()
    print(f"Available camera indices: {cameras}")
    
    # Select camera from available list
    if cameras:
        selected_camera = select_camera(cameras)
        if selected_camera is not None:
            main(camera_index=selected_camera)
        else:
            print("No camera selected. Program is exiting.")
    else:
        print("No available cameras found. Please connect a webcam and try again.")