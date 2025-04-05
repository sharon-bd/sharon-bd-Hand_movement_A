import socket
import time

class CarController:
    def __init__(self, car_ip="192.168.4.1", car_port=100, simulation_mode=True):
        self.car_ip = car_ip
        self.car_port = car_port
        self.socket = None
        self.last_command = None
        self.command_timeout = 0.2  # Minimum time between commands (seconds)
        self.last_command_time = 0
        self.simulation_mode = simulation_mode
        
        if not simulation_mode:
            self.connect()
        else:
            print("Car controller running in simulation mode - commands will be logged but not sent")
        
    def connect(self):
        """Establish connection to the car"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            print(f"Car controller initialized - ready to send commands to {self.car_ip}:{self.car_port}")
        except Exception as e:
            print(f"Failed to initialize car controller: {e}")
            self.socket = None
    
    def send_command(self, command):
        current_time = time.time()
        
        # Don't send duplicate commands in quick succession
        if self.last_command == command and current_time - self.last_command_time < self.command_timeout:
            if not self.simulation_mode:
                print(f"Ignoring duplicate command {command} (too soon)")
            return False
        
        # If in simulation mode, just log the command and return success
        if self.simulation_mode:
            # Store command for future reference but don't try to send it
            self.last_command = command
            self.last_command_time = current_time
            return True
            
        # Only try to send if not in simulation mode
        try:
            if self.socket:
                print(f"Sending UDP packet to {self.car_ip}:{self.car_port}")
                self.socket.sendto(command.encode(), (self.car_ip, self.car_port))
                self.last_command = command
                self.last_command_time = current_time
                print(f"Command {command} sent successfully")
                return True
            else:
                print("Socket not initialized")
        except Exception as e:
            print(f"Error sending command: {e}")
            self.connect()  # Try to reconnect
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
        if self.socket and not self.simulation_mode:
            self.socket.close()
            self.socket = None
