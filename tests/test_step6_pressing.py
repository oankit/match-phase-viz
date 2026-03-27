"""Test pipeline Step 6 (Pressing Heatmaps)"""
import sys
sys.path.insert(0, '../pipeline')

import importlib
import numpy as np

# Import steps
step1 = importlib.import_module('01_load_data')
step2 = importlib.import_module('02_compute_features')
step3 = importlib.import_module('03_classify_phases')
step6 = importlib.import_module('06_compute_pressing')

print("="*80)
print("TESTING PIPELINE: STEP 6 (PRESSING HEATMAPS)")
print("="*80)

# Step 1: Load data
print("\n" + "="*80)
print("[STEP 1] Loading match data")
print("="*80)
event_dataset, tracking_dataset, events_df, tracking_df_sample = step1.load_match(
    match_id="J03WN1",
    sample_rate=0.04  # 1 Hz
)

tracking_df = tracking_dataset.to_df()
print(f"Loaded: {len(events_df)} events, {len(tracking_df)} tracking frames")

# Step 2: Compute features
print("\n" + "="*80)
print("[STEP 2] Computing features")
print("="*80)
features_df = step2.main(tracking_dataset, tracking_df)

# Step 3: Classify phases
print("\n" + "="*80)
print("[STEP 3] Classifying phases")
print("="*80)
features_df, phases_df = step3.main(features_df, events_df)

# Step 6: Compute pressing heatmaps
print("\n" + "="*80)
print("[STEP 6] Computing pressing heatmaps")
print("="*80)
heatmaps = step6.main(events_df, phases_df)

# Show results
print("\n" + "="*80)
print("FINAL RESULTS")
print("="*80)

print(f"\nPressing heatmaps computed: {len(heatmaps)}")

if len(heatmaps) > 0:
    # Show first heatmap
    sample = heatmaps[0]
    print(f"\nFirst heatmap (phase ID: {sample['phase_id']}):")
    print(f"  Team: {sample['team_id']}")
    print(f"  Grid shape: {np.array(sample['heatmap']).shape}")
    print(f"  Num actions: {sample['num_actions']}")
    print(f"  Max intensity: {np.array(sample['heatmap']).max():.3f}")
    print(f"  Non-zero cells: {(np.array(sample['heatmap']) > 0).sum()}")

    # Check grid dimensions
    expected_shape = (14, 21)  # (height, width) from config.HEATMAP_GRID_SIZE = (21, 14)
    actual_shape = np.array(sample['heatmap']).shape
    if actual_shape == expected_shape:
        print(f"  [OK] Grid shape correct: {actual_shape}")
    else:
        print(f"  [ERROR] Grid shape mismatch: expected {expected_shape}, got {actual_shape}")

print("\n" + "="*80)
print("[SUCCESS] Step 6 completed!")
print("="*80)
