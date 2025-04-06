import cv2
import time
import matplotlib.pyplot as plt
from collections import deque

class MovementDebugger:
    def __init__(self, history_length=100):
        self.movement_history = deque(maxlen=history_length)
        self.time_history = deque(maxlen=history_length)
        self.start_time = time.time()
        self.is_recording = False
        self.record_data = []
        
    def add_movement(self, movement):
        """Add a movement value to the history"""
        self.movement_history.append(movement)
        self.time_history.append(time.time() - self.start_time)
        
        if self.is_recording:
            self.record_data.append((time.time() - self.start_time, movement))
    
    def start_recording(self):
        """Start recording movement data"""
        self.record_data = []
        self.is_recording = True
        print("Started recording movement data")
    
    def stop_recording(self):
        """Stop recording and save the data"""
        self.is_recording = False
        if len(self.record_data) > 0:
            # Create a simple plot
            times, movements = zip(*self.record_data)
            plt.figure(figsize=(10, 6))
            plt.plot(times, movements)
            plt.title("Hand Movement Data")
            plt.xlabel("Time (seconds)")
            plt.ylabel("Movement magnitude")
            plt.axhline(y=30, color='r', linestyle='--', label="Threshold")
            plt.legend()
            plt.grid(True)
            plt.savefig("movement_debug.png")
            print("Saved movement debug data to movement_debug.png")
    
    def draw_debug_info(self, img, current_movement):
        """Draw debug information on the frame"""
        # Draw current movement value
        cv2.putText(img, f"Movement: {current_movement:.1f}", 
                   (10, 70), cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 0), 2)
        
        # Draw recording status
        if self.is_recording:
            cv2.putText(img, "REC", (img.shape[1] - 100, 50), 
                       cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 255), 2)
            # Draw red circle to indicate recording
            cv2.circle(img, (img.shape[1] - 50, 40), 10, (0, 0, 255), cv2.FILLED)
        
        # Draw mini graph of recent movement
        if len(self.movement_history) > 10:
            graph_width = 200
            graph_height = 100
            graph_x = img.shape[1] - graph_width - 20
            graph_y = img.shape[0] - graph_height - 20
            
            # Draw graph background
            cv2.rectangle(img, (graph_x, graph_y), 
                         (graph_x + graph_width, graph_y + graph_height), 
                         (255, 255, 255), cv2.FILLED)
            
            # Draw threshold line
            threshold_y = graph_y + graph_height - int(30 * graph_height / 100)
            cv2.line(img, (graph_x, threshold_y), (graph_x + graph_width, threshold_y), 
                    (0, 0, 255), 1)
            
            # Draw movement history
            max_val = max(self.movement_history) if max(self.movement_history) > 0 else 100
            
            for i in range(len(self.movement_history) - 1):
                p1_x = graph_x + int(i * graph_width / (len(self.movement_history) - 1))
                p1_y = graph_y + graph_height - int(self.movement_history[i] * graph_height / max_val)
                
                p2_x = graph_x + int((i+1) * graph_width / (len(self.movement_history) - 1))
                p2_y = graph_y + graph_height - int(self.movement_history[i+1] * graph_height / max_val)
                
                cv2.line(img, (p1_x, p1_y), (p2_x, p2_y), (0, 255, 0), 2)
        
        return img
