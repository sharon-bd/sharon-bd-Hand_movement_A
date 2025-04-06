class Player:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.move_speed = 30  # Adjust movement speed as needed
        self.jump_speed = 20  # Adjust jump height as needed
        self.gravity = 1      # Adjust gravity as needed
        self.is_jumping = False
        self.jump_count = 0
        self.max_jump = 15    # Maximum jump frames
    
    def move_left(self):
        self.x -= self.move_speed
        # Boundary check
        if self.x < 0:
            self.x = 0
        # Log movement for debugging
        print(f"Moving left to: {self.x}")
    
    def move_right(self):
        self.x += self.move_speed
        # Boundary check (assuming screen_width is defined elsewhere)
        if self.x + self.width > 800:  # Adjust with your screen width
            self.x = 800 - self.width
        # Log movement for debugging
        print(f"Moving right to: {self.x}")
    
    def jump(self):
        if not self.is_jumping:
            self.is_jumping = True
            self.jump_count = 0
            # Log jump for debugging
            print("Jump initiated")
    
    def update(self):
        # Handle jumping physics
        if self.is_jumping:
            if self.jump_count < self.max_jump:
                self.y -= self.jump_speed - (self.jump_count * self.gravity)
                self.jump_count += 1
            else:
                self.is_jumping = False
                # Add any landing logic here
        
        # Add other update logic here