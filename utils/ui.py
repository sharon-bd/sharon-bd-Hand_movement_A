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