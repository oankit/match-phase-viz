"""
Formation Templates for EFPI-style Template Matching

Based on Bekkers 2025 (EFPI paper) approach: define common formation templates
with 10 outfield player positions on a normalized half-pitch.

Positions are (x, y) where:
  x = depth (0 = own goal line, 1 = opponent goal line)
  y = width (0 = left touchline, 1 = right touchline)

Defense at low x, attack at high x.
Templates derived from mplsoccer standard formations (EFPI Appendix A).
"""

import numpy as np

# Each template has 10 positions (outfield only, GK excluded)
# Positions are ordered: defenders (low x), midfielders (mid x), forwards (high x)
TEMPLATES = {
    # === 4-back formations ===
    '4-4-2': [
        [0.15, 0.20], [0.15, 0.40], [0.15, 0.60], [0.15, 0.80],  # 4 defenders
        [0.45, 0.20], [0.45, 0.40], [0.45, 0.60], [0.45, 0.80],  # 4 midfielders
        [0.75, 0.35], [0.75, 0.65],                                # 2 forwards
    ],
    '4-4-1-1': [
        [0.15, 0.20], [0.15, 0.40], [0.15, 0.60], [0.15, 0.80],  # 4 defenders
        [0.40, 0.20], [0.40, 0.40], [0.40, 0.60], [0.40, 0.80],  # 4 midfielders
        [0.60, 0.50],                                               # 1 AM/SS
        [0.80, 0.50],                                               # 1 striker
    ],
    '4-3-3': [
        [0.15, 0.20], [0.15, 0.40], [0.15, 0.60], [0.15, 0.80],  # 4 defenders
        [0.45, 0.30], [0.45, 0.50], [0.45, 0.70],                 # 3 midfielders
        [0.75, 0.20], [0.75, 0.50], [0.75, 0.80],                 # 3 forwards
    ],
    '4-2-3-1': [
        [0.15, 0.20], [0.15, 0.40], [0.15, 0.60], [0.15, 0.80],  # 4 defenders
        [0.35, 0.35], [0.35, 0.65],                                # 2 DMs
        [0.55, 0.20], [0.55, 0.50], [0.55, 0.80],                 # 3 AMs
        [0.78, 0.50],                                               # 1 striker
    ],
    '4-1-4-1': [
        [0.15, 0.20], [0.15, 0.40], [0.15, 0.60], [0.15, 0.80],  # 4 defenders
        [0.30, 0.50],                                               # 1 DM
        [0.50, 0.15], [0.50, 0.40], [0.50, 0.60], [0.50, 0.85],  # 4 midfielders
        [0.78, 0.50],                                               # 1 striker
    ],
    '4-3-1-2': [
        [0.15, 0.20], [0.15, 0.40], [0.15, 0.60], [0.15, 0.80],  # 4 defenders
        [0.38, 0.30], [0.38, 0.50], [0.38, 0.70],                 # 3 midfielders
        [0.58, 0.50],                                               # 1 AM
        [0.78, 0.35], [0.78, 0.65],                                # 2 strikers
    ],
    '4-1-2-3': [
        [0.15, 0.20], [0.15, 0.40], [0.15, 0.60], [0.15, 0.80],  # 4 defenders
        [0.30, 0.50],                                               # 1 DM
        [0.48, 0.35], [0.48, 0.65],                                # 2 CMs
        [0.75, 0.20], [0.75, 0.50], [0.75, 0.80],                 # 3 forwards
    ],
    '4-2-2-2': [
        [0.15, 0.20], [0.15, 0.40], [0.15, 0.60], [0.15, 0.80],  # 4 defenders
        [0.35, 0.35], [0.35, 0.65],                                # 2 DMs
        [0.55, 0.35], [0.55, 0.65],                                # 2 AMs
        [0.75, 0.35], [0.75, 0.65],                                # 2 strikers
    ],
    '4-5-1': [
        [0.15, 0.20], [0.15, 0.40], [0.15, 0.60], [0.15, 0.80],  # 4 defenders
        [0.45, 0.10], [0.45, 0.30], [0.45, 0.50], [0.45, 0.70], [0.45, 0.90],  # 5 midfielders
        [0.78, 0.50],                                               # 1 striker
    ],
    '4-2-1-3': [
        [0.15, 0.20], [0.15, 0.40], [0.15, 0.60], [0.15, 0.80],  # 4 defenders
        [0.35, 0.35], [0.35, 0.65],                                # 2 DMs
        [0.55, 0.50],                                               # 1 AM
        [0.75, 0.20], [0.75, 0.50], [0.75, 0.80],                 # 3 forwards
    ],

    # === 3-back formations ===
    '3-4-3': [
        [0.15, 0.25], [0.15, 0.50], [0.15, 0.75],                # 3 CBs
        [0.40, 0.15], [0.40, 0.40], [0.40, 0.60], [0.40, 0.85],  # 4 midfielders
        [0.72, 0.20], [0.72, 0.50], [0.72, 0.80],                # 3 forwards
    ],
    '3-5-2': [
        [0.15, 0.25], [0.15, 0.50], [0.15, 0.75],                # 3 CBs
        [0.40, 0.10], [0.40, 0.30], [0.40, 0.50], [0.40, 0.70], [0.40, 0.90],  # 5 midfielders
        [0.72, 0.35], [0.72, 0.65],                                # 2 strikers
    ],
    '3-4-1-2': [
        [0.15, 0.25], [0.15, 0.50], [0.15, 0.75],                # 3 CBs
        [0.38, 0.15], [0.38, 0.40], [0.38, 0.60], [0.38, 0.85],  # 4 midfielders
        [0.58, 0.50],                                               # 1 AM
        [0.78, 0.35], [0.78, 0.65],                                # 2 strikers
    ],
    '3-4-2-1': [
        [0.15, 0.25], [0.15, 0.50], [0.15, 0.75],                # 3 CBs
        [0.38, 0.15], [0.38, 0.40], [0.38, 0.60], [0.38, 0.85],  # 4 midfielders
        [0.58, 0.35], [0.58, 0.65],                                # 2 AMs
        [0.78, 0.50],                                               # 1 striker
    ],
    '3-1-4-2': [
        [0.15, 0.25], [0.15, 0.50], [0.15, 0.75],                # 3 CBs
        [0.30, 0.50],                                               # 1 DM
        [0.48, 0.15], [0.48, 0.40], [0.48, 0.60], [0.48, 0.85],  # 4 midfielders
        [0.72, 0.35], [0.72, 0.65],                                # 2 strikers
    ],

    # === 5-back formations ===
    '5-4-1': [
        [0.12, 0.10], [0.12, 0.30], [0.12, 0.50], [0.12, 0.70], [0.12, 0.90],  # 5 defenders
        [0.40, 0.20], [0.40, 0.40], [0.40, 0.60], [0.40, 0.80],  # 4 midfielders
        [0.72, 0.50],                                               # 1 striker
    ],
    '5-3-2': [
        [0.12, 0.10], [0.12, 0.30], [0.12, 0.50], [0.12, 0.70], [0.12, 0.90],  # 5 defenders
        [0.40, 0.30], [0.40, 0.50], [0.40, 0.70],                 # 3 midfielders
        [0.72, 0.35], [0.72, 0.65],                                # 2 strikers
    ],
    '5-2-3': [
        [0.12, 0.10], [0.12, 0.30], [0.12, 0.50], [0.12, 0.70], [0.12, 0.90],  # 5 defenders
        [0.38, 0.35], [0.38, 0.65],                                # 2 midfielders
        [0.70, 0.20], [0.70, 0.50], [0.70, 0.80],                 # 3 forwards
    ],
}

# === 9-player templates (red card scenarios) ===
TEMPLATES_9 = {
    '4-4-1': [
        [0.15, 0.20], [0.15, 0.40], [0.15, 0.60], [0.15, 0.80],  # 4 defenders
        [0.45, 0.20], [0.45, 0.40], [0.45, 0.60], [0.45, 0.80],  # 4 midfielders
        [0.75, 0.50],                                               # 1 striker
    ],
    '4-3-2': [
        [0.15, 0.20], [0.15, 0.40], [0.15, 0.60], [0.15, 0.80],  # 4 defenders
        [0.42, 0.30], [0.42, 0.50], [0.42, 0.70],                 # 3 midfielders
        [0.72, 0.35], [0.72, 0.65],                                # 2 forwards
    ],
    '4-3-1-1': [
        [0.15, 0.20], [0.15, 0.40], [0.15, 0.60], [0.15, 0.80],  # 4 defenders
        [0.38, 0.30], [0.38, 0.50], [0.38, 0.70],                 # 3 midfielders
        [0.58, 0.50],                                               # 1 AM
        [0.78, 0.50],                                               # 1 striker
    ],
    '4-2-2-1': [
        [0.15, 0.20], [0.15, 0.40], [0.15, 0.60], [0.15, 0.80],  # 4 defenders
        [0.35, 0.35], [0.35, 0.65],                                # 2 DMs
        [0.55, 0.35], [0.55, 0.65],                                # 2 AMs
        [0.78, 0.50],                                               # 1 striker
    ],
    '4-2-3': [
        [0.15, 0.20], [0.15, 0.40], [0.15, 0.60], [0.15, 0.80],  # 4 defenders
        [0.40, 0.35], [0.40, 0.65],                                # 2 midfielders
        [0.70, 0.20], [0.70, 0.50], [0.70, 0.80],                 # 3 forwards
    ],
    '3-4-2': [
        [0.15, 0.25], [0.15, 0.50], [0.15, 0.75],                # 3 CBs
        [0.40, 0.15], [0.40, 0.40], [0.40, 0.60], [0.40, 0.85],  # 4 midfielders
        [0.72, 0.35], [0.72, 0.65],                                # 2 forwards
    ],
    '3-5-1': [
        [0.15, 0.25], [0.15, 0.50], [0.15, 0.75],                # 3 CBs
        [0.40, 0.10], [0.40, 0.30], [0.40, 0.50], [0.40, 0.70], [0.40, 0.90],  # 5 midfielders
        [0.72, 0.50],                                               # 1 striker
    ],
    '3-3-3': [
        [0.15, 0.25], [0.15, 0.50], [0.15, 0.75],                # 3 CBs
        [0.42, 0.25], [0.42, 0.50], [0.42, 0.75],                 # 3 midfielders
        [0.72, 0.25], [0.72, 0.50], [0.72, 0.75],                 # 3 forwards
    ],
    '5-3-1': [
        [0.12, 0.10], [0.12, 0.30], [0.12, 0.50], [0.12, 0.70], [0.12, 0.90],  # 5 defenders
        [0.40, 0.30], [0.40, 0.50], [0.40, 0.70],                 # 3 midfielders
        [0.72, 0.50],                                               # 1 striker
    ],
}

# Convert to numpy arrays
FORMATION_TEMPLATES = {
    name: np.array(positions)
    for name, positions in TEMPLATES.items()
}

FORMATION_TEMPLATES_9 = {
    name: np.array(positions)
    for name, positions in TEMPLATES_9.items()
}


def get_templates(num_players=10):
    """Get formation templates for the given number of outfield players."""
    if num_players == 9:
        return FORMATION_TEMPLATES_9
    return FORMATION_TEMPLATES


def get_template_names(num_players=10):
    """Return list of all available formation template names."""
    return list(get_templates(num_players).keys())


def get_template(name, num_players=10):
    """Get a specific formation template by name."""
    return get_templates(num_players).get(name)
