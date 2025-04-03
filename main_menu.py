# main_menu.py - Game Main Menu
import pygame
import sys
import config

class Button:
    def __init__(self, x, y, width, height, text, color, hover_color, text_color, font_size=36):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.text_color = text_color
        self.font_size = font_size
        self.is_hovered = False
        
    def draw(self, screen):
        # Draw button rectangle
        color = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(screen, color, self.rect)
        pygame.draw.rect(screen, (0, 0, 0), self.rect, 2)  # Border
        
        # Draw button text
        font = pygame.font.SysFont(None, self.font_size)
        text_surf = font.render(self.text, True, self.text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)
    
    def check_hover(self, pos):
        self.is_hovered = self.rect.collidepoint(pos)
        return self.is_hovered
    
    def is_clicked(self, pos, click):
        return self.rect.collidepoint(pos) and click

class MainMenu:
    def __init__(self, screen):
        self.screen = screen
        self.screen_width, self.screen_height = screen.get_size()
        self.running = True
        self.selected_mode = config.DEFAULT_GAME_MODE
        
        # Define colors
        self.bg_color = (240, 240, 255)
        self.title_color = (20, 20, 100)
        self.button_color = (100, 100, 220)
        self.button_hover_color = (120, 120, 255)
        self.text_color = (255, 255, 255)
        self.description_color = (60, 60, 100)
        
        # Create buttons
        button_width = 300
        button_height = 60
        button_spacing = 20
        button_start_y = 200
        
        # Create buttons for each game mode
        self.mode_buttons = {}
        
        # Debug print to check game modes
        print("Available game modes:", list(config.GAME_MODES.keys()))
        
        # Create a button for each game mode
        for i, (mode_key, mode_info) in enumerate(config.GAME_MODES.items()):
            print(f"Creating button for mode: {mode_key} - {mode_info['name']}")
            y_pos = button_start_y + i * (button_height + button_spacing)
            self.mode_buttons[mode_key] = Button(
                self.screen_width // 2 - button_width // 2,
                y_pos,
                button_width,
                button_height,
                mode_info['name'],
                self.button_color,
                self.button_hover_color,
                self.text_color
            )
        
        # Start game button (positioned below mode buttons)
        last_y = button_start_y + len(config.GAME_MODES) * (button_height + button_spacing) + 20
        print(f"Creating start button at position: {self.screen_width // 2 - button_width // 2}, {last_y}")
        self.start_button = Button(
            self.screen_width // 2 - button_width // 2,
            last_y,
            button_width,
            button_height,
            "Start Game",
            (50, 150, 50),  # Green color
            (70, 180, 70),  # Hover green
            self.text_color,
            42  # Larger font for start button
        )
    
    def run(self):
        clock = pygame.time.Clock()
        self.running = True
        
        while self.running:
            # Get mouse position and reset click state
            mouse_pos = pygame.mouse.get_pos()
            mouse_clicked = False
            
            # Process events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None  # Exit game
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left click
                        mouse_clicked = True
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return None  # Exit to main menu
            
            # Handle button hovers and clicks
            for mode_key, button in self.mode_buttons.items():
                button.check_hover(mouse_pos)
                if button.is_clicked(mouse_pos, mouse_clicked):
                    self.selected_mode = mode_key
                    print(f"Selected mode: {mode_key}")
            
            # Check if start button is clicked
            self.start_button.check_hover(mouse_pos)
            if self.start_button.is_clicked(mouse_pos, mouse_clicked):
                self.running = False
                print(f"Starting game with mode: {self.selected_mode}")
                return self.selected_mode  # Return selected game mode
            
            # Draw menu
            self.draw()
            
            pygame.display.flip()
            clock.tick(60)
            
        return self.selected_mode
    
    def draw(self):
        # Fill background
        self.screen.fill(self.bg_color)
        
        # Draw title
        font_title = pygame.font.SysFont(None, 60)
        title_text = font_title.render("Hand Gesture Car Control", True, self.title_color)
        title_rect = title_text.get_rect(center=(self.screen_width//2, 100))
        self.screen.blit(title_text, title_rect)
        
        # Draw subtitle
        font_subtitle = pygame.font.SysFont(None, 36)
        subtitle_text = font_subtitle.render("Select Game Mode", True, self.title_color)
        subtitle_rect = subtitle_text.get_rect(center=(self.screen_width//2, 150))
        self.screen.blit(subtitle_text, subtitle_rect)
        
        # Draw mode buttons
        for mode_key, button in self.mode_buttons.items():
            # Highlight selected mode button
            original_color = button.color
            if mode_key == self.selected_mode:
                button.color = (50, 100, 200)  # Different color for selected mode
            
            button.draw(self.screen)
            button.color = original_color
        
        # Draw description of selected mode
        mode_info = config.GAME_MODES[self.selected_mode]
        font_desc = pygame.font.SysFont(None, 30)
        desc_text = font_desc.render(mode_info['description'], True, self.description_color)
        desc_rect = desc_text.get_rect(center=(self.screen_width//2, 450))
        self.screen.blit(desc_text, desc_rect)
        
        # Ensure start button is drawn
        self.start_button.draw(self.screen)
        
        # Debug output - add this to check if the button is being created
        print(f"Start button position: {self.start_button.rect}")