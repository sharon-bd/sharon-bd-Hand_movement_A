# main.py - Main entry point for the Hand Gesture Car Control application

import cv2
import numpy as np  # Fixed the import statement
import pygame
import os
import time
import sys
from pygame.locals import *

# Import our application modules
import config
from main_menu import MainMenu
from hand_detector.gestures import HandGestureDetector
from utils.camera import find_available_cameras, select_camera
from game.car import Car
from game.objects import RoadObjectManager
from utils.sound import SoundManager
from utils.ui import GameUI
from game_ui import GameUI

class HandGestureCarControl:
    def __init__(self):
        # Initialize pygame first
        pygame.init()
        
        # Setup display
        self.screen_width, self.screen_height = 1280, 720
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Hand Gesture Car Control")
        
        # Initialize camera
        self.cap = None
        self.init_camera()
        
        # Now show loading screen after display is initialized
        self.show_loading_screen("Initializing hand tracking...")
        
        # Initialize hand gesture detector
        self.show_loading_screen("Initializing hand tracking...")
        self.hand_detector = HandGestureDetector()
        
        # Initialize sound manager
        self.show_loading_screen("Loading sounds...")
        self.sound_manager = SoundManager()
        
        # Default game state
        self.game_mode = config.DEFAULT_GAME_MODE
        self.game_active = False
        self.paused = False
        
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
        
        # Initialize the selected camera
        self.cap = cv2.VideoCapture(selected_camera)
        if not self.cap.isOpened():
            message = f"Failed to open camera {selected_camera}. Please try another camera."
            print(message)
            self.show_error("Camera Error", message)
            pygame.quit()
            sys.exit(1)
        
        print(f"Using camera index {selected_camera}")
        
        # Reinitialize pygame to ensure display is active
        pygame.quit()
        pygame.init()
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Hand Gesture Car Control")
        
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
                        print(f"Sound {'muted' if self.game_ui.sound_muted else 'unmuted'}")
        
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
        
        # Process hand detection
        ret, frame = self.cap.read()
        if not ret:
            print("Error reading from camera")
            return False
        
        # Flip the image horizontally to act as a mirror
        frame = cv2.flip(frame, 1)
        
        # Process hand gestures
        controls, processed_frame = self.hand_detector.detect_gestures(frame)
        
        # Add the 'speed' key if it doesn't exist
        if 'speed' not in controls:
            # Determine speed based on other controls
            # This is a placeholder - adjust based on your actual control scheme
            if 'boost' in controls and controls['boost']:
                controls['speed'] = 1.0  # Full speed when boosting
            elif 'braking' in controls and controls['braking']:
                controls['speed'] = 0.0  # Zero speed when braking
            else:
                # Default speed, adjust as needed
                controls['speed'] = 0.5  # Half speed
        
        # Ensure controls contains the 'direction' key before passing to car.update
        if 'direction' not in controls:
            controls['direction'] = 0  # Add a default direction value
        
        self.car.update(controls)
        
        # Update road objects
        collision, objects_passed = self.road_objects.update(self.car)
        
        # Handle collision
        if collision:
            self.collisions += 1
            self.sound_manager.play_collision()
        
        # Update score
        self.score += objects_passed * self.score_multiplier
        
        # Update sound
        self.sound_manager.update_engine_sound(self.car.speed, controls['braking'], controls['boost'])
        
        # Draw game
        self.draw_game()
        
        # Draw hand detection frame in a separate window
        cv2.imshow("Hand Gesture Detection", processed_frame)
        
        # Limit to 60 FPS
        self.clock.tick(60)
        
        return True
    
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
            title_rect = title_text.get_rect(center=(400, 200))
            self.screen.blit(title_text, title_rect)
            
            # Draw loading message
            font_message = pygame.font.SysFont(None, 36)
            message_text = font_message.render(message, True, (50, 50, 150))
            message_rect = message_text.get_rect(center=(400, 300))
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
        title_rect = title_text.get_rect(center=(400, 200))
        self.screen.blit(title_text, title_rect)
        
        # Draw error message
        font_message = pygame.font.SysFont(None, 36)
        message_text = font_message.render(message, True, (100, 0, 0))
        message_rect = message_text.get_rect(center=(400, 300))
        self.screen.blit(message_text, message_rect)
        
        # Draw exit instruction
        font_exit = pygame.font.SysFont(None, 30)
        exit_text = font_exit.render("Press any key to exit...", True, (100, 0, 0))
        exit_rect = exit_text.get_rect(center=(400, 400))
        self.screen.blit(exit_text, exit_rect)
        
        pygame.display.flip()
        
        # Wait for key press
        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or event.type == pygame.KEYDOWN:
                    waiting = False

    def find_available_camera(self):
        """Find the first available camera."""
        for index in range(10):  # Check first 10 camera indices
            cap = cv2.VideoCapture(index)
            if cap.isOpened():  # Added the missing dot before isOpened()
                print(f"Camera index {index} is working")
                cap.release()
                return index
            else:
                print(f"Camera index {index} is not available")
        
        # If no camera found, handle gracefully
        print("No cameras available. Please connect a camera and try again.")
        pygame.quit()
        sys.exit()

    def __del__(self):
        """Clean up resources when the object is destroyed."""
        if hasattr(self, 'cap') and self.cap is not None:
            self.cap.release()

class RoadObjects:
    # ...existing code...
    
    def update(self, car):
        collision = False
        objects_passed = 0
        
        # Your existing update logic here...
        # ...existing code...
        
        # Before any return statement, ensure we return the required values
        return collision, objects_passed

def main():
    # Initialize pygame
    pygame.init()
    
    # Set up the display
    screen_width, screen_height = 800, 600
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Hand Movement Game")
    
    # Create game UI
    game_ui = GameUI(screen, screen_width, screen_height)
    
    # Game states
    game_running = False
    
    # Main game loop
    while True:
        screen.fill((240, 240, 240))  # Light gray background
        
        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left mouse button
                    action = game_ui.check_button_click(event.pos)
                    if action == 'run_game':
                        game_running = True
                        print("Game started!")
        
        # Draw UI elements
        game_ui.draw_buttons()
        
        # If game is running, draw game elements
        if game_running:
            # Game logic here
            pass
        
        pygame.display.flip()
        pygame.time.Clock().tick(60)

if __name__ == "__main__":
    main()