# main.py - Main entry point for the Hand Gesture Car Control application

import cv2
import numpy as np
import pygame
import os
import time
import sys
from pygame.locals import *

# Import our application modules
import config
from main_menu import MainMenu
from hand_detector.improved_hand_gesture_detector import EnhancedHandGestureDetector  # Make sure this path is correct
from utils.camera import find_available_cameras, select_camera
from game.car import Car
from game.objects import RoadObjectManager
from utils.sound import SoundManager
from utils.ui import GameUI

# Import car controller
from car_control import ImprovedCarController  # Make sure this path is correct

# Add this import at the top
from debug_utils import MovementDebugger

# Add these constants at the beginning of the file after imports
MOVEMENT_THRESHOLD = 30  # Minimum movement distance to register as a movement
GESTURE_COOLDOWN = 15    # Frames to wait before detecting another gesture

class HandGestureCarControl:
    def __init__(self):
        # Initialize pygame first
        pygame.init()
        
        # Setup display
        self.screen_width, self.screen_height = 800, 600
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Hand Gesture Car Control")
        
        # Initialize camera
        self.cap = None
        self.init_camera()
        
        # Now show loading screen after display is initialized
        self.show_loading_screen("Initializing hand tracking...")
        
        # Initialize enhanced hand gesture detector
        self.hand_detector = EnhancedHandGestureDetector()
        
        # Initialize improved car controller
        self.car_controller = ImprovedCarController(
            simulation_mode=True  # Set to False for real car control
        )
        
        # Initialize sound manager
        self.show_loading_screen("Loading sounds...")
        self.sound_manager = SoundManager()
        
        # Default game state
        self.game_mode = config.DEFAULT_GAME_MODE
        self.game_active = False
        self.paused = False
        
        # Frame skipping for performance
        self.frame_skip = 0
        self.max_frame_skip = 0  # 0 means process every frame, increase for better performance
        
        self.show_loading_screen("Ready to play!")
        time.sleep(1)  # Show ready message briefly
    
    def init_camera(self):
        """Initialize the camera capture using camera selection interface."""
        # Find available cameras
        available_cameras = find_available_cameras()
        print(f"Available camera indices: {available_cameras}")
        
        if not available_cameras:
            message = "No cameras available. Please connect a webcam and try again."
            print(message)
            self.show_error("No Cameras Found", message)
            pygame.quit()
            sys.exit(1)
        
        # Let user select a camera
        selected_camera = select_camera(available_cameras)
        if selected_camera is None:
            message = "No camera selected. Exiting."
            print(message)
            pygame.quit()
            sys.exit(1)
        
        # Store selected camera index for potential reconnection
        self.selected_camera = selected_camera
        
        # Initialize the selected camera with lower resolution for better performance
        self.cap = cv2.VideoCapture(selected_camera)
        
        # Set camera properties for more reliable operation
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)  
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480) 
        
        if not self.cap.isOpened():
            message = f"Failed to open camera {selected_camera}. Please try another camera."
            print(message)
            self.show_error("Camera Error", message)
            pygame.quit()
            sys.exit(1)
        
        print(f"Using camera index {selected_camera}")
        
    def run(self):
        """Main application loop."""
        running = True
        while running:
            # Show main menu if game is not active
            if not self.game_active:
                menu = MainMenu(self.screen)
                selected_mode = menu.run()
                
                if selected_mode is None:
                    running = False  # Exit if menu was closed
                    continue
                    
                self.game_mode = selected_mode
                self.initialize_game()
                self.game_active = True
            
            # Main game loop
            if self.game_active:
                running = self.run_game()
        
        # Clean up and exit
        self.cleanup()
    
    def initialize_game(self):
        """Initialize or reset the game with the selected mode."""
        # Get game mode settings
        mode_settings = config.GAME_MODES[self.game_mode]
        
        # Initialize game objects
        self.car = Car(400, 300)  # Start car at center position
        self.road_objects = RoadObjectManager(
            obstacle_frequency=mode_settings['obstacle_frequency'],
            speed_multiplier=mode_settings['obstacle_speed_multiplier']
        )
        
        # Initialize game state variables
        self.score = 0
        self.collisions = 0
        self.game_time = 0
        self.start_time = time.time()
        self.time_limit = mode_settings['time_limit']
        self.score_multiplier = mode_settings['score_multiplier']
        
        # Initialize UI
        self.game_ui = GameUI(self.screen, self.game_mode)
        
        # Reset sound
        self.sound_manager.reset()
        
        # Initialize clock for FPS control
        self.clock = pygame.time.Clock()
    
    def run_game(self):
        """Run the main game loop."""
        # Add these variables to track movement
        prev_hand_position = None
        gesture_cooldown = 0
        movement_history = []

        # Initialize the debugger
        movement_debugger = MovementDebugger()

        # Process events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False  # Exit the application
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    # Toggle pause
                    self.paused = not self.paused
                
                if event.key == pygame.K_q and self.paused:
                    # Quit to main menu if paused
                    self.game_active = False
                    return True
            
            # Handle mouse clicks
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    # Check if mute button was clicked
                    if self.game_ui.check_mute_button_click(event.pos):
                        # Update sound manager's mute state to match UI
                        self.sound_manager.set_mute(self.game_ui.sound_muted)
                        print(f"Sound state changed in run_game: {'MUTED' if self.game_ui.sound_muted else 'UNMUTED'}")
                        # Force sound update after mute state change
                        self.sound_manager.update_engine_sound(
                            self.car.speed, 
                            False,  # Not braking
                            False   # Not boosting
                        )
        
        # If paused, show pause menu and don't update game state
        if self.paused:
            self.draw_pause_menu()
            pygame.display.flip()
            self.clock.tick(60)
            return True
        
        # Update game time
        current_time = time.time()
        self.game_time = current_time - self.start_time
        
        # Check time limit if set
        if self.time_limit and self.game_time >= self.time_limit:
            self.game_over("Time Up!")
            return True
        
        # Process hand detection with frame skipping
        controls = {'steering': 0.0, 'throttle': 0.0}  # Default controls
        
        if self.frame_skip <= 0:
            # Process frame only if not skipping
            ret, frame = self.cap.read()
            if not ret:
                print("Error reading frame from camera, trying again...")
                # Try to reinitialize the camera
                self.cap.release()
                time.sleep(1.0)  # Wait a bit longer
                self.cap = cv2.VideoCapture(self.selected_camera)
                
                # Re-apply camera settings
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                
                if not self.cap.isOpened():
                    print("Cannot reopen camera, returning to menu...")
                    self.game_active = False
                    return True
                return True  # Continue trying next frame
            
            # Flip the image horizontally to act as a mirror
            frame = cv2.flip(frame, 1)
            
            try:
                # Process hand gestures with improved detection
                controls, processed_frame = self.hand_detector.detect_gestures(frame)
                
                # Get a stable command (helps reduce jitter)
                stable_command = self.hand_detector.get_stable_command()
                
                if stable_command:
                    # Send the command to the car with improved command handling
                    command_sent = self.car_controller.send_command(stable_command)
                    print(f"Command sent to car: {stable_command}, Success: {command_sent}")
                
                # Display hand detection frame
                cv2.imshow("Hand Gesture Detection", processed_frame)
            except Exception as e:
                print(f"Error in hand gesture detection: {e}")
                cv2.imshow("Hand Gesture Detection", frame)  # Show original frame on error
            
            # Reset frame skip counter
            self.frame_skip = self.max_frame_skip
        else:
            # Skip frame processing but decrement counter
            self.frame_skip -= 1
        
        # Ensure controls contains all necessary keys for game mechanics
        if 'speed' not in controls and 'throttle' in controls:
            controls['speed'] = controls['throttle']  # Map throttle to speed for car update
        elif 'speed' not in controls:
            controls['speed'] = 0.5  # Default speed
        
        if 'direction' not in controls and 'steering' in controls:
            controls['direction'] = controls['steering']  # Map steering to direction for car update
        elif 'direction' not in controls:
            controls['direction'] = 0  # Default direction

        # Update car with controls
        self.car.update(controls)
        
        # Update road objects
        collision, objects_passed = self.road_objects.update(self.car)
        
        # Handle collision
        if collision:
            self.collisions += 1
            self.sound_manager.play_collision()
        
        # Update score
        self.score += objects_passed * self.score_multiplier
        
        # Update sound - make sure mute state is respected
        self.sound_manager.update_engine_sound(
            self.car.speed, 
            controls.get('braking', False), 
            controls.get('boost', False)
        )
        
        # Draw game
        self.draw_game()
        
        # Exit if ESC key is pressed in the OpenCV window
        if cv2.waitKey(1) == 27:
            self.game_active = False
            return True
            
        # Limit to 60 FPS
        self.clock.tick(60)
        
        return True  # Continue the game loop
        
    def draw_game(self):
        """Draw the game screen."""
        # Clear screen
        self.screen.fill((255, 255, 255))  # White background
        
        # Draw road
        road_color = (200, 200, 200)
        pygame.draw.rect(self.screen, road_color, (300, 0, 200, 600))
        
        # Draw road objects
        self.road_objects.draw(self.screen)
        
        # Draw car
        self.car.draw(self.screen)
        
        # Draw UI
        self.game_ui.draw(
            score=self.score, 
            collisions=self.collisions, 
            speed=self.car.speed,
            time_elapsed=self.game_time,
            time_limit=self.time_limit
        )
        
        # Update display
        pygame.display.flip()
    
    def draw_pause_menu(self):
        """Draw the pause menu overlay."""
        # Semi-transparent overlay
        overlay = pygame.Surface((800, 600), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))  # Semi-transparent black
        self.screen.blit(overlay, (0, 0))
        
        # Pause title
        font_title = pygame.font.SysFont(None, 60)
        title_text = font_title.render("PAUSED", True, (255, 255, 255))
        title_rect = title_text.get_rect(center=(400, 200))
        self.screen.blit(title_text, title_rect)
        
        # Instructions
        font_instructions = pygame.font.SysFont(None, 36)
        
        resume_text = font_instructions.render("Press ESC to Resume", True, (255, 255, 255))
        resume_rect = resume_text.get_rect(center=(400, 300))
        self.screen.blit(resume_text, resume_rect)
        
        quit_text = font_instructions.render("Press Q to Quit to Menu", True, (255, 255, 255))
        quit_rect = quit_text.get_rect(center=(400, 350))
        self.screen.blit(quit_text, quit_rect)
    
    def game_over(self, reason="Game Over"):
        """Handle game over state."""
        # Display game over screen
        overlay = pygame.Surface((800, 600), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 192))  # More opaque black
        self.screen.blit(overlay, (0, 0))
        
        # Game over title
        font_title = pygame.font.SysFont(None, 72)
        title_text = font_title.render(reason, True, (255, 50, 50))
        title_rect = title_text.get_rect(center=(400, 200))
        self.screen.blit(title_text, title_rect)
        
        # Final score
        font_score = pygame.font.SysFont(None, 48)
        score_text = font_score.render(f"Final Score: {int(self.score)}", True, (255, 255, 255))
        score_rect = score_text.get_rect(center=(400, 300))
        self.screen.blit(score_text, score_rect)
        
        # Continue instructions
        font_continue = pygame.font.SysFont(None, 36)
        continue_text = font_continue.render("Press any key to continue...", True, (200, 200, 200))
        continue_rect = continue_text.get_rect(center=(400, 400))
        self.screen.blit(continue_text, continue_rect)
        
        pygame.display.flip()
        
        # Play game over sound
        self.sound_manager.play_game_over()
        
        # Wait for key press
        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.cleanup()
                    exit()
                if event.type == pygame.KEYDOWN:
                    waiting = False
        
        # Return to menu
        self.game_active = False
    
    def cleanup(self):
        """Clean up resources before exit."""
        if self.cap and self.cap.isOpened():
            self.cap.release()
        cv2.destroyAllWindows()
        pygame.quit()
    
    def show_loading_screen(self, message):
        """Display a loading screen with a message."""
        try:
            # Check if display is still active
            if not pygame.get_init() or not pygame.display.get_surface():
                return
                
            self.screen.fill((240, 240, 255))  # Light blue background
            # Draw title
            font_title = pygame.font.SysFont(None, 60)
            title_text = font_title.render("Hand Gesture Car Control", True, (20, 20, 100))
            title_rect = title_text.get_rect(center=(self.screen_width//2, 200))
            self.screen.blit(title_text, title_rect)
            
            # Draw loading message
            font_message = pygame.font.SysFont(None, 36)
            message_text = font_message.render(message, True, (50, 50, 150))
            message_rect = message_text.get_rect(center=(self.screen_width//2, 300))
            self.screen.blit(message_text, message_rect)
            
            pygame.display.flip()
        except pygame.error as e:
            print(f"pygame error during loading screen: {e}")
    
    def show_error(self, title, message):
        """Display an error message."""
        self.screen.fill((255, 200, 200))  # Light red background
        
        # Draw error title
        font_title = pygame.font.SysFont(None, 60)
        title_text = font_title.render(title, True, (200, 0, 0))
        title_rect = title_text.get_rect(center=(self.screen_width//2, 200))
        self.screen.blit(title_text, title_rect)
        
        # Draw error message
        font_message = pygame.font.SysFont(None, 36)
        message_text = font_message.render(message, True, (100, 0, 0))
        message_rect = message_text.get_rect(center=(self.screen_width//2, 300))
        self.screen.blit(message_text, message_rect)
        
        # Draw exit instruction
        font_exit = pygame.font.SysFont(None, 30)
        exit_text = font_exit.render("Press any key to exit...", True, (100, 0, 0))
        exit_rect = exit_text.get_rect(center=(self.screen_width//2, 400))
        self.screen.blit(exit_text, exit_rect)
        
        pygame.display.flip()
        
        # Wait for key press
        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or event.type == pygame.KEYDOWN:
                    waiting = False

    def troubleshoot_connectivity(self):
        """Diagnose and fix connectivity issues with the car."""
        import socket
        import subprocess
        import platform
        
        print("======= Connectivity Troubleshooting =======")
        
        # Check network configuration
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('10.255.255.255', 1))
            local_ip = s.getsockname()[0]
        except Exception:
            local_ip = '127.0.0.1'
        finally:
            s.close()
        
        print(f"Local IP: {local_ip}")
        network_ok = local_ip.startswith("192.168.4.")
        
        if not network_ok:
            print("WARNING: Your computer appears to be on a different subnet than the car.")
            print("The car typically uses 192.168.4.x network.")
        
        # Try to ping the car
        car_ip = "192.168.4.1"  # Default car IP
        param = '-n' if platform.system().lower() == 'windows' else '-c'
        command = ['ping', param, '1', car_ip]
        
        try:
            output = subprocess.check_output(command).decode('utf-8')
            print(f"Ping result: {output}")
            ping_ok = "time=" in output or "time<" in output
        except subprocess.CalledProcessError:
            print(f"Failed to ping car at {car_ip}.")
            ping_ok = False
        
        # Provide recommendations based on results
        print("\n------- Recommendations -------")
        if not network_ok:
            print("1. Connect to the car's WiFi network")
            print("2. Verify your WiFi connection settings")
        if not ping_ok:
            print("1. Check if the car is powered on")
            print("2. Verify the car's IP address")
            print("3. Restart the car's control system")
        
        return network_ok and ping_ok

    def __del__(self):
        """Clean up resources when the object is destroyed."""
        if hasattr(self, 'cap') and self.cap is not None:
            self.cap.release()

def main():
    """Main entry point for the application."""
    try:
        # Create and run the game application
        app = HandGestureCarControl()
        app.run()
        print("Application exited successfully")
    except Exception as e:
        print(f"Error in main application: {e}")
        # Make sure CV windows are closed on error
        cv2.destroyAllWindows()
        pygame.quit()
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
