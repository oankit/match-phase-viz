"""
Test the fixed pressing heatmap computation using tracking data.
"""

import sys
import pandas as pd
from pathlib import Path
sys.path.append('../pipeline')

# Import pipeline modules
from step1 import load_match
from step2 import main as compute_features
from step3 import main as classify_phases

# Load match data
print("Loading match data...")
event_dataset, tracking_dataset, events_df, tracking_df = load_match(
    match_id="J03WN1",
    sample_rate=0.04,
    data_dir="../data"
)

# Compute features
print("Computing features...")
features_df = compute_features(tracking_dataset, tracking_df)

# Classify phases
print("Classifying phases...")
features_df_with_phases, phases_df = classify_phases(features_df, events_df)

# Import fixed heatmap computation
sys.path.append('../pipeline')
import importlib.util
spec = importlib.util.spec_from_file_location("step6_fixed", "../pipeline/06_compute_pressing_fixed.py")
step6_fixed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(step6_fixed)

# Compute pressing heatmaps with fixed version
print("\nComputing pressing heatmaps with tracking data...")
heatmaps = step6_fixed.main(phases_df, features_df_with_phases, tracking_df)

print("\n" + "=" * 50)
print("RESULTS")
print("=" * 50)

import numpy as np
for i, hm in enumerate(heatmaps[:5]):  # Check first 5
    print(f'\nHeatmap {i}:')
    print(f'  Phase ID: {hm["phase_id"]}')
    print(f'  Team: {hm["team_id"]}')
    print(f'  Pressing actions: {hm["num_actions"]}')

    grid = np.array(hm['heatmap'])
    print(f'  Grid shape: {grid.shape}')
    print(f'  Non-zero cells: {np.count_nonzero(grid)}')
    print(f'  Max intensity: {grid.max():.3f}')
    print(f'  Mean intensity: {grid.mean():.4f}')

print("\n" + "=" * 50)
if any(hm['num_actions'] > 0 for hm in heatmaps):
    print("[SUCCESS] Heatmaps now contain pressing data!")
else:
    print("[WARNING] Still no pressing data found")