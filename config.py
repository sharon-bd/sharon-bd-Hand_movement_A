# config.py - Game Configuration Settings

# Game mode settings
GAME_MODES = {
    'practice': {
        'name': 'Practice Mode',
        'description': 'Learn to control the car without obstacles',
        'obstacle_frequency': 0.0,  # No obstacles 
        'obstacle_speed_multiplier': 1.0,
        'score_multiplier': 0.5,
        'time_limit': None  # No time limit
    },
    'easy': {
        'name': 'Easy Mode',
        'description': 'Few obstacles at a slow pace',
        'obstacle_frequency': 0.01,  # Lower frequency of obstacles
        'obstacle_speed_multiplier': 0.8,  # Slower obstacles
        'score_multiplier': 1.0,
        'time_limit': None
    },
    'normal': {
        'name': 'Normal Mode',
        'description': 'Standard gameplay',
        'obstacle_frequency': 0.02,  # Default frequency
        'obstacle_speed_multiplier': 1.0,
        'score_multiplier': 1.5,
        'time_limit': None
    },
    'hard': {
        'name': 'Hard Mode',
        'description': 'Many fast obstacles',
        'obstacle_frequency': 0.03,  # Higher frequency
        'obstacle_speed_multiplier': 1.3,  # Faster obstacles
        'score_multiplier': 2.0,
        'time_limit': None
    },
    'time_trial': {
        'name': 'Time Trial',
        'description': 'Race against the clock',
        'obstacle_frequency': 0.015,
        'obstacle_speed_multiplier': 1.1,
        'score_multiplier': 2.5,
        'time_limit': 120  # 2-minute time limit
    }
}

# Default game mode
DEFAULT_GAME_MODE = 'normal'