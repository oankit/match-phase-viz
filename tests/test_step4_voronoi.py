"""Test pipeline Step 4 (Voronoi)"""
import sys
sys.path.insert(0, '../pipeline')

import importlib

# Import steps
step1 = importlib.import_module('01_load_data')
step4 = importlib.import_module('04_compute_voronoi')

print("="*80)
print("TESTING PIPELINE: STEP 4 (VORONOI)")
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

# Step 4: Compute Voronoi
print("\n" + "="*80)
print("[STEP 4] Computing Voronoi diagrams")
print("="*80)
voronoi_data = step4.main(tracking_dataset, tracking_df, output_format='polygons')

# Show results
print("\n" + "="*80)
print("FINAL RESULTS")
print("="*80)

print(f"\nVoronoi data: {len(voronoi_data)} frames")

# Show first frame details
sample = voronoi_data[0]
print(f"\nFirst frame (ID: {sample['frame_id']}):")
print(f"  Timestamp: {sample['timestamp']}")
print(f"  Cells: {len(sample['cells'])}")

# Count valid polygons
valid_cells = [c for c in sample['cells'] if c['polygon'] is not None]
print(f"  Valid polygons: {len(valid_cells)}")

# Show first few cells
print(f"\nFirst 3 cells:")
for i, cell in enumerate(sample['cells'][:3]):
    vertices = len(cell['polygon']) if cell['polygon'] else 0
    print(f"  [{i}] player={cell['player_id']}, team={cell['team_id']}, vertices={vertices}")

print("\n" + "="*80)
print("[SUCCESS] Step 4 completed!")
print("="*80)
