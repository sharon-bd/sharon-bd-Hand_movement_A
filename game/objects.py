# game/objects.py - Road objects implementation

import pygame
import random
import math

class RoadObject:
    def __init__(self, x, y, size, color, object_type=0, speed_multiplier=1.0, use_effects=True):
        self.x = x
        self.y = y
        self.size = size
        self.color = color
        self.type = object_type  # 0=circle, 1=square, 2=triangle
        self.passed = False
        self.speed_multiplier = speed_multiplier
        self.angle = 0  # For rotation animations
        self.use_effects = use_effects
    
    def update(self, car_speed):
        """Update object position based on car speed."""
        # Move object down the road relative to car speed
        self.y += car_speed * 2 * self.speed_multiplier
        
        # Animate rotation for more visual interest
        self.angle = (self.angle + 2) % 360
    
    def draw(self, screen):
        """Draw the object on the screen."""
        if not self.use_effects:
            # Simple drawing without effects
            pygame.draw.rect(screen, self.color, self.get_rect())
            return
            
        # Original drawing code with effects
        if self.type == 0:
            # Draw circle
            pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.size)
            
            # Add detail (concentric circles)
            inner_color = (max(0, self.color[0] - 50), 
                          max(0, self.color[1] - 50), 
                          max(0, self.color[2] - 50))
            pygame.draw.circle(screen, inner_color, (int(self.x), int(self.y)), self.size // 2)
            
        elif self.type == 1:
            # Draw rotated square
            points = []
            for i in range(4):
                angle_rad = math.radians(self.angle + i * 90)
                px = self.x + self.size * math.cos(angle_rad)
                py = self.y + self.size * math.sin(angle_rad)
                points.append((px, py))
            
            pygame.draw.polygon(screen, self.color, points)
            
            # Add detail (inner square)
            inner_points = []
            inner_size = self.size * 0.6
            for i in range(4):
                angle_rad = math.radians(self.angle + i * 90)
                px = self.x + inner_size * math.cos(angle_rad)
                py = self.y + inner_size * math.sin(angle_rad)
                inner_points.append((px, py))
            
            inner_color = (min(255, self.color[0] + 50), 
                           min(255, self.color[1] + 50), 
                           min(255, self.color[2] + 50))
            pygame.draw.polygon(screen, inner_color, inner_points)
            
        else:
            # Draw triangle
            points = []
            for i in range(3):
                angle_rad = math.radians(self.angle + i * 120)
                px = self.x + self.size * math.cos(angle_rad)
                py = self.y + self.size * math.sin(angle_rad)
                points.append((px, py))
            
            pygame.draw.polygon(screen, self.color, points)
            
            # Add detail (inner triangle)
            inner_points = []
            inner_size = self.size * 0.6
            for i in range(3):
                angle_rad = math.radians(self.angle + i * 120)
                px = self.x + inner_size * math.cos(angle_rad)
                py = self.y + inner_size * math.sin(angle_rad)
                inner_points.append((px, py))
            
            inner_color = (min(255, self.color[0] + 50), 
                          min(255, self.color[1] + 50), 
                          min(255, self.color[2] + 50))
            pygame.draw.polygon(screen, inner_color, inner_points)
    
    def get_rect(self):
        """Get the object's collision rectangle."""
        # Create a square bounding box for collision detection
        return pygame.Rect(
            self.x - self.size,
            self.y - self.size,
            self.size * 2,
            self.size * 2
        )

class PowerUp(RoadObject):
    def __init__(self, x, y, power_type, use_effects=True):
        # Power types: 0=boost, 1=shield, 2=point multiplier
        super().__init__(x, y, 15, self.get_color_for_type(power_type), 0, 1.0, use_effects)
        self.power_type = power_type
        self.pulse_factor = 0
        self.pulse_direction = 1
    
    def get_color_for_type(self, power_type):
        """Get color based on power-up type."""
        if power_type == 0:  # Boost
            return (255, 165, 0)  # Orange
        elif power_type == 1:  # Shield
            return (0, 191, 255)  # Deep sky blue
        else:  # Point multiplier
            return (255, 215, 0)  # Gold
    
    def update(self, car_speed):
        """Update power-up position and animation."""
        super().update(car_speed)
        
        # Pulsing animation
        self.pulse_factor += 0.05 * self.pulse_direction
        if self.pulse_factor >= 1.0:
            self.pulse_direction = -1
        elif self.pulse_factor <= 0.0:
            self.pulse_direction = 1
    
    def draw(self, screen):
        """Draw the power-up with or without special effects."""
        if not self.use_effects:
            # Simple drawing without effects
            rect = self.get_rect()
            pygame.draw.rect(screen, self.color, rect)
            
            # Simple identifier based on power-up type
            if self.power_type == 0:  # Boost
                pygame.draw.line(screen, (255, 255, 255), 
                               (rect.centerx - 5, rect.centery), 
                               (rect.centerx + 5, rect.centery), 2)
            elif self.power_type == 1:  # Shield
                pygame.draw.circle(screen, (255, 255, 255), 
                                 (rect.centerx, rect.centery), 
                                 self.size // 2, 1)
            else:  # Point multiplier
                pygame.draw.line(screen, (255, 255, 255), 
                               (rect.centerx - 5, rect.centery - 5), 
                               (rect.centerx + 5, rect.centery + 5), 2)
                pygame.draw.line(screen, (255, 255, 255), 
                               (rect.centerx - 5, rect.centery + 5), 
                               (rect.centerx + 5, rect.centery - 5), 2)
            return
            
        # Original drawing code with effects
        # Outer glow effect
        glow_size = self.size + 5 + int(self.pulse_factor * 5)
        glow_color = list(self.color)
        glow_color[0] = min(255, glow_color[0] + 50)
        glow_color[1] = min(255, glow_color[1] + 50)
        glow_color[2] = min(255, glow_color[2] + 50)
        glow_alpha = int(100 + self.pulse_factor * 155)
        
        # Create a surface with per-pixel alpha for the glow
        glow_surface = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surface, (*glow_color, glow_alpha), 
                          (glow_size, glow_size), glow_size)
        screen.blit(glow_surface, 
                   (int(self.x - glow_size), int(self.y - glow_size)))
        
        # Draw the main power-up
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.size)
        
        # Draw icon inside based on power-up type
        if self.power_type == 0:  # Boost - lightning bolt
            points = [
                (self.x - 5, self.y - 7),
                (self.x + 2, self.y - 2),
                (self.x - 2, self.y),
                (self.x + 5, self.y + 7)
            ]
            pygame.draw.lines(screen, (255, 255, 255), False, points, 2)
            
        elif self.power_type == 1:  # Shield - circle
            pygame.draw.circle(screen, (255, 255, 255), 
                              (int(self.x), int(self.y)), self.size // 2, 2)
            
        else:  # Point multiplier - 'x2'
            font = pygame.font.SysFont(None, 16)
            text = font.render('x2', True, (255, 255, 255))
            text_rect = text.get_rect(center=(self.x, self.y))
            screen.blit(text, text_rect)

class RoadObjectManager:
    def __init__(self, obstacle_frequency=0.02, speed_multiplier=1.0, use_effects=True):
        self.objects = []
        self.obstacle_frequency = obstacle_frequency
        self.speed_multiplier = speed_multiplier
        self.power_up_chance = 0.3  # 30% chance of power-up instead of obstacle
        self.last_spawn_time = 0
        self.min_spawn_interval = 0.5  # Minimum time between spawns in seconds
        self.active_camera = 0  # Default to first camera (index 0)
        self.use_effects = use_effects  # Toggle for using advanced visual effects
    
    def set_active_camera(self, camera_index):
        """
        Set which camera to use as the active one.
        
        Args:
            camera_index (int): Index of the camera to use (0 or 1)
        
        Returns:
            bool: True if camera switch was successful, False otherwise
        """
        if camera_index in [0, 1]:
            self.active_camera = camera_index
            return True
        return False
    
    def get_active_camera(self):
        """
        Get the currently active camera index.
        
        Returns:
            int: Index of the currently active camera (0 or 1)
        """
        return self.active_camera
    
    def set_effects(self, enabled):
        """Enable or disable advanced visual effects."""
        self.use_effects = enabled
        # Update existing objects
        for obj in self.objects:
            obj.use_effects = enabled
    
    def update(self, car):
        """Update all road objects and check for collisions."""
        current_time = pygame.time.get_ticks() / 1000  # Current time in seconds
        collision_occurred = False
        objects_passed = 0
        
        # Add a new object with certain probability and timing constraints
        if (len(self.objects) < 10 and 
            random.random() < self.obstacle_frequency and 
            current_time - self.last_spawn_time >= self.min_spawn_interval):
            
            # Decide if this is a regular obstacle or power-up
            is_power_up = random.random() < self.power_up_chance
            
            if is_power_up:
                # Create a power-up
                x_pos = random.randint(320, 480)  # Random position on road
                power_type = random.randint(0, 2)  # Random power-up type
                self.objects.append(PowerUp(x_pos, -20, power_type, self.use_effects))
            else:
                # Create a regular obstacle
                object_type = random.randint(0, 2)
                x_pos = random.randint(320, 480)
                y_pos = -20  # Just above the visible screen
                color = (
                    random.randint(50, 200), 
                    random.randint(50, 200), 
                    random.randint(50, 200)
                )
                size = random.randint(15, 25)
                
                self.objects.append(RoadObject(
                    x_pos, y_pos, size, color, object_type, 
                    self.speed_multiplier, self.use_effects
                ))
            
            self.last_spawn_time = current_time
        
        # Update position of all objects and check for collisions/passes
        for obj in self.objects[:]:  # Use a copy of the list for safe modification
            obj.update(car.speed)
            
            # Check for collision with the car
            if car.collide_with(obj.get_rect()):
                # Handle collision
                collision_occurred = True
                self.objects.remove(obj)
                continue
            
            # Check if car has passed the object
            if not obj.passed and obj.y > car.y + car.height:
                obj.passed = True
                objects_passed += 1
            
          # Remove objects that exit the screen
            if obj.y > 650:
                self.objects.remove(obj)
        
        return collision_occurred, objects_passed
        
    def draw(self, screen):
        """Draw all road objects on the screen."""
        for obj in self.objects:
            obj.draw(screen)