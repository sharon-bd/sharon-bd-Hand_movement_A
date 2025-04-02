import pygame
import sys

class GameUI:
    def __init__(self, screen, screen_width, screen_height):
        self.screen = screen
        self.screen_width = screen_width
        self.screen_height = screen_height
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
