"""
Quick test of phase detection with v2 thresholds
"""
import sys
sys.path.insert(0, '../pipeline')

import importlib

# Import steps
step1 = importlib.import_module('01_load_data')
step2 = importlib.import_module('02_compute_features')
step3 = importlib.import_module('03_classify_phases')

print("Testing phase detection with v2 thresholds...")
print("=" * 60)

# Load data
match_id = "J03WN1"
event_dataset, tracking_dataset, events_df, tracking_df = step1.load_match(
    match_id=match_id,
    sample_rate=0.04  # 1 Hz for quick test
)
tracking_df = tracking_dataset.to_df()
print(f"Loaded: {len(events_df)} events, {len(tracking_df)} tracking frames")

# Compute features
features_df = step2.main(tracking_dataset, tracking_df)
print(f"Computed {features_df.shape[0]} feature rows")

# Classify phases
features_df, phases_df = step3.main(features_df, events_df)
print(f"\nDetected {len(phases_df)} phase segments")

# Check phase distribution
print("\nPhase type distribution:")
for phase_type in ['high_press', 'defensive_block', 'counter_attack', 'open_play']:
    count = (phases_df['phase_type'] == phase_type).sum()
    pct = count / len(phases_df) * 100 if len(phases_df) > 0 else 0
    print(f"  {phase_type:15s}: {count:3d} ({pct:5.1f}%)")

# Check if we have high press phases for heatmaps
high_press_count = (phases_df['phase_type'] == 'high_press').sum()
if high_press_count > 0:
    print(f"\n✓ SUCCESS: {high_press_count} high press phases detected!")
    print("   Pressing heatmaps will be generated.")
else:
    print("\n✗ WARNING: No high press phases detected!")
    print("   No pressing heatmaps will be visible.")