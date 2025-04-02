# utils/camera.py - Camera handling functions

import cv2
import pygame

def find_available_cameras():
    """Check available camera devices and their indices."""
    available_cameras = []
    
    # Check camera indices 0-9
    for i in range(10):
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
    """Let the user select a camera from the available ones using a GUI."""
    if not available_cameras:
        return None
    
    if len(available_cameras) == 1:
        print(f"Only one camera found (index {available_cameras[0]}), using it automatically.")
        return available_cameras[0]
    
    # Initialize pygame for camera selection screen
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Camera Selection")
    font_title = pygame.font.SysFont(None, 48)
    font_option = pygame.font.SysFont(None, 36)
    font_desc = pygame.font.SysFont(None, 24)
    
    # Create buttons for each camera
    buttons = []
    button_height = 60
    button_spacing = 20
    button_start_y = 200
    
    for i, cam_idx in enumerate(available_cameras):
        y_pos = button_start_y + i * (button_height + button_spacing)
        buttons.append({
            'rect': pygame.Rect(250, y_pos, 300, button_height),
            'index': cam_idx,
            'text': f"Camera {cam_idx}",
            'hover': False
        })
    
    # Main selection loop
    clock = pygame.time.Clock()
    running = True
    
    while running:
        mouse_pos = pygame.mouse.get_pos()
        mouse_clicked = False
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None  # Exit camera selection
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    mouse_clicked = True
        
        # Handle button hovers and clicks
        for button in buttons:
            button['hover'] = button['rect'].collidepoint(mouse_pos)
            if button['hover'] and mouse_clicked:
                pygame.quit()
                return button['index']  # Return selected camera index
        
        # Draw selection screen
        screen.fill((240, 240, 255))  # Light blue background
        
        # Draw title
        title_text = font_title.render("Select Camera", True, (20, 20, 100))
        title_rect = title_text.get_rect(center=(400, 100))
        screen.blit(title_text, title_rect)
        
        # Draw description
        desc_text = font_desc.render("Select which camera to use for hand tracking", True, (60, 60, 100))
        desc_rect = desc_text.get_rect(center=(400, 150))
        screen.blit(desc_text, desc_rect)
        
        # Draw buttons
        for button in buttons:
            # Button background
            color = (120, 120, 255) if button['hover'] else (100, 100, 220)
            pygame.draw.rect(screen, color, button['rect'])
            pygame.draw.rect(screen, (0, 0, 0), button['rect'], 2)  # Border
            
            # Button text
            text = font_option.render(button['text'], True, (255, 255, 255))
            text_rect = text.get_rect(center=button['rect'].center)
            screen.blit(text, text_rect)
        
        pygame.display.flip()
        clock.tick(60)
    
    # If the loop exits without selection, use first camera
    pygame.quit()
    return available_cameras[0] if available_cameras else None

def test_camera(camera_index):
    """Test if a camera works by displaying a preview window."""
    cap = cv2.VideoCapture(camera_index)
    
    if not cap.isOpened():
        print(f"Error: Cannot open camera with index {camera_index}")
        return False
    
    print(f"Testing camera {camera_index}...")
    
    # Show preview for 3 seconds
    frames_shown = 0
    max_frames = 90  # At 30fps, this is about 3 seconds
    
    while frames_shown < max_frames:
        ret, frame = cap.read()
        
        if not ret:
            print("Error reading frame from camera")
            cap.release()
            return False
        
        # Flip horizontally for mirror effect
        frame = cv2.flip(frame, 1)
        
        # Add info text
        cv2.putText(frame, f"Camera {camera_index} Test", (20, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, "Press any key to stop test", (20, 70),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 0), 2)
        
        # Display frame
        cv2.imshow(f"Camera {camera_index} Test", frame)
        
        # Break on key press
        if cv2.waitKey(30) >= 0:
            break
            
        frames_shown += 1
    
    # Clean up
    cap.release()
    cv2.destroyAllWindows()
    
    return True