# Audio management for handling sound in the game

class AudioManager:
    def __init__(self):
        """
        Initialize the audio manager.
        """
        self.muted = False
        self.volume = 1.0  # Default volume (0.0 to 1.0)
        # Add additional audio initialization here if needed
    
    def toggle_mute(self):
        """
        Toggle the mute state.
        
        Returns:
            bool: New mute state
        """
        self.muted = not self.muted
        return self.muted
    
    def set_mute(self, mute_state):
        """
        Set a specific mute state.
        
        Args:
            mute_state (bool): True to mute, False to unmute
            
        Returns:
            bool: New mute state
        """
        self.muted = mute_state
        return self.muted
    
    def is_muted(self):
        """
        Check if audio is currently muted.
        
        Returns:
            bool: True if muted, False otherwise
        """
        return self.muted
    
    def set_volume(self, volume):
        """
        Set the audio volume.
        
        Args:
            volume (float): Volume level from 0.0 to 1.0
            
        Returns:
            float: New volume level
        """
        # Ensure volume is between 0 and 1
        self.volume = max(0.0, min(1.0, volume))
        return self.volume
    
    def get_volume(self):
        """
        Get the current volume level.
        
        Returns:
            float: Current volume level
        """
        return self.volume
