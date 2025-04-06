import time
import random
import matplotlib.pyplot as plt
import numpy as np
import cv2
import threading
import queue

class ReactionTimeAnalyzer:
    def __init__(self):
        self.reaction_times = []
        self.processing_times = []
        self.execution_times = []
        self.input_queue = queue.Queue()
        self.output_queue = queue.Queue()
        self.running = False

    def start_system(self):
        """Start the simulation system with all components."""
        self.running = True
        # Start threads for each component
        threading.Thread(target=self.input_processor, daemon=True).start()
        threading.Thread(target=self.central_processor, daemon=True).start()
        threading.Thread(target=self.output_executor, daemon=True).start()

    def stop_system(self):
        """Stop the simulation system."""
        self.running = False

    def input_processor(self):
        """Simulates the hand gesture recognition component."""
        while self.running:
            # Wait for input from the test_reaction method
            if not self.input_queue.empty():
                gesture, start_time = self.input_queue.get()
                
                # Simulate processing time for gesture recognition
                process_time = random.uniform(0.05, 0.2)  # 50-200ms
                time.sleep(process_time)
                
                # Record processing time
                self.processing_times.append(process_time)
                
                # Send to central processor
                self.central_processor_queue = (gesture, start_time, process_time)
                
            time.sleep(0.01)

    def central_processor(self):
        """Simulates the central decision-making component."""
        while self.running:
            # Check if there's input from the input processor
            if hasattr(self, 'central_processor_queue'):
                gesture, start_time, input_process_time = self.central_processor_queue
                
                # Simulate central processing
                process_time = random.uniform(0.1, 0.3)  # 100-300ms
                time.sleep(process_time)
                
                # Send to output executor
                self.output_queue.put((gesture, start_time, input_process_time + process_time))
                
                # Remove the attribute to prevent reprocessing
                delattr(self, 'central_processor_queue')
                
            time.sleep(0.01)

    def output_executor(self):
        """Simulates the vehicle movement component."""
        while self.running:
            # Check if there's a command to execute
            if not self.output_queue.empty():
                gesture, start_time, previous_process_time = self.output_queue.get()
                
                # Simulate execution time for vehicle movement
                execution_time = random.uniform(0.2, 0.5)  # 200-500ms
                time.sleep(execution_time)
                
                # Record execution time
                self.execution_times.append(execution_time)
                
                # Calculate total reaction time
                end_time = time.time()
                total_time = end_time - start_time
                self.reaction_times.append(total_time)
                
                print(f"Gesture '{gesture}' executed. Total reaction time: {total_time:.3f}s")
                
            time.sleep(0.01)

    def test_reaction(self, gesture="move_forward"):
        """Simulate a hand gesture input and measure reaction time."""
        start_time = time.time()
        self.input_queue.put((gesture, start_time))
        return start_time

    def analyze_bottlenecks(self):
        """Analyze where the bottlenecks are in the system."""
        if not self.reaction_times:
            return "No reaction data available for analysis."
            
        avg_reaction = np.mean(self.reaction_times)
        avg_processing = np.mean(self.processing_times)
        avg_execution = np.mean(self.execution_times)
        
        # Calculate estimated central processing time
        avg_central = avg_reaction - avg_processing - avg_execution
        
        components = ["Input Processing", "Central Processing", "Output Execution"]
        times = [avg_processing, avg_central, avg_execution]
        
        bottleneck = components[np.argmax(times)]
        bottleneck_percentage = (np.max(times) / avg_reaction) * 100
        
        return {
            "avg_reaction_time": avg_reaction,
            "component_times": {
                "input_processing": avg_processing,
                "central_processing": avg_central,
                "output_execution": avg_execution
            },
            "bottleneck": bottleneck,
            "bottleneck_percentage": bottleneck_percentage
        }

    def visualize_results(self):
        """Visualize the reaction times and bottlenecks."""
        if not self.reaction_times:
            return "No data to visualize."
            
        analysis = self.analyze_bottlenecks()
        
        # Create figure with multiple subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        # Plot 1: Reaction time histogram
        ax1.hist(self.reaction_times, bins=10, alpha=0.7, color='blue')
        ax1.set_title('Reaction Time Distribution')
        ax1.set_xlabel('Time (seconds)')
        ax1.set_ylabel('Frequency')
        ax1.axvline(analysis["avg_reaction_time"], color='red', linestyle='dashed', 
                   linewidth=1, label=f'Avg: {analysis["avg_reaction_time"]:.3f}s')
        ax1.legend()
        
        # Plot 2: Component breakdown
        components = ["Input\nProcessing", "Central\nProcessing", "Output\nExecution"]
        times = [
            analysis["component_times"]["input_processing"],
            analysis["component_times"]["central_processing"],
            analysis["component_times"]["output_execution"]
        ]
        
        bars = ax2.bar(components, times, color=['green', 'blue', 'orange'])
        ax2.set_title('System Component Times')
        ax2.set_ylabel('Time (seconds)')
        
        # Highlight the bottleneck
        bottleneck_index = components.index(analysis["bottleneck"].replace(' ', '\n'))
        bars[bottleneck_index].set_color('red')
        
        # Add percentages on top of bars
        for i, bar in enumerate(bars):
            percentage = (times[i] / analysis["avg_reaction_time"]) * 100
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                   f'{percentage:.1f}%', ha='center', va='bottom')
        
        plt.tight_layout()
        plt.savefig('reaction_analysis.png')
        plt.show()
        
        return "Visualization saved as 'reaction_analysis.png'"

def run_simulation(duration=10):
    """Run a simulation for a specified duration."""
    analyzer = ReactionTimeAnalyzer()
    analyzer.start_system()
    
    print(f"Running simulation for {duration} seconds...")
    gestures = ["move_forward", "turn_left", "turn_right", "stop", "speed_up", "slow_down"]
    
    end_time = time.time() + duration
    while time.time() < end_time:
        # Randomly select a gesture
        gesture = random.choice(gestures)
        analyzer.test_reaction(gesture)
        
        # Wait between gestures
        time.sleep(random.uniform(0.5, 1.5))
    
    # Allow time for final operations to complete
    time.sleep(2)
    analyzer.stop_system()
    
    # Analyze and visualize results
    print("\nAnalysis Results:")
    analysis = analyzer.analyze_bottlenecks()
    print(f"Average Reaction Time: {analysis['avg_reaction_time']:.3f} seconds")
    print(f"Bottleneck: {analysis['bottleneck']} ({analysis['bottleneck_percentage']:.1f}% of total time)")
    
    print("\nCreating visualization...")
    analyzer.visualize_results()
    
    return analyzer

if __name__ == "__main__":
    # Run a 15-second simulation
    analyzer = run_simulation(15)