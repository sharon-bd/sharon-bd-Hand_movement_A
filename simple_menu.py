import pygame
import sys
import config
import os
import time

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

class SimpleMenu:
    def __init__(self, screen=None):
        # Initialize pygame if needed
        if not pygame.get_init():
            pygame.init()
            
        # Setup display if not provided
        if screen is None:
            self.screen_width, self.screen_height = 800, 600
            self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
            pygame.display.set_caption("Hand Gesture Car Control")
        else:
            self.screen = screen
            self.screen_width, self.screen_height = screen.get_size()
        
        # Define colors
        self.bg_color = (240, 240, 255)
        self.title_color = (20, 20, 100)
        self.text_color = (0, 0, 0)
        
        # Create run button (centered and positioned near bottom)
        button_width = 300
        button_height = 60
        self.run_button = Button(
            self.screen_width // 2 - button_width // 2,
            self.screen_height - 150,
            button_width,
            button_height,
            "Run Game",
            (50, 150, 50),  # Green color
            (70, 180, 70),  # Hover green
            (255, 255, 255),  # White text
            42  # Larger font
        )
    
    def run(self):
        clock = pygame.time.Clock()
        running = True
        
        while running:
            # Get mouse position and reset click state
            mouse_pos = pygame.mouse.get_pos()
            mouse_clicked = False
            
            # Process events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False  # Exit game
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left click
                        mouse_clicked = True
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return False  # Exit to main menu
            
            # Handle button hover and click
            self.run_button.check_hover(mouse_pos)
            if self.run_button.is_clicked(mouse_pos, mouse_clicked):
                return True  # Start the game
            
            # Draw menu
            self.draw()
            
            pygame.display.flip()
            clock.tick(60)
        
        return False
    
    def draw(self):
        # Fill background
        self.screen.fill(self.bg_color)
        
        # Draw title
        font_title = pygame.font.SysFont(None, 60)
        title_text = font_title.render("Hand Gesture Car Control", True, self.title_color)
        title_rect = title_text.get_rect(center=(self.screen_width//2, 200))
        self.screen.blit(title_text, title_rect)
        
        # Draw subtitle
        font_subtitle = pygame.font.SysFont(None, 30)
        subtitle_text = font_subtitle.render("Control a virtual car using hand gestures", True, self.title_color)
        subtitle_rect = subtitle_text.get_rect(center=(self.screen_width//2, 260))
        self.screen.blit(subtitle_text, subtitle_rect)
        
        # Draw instructions
        font_instructions = pygame.font.SysFont(None, 36)
        instructions_text = font_instructions.render("Click the button below to start", True, self.text_color)
        instructions_rect = instructions_text.get_rect(center=(self.screen_width//2, 330))
        self.screen.blit(instructions_text, instructions_rect)
        
        # Draw run button
        self.run_button.draw(self.screen)

def main():
    print("Starting Hand Gesture Car Control System...")
    
    # Setup directory and environment
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    sys.path.insert(0, script_dir)
    
    # Show menu
    menu = SimpleMenu()
    if menu.run():
        print("Starting the game...")
        
        pygame.quit()  # Clean up pygame before importing game modules
        
        try:
            # Import and run game modules here
            print("Game would start here!")
            print("Loading main application...")
            
            # Wait for modules to load
            time.sleep(1)
            
            # You would import your main game here, for example:
            # from main import start_game
            # start_game()
            
        except ImportError as e:
            print(f"Error importing game modules: {e}")
            print("Make sure all required packages are installed.")
        except Exception as e:
            print(f"Error running game: {e}")
            import traceback
            traceback.print_exc()
    
    else:
        print("Menu closed, exiting.")

if __name__ == "__main__":
    main()
