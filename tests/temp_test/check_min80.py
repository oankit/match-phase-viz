"""Check what's causing the spike at minute 80."""
import json
from pathlib import Path

data_dir = Path('../../frontend/public/data/J03WN1')

with open(data_dir / 'phases.json') as f:
    phases = json.load(f)

print("=== Phases with positive xThreat at minute 80 (t=4800-4860s) ===")
for p in phases:
    if p['xthreat_gained'] <= 0:
        continue
    start_min = int(p['start'] // 60)
    end_min = int(p['end'] // 60)
    if start_min <= 80 <= end_min:
        dur_mins = end_min - start_min + 1
        per_min = p['xthreat_gained'] / dur_mins
        print(f"  Phase {p['id']}: t={p['start']:.0f}-{p['end']:.0f}s "
              f"({start_min}'-{end_min}') xT={p['xthreat_gained']:.4f} "
              f"per_min={per_min:.4f} team={p['team']} type={p['type']}")
