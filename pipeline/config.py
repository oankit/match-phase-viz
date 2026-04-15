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
PROCESSING_MODE = 'production'  # 'testing' or 'production'

# Testing mode settings (fast processing, lower quality)
TESTING_LOAD_SAMPLE_RATE = 0.04  # Load at 1 Hz (every 25th frame from 25 Hz)
TESTING_EXPORT_FPS = 1  # Export at 1 Hz for quick loading

# Production mode settings (slower processing, full quality)
PRODUCTION_LOAD_SAMPLE_RATE = 1.0  # Load at full 25 Hz
PRODUCTION_EXPORT_FPS = 25  # Export at 25 Hz for full resolution playback

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

# Phase classification thresholds (possession-aware)
# NOTE: Coordinates are NORMALIZED (0-1) not absolute meters
# REFINED 2026-03-27 v3: Possession-aware with attacking + defensive phases
PHASE_THRESHOLDS = {
    # ---- DEFENSIVE PHASES (team does NOT have ball) ----
    'high_press': {
        'def_line_height_min': 0.40,  # 42m / 105m, pushing high
        'ball_x_min': 0.48,  # ~50m, ball in opponent half
        'pressure_proxy_min': 1,  # At least 1 player pressuring
    },
    'defensive_block': {
        'def_line_height_max': 0.30,  # 31.5m / 105m, deep
        'compactness_max': 0.18,  # ~360m^2 normalized, compact
        'ball_x_max': 0.45,  # ball in own half
    },
    'mid_block': {
        'def_line_height_min': 0.30,  # Between deep block and high press
        'def_line_height_max': 0.40,
    },
    # ---- ATTACKING PHASES (team HAS ball) ----
    'attacking': {
        'ball_x_min': 0.50,  # Ball in opponent half
        'def_line_height_min': 0.38,  # Team pushed forward
    },
    'build_up': {
        'ball_x_max': 0.50,  # Ball in own half
    },
}

# Path B: Event-based counter-attack detection
# NOTE: Coordinates are NORMALIZED (0-1) not absolute meters
# REFINED 2026-03-27: Relaxed to catch more transitions
COUNTERATTACK_RULES = {
    'start_half': 'defensive',  # Start in defensive half
    'forward_distance_min': 0.071,  # 7.5m / 105m, lowered from 0.095
    'forward_velocity_min': 0.028,  # 3 m/s / 105m, lowered from 0.038
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

# Shape graph parameters (Brandes et al. 2025, Sotudeh 2026)
SHAPE_GRAPH_ANGLE_THRESHOLD = 45.0   # degrees, edges below this stability are removed
SHAPE_GRAPH_MIN_EDGES = 5            # fallback to Delaunay if fewer edges remain

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
# Changed to output directly to frontend public folder for immediate access
OUTPUT_DIR = '../frontend/public/data'
# Fallback to main output directory if frontend doesn't exist
BACKUP_OUTPUT_DIR = '../output'
DATA_DIR = '../data'

# JSON export limits
MAX_JSON_SIZE_MB = 5  # Split files if larger
