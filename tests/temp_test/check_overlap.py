"""Check for timestamp overlap between periods."""
import json
from pathlib import Path

data_dir = Path('../../frontend/public/data/J03WN1')

with open(data_dir / 'frames.json') as f:
    frames = json.load(f)

period_1_frames = [f for f in frames if f.get('period_id') == 1]
period_2_frames = [f for f in frames if f.get('period_id') == 2]

p1_max = max(f['t'] for f in period_1_frames) if period_1_frames else 0
p2_min = min(f['t'] for f in period_2_frames) if period_2_frames else 0

print(f"Period 1: {len(period_1_frames)} frames, max t = {p1_max:.1f}s ({p1_max/60:.1f}min)")
print(f"Period 2: {len(period_2_frames)} frames, min t = {p2_min:.1f}s ({p2_min/60:.1f}min)")
print(f"Gap/Overlap: {p2_min - p1_max:.1f}s")

if p2_min < p1_max:
    overlap_count = sum(1 for f in period_2_frames if f['t'] <= p1_max)
    print(f"WARNING: {overlap_count} period 2 frames overlap with period 1!")
