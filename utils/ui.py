# utils/ui.py - UI elements for the game

import pygame
import config

class GameUI:
    def __init__(self, screen, game_mode):
        self.screen = screen
        self.game_mode = game_mode
        self.mode_settings = config.GAME_MODES[game_mode]
        
        # Define colors
        self.text_color = (20, 20, 100)
        self.warning_color = (255, 50, 50)
        self.highlight_color = (50, 200, 50)
        self.panel_color = (220, 220, 240, 180)  # Semi-transparent
        
        # UI elements positions
        self.panel_rect = pygame.Rect(10, 10, 200, 180)
        
        # Create mute button
        self.mute_button_rect = pygame.Rect(20, 550, 40, 40)
        self.sound_muted = False
    
    def draw(self, score, collisions, speed, time_elapsed, time_limit=None):
        """Draw all UI elements."""
        # Draw stats panel background
        panel_surface = pygame.Surface((self.panel_rect.width, self.panel_rect.height), pygame.SRCALPHA)
        panel_surface.fill(self.panel_color)
        self.screen.blit(panel_surface, self.panel_rect.topleft)
        
        # Draw game mode
        font_mode = pygame.font.SysFont(None, 24)
        mode_text = font_mode.render(f"Mode: {self.mode_settings['name']}", True, self.text_color)
        self.screen.blit(mode_text, (self.panel_rect.left + 10, self.panel_rect.top + 10))
        
        # Draw score
        font_stats = pygame.font.SysFont(None, 30)
        score_text = font_stats.render(f"Score: {int(score)}", True, self.highlight_color)
        self.screen.blit(score_text, (self.panel_rect.left + 10, self.panel_rect.top + 40))
        
        # Draw collisions
        collision_color = self.warning_color if collisions > 0 else self.text_color
        collision_text = font_stats.render(f"Collisions: {collisions}", True, collision_color)
        self.screen.blit(collision_text, (self.panel_rect.left + 10, self.panel_rect.top + 70))
        
        # Draw speed
        speed_text = font_stats.render(f"Speed: {speed:.1f}", True, self.text_color)
        self.screen.blit(speed_text, (self.panel_rect.left + 10, self.panel_rect.top + 100))
        
        # Draw time (format as MM:SS)
        minutes = int(time_elapsed) // 60
        seconds = int(time_elapsed) % 60
        time_str = f"{minutes:02d}:{seconds:02d}"
        
        # Change color if time limit is close
        time_color = self.text_color
        if time_limit:
            time_left = time_limit - time_elapsed
            if time_left < 10:
                time_color = self.warning_color
            time_str = f"Time: {time_str} / {int(time_limit)//60:02d}:{int(time_limit)%60:02d}"
        else:
            time_str = f"Time: {time_str}"
            
        time_text = font_stats.render(time_str, True, time_color)
        self.screen.blit(time_text, (self.panel_rect.left + 10, self.panel_rect.top + 130))
        
        # Draw mute button
        self.draw_mute_button()
    
    def draw_mute_button(self):
        """Draw mute/unmute button."""
        # Draw button background
        button_color = (200, 50, 50) if self.sound_muted else (50, 200, 50)
        pygame.draw.rect(self.screen, button_color, self.mute_button_rect)
        pygame.draw.rect(self.screen, (0, 0, 0), self.mute_button_rect, 2)  # Black border
        
        # Draw speaker icon
        speaker_color = (255, 255, 255)  # White icon
        
        # Draw speaker base
        pygame.draw.rect(self.screen, speaker_color, 
                        (self.mute_button_rect.left + 10, self.mute_button_rect.top + 15, 8, 10))
        
        # Draw speaker cone
        points = [
            (self.mute_button_rect.left + 18, self.mute_button_rect.top + 10),
            (self.mute_button_rect.left + 28, self.mute_button_rect.top + 5),
            (self.mute_button_rect.left + 28, self.mute_button_rect.top + 35),
            (self.mute_button_rect.left + 18, self.mute_button_rect.top + 30)
        ]
        pygame.draw.polygon(self.screen, speaker_color, points)
        
        # Draw X over speaker if muted
        if self.sound_muted:
            pygame.draw.line(self.screen, (255, 0, 0), 
                            (self.mute_button_rect.left + 8, self.mute_button_rect.top + 8),
                            (self.mute_button_rect.left + 32, self.mute_button_rect.top + 32), 3)
            pygame.draw.line(self.screen, (255, 0, 0), 
                            (self.mute_button_rect.left + 32, self.mute_button_rect.top + 8),
                            (self.mute_button_rect.left + 8, self.mute_button_rect.top + 32), 3)
        
        # Draw label for mute button
        font = pygame.font.SysFont(None, 24)
        mute_label = font.render("Sound", True, (0, 0, 0))
        self.screen.blit(mute_label, (self.mute_button_rect.left - 5, self.mute_button_rect.bottom + 5))
    
    def check_mute_button_click(self, pos):
        """Check if mouse clicked on mute button and toggle mute state."""
        if self.mute_button_rect.collidepoint(pos):
            self.sound_muted = not self.sound_muted
            return True
        return False

class MenuUI:
    """UI class for the main menu screen.
    Separate from GameUI to avoid conflicts with the in-game UI."""
    
    def __init__(self, screen):
        self.screen = screen
        self.screen_width, self.screen_height = screen.get_size()
        self.font = pygame.font.SysFont('Arial', 24)
        self.buttons = {}
        self.create_buttons()
        
    def create_buttons(self):
        # Define run button
        run_button = {
            'rect': pygame.Rect(self.screen_width // 2 - 50, self.screen_height - 80, 100, 40),
            'color': (50, 200, 50),
            'hover_color': (100, 250, 100),
            'text': 'Run Game',
            'action': 'run_game'
        }
        self.buttons['run_game'] = run_button
    
    def draw_buttons(self):
        mouse_pos = pygame.mouse.get_pos()
        for button_name, button in self.buttons.items():
            # Change color when hovering
            color = button['hover_color'] if button['rect'].collidepoint(mouse_pos) else button['color']
            
            # Draw button rectangle
            pygame.draw.rect(self.screen, color, button['rect'])
            pygame.draw.rect(self.screen, (0, 0, 0), button['rect'], 2)  # Border
            
            # Draw button text
            text_surf = self.font.render(button['text'], True, (0, 0, 0))
            text_rect = text_surf.get_rect(center=button['rect'].center)
            self.screen.blit(text_surf, text_rect)
    
    def check_button_click(self, mouse_pos):
        for button_name, button in self.buttons.items():
            if button['rect'].collidepoint(mouse_pos):
                return button['action']
        return None