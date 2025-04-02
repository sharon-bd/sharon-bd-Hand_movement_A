# game/car.py - Car class implementation

import pygame
import math

class Car:
    def __init__(self, x, y):
        # Position and movement properties
        self.x = x
        self.y = y
        self.speed = 0
        self.direction = 0  # -1 = left, 0 = straight, 1 = right
        self.max_speed = 5
        self.acceleration = 0.1
        self.deceleration = 0.2
        self.handling = 5  # How quickly the car can change direction
        
        # Visual properties
        self.width = 30
        self.height = 50
        self.color = (255, 0, 0)  # Red
        self.collision_color = (255, 255, 0)  # Yellow for collision flash
        
        # State properties
        self.boosting = False
        self.braking = False
        self.auto_stopping = False
        self.collision_flash = False
        self.collision_time = 0
        self.brake_start_time = 0
        self.boost_start_time = 0
        self.original_brake_speed = 0
        
    def update(self, controls):
        """Update car state based on controls from hand gestures."""
        # Add default value for direction if not present
        target_direction = controls.get('direction', 0)  # Default to 0 if 'direction' is missing
        
        # Store current time
        current_time = pygame.time.get_ticks() / 1000  # Convert to seconds
        
        # Handle boosting (boost lasts for 1 second)
        if controls['boost'] and not self.braking:
            if not self.boosting:
                self.boosting = True
                self.boost_start_time = current_time
            
            # Apply boost effect (1 second of boosting)
            if current_time - self.boost_start_time < 1.0:
                self.speed = self.max_speed
            else:
                self.boosting = False
                
        # Handle braking
        if controls['braking'] and not self.boosting:
            if not self.braking:
                self.braking = True
                self.brake_start_time = current_time
                self.original_brake_speed = self.speed
                
            # Apply brake effect (gradual stopping over 1.5 seconds)
            brake_duration = 1.5
            elapsed_time = current_time - self.brake_start_time
            
            if elapsed_time >= brake_duration:
                # Car has completely stopped
                self.speed = 0
                self.braking = False
            else:
                # Gradually decrease speed
                deceleration_factor = elapsed_time / brake_duration
                self.speed = self.original_brake_speed * (1 - deceleration_factor)
        
        # Regular driving (not boosting or braking)
        elif not self.boosting and not self.braking:
            # Target speed from controls
            target_speed = controls['speed']
            
            # Smooth acceleration/deceleration
            if target_speed > self.speed:
                self.speed = min(target_speed, self.speed + self.acceleration)
            else:
                self.speed = max(target_speed, self.speed - self.deceleration)
            
            # Ensure speed is within limits
            self.speed = max(0, min(self.max_speed, self.speed))
        
        # Update direction based on controls (unless braking or boosting)
        if not self.braking:
            # Smooth direction change
            
            # Gradually change direction based on handling
            direction_change = self.handling * 0.1  # Adjust this factor to control responsiveness
            
            if target_direction > self.direction:
                self.direction = min(target_direction, self.direction + direction_change)
            elif target_direction < self.direction:
                self.direction = max(target_direction, self.direction - direction_change)
        
        # Update car position based on direction (only if moving)
        if self.speed > 0:
            # Move car based on direction and speed
            self.x += self.direction * self.speed * 2
        
        # Keep car within screen boundaries
        self.x = max(50, min(750, self.x))
        
        # Handle collision flash (if any)
        if self.collision_flash:
            if current_time - self.collision_time > 0.3:  # Flash for 0.3 seconds
                self.collision_flash = False
    
    def collide_with(self, obj_rect):
        """Check for collision with another object and trigger visual feedback."""
        car_rect = self.get_rect()
        
        if car_rect.colliderect(obj_rect):
            # Collision detected
            self.collision_flash = True
            self.collision_time = pygame.time.get_ticks() / 1000
            return True
        
        return False
    
    def get_rect(self):
        """Get the car's collision rectangle."""
        return pygame.Rect(
            self.x - self.width // 2,
            self.y - self.height // 2,
            self.width,
            self.height
        )
    
    def draw(self, screen):
        """Draw the car on the screen."""
        # Determine car color (flash if collision)
        color = self.collision_color if self.collision_flash else self.color
        
        # Change color when boosting or braking
        if self.boosting:
            color = (255, 165, 0)  # Orange for boost
        elif self.braking:
            color = (150, 0, 0)  # Dark red for braking
        
        # Create car rectangle
        car_rect = pygame.Rect(
            self.x - self.width // 2,
            self.y - self.height // 2,
            self.width,
            self.height
        )
        
        # Draw car body
        pygame.draw.rect(screen, color, car_rect)
        
        # Draw car details (windshield)
        pygame.draw.rect(screen, (30, 30, 60), 
                        (self.x - self.width // 2 + 5, 
                         self.y - self.height // 2 + 10, 
                         self.width - 10, 15))
        
        # Draw car headlights
        pygame.draw.circle(screen, (255, 255, 100), 
                          (int(self.x - self.width // 3), int(self.y + self.height // 2 - 5)), 3)
        pygame.draw.circle(screen, (255, 255, 100), 
                          (int(self.x + self.width // 3), int(self.y + self.height // 2 - 5)), 3)
        
        # Draw boost flames if boosting
        if self.boosting:
            flame_points = [
                (self.x - 5, self.y + self.height // 2 + 5),
                (self.x + 5, self.y + self.height // 2 + 5),
                (self.x, self.y + self.height // 2 + 15 + int(5 * math.sin(pygame.time.get_ticks() / 50)))
            ]
            pygame.draw.polygon(screen, (255, 165, 0), flame_points)  # Orange flame
            
            inner_flame_points = [
                (self.x - 3, self.y + self.height // 2 + 5),
                (self.x + 3, self.y + self.height // 2 + 5),
                (self.x, self.y + self.height // 2 + 10 + int(3 * math.sin(pygame.time.get_ticks() / 30)))
            ]
            pygame.draw.polygon(screen, (255, 255, 0), inner_flame_points)  # Yellow inner flame
        
        # Draw brake lights if braking
        if self.braking:
            pygame.draw.rect(screen, (255, 0, 0),
                           (self.x - self.width // 2 + 2, self.y + self.height // 2 - 8, 5, 3))
            pygame.draw.rect(screen, (255, 0, 0),
                           (self.x + self.width // 2 - 7, self.y + self.height // 2 - 8, 5, 3))