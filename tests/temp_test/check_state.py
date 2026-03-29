"""Full diagnostic of current data state."""
import json
from pathlib import Path

data_dir = Path('../../frontend/public/data/J03WN1')

# Goals
with open(data_dir / 'metadata.json', encoding='utf-8') as f:
    meta = json.load(f)

home_id = meta['teams'][0]['id']
away_id = meta['teams'][1]['id']
home_name = meta['teams'][0]['name']
away_name = meta['teams'][1]['name']
print(f"Home: {home_name} ({home_id})")
print(f"Away: {away_name} ({away_id})")
print(f"Duration: {meta.get('duration', 'NOT SET')}")

print(f"\nGoals ({len(meta.get('goals', []))}):")
for g in meta.get('goals', []):
    side = "HOME" if g['team_id'] == home_id else "AWAY"
    print(f"  {g['player_name']} min={g['minute']} t={g['match_seconds']}s "
          f"period={g['period']} team={side}")

# Phases xThreat around each goal
with open(data_dir / 'phases.json') as f:
    phases = json.load(f)

for goal in meta.get('goals', []):
    gmin = goal['minute']
    gt = goal['match_seconds']
    print(f"\nxThreat around goal at min {gmin} (t={gt}s):")
    
    # Find phases within +/- 120s of goal
    nearby = [p for p in phases 
              if abs(p['start'] - gt) < 120 or abs(p['end'] - gt) < 120]
    
    home_xt = sum(p['xthreat_gained'] for p in nearby 
                  if p['team'] == home_id and p['xthreat_gained'] > 0)
    away_xt = sum(p['xthreat_gained'] for p in nearby 
                  if p['team'] == away_id and p['xthreat_gained'] > 0)
    print(f"  Home positive xT: {home_xt:.4f}")
    print(f"  Away positive xT: {away_xt:.4f}")
    
    # Show phases with high xThreat
    high_xt = [p for p in nearby if abs(p['xthreat_gained']) > 0.05]
    for p in high_xt:
        print(f"    Phase {p['id']}: t={p['start']:.0f}-{p['end']:.0f}s "
              f"team={p['team']} xT={p['xthreat_gained']:.4f}")

# Per-minute bins (same logic as ThreatTimeline.jsx)
print("\n=== Per-minute bins (positive xT only, NO smoothing) ===")
duration = meta.get('duration', 5660)
total_minutes = int(duration // 60) + 1
bins = {}
for p in phases:
    if p['xthreat_gained'] <= 0:
        continue
    start_min = int(p['start'] // 60)
    end_min = int(p['end'] // 60)
    phase_mins = max(1, end_min - start_min + 1)
    per_min = p['xthreat_gained'] / phase_mins
    for m in range(start_min, end_min + 1):
        if m not in bins:
            bins[m] = {}
        bins[m][p['team']] = bins[m].get(p['team'], 0) + per_min

# Show bins around goals
for goal in meta.get('goals', []):
    gmin = goal['minute']
    print(f"\n  Goal at minute {gmin}:")
    for m in range(max(0, gmin - 2), gmin + 3):
        if m in bins:
            vals = {("HOME" if k == home_id else "AWAY"): f"{v:.4f}" 
                    for k, v in bins[m].items()}
            print(f"    Bin {m} (chart minute {m+1}): {vals}")
        else:
            print(f"    Bin {m} (chart minute {m+1}): (empty)")

# Find max bin value
all_vals = []
for m, teams in bins.items():
    for v in teams.values():
        all_vals.append(v)
if all_vals:
    max_val = max(all_vals)
    print(f"\n  Max bin value: {max_val:.4f}")
    # Show which minutes have values > 50% of max
    print(f"  Minutes with bars > 50% of max:")
    for m in sorted(bins.keys()):
        for team, v in bins[m].items():
            if v > max_val * 0.5:
                side = "HOME" if team == home_id else "AWAY"
                print(f"    Minute {m} (chart {m+1}): {side} = {v:.4f} ({100*v/max_val:.0f}%)")
