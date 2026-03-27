"""
Configuration constants for the soccer analytics pipeline.
"""

# Pitch dimensions (kloppy normalized coordinates)
PITCH_LENGTH = 105.0  # meters
PITCH_WIDTH = 68.0    # meters

# ==============================================================================
# PROCESSING MODE CONFIGURATION
# ==============================================================================
# Set this to 'testing' for fast iteration or 'production' for final output
PROCESSING_MODE = 'testing'  # 'testing' or 'production'

# Testing mode settings (fast processing, lower quality)
TESTING_LOAD_SAMPLE_RATE = 0.04  # Load at 1 Hz (every 25th frame from 25 Hz)
TESTING_EXPORT_FPS = 1  # Export at 1 Hz for quick loading

# Production mode settings (slower processing, full quality)
PRODUCTION_LOAD_SAMPLE_RATE = 1.0  # Load at full 25 Hz
PRODUCTION_EXPORT_FPS = 4  # Export at 4 Hz for smooth playback

# Automatically set values based on mode
if PROCESSING_MODE == 'testing':
    # Testing: Load at 1 Hz, export at 1 Hz
    # Results in ~2,700 frames that process in ~1 minute
    LOAD_SAMPLE_RATE = TESTING_LOAD_SAMPLE_RATE
    EXPORT_TARGET_FPS = TESTING_EXPORT_FPS
else:
    # Production: Load at 25 Hz, export at 4 Hz
    # Results in ~68,000 frames that process in ~10-15 minutes
    LOAD_SAMPLE_RATE = PRODUCTION_LOAD_SAMPLE_RATE
    EXPORT_TARGET_FPS = PRODUCTION_EXPORT_FPS

# Original tracking data parameters
TRACKING_FPS = 25  # Hz, original sampling rate from Sportec/DFL data

# Calculate actual loaded FPS based on sample rate
LOADED_FPS = int(TRACKING_FPS * LOAD_SAMPLE_RATE)  # Actual FPS after Step 1 loading

# Calculate downsample factor for Step 8 export
# This ensures we downsample correctly from whatever rate Step 1 loaded at
EXPORT_DOWNSAMPLE_FACTOR = max(1, LOADED_FPS // EXPORT_TARGET_FPS)

# Sliding window for feature computation
WINDOW_SECONDS = 5.0
WINDOW_FRAMES = int(WINDOW_SECONDS * TRACKING_FPS)  # 125 frames

# Phase classification thresholds (Path A: tracking-based)
# NOTE: Coordinates are NORMALIZED (0-1) not absolute meters
PHASE_THRESHOLDS = {
    'high_press': {
        'def_line_height_min': 0.43,  # 45m / 105m, high up the pitch
        'ball_x_min': 0.5,  # opponent half
        'pressure_proxy_min': 1,  # players within radius (lowered from 3)
    },
    'defensive_block': {
        'def_line_height_max': 0.33,  # 35m / 105m, deep in own half
        'compactness_max': 0.20,  # normalized convex hull area (400m² / (105*68)²)
        'ball_x_max': 0.5,  # own half
    },
}

# Path B: Event-based counter-attack detection
# NOTE: Coordinates are NORMALIZED (0-1) not absolute meters
COUNTERATTACK_RULES = {
    'start_half': 'defensive',  # Start in defensive half
    'forward_distance_min': 0.095,  # 10m / 105m in normalized coordinates
    'forward_velocity_min': 0.038,  # 4 m/s / 105m in normalized units/s
    'timeout': 15.0,  # seconds
    'set_piece_types': {
        'KICK_OFF', 'FREE_KICK', 'CORNER', 'THROW_IN', 'GOAL_KICK', 'PENALTY'
    },
}

# Pressure proxy parameters
PRESSURE_RADIUS = 5.0  # meters, defenders within this radius count as pressing

# Phase post-processing
MIN_PHASE_DURATION = 5.0  # seconds, drop shorter segments

# Formation analysis
FORMATION_TEMPLATE_DURATION = 300.0  # seconds, first 5 minutes per half
NUM_OUTFIELD_ROLES = 10  # Exclude goalkeeper

# Pressing heatmap
HEATMAP_GRID_SIZE = (21, 14)  # 5m resolution (105/5, 68/5)
HEATMAP_BANDWIDTH = 'scott'  # KDE bandwidth method

# xThreat grid
XTHREAT_GRID_SIZE = (12, 8)  # Zones along pitch

# Match IDs (DFL IDSSE dataset) — all 7 Bundesliga matches
# Source: kloppy.sportec.load_open_tracking_data / load_open_event_data
AVAILABLE_MATCHES = [
    'J03WMX',  # 1. FC Köln vs. FC Bayern München (Bundesliga 1)
    'J03WN1',  # VfL Bochum 1848 vs. Bayer 04 Leverkusen (Bundesliga 1)
    'J03WPY',  # Fortuna Düsseldorf vs. 1. FC Nürnberg (Bundesliga 2)
    'J03WOH',  # Fortuna Düsseldorf vs. SSV Jahn Regensburg (Bundesliga 2)
    'J03WQQ',  # Fortuna Düsseldorf vs. FC St. Pauli (Bundesliga 2)
    'J03WOY',  # Fortuna Düsseldorf vs. F.C. Hansa Rostock (Bundesliga 2)
    'J03WR9',  # Fortuna Düsseldorf vs. 1. FC Kaiserslautern (Bundesliga 2)
]

# Output paths
OUTPUT_DIR = '../output'
DATA_DIR = '../data'

# JSON export limits
MAX_JSON_SIZE_MB = 5  # Split files if larger
