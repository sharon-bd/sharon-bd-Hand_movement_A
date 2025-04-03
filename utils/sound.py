# utils/sound.py - Sound management

import pygame
import numpy as np
import os
import io

class SoundManager:
    def __init__(self):
        """Initialize the sound manager."""
        # Initialize pygame mixer if not already done
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        
        print("Sound system initialized successfully")
        
        # Create synthesized sounds
        self.create_engine_sounds()
        self.create_game_sounds()
        
        # Track current engine sound state
        self.current_engine_state = "idle"
        
        # Track mute state
        self.muted = False
    
    def create_engine_sounds(self):
        """Create synthesized engine sounds."""
        # Idle engine sound (low frequency)
        self.engine_idle = self.synthesize_engine_sound(220, 0.3)
        print("Created synthesized engine idle sound")
        
        # Revving engine sound (higher frequency)
        self.engine_revving = self.synthesize_engine_sound(330, 0.5)
        print("Created synthesized engine revving sound")
        
        # Boost sound (even higher frequency)
        self.engine_boost = self.synthesize_engine_sound(440, 0.8)
        print("Created synthesized engine boost sound")
    
    def create_game_sounds(self):
        """Create game effect sounds."""
        # Collision sound (harsh noise)
        self.collision_sound = self.synthesize_collision_sound()
        print("Created synthesized collision sound")
        
        # Power-up sound (ascending tone)
        self.powerup_sound = self.synthesize_powerup_sound()
        print("Created synthesized power-up sound")
        
        # Brake sound (descending tone)
        self.brake_sound = self.synthesize_brake_sound()
        print("Created synthesized brake sound")
        
        # Game over sound (dramatic)
        self.game_over_sound = self.synthesize_game_over_sound()
        print("Created synthesized game over sound")
    
    def synthesize_engine_sound(self, frequency, volume):
        """Create a synthetic engine sound."""
        # Create a short sample (~1 second) of engine sound
        sample_rate = 22050
        samples = np.sin(2 * np.pi * frequency * np.arange(sample_rate) / sample_rate)
        
        # Add harmonics for richer sound
        samples += 0.5 * np.sin(2 * np.pi * (frequency * 2) * np.arange(sample_rate) / sample_rate)
        samples += 0.25 * np.sin(2 * np.pi * (frequency * 3) * np.arange(sample_rate) / sample_rate)
        
        # Add noise for realism
        samples += 0.1 * np.random.random(sample_rate)
        
        # Normalize and scale by volume
        samples = (samples / np.max(np.abs(samples))) * volume
        
        # Convert to 16-bit PCM
        samples = (samples * 32767).astype(np.int16)
        
        # Create sound from buffer
        buffer = io.BytesIO()
        import wave
        with wave.open(buffer, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(samples.tobytes())
        
        buffer.seek(0)
        return pygame.mixer.Sound(buffer)
    
    def synthesize_collision_sound(self):
        """Create a collision sound effect."""
        sample_rate = 22050
        duration = 0.5  # Short duration
        samples = np.random.random(int(sample_rate * duration)) * 2 - 1
        
        # Apply envelope
        envelope = np.exp(-np.linspace(0, 10, int(sample_rate * duration)))
        samples = samples * envelope
        
        # Convert to 16-bit PCM
        samples = (samples * 32767).astype(np.int16)
        
        # Create sound from buffer
        buffer = io.BytesIO()
        import wave
        with wave.open(buffer, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(samples.tobytes())
        
        buffer.seek(0)
        return pygame.mixer.Sound(buffer)
    
    def synthesize_powerup_sound(self):
        """Create a power-up sound effect."""
        sample_rate = 22050
        duration = 0.6
        
        # Ascending frequency
        samples = np.zeros(int(sample_rate * duration))
        for i in range(int(sample_rate * duration)):
            t = i / sample_rate
            freq = 440 + t * 1000
            samples[i] = np.sin(2 * np.pi * freq * t)
        
        # Apply envelope
        envelope = np.ones_like(samples)
        envelope[-int(0.1 * sample_rate):] = np.linspace(1, 0, int(0.1 * sample_rate))
        samples = samples * envelope
        
        # Convert to 16-bit PCM
        samples = (samples * 32767).astype(np.int16)
        
        # Create sound from buffer
        buffer = io.BytesIO()
        import wave
        with wave.open(buffer, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(samples.tobytes())
        
        buffer.seek(0)
        return pygame.mixer.Sound(buffer)
    
    def synthesize_brake_sound(self):
        """Create a braking sound effect."""
        sample_rate = 22050
        duration = 0.4
        
        # Descending frequency
        samples = np.zeros(int(sample_rate * duration))
        for i in range(int(sample_rate * duration)):
            t = i / sample_rate
            freq = 880 - t * 600
            samples[i] = np.sin(2 * np.pi * freq * t)
        
        # Add friction noise
        noise = np.random.random(int(sample_rate * duration)) * 0.3
        samples = samples + noise
        
        # Apply envelope
        envelope = np.ones_like(samples)
        envelope[-int(0.1 * sample_rate):] = np.linspace(1, 0, int(0.1 * sample_rate))
        samples = samples * envelope
        
        # Convert to 16-bit PCM
        samples = (samples * 32767).astype(np.int16)
        
        # Create sound from buffer
        buffer = io.BytesIO()
        import wave
        with wave.open(buffer, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(samples.tobytes())
        
        buffer.seek(0)
        return pygame.mixer.Sound(buffer)
    
    def synthesize_game_over_sound(self):
        """Create a game over sound effect."""
        sample_rate = 22050
        duration = 1.5
        
        # Descending melody
        samples = np.zeros(int(sample_rate * duration))
        notes = [660, 550, 440, 330, 220]
        note_duration = duration / len(notes)
        
        for i, note in enumerate(notes):
            start = int(i * note_duration * sample_rate)
            end = int((i + 1) * note_duration * sample_rate)
            t = np.arange(end - start) / sample_rate
            samples[start:end] = np.sin(2 * np.pi * note * t)
        
        # Add tremolo effect
        tremolo = 0.5 + 0.5 * np.sin(2 * np.pi * 8 * np.arange(len(samples)) / sample_rate)
        samples = samples * tremolo
        
        # Apply overall envelope
        envelope = np.ones_like(samples)
        envelope[-int(0.2 * sample_rate):] = np.linspace(1, 0, int(0.2 * sample_rate))
        samples = samples * envelope
        
        # Convert to 16-bit PCM
        samples = (samples * 32767).astype(np.int16)
        
        # Create sound from buffer
        buffer = io.BytesIO()
        import wave
        with wave.open(buffer, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(samples.tobytes())
        
        buffer.seek(0)
        return pygame.mixer.Sound(buffer)
    
    def update_engine_sound(self, speed, braking, boost):
        """Update engine sound based on car state."""
        # Check mute state first - if muted, stop all sounds and return
        if self.muted:
            self.engine_idle.stop()
            self.engine_revving.stop()
            self.engine_boost.stop()
            self.current_engine_state = "muted"
            return
        
        if boost:
            if self.current_engine_state != "boost":
                self.engine_idle.stop()
                self.engine_revving.stop()
                self.engine_boost.play(-1)  # Loop indefinitely
                self.current_engine_state = "boost"
        elif speed > 0.5:
            if self.current_engine_state != "revving":
                self.engine_idle.stop()
                self.engine_boost.stop()
                self.engine_revving.play(-1)  # Loop indefinitely
                self.current_engine_state = "revving"
        else:
            if self.current_engine_state != "idle":
                self.engine_revving.stop()
                self.engine_boost.stop()
                self.engine_idle.play(-1)  # Loop indefinitely
                self.current_engine_state = "idle"
        
        if braking:
            self.brake_sound.play()
    
    def play_collision(self):
        """Play collision sound effect."""
        if not self.muted:
            self.collision_sound.play()
    
    def play_powerup(self):
        """Play power-up sound effect."""
        if not self.muted:
            self.powerup_sound.play()
    
    def play_game_over(self):
        """Play game over sound effect."""
        # Stop engine sounds
        self.engine_idle.stop()
        self.engine_revving.stop()
        self.engine_boost.stop()
        
        # Play game over sound if not muted
        if not self.muted:
            self.game_over_sound.play()
    
    def reset(self):
        """Reset sound manager state."""
        # Stop all currently playing sounds
        self.engine_idle.stop()
        self.engine_revving.stop()
        self.engine_boost.stop()
        
        # Reset current engine state
        self.current_engine_state = "idle"
        
        # Restart idle sound if not muted
        if not self.muted:
            self.engine_idle.play(-1)
    
    def set_mute(self, muted):
        """Set whether sound is muted."""
        # Check if mute state is changing
        if muted != self.muted:
            self.muted = muted
            print(f"Sound manager mute state changed to: {muted}")
            
            if muted:
                # Stop all sounds if muting
                pygame.mixer.stop()
                self.current_engine_state = "muted"
                print("All sounds stopped due to muting")
            else:
                # Restart idle sound if unmuting
                self.current_engine_state = "idle"
                self.engine_idle.play(-1)
                print("Idle sound restarted after unmuting")
                
        return self.muted
    
    def is_muted(self):
        """Check if sound is currently muted."""
        return self.muted