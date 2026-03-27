"""
Quick test of updated Rest Defence (time-to-intercept model)
Generates only Step 4 output with the new implementation
"""
import sys
sys.path.insert(0, '../pipeline')

import importlib
import json
from pathlib import Path

# Import steps
step1 = importlib.import_module('01_load_data')
step4 = importlib.import_module('04_compute_voronoi')

print("Testing updated Rest Defence (time-to-intercept model)")
print("=" * 60)

# Load data
match_id = "J03WN1"
print("Loading match data...")
event_dataset, tracking_dataset, events_df, tracking_df = step1.load_match(
    match_id=match_id,
    sample_rate=0.04  # 1 Hz for quick test
)
tracking_df = tracking_dataset.to_df()
print(f"  Loaded {len(tracking_df)} tracking frames")

# Compute Rest Defence
print("\nComputing Rest Defence with time-to-intercept...")
voronoi_data = step4.main(tracking_dataset, tracking_df, output_format='rest_defence')
print(f"  Computed Rest Defence for {len(voronoi_data)} frames")

# Check sample frame
sample = next((v for v in voronoi_data if v.get('control_grid') and len(v['control_grid']) > 0), None)
if sample:
    print(f"\nSample frame {sample['frame_id']}:")
    print(f"  Grid points: {len(sample['control_grid'])}")

    # Check team distribution
    team_counts = {}
    time_sum = {}
    for pt in sample['control_grid']:
        team = pt['team_id']
        time = pt.get('time', 0)
        team_counts[team] = team_counts.get(team, 0) + 1
        time_sum[team] = time_sum.get(team, 0) + time

    print(f"\n  Pitch control distribution:")
    for team, count in team_counts.items():
        pct = count / len(sample['control_grid']) * 100
        avg_time = time_sum[team] / count if count > 0 else 0
        print(f"    {team}: {count} points ({pct:.1f}%), avg time: {avg_time:.2f}s")

    # Sample of control points
    print(f"\n  First 5 control points:")
    for i, pt in enumerate(sample['control_grid'][:5]):
        print(f"    {i+1}. x={pt['x']:.3f}, y={pt['y']:.3f}, team={pt['team_id']}, time={pt.get('time', 0):.2f}s")

# Save sample to verify
output_path = Path('../frontend/public/data/J03WN1/voronoi_sample.json')
with open(output_path, 'w') as f:
    json.dump(voronoi_data[:10], f, indent=2)
print(f"\nSaved sample (10 frames) to: {output_path}")