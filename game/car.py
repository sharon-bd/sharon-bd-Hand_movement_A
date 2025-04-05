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
        self.acceleration = 0.15     # מהירות האצה מופחתת לשליטה טובה יותר
        self.deceleration = 0.2      # מהירות האטה מוגברת
        self.handling = 5            # ערך נמוך יותר להגה יציב יותר
        
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
        
        # Add movement smoothing
        self.target_direction = 0
        self.target_speed = 0
        self.direction_smoothing = 0.8  # החלקת היגוי חזקה יותר
        self.speed_smoothing = 0.7      # החלקת מהירות חזקה יותר
        
    def update(self, controls):
        """Update car state based on controls from hand gestures."""
        # בדוק ומפה את המפתחות שחסרים
        if 'speed' not in controls and 'throttle' in controls:
            controls['speed'] = controls['throttle'] * self.max_speed
        
        if 'direction' not in controls and 'steering' in controls:
            controls['direction'] = controls['steering']
            
        # Add default value for direction if not present
        target_direction = controls.get('direction', 0)  # Default to 0 if 'direction' is missing
        
        # Store current time
        current_time = pygame.time.get_ticks() / 1000  # Convert to seconds
        
        # Apply smoothing for direction changes
        self.target_direction = target_direction
        direction_change = (self.target_direction - self.direction) * (1 - self.direction_smoothing)
        self.direction += direction_change
        
        # Handle boosting (boost lasts for 1 second)
        if controls['boost'] and not self.braking:
            if not self.boosting:
                self.boosting = True
                self.boost_start_time = current_time
            
            # Apply boost effect (1 second of boosting)
            if current_time - self.boost_start_time < 1.0:
                self.target_speed = self.max_speed
                # בוסט מקבל החלקה מהירה יותר
                self.speed = self.speed * 0.5 + self.target_speed * 0.5
            else:
                self.boosting = False
                
        # Handle braking
        elif controls['braking'] and not self.boosting:
            if not self.braking:
                self.braking = True
                self.brake_start_time = current_time
                self.original_brake_speed = self.speed
                
            # Apply brake effect (gradual stopping over 1.5 seconds)
            brake_duration = 1.0  # קיצור זמן הבלימה ל-1 שניה
            elapsed_time = current_time - self.brake_start_time
            
            if elapsed_time >= brake_duration:
                # Car has completely stopped
                self.speed = 0
                self.braking = False
            else:
                # בלימה חזקה יותר בהתחלה ועדינה יותר בסוף
                deceleration_factor = (elapsed_time / brake_duration) ** 0.5  # שימוש בחזקה להאטה מהירה יותר
                self.speed = self.original_brake_speed * (1 - deceleration_factor)
        
        # Regular driving (not boosting or braking)
        elif not self.boosting and not self.braking:
            # Target speed from controls
            self.target_speed = controls['speed']
            
            # Apply smooth acceleration/deceleration with improved responsiveness
            if self.target_speed > self.speed:
                # אצה מהירה יותר כשהמכונית כבר בתנועה
                acceleration_factor = self.acceleration * (1 + self.speed / self.max_speed)
                self.speed = min(self.target_speed, self.speed + acceleration_factor)
            else:
                self.speed = max(self.target_speed, self.speed - self.deceleration)
            
            # Ensure speed is within limits
            self.speed = max(0, min(self.max_speed, self.speed))
        
        # Update car position based on direction (only if moving)
        if self.speed > 0:
            # התאמה לא-לינארית של ההיגוי למהירות
            # מהירות גבוהה = פחות היגוי להגברת היציבות
            effective_direction = self.direction * (1.0 - (self.speed / self.max_speed) * 0.3)
            
            # סקלת פניה תלויית מהירות
            turn_scale = 2.0 + self.speed * 0.5  # מהירות גבוהה יותר = פניה חדה יותר
            
            # Move car based on direction and speed with speed-dependent steering
            self.x += effective_direction * turn_scale
        
        # Keep car within screen boundaries with gradual steering correction
        screen_margin = 50
        if self.x < screen_margin:
            # הוספת תיקון היגוי אוטומטי כשמתקרבים לקצה המסך
            self.x = screen_margin
            # החזרת ההיגוי למרכז כשמגיעים לקצה
            self.direction = self.direction * 0.5
        elif self.x > 750:
            self.x = 750
            self.direction = self.direction * 0.5
        
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
            
            # האט את המכונית קלות בעת התנגשות
            self.speed = max(0, self.speed * 0.8)
            
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
        
        # חישוב זווית הטיה למכונית (מבוסס על כיוון)
        tilt_angle = -self.direction * 20  # מקסימום 20 מעלות הטיה
        
        # יצירת נקודות המכונית המוטה
        car_points = [
            (-self.width // 2, -self.height // 2),  # top-left
            (self.width // 2, -self.height // 2),   # top-right
            (self.width // 2, self.height // 2),    # bottom-right
            (-self.width // 2, self.height // 2)    # bottom-left
        ]
        
        # סיבוב הנקודות בהתאם לזווית ההטיה
        rotated_points = []
        cos_angle = math.cos(math.radians(tilt_angle))
        sin_angle = math.sin(math.radians(tilt_angle))
        
        for x, y in car_points:
            # סיבוב הנקודה
            rotated_x = x * cos_angle - y * sin_angle
            rotated_y = x * sin_angle + y * cos_angle
            
            # הוספת מיקום המכונית
            rotated_points.append((int(self.x + rotated_x), int(self.y + rotated_y)))
        
        # ציור המכונית המוטה
        pygame.draw.polygon(screen, color, rotated_points)
        
        # ציור חלקים נוספים של המכונית בהתאם להטיה
        # חלון קדמי
        windshield_width = self.width - 10
        windshield_height = 15
        windshield_y_offset = -10
        
        windshield_points = [
            (-windshield_width // 2, windshield_y_offset - windshield_height // 2),
            (windshield_width // 2, windshield_y_offset - windshield_height // 2),
            (windshield_width // 2, windshield_y_offset + windshield_height // 2),
            (-windshield_width // 2, windshield_y_offset + windshield_height // 2)
        ]
        
        rotated_windshield = []
        for x, y in windshield_points:
            # סיבוב הנקודה
            rotated_x = x * cos_angle - y * sin_angle
            rotated_y = x * sin_angle + y * cos_angle
            
            # הוספת מיקום המכונית
            rotated_windshield.append((int(self.x + rotated_x), int(self.y + rotated_y)))
        
        # ציור חלון קדמי
        pygame.draw.polygon(screen, (30, 30, 60), rotated_windshield)
        
        # פנסים קדמיים
        headlight_offset_y = self.height // 2 - 5
        headlight_offset_x = self.width // 3
        
        # מיקום עם סיבוב
        left_headlight_x = -headlight_offset_x * cos_angle - headlight_offset_y * sin_angle + self.x
        left_headlight_y = -headlight_offset_x * sin_angle + headlight_offset_y * cos_angle + self.y
        
        right_headlight_x = headlight_offset_x * cos_angle - headlight_offset_y * sin_angle + self.x
        right_headlight_y = headlight_offset_x * sin_angle + headlight_offset_y * cos_angle + self.y
        
        # ציור פנסים
        pygame.draw.circle(screen, (255, 255, 100), 
                         (int(left_headlight_x), int(left_headlight_y)), 3)
        pygame.draw.circle(screen, (255, 255, 100), 
                         (int(right_headlight_x), int(right_headlight_y)), 3)
        
        # Draw boost flames if boosting
        if self.boosting:
            # מיקום הלהבות בתחתית המכונית עם סיבוב
            flame_base_y = self.height // 2 + 5
            
            flame_center_x = 0
            flame_center_y = flame_base_y
            
            rotated_flame_x = flame_center_x * cos_angle - flame_center_y * sin_angle + self.x
            rotated_flame_y = flame_center_x * sin_angle + flame_center_y * cos_angle + self.y
            
            flame_width = 10
            flame_length = 15 + int(5 * math.sin(pygame.time.get_ticks() / 50))
            
            # נקודות הלהבה החיצונית
            left_x = -flame_width // 2 * cos_angle - flame_base_y * sin_angle + self.x
            left_y = -flame_width // 2 * sin_angle + flame_base_y * cos_angle + self.y
            
            right_x = flame_width // 2 * cos_angle - flame_base_y * sin_angle + self.x
            right_y = flame_width // 2 * sin_angle + flame_base_y * cos_angle + self.y
            
            # נקודת קצה הלהבה
            tip_x = flame_center_x * cos_angle - (flame_base_y + flame_length) * sin_angle + self.x
            tip_y = flame_center_x * sin_angle + (flame_base_y + flame_length) * cos_angle + self.y
            
            # ציור הלהבה החיצונית
            flame_points = [(int(left_x), int(left_y)), 
                            (int(right_x), int(right_y)), 
                            (int(tip_x), int(tip_y))]
            pygame.draw.polygon(screen, (255, 165, 0), flame_points)  # Orange flame
            
            # להבה פנימית קטנה יותר
            inner_flame_width = flame_width * 0.6
            inner_flame_length = flame_length * 0.7
            
            inner_left_x = -inner_flame_width // 2 * cos_angle - flame_base_y * sin_angle + self.x
            inner_left_y = -inner_flame_width // 2 * sin_angle + flame_base_y * cos_angle + self.y
            
            inner_right_x = inner_flame_width // 2 * cos_angle - flame_base_y * sin_angle + self.x
            inner_right_y = inner_flame_width // 2 * sin_angle + flame_base_y * cos_angle + self.y
            
            inner_tip_x = flame_center_x * cos_angle - (flame_base_y + inner_flame_length) * sin_angle + self.x
            inner_tip_y = flame_center_x * sin_angle + (flame_base_y + inner_flame_length) * cos_angle + self.y
            
            # ציור הלהבה הפנימית
            inner_flame_points = [(int(inner_left_x), int(inner_left_y)), 
                                 (int(inner_right_x), int(inner_right_y)), 
                                 (int(inner_tip_x), int(inner_tip_y))]
            pygame.draw.polygon(screen, (255, 255, 0), inner_flame_points)  # Yellow inner flame
        
        # Draw brake lights if braking
        if self.braking:
            brake_light_width = 5
            brake_light_height = 3
            brake_light_offset_y = self.height // 2 - 8
            brake_light_offset_x = self.width // 2 - 7
            
            # מיקום אור בלם שמאלי
            left_brake_points = [
                (-brake_light_offset_x - brake_light_width, brake_light_offset_y),
                (-brake_light_offset_x, brake_light_offset_y),
                (-brake_light_offset_x, brake_light_offset_y + brake_light_height),
                (-brake_light_offset_x - brake_light_width, brake_light_offset_y + brake_light_height)
            ]
            
            # מיקום אור בלם ימני
            right_brake_points = [
                (brake_light_offset_x, brake_light_offset_y),
                (brake_light_offset_x + brake_light_width, brake_light_offset_y),
                (brake_light_offset_x + brake_light_width, brake_light_offset_y + brake_light_height),
                (brake_light_offset_x, brake_light_offset_y + brake_light_height)
            ]
            
            # סיבוב אורות הבלמים
            rotated_left_brake = []
            rotated_right_brake = []
            
            for x, y in left_brake_points:
                rotated_x = x * cos_angle - y * sin_angle + self.x
                rotated_y = x * sin_angle + y * cos_angle + self.y
                rotated_left_brake.append((int(rotated_x), int(rotated_y)))
            
            for x, y in right_brake_points:
                rotated_x = x * cos_angle - y * sin_angle + self.x
                rotated_y = x * sin_angle + y * cos_angle + self.y
                rotated_right_brake.append((int(rotated_x), int(rotated_y)))
            
            # ציור אורות בלמים
            pygame.draw.polygon(screen, (255, 0, 0), rotated_left_brake)
            pygame.draw.polygon(screen, (255, 0, 0), rotated_right_brake)