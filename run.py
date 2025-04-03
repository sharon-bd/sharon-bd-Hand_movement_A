#!/usr/bin/env python
"""
Run script for Hand Gesture Car Control System
This is a simple script to launch the application
"""

import sys
import os

def main():
    # Ensure the script runs from the correct directory
    # to avoid import errors
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Make sure Python can find all our modules
    sys.path.insert(0, script_dir)
    
    print("Starting Hand Gesture Car Control System...")
    
    # Import and run the game
    try:
        from main import main as start_game_main
        start_game_main()
    except ImportError as e:
        print(f"Error importing game modules: {e}")
        print("Make sure all required packages are installed.")
        print("Try running: pip install -r requirements.txt")
        input("Press Enter to exit...")
    except Exception as e:
        print(f"Error running game: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()
