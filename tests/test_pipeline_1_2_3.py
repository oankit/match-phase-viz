"""Test pipeline Steps 1, 2, and 3 together"""
import sys
sys.path.insert(0, '.')

import importlib

# Import steps
step1 = importlib.import_module('01_load_data')
step2 = importlib.import_module('02_compute_features')
step3 = importlib.import_module('03_classify_phases')

print("="*80)
print("TESTING PIPELINE: STEPS 1, 2, 3")
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

# Show final results
print("\n" + "="*80)
print("FINAL RESULTS")
print("="*80)

print(f"\nFeatures DataFrame: {features_df.shape}")
print(f"Columns: {features_df.columns.tolist()}")

print(f"\nPhases DataFrame: {phases_df.shape}")
print(f"\nPhase segments (first 10):")
print(phases_df.head(10).to_string())

print(f"\nPhase type counts:")
print(phases_df['phase_type'].value_counts())

print(f"\nPhase duration statistics (seconds):")
print(phases_df.groupby('phase_type')['duration'].describe())

print("\n" + "="*80)
print("[SUCCESS] Pipeline Steps 1-3 completed!")
print("="*80)

# Save for inspection
print("\nSaving outputs...")
features_df.to_csv('temp_test/features_with_phases.csv', index=False)
phases_df.to_csv('temp_test/phase_segments.csv', index=False)
print("  Saved: temp_test/features_with_phases.csv")
print("  Saved: temp_test/phase_segments.csv")