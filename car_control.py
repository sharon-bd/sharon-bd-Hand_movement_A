import socket
import time

class CarController:
    def __init__(self, car_ip="192.168.4.1", car_port=100):
        self.car_ip = car_ip
        self.car_port = car_port
        self.socket = None
        self.last_command = None
        self.command_timeout = 0.2  # Minimum time between commands (seconds)
        self.last_command_time = 0
        self.connect()
        
    def connect(self):
        """Establish connection to the car"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            print(f"Car controller initialized - ready to send commands to {self.car_ip}:{self.car_port}")
        except Exception as e:
            print(f"Failed to initialize car controller: {e}")
            self.socket = None
    
    def send_command(self, command):
        """Send command to car with throttling to prevent command flooding"""
        current_time = time.time()
        
        # Don't send duplicate commands in quick succession
        if self.last_command == command and current_time - self.last_command_time < self.command_timeout:
            return False
            
        try:
            if self.socket:
                self.socket.sendto(command.encode(), (self.car_ip, self.car_port))
                self.last_command = command
                self.last_command_time = current_time
                return True
        except Exception as e:
            print(f"Failed to send command to car: {e}")
            # Try to reconnect
            self.connect()
        return False
    
    def translate_gesture(self, gesture, hand_position=None):
        """
        Translate gesture and hand position to car commands
        Returns appropriate command string for the car
        """
        if gesture == "open_palm":
            return "STOP"
        elif gesture == "fist":
            return "FORWARD"
        elif gesture == "thumbs_up":
            return "BACKWARD"
        elif gesture == "pointing":
            # Use hand position to determine direction
            if hand_position:
                x, y = hand_position
                # Determine left/right based on horizontal position
                if x < 0.4:
                    return "LEFT"
                elif x > 0.6:
                    return "RIGHT"
            return "FORWARD"  # Default if no position info
        
        # Default command if gesture is not recognized
        return "STOP"
    
    def close(self):
        """Close the connection"""
        if self.socket:
            self.socket.close()
            self.socket = None
