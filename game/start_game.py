#!/usr/bin/env python
# start_game.py - Main entry point for Hand Gesture Car Control System

import pygame
import cv2
import sys
import time
import os

# Import game modules
from main_menu import MainMenu
from game.car import Car
from game.objects import RoadObjectManager
from hand_detector.gestures import HandGestureDetector
from utils.camera import find_available_cameras, select_camera
from utils.sound import SoundManager
from utils.ui import GameUI
import config

class HandGestureCarGame:
    def __init__(self):
        # Initialize pygame
        pygame.init()
        
        # Setup display
        self.screen_width, self.screen_height = 800, 600
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Hand Gesture Car Control")
        
        # Show loading screen
        self.show_loading_message("Starting application...")
        
        # Game state
        self.game_active = False
        self.current_mode = config.DEFAULT_GAME_MODE
        
        # Initialize camera parameters
        self.cap = None
        self.selected_camera = None
        
        # Initialize core components
        self.detector = None
        self.sound_manager = None
        self.car = None
        self.road_objects = None
        self.game_ui = None
        self.clock = pygame.time.Clock()
    
    def init_camera(self):
        """Initialize the camera system."""
        self.show_loading_message("Checking for cameras...")
        
        # Find available cameras
        available_cameras = find_available_cameras()
        
        if not available_cameras:
            self.show_error("No cameras found", "Please connect a webcam and restart the application.")
            return False
        
        # Select camera
        self.selected_camera = select_camera(available_cameras)
        if self.selected_camera is None:
            self.show_error("No camera selected", "You must select a camera to continue.")
            return False
        
        # Initialize the selected camera
        self.cap = cv2.VideoCapture(self.selected_camera)
        if not self.cap.isOpened():
            self.show_error("Camera error", f"Failed to open camera {self.selected_camera}.")
            return False
        
        return True
    
    def init_game_components(self):
        """Initialize core game components."""
        self.show_loading_message("Initializing hand tracking...")
        
        # Initialize hand detection
        self.detector = HandGestureDetector()
        
        # Initialize sound
        self.show_loading_message("Loading sounds...")
        self.sound_manager = SoundManager()
        
        return True
    
    def setup_game(self, game_mode):
        """Set up a new game with specified mode."""
        # Get mode settings
        mode_settings = config.GAME_MODES[game_mode]
        
        # Initialize game objects
        self.car = Car(self.screen_width // 2, self.screen_height // 2)
        self.road_objects = RoadObjectManager(
            obstacle_frequency=mode_settings['obstacle_frequency'],
            speed_multiplier=mode_settings['obstacle_speed_multiplier']
        )
        
        # Initialize UI
        self.game_ui = GameUI(self.screen, game_mode)
        
        # Reset game state
        self.score = 0
        self.collisions = 0
        self.objects_passed = 0
        self.last_collision_time = 0
        self.collision_flash = False
        
        # Reset sound
        self.sound_manager.reset()
        
        return True
    
    def run(self):
        """Main application loop."""
        # First-time setup
        if not self.init_camera():
            return
        
        if not self.init_game_components():
            return
        
        self.show_loading_message("Ready to play!")
        time.sleep(1)  # Brief delay to show ready message
        
        # Main application loop
        running = True
        while running:
            # Show main menu if game is not active
            if not self.game_active:
                menu = MainMenu(self.screen)
                selected_mode = menu.run()
                
                if selected_mode is None:
                    running = False  # Exit the application
                    continue
                
                # Setup new game with selected mode
                self.current_mode = selected_mode
                if self.setup_game(selected_mode):
                    self.game_active = True
                else:
                    continue  # Stay in menu if setup fails
            
            # Run game loop if game is active
            if self.game_active:
                game_result = self.run_game_loop()
                if game_result == "quit":
                    running = False
                elif game_result == "menu":
                    self.game_active = False
        
        # Clean up and exit
        self.cleanup()
    
    def run_game_loop(self):
        """Run the main game loop."""
        paused = False
        
        while True:
            # Process events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "quit"
                
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if paused:
                            paused = False
                        else:
                            paused = True
                    
                    if event.key == pygame.K_q and paused:
                        return "menu"
                
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left click
                        if self.game_ui.check_mute_button_click(event.pos):
                            # Update sound manager's mute state
                            self.sound_manager.set_mute(self.game_ui.sound_muted)
            
            # If paused, show pause menu and continue to next frame
            if paused:
                self.draw_pause_menu()
                pygame.display.flip()
                self.clock.tick(60)
                continue
            
            # Read frame from webcam
            ret, frame = self.cap.read()
            if not ret:
                print("Error reading frame from camera, trying again...")
                # Try to reinitialize the camera
                self.cap.release()
                time.sleep(0.5)
                self.cap = cv2.VideoCapture(self.selected_camera)
                if not self.cap.isOpened():
                    print("Cannot reopen camera, returning to menu...")
                    return "menu"
                continue
            
            # Flip the image to act as a mirror
            frame = cv2.flip(frame, 1)
            
            # Detect hand gestures
            controls, processed_frame = self.detector.detect_gestures(frame)
            
            # Update car based on hand gestures
            self.car.update(controls)
            
            # Update road objects
            collision, objects_passed = self.road_objects.update(self.car)
            
            # Handle collision
            if collision:
                self.collisions += 1
                self.last_collision_time = time.time()
                self.collision_flash = True
                self.sound_manager.play_collision()
            
            # Update collision flash effect
            if self.collision_flash and time.time() - self.last_collision_time > 0.3:
                self.collision_flash = False
                
            # Update score
            self.objects_passed += objects_passed
            self.score = self.objects_passed - self.collisions * 2  # Collisions reduce score
            self.score = max(0, self.score)  # Ensure score doesn't go negative
            
            # Check for time limit if applicable
            current_time = pygame.time.get_ticks() / 1000
            time_limit = config.GAME_MODES[self.current_mode]['time_limit']
            if time_limit and current_time >= time_limit:
                self.game_over("Time's Up!")
                return "menu"
            
            # Update sound
            self.sound_manager.update_engine_sound(
                self.car.speed, 
                controls.get('braking', False), 
                controls.get('boost', False)
            )
            
            # Draw game screen
            self.draw_game(current_time)
            
            # Display webcam frame in separate window
            cv2.imshow("Hand Gesture Detection", processed_frame)
            
            # Exit if ESC key is pressed in the OpenCV window
            if cv2.waitKey(1) == 27:
                return "menu"
                
            # Limit to 60 frames per second
            self.clock.tick(60)
    
    def draw_game(self, current_time):
        """Draw the game screen."""
        # Fill background
        self.screen.fill((255, 255, 255))  # White background
        
        # Draw road
        road_color = (200, 200, 200)
        pygame.draw.rect(self.screen, road_color, (300, 0, 200, 600))
        
        # Draw road objects
        self.road_objects.draw(self.screen)
        
        # Draw car
        self.car.draw(self.screen)
        
        # Draw UI
        time_limit = config.GAME_MODES[self.current_mode]['time_limit']
        self.game_ui.draw(
            score=self.score,
            collisions=self.collisions,
            speed=self.car.speed,
            time_elapsed=current_time,
            time_limit=time_limit
        )
        
        # Update display
        pygame.display.flip()
    
    def draw_pause_menu(self):
        """Draw pause menu overlay."""
        # Semi-transparent overlay
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))  # Semi-transparent black
        self.screen.blit(overlay, (0, 0))
        
        # Pause title
        font_title = pygame.font.SysFont(None, 60)
        title_text = font_title.render("PAUSED", True, (255, 255, 255))
        title_rect = title_text.get_rect(center=(self.screen_width // 2, 200))
        self.screen.blit(title_text, title_rect)
        
        # Instructions
        font_instructions = pygame.font.SysFont(None, 36)
        
        resume_text = font_instructions.render("Press ESC to Resume", True, (255, 255, 255))
        resume_rect = resume_text.get_rect(center=(self.screen_width // 2, 300))
        self.screen.blit(resume_text, resume_rect)
        
        quit_text = font_instructions.render("Press Q to Quit to Menu", True, (255, 255, 255))
        quit_rect = quit_text.get_rect(center=(self.screen_width // 2, 350))
        self.screen.blit(quit_text, quit_rect)
    
    def game_over(self, reason="Game Over"):
        """Handle game over state."""
        # Display game over screen
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 192))  # More opaque black
        self.screen.blit(overlay, (0, 0))
        
        # Game over title
        font_title = pygame.font.SysFont(None, 72)
        title_text = font_title.render(reason, True, (255, 50, 50))
        title_rect = title_text.get_rect(center=(self.screen_width // 2, 200))
        self.screen.blit(title_text, title_rect)
        
        # Final score
        font_score = pygame.font.SysFont(None, 48)
        score_text = font_score.render(f"Final Score: {int(self.score)}", True, (255, 255, 255))
        score_rect = score_text.get_rect(center=(self.screen_width // 2, 300))
        self.screen.blit(score_text, score_rect)
        
        # Continue instructions
        font_continue = pygame.font.SysFont(None, 36)
        continue_text = font_continue.render("Press any key to continue...", True, (200, 200, 200))
        continue_rect = continue_text.get_rect(center=(self.screen_width // 2, 400))
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
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    waiting = False
    
    def show_loading_message(self, message):
        """Display a loading message."""
        try:
            self.screen.fill((240, 240, 255))  # Light blue background
            
            # Draw title
            font_title = pygame.font.SysFont(None, 60)
            title_text = font_title.render("Hand Gesture Car Control", True, (20, 20, 100))
            title_rect = title_text.get_rect(center=(self.screen_width // 2, 200))
            self.screen.blit(title_text, title_rect)
            
            # Draw loading message
            font_message = pygame.font.SysFont(None, 36)
            message_text = font_message.render(message, True, (50, 50, 150))
            message_rect = message_text.get_rect(center=(self.screen_width // 2, 300))
            self.screen.blit(message_text, message_rect)
            
            pygame.display.flip()
        except Exception as e:
            print(f"Error displaying loading message: {e}")
    
    def show_error(self, title, message):
        """Display an error message and wait for user acknowledgment."""
        try:
            self.screen.fill((255, 200, 200))  # Light red background
            
            # Draw error title
            font_title = pygame.font.SysFont(None, 48)
            title_text = font_title.render(title, True, (200, 0, 0))
            title_rect = title_text.get_rect(center=(self.screen_width // 2, 200))
            self.screen.blit(title_text, title_rect)
            
            # Draw error message
            font_message = pygame.font.SysFont(None, 36)
            message_text = font_message.render(message, True, (150, 0, 0))
            message_rect = message_text.get_rect(center=(self.screen_width // 2, 300))
            self.screen.blit(message_text, message_rect)
            
            # Draw instruction
            font_instruction = pygame.font.SysFont(None, 30)
            instruction_text = font_instruction.render("Press any key to continue...", True, (100, 0, 0))
            instruction_rect = instruction_text.get_rect(center=(self.screen_width // 2, 400))
            self.screen.blit(instruction_text, instruction_rect)
            
            pygame.display.flip()
            
            # Wait for key press
            waiting = True
            while waiting:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()
                    if event.type == pygame.KEYDOWN:
                        waiting = False
                        
            return False  # Error occurred
        except Exception as e:
            print(f"Error displaying error message: {e}")
            return False
    
    def cleanup(self):
        """Clean up resources before exit."""
        if self.cap and self.cap.isOpened():
            self.cap.release()
        cv2.destroyAllWindows()
        pygame.quit()

def main():
    game = HandGestureCarGame()
    game.run()
    print("Game exited normally")

if __name__ == "__main__":
    main()