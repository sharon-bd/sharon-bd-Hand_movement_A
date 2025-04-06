import socket
import time
import threading
import queue

class ImprovedCarController:
    def __init__(self, car_ip="192.168.4.1", car_port=100, simulation_mode=True):
        self.car_ip = car_ip
        self.car_port = car_port
        self.socket = None
        self.simulation_mode = simulation_mode
        
        # Improved command management
        self.command_queue = queue.Queue()  # Queue for commands
        self.last_command = None
        self.last_command_time = 0
        self.command_timeout = 0.2  # Minimum seconds between duplicate commands
        self.retry_count = 0
        self.max_retries = 3
        
        # Command success tracking
        self.success_tracking = {
            "FORWARD": {"success": 0, "failure": 0},
            "LEFT": {"success": 0, "failure": 0},
            "RIGHT": {"success": 0, "failure": 0},
            "BACKWARD": {"success": 0, "failure": 0},
            "STOP": {"success": 0, "failure": 0},
            "FORWARD_BOOST": {"success": 0, "failure": 0}  # Added for boost
        }
        
        # Connection status
        self.connected = False
        self.connection_attempts = 0
        self.max_connection_attempts = 5
        
        # Start worker thread for sending commands
        if not simulation_mode:
            self.running = True
            self.worker_thread = threading.Thread(target=self._command_worker, daemon=True)
            self.worker_thread.start()
            self.connect()
        else:
            print("Car controller running in simulation mode - commands will be logged but not sent")
        
    def connect(self):
        """Establish connection to the car with improved error handling"""
        if self.connection_attempts >= self.max_connection_attempts:
            print(f"Maximum connection attempts ({self.max_connection_attempts}) reached. Giving up.")
            return False
            
        try:
            if self.socket is not None:
                self.socket.close()
                
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.settimeout(1.0)  # 1 second timeout
            
            # For UDP, we can't really "connect", but we can test by sending a ping
            self.socket.sendto(b"PING", (self.car_ip, self.car_port))
            
            print(f"Car controller initialized - ready to send commands to {self.car_ip}:{self.car_port}")
            self.connected = True
            self.connection_attempts = 0  # Reset counter on successful connection
            return True
            
        except Exception as e:
            self.connection_attempts += 1
            print(f"Failed to initialize car controller (attempt {self.connection_attempts}): {e}")
            self.socket = None
            self.connected = False
            return False
    
    def send_command(self, command):
        """Queue command for sending"""
        current_time = time.time()
        
        # Make sure command is valid
        if command not in self.success_tracking and command != "FORWARD_BOOST":
            print(f"Warning: Unknown command {command}")
            # Map to closest known command
            if "FORWARD" in command:
                command = "FORWARD"
            elif "LEFT" in command:
                command = "LEFT"
            elif "RIGHT" in command:
                command = "RIGHT"
            elif "STOP" in command or "BRAKE" in command:
                command = "STOP"
            else:
                print(f"Unable to map unknown command {command}, defaulting to STOP")
                command = "STOP"
        
        # Don't send duplicate commands in quick succession
        if self.last_command == command and current_time - self.last_command_time < self.command_timeout:
            # If the same command is sent too quickly, just ignore it
            print(f"Ignoring duplicate command {command} (too soon)")
            return False
        
        # If in simulation mode, just log the command and return success
        if self.simulation_mode:
            # Store command for future reference but don't try to send it
            self.last_command = command
            self.last_command_time = current_time
            print(f"SIMULATION: Command {command} processed successfully")
            
            # Track as success in statistics
            if command == "FORWARD_BOOST":
                self.success_tracking["FORWARD"]["success"] += 1
            else:
                self.success_tracking[command]["success"] += 1
                
            return True
            
        # Add command to queue for sending
        self.command_queue.put(command)
        self.last_command = command
        self.last_command_time = current_time
        return True
    
    def _command_worker(self):
        """Background thread to process command queue"""
        while self.running:
            try:
                # Get command from queue with timeout
                try:
                    command = self.command_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                
                # Handle special FORWARD_BOOST command
                actual_command = "FORWARD" if command == "FORWARD_BOOST" else command
                
                # Send the command
                success = self._send_command_direct(actual_command)
                
                # Track success/failure for the original command
                if success:
                    if command == "FORWARD_BOOST":
                        self.success_tracking["FORWARD"]["success"] += 1
                    else:
                        self.success_tracking[command]["success"] += 1
                else:
                    if command == "FORWARD_BOOST":
                        self.success_tracking["FORWARD"]["failure"] += 1
                    else:
                        self.success_tracking[command]["failure"] += 1
                    
                    # Retry logic
                    if self.retry_count < self.max_retries:
                        print(f"Command {command} failed, retrying ({self.retry_count + 1}/{self.max_retries})...")
                        self.retry_count += 1
                        self.command_queue.put(command)  # Put back in queue
                    else:
                        self.retry_count = 0
                
                # Mark task as done
                self.command_queue.task_done()
                
            except Exception as e:
                print(f"Error in command worker: {e}")
                time.sleep(0.5)  # Prevent tight loop on error
    
    def _send_command_direct(self, command):
        """Directly send command to car (used by worker thread)"""
        try:
            if not self.socket or not self.connected:
                if not self.connect():
                    return False
                    
            self.socket.sendto(command.encode(), (self.car_ip, self.car_port))
            print(f"Command {command} sent successfully")
            return True
            
        except Exception as e:
            print(f"Error sending command: {e}")
            self.connected = False
            return False
    
    def translate_gesture(self, gesture_data):
        """
        Translate gesture detection data to car commands
        Returns appropriate command string for the car
        
        Args:
            gesture_data: Dictionary containing gesture detection information
        """
        # Extract basic controls
        steering = gesture_data.get('steering', 0.0)
        throttle = gesture_data.get('throttle', 0.0)
        braking = gesture_data.get('braking', False)
        boost = gesture_data.get('boost', False)
        
        # Logic for command selection with thresholds
        if braking:
            return "STOP"
        elif boost:
            return "FORWARD_BOOST"  # Special command for boost
        elif abs(steering) > 0.3:  # Significant steering
            if steering < 0:
                return "LEFT"
            else:
                return "RIGHT"
        elif throttle > 0.1:  # Forward with minimal throttle
            return "FORWARD"
        else:
            return "STOP"  # Default to stop if no clear input
    
    def get_success_rate(self, command=None):
        """Get success rate for commands"""
        if command is not None:
            if command in self.success_tracking:
                stats = self.success_tracking[command]
                total = stats["success"] + stats["failure"]
                if total == 0:
                    return 0
                return (stats["success"] / total) * 100
            else:
                return 0
        
        # Overall success rate
        total_success = sum(cmd["success"] for cmd in self.success_tracking.values())
        total_failure = sum(cmd["failure"] for cmd in self.success_tracking.values())
        total = total_success + total_failure
        if total == 0:
            return 0
        return (total_success / total) * 100
    
    def close(self):
        """Close the connection and stop worker thread"""
        self.running = False
        if hasattr(self, 'worker_thread') and self.worker_thread and not self.simulation_mode:
            self.worker_thread.join(timeout=1.0)
            
        if self.socket:
            self.socket.close()
            self.socket = None