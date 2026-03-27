"""Test pipeline Step 5 (Formations)"""
import sys
sys.path.insert(0, '../pipeline')

import importlib

# Import steps
step1 = importlib.import_module('01_load_data')
step2 = importlib.import_module('02_compute_features')
step3 = importlib.import_module('03_classify_phases')
step5 = importlib.import_module('05_compute_formations')

print("="*80)
print("TESTING PIPELINE: STEP 5 (FORMATIONS)")
print("="*80)

# Step 1: Load data (at 1 Hz for faster testing)
print("\n" + "="*80)
print("[STEP 1] Loading match data")
print("="*80)
event_dataset, tracking_dataset, events_df, tracking_df_sample = step1.load_match(
    match_id="J03WN1",
    sample_rate=0.04  # 1 Hz for testing
)

# Convert full tracking to DataFrame
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

# Step 5: Compute formations
print("\n" + "="*80)
print("[STEP 5] Computing formations")
print("="*80)
formations = step5.main(tracking_dataset, tracking_df, phases_df)

# Show results
print("\n" + "="*80)
print("FINAL RESULTS")
print("="*80)

print(f"\nFormations computed: {len(formations)}")

if len(formations) > 0:
    # Show first formation
    sample = formations[0]
    print(f"\nFirst formation (phase ID: {sample['phase_id']}):")
    print(f"  Phase type: {sample['phase_type']}")
    print(f"  Team: {sample['team_id']}")
    print(f"  Frames: {sample['num_frames']}")
    print(f"  Mean positions shape: {len(sample['mean_positions'])}x{len(sample['mean_positions'][0])}")
    print(f"  Mean adjacency shape: {len(sample['mean_adjacency'])}x{len(sample['mean_adjacency'][0])}")
    print(f"  Stability scores: {sample['stability_scores'][:3]}... (first 3 roles)")

    # Phase type distribution
    import pandas as pd
    formations_df = pd.DataFrame(formations)
    print(f"\nFormations by phase type:")
    print(formations_df.groupby('phase_type').size())

    print(f"\nFormations by team:")
    print(formations_df.groupby('team_id').size())

print("\n" + "="*80)
print("[SUCCESS] Step 5 completed!")
print("="*80)
