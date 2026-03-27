"""
Validate Rest Defence implementation
"""
import json
import sys
from pathlib import Path

# Load voronoi data
voronoi_path = Path('../output/J03WN1/voronoi.json')
with open(voronoi_path, 'r') as f:
    data = json.load(f)

print(f"Total frames: {len(data)}")

# Find frames with control grid data
frames_with_grid = [d for d in data if 'control_grid' in d and len(d.get('control_grid', [])) > 0]
print(f"Frames with control grid: {len(frames_with_grid)}")

if frames_with_grid:
    sample = frames_with_grid[0]
    print(f"\nSample frame {sample['frame_id']}:")
    print(f"  Attacking team: {sample.get('attacking_team_id')}")
    print(f"  Convex hull vertices: {len(sample.get('convex_hull', []))}")
    print(f"  Control grid points: {len(sample.get('control_grid', []))}")

    print("\n  First 5 control grid points:")
    for i, pt in enumerate(sample['control_grid'][:5]):
        print(f"    {i+1}. x={pt['x']:.3f}, y={pt['y']:.3f}, team={pt['team_id']}")

    # Check team distribution in control grid
    team_counts = {}
    for pt in sample['control_grid']:
        team = pt['team_id']
        team_counts[team] = team_counts.get(team, 0) + 1

    print(f"\n  Team distribution in grid:")
    for team, count in team_counts.items():
        pct = count / len(sample['control_grid']) * 100
        print(f"    {team}: {count} points ({pct:.1f}%)")

    # Check hull coordinates
    print(f"\n  Convex hull coordinates:")
    for i, vertex in enumerate(sample.get('convex_hull', [])[:3]):
        print(f"    Vertex {i+1}: x={vertex[0]:.3f}, y={vertex[1]:.3f}")
else:
    print("No frames with control grid data found")

print("\n✓ Rest Defence validation complete")