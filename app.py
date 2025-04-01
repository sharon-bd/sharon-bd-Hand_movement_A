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

# Function to detect hand gestures
def detect_hand_gestures(frame):
    global car_speed, car_direction, last_hand_detection_time, auto_stopping, auto_stop_start_time
    
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
    
    # Handle auto-stopping if needed
    if auto_stopping:
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
    global engine_sound, car_speed, diesel_idle_sound, diesel_revving_sound, current_sound_playing
    
    # Import time explicitly to avoid conflicts with numpy
    import time as py_time
    
    # If no sounds are loaded, return
    if not diesel_idle_sound and not diesel_revving_sound:
        return
    
    # Print debug info periodically (every ~5 seconds)
    if int(py_time.time()) % 5 == 0:
        print(f"Debug - Speed: {car_speed:.1f}, Sound playing: {pygame.mixer.get_busy()}")
        
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
    
    # If car is completely stopped, fade out any playing sound
    if car_speed <= 0.1:
        if pygame.mixer.get_busy():
            # Just reduce volume instead of stopping
            if current_sound_playing:
                current_sound_playing.set_volume(0.2)
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
        elif car_speed > 0.1 and current_sound_playing and not pygame.mixer.get_busy():
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
    global engine_sound, diesel_idle_sound, diesel_revving_sound, current_sound_playing
    
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
        try:
            # Fallback to basic sound initialization
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
        print("Check if pygame.mixer is properly initialized and sound files exist.")
        print("Make sure your system's audio is not muted and volume is turned up.")
    else:
        # Test sound playback
        if diesel_idle_sound:
            try:
                diesel_idle_sound.play()
                print("⚠️ CHECK YOUR SPEAKERS NOW - Gasoline idle sound test playing for 1 second! ⚠️")
                # Use imported time module to avoid numpy conflict
                py_time.sleep(1.0)
                diesel_idle_sound.stop()
                print("Gasoline idle sound test completed!")
            except Exception as e:
                print(f"Sound test failed for idle: {e}")
                diesel_idle_sound = None
                
        if diesel_revving_sound:
            try:
                diesel_revving_sound.play()
                print("⚠️ CHECK YOUR SPEAKERS NOW - Gasoline revving sound test playing for 1 second! ⚠️")
                # Use imported time module to avoid numpy conflict
                py_time.sleep(1.0)
                diesel_revving_sound.stop()
                print("Gasoline revving sound test completed!")
            except Exception as e:
                print(f"Sound test failed for revving: {e}")
                diesel_revving_sound = None
    
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
        
        # Display webcam frame in separate window
        cv2.imshow("Hand Gesture Detection", frame)
        
        # Force sound update periodically to ensure continuous playback
        # Use the explicitly imported time module
        if int(py_time.time()) % 2 == 0 and car_speed > 0.1:
            if current_sound_playing and not pygame.mixer.get_busy():
                print("Forcing sound restart - sound stopped unexpectedly")
                current_sound_playing.play(-1)
        
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