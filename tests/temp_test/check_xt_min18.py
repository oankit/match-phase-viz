"""Check xThreat around minute 18 (first goal)."""
import json
from pathlib import Path

data_dir = Path('../../frontend/public/data/J03WN1')

with open(data_dir / 'phases.json') as f:
    phases = json.load(f)

# Goal 1 is at match_seconds=1083.6, minute 18
# Check phases from minute 16-20 (960s to 1200s)
print("=== Phases around minute 18 (t=960-1200s) ===")
print(f"{'id':>4} {'type':<20} {'team':<20} {'start':>8} {'end':>8} {'xt_gained':>10}")
for p in phases:
    if 900 <= p['start'] <= 1200 or 900 <= p['end'] <= 1200:
        print(f"{p['id']:>4} {p['type']:<20} {p['team']:<20} "
              f"{p['start']:>8.1f} {p['end']:>8.1f} {p['xthreat_gained']:>10.4f}")

# Now check what the ThreatTimeline would compute for minutes 16-20
print("\n=== Per-minute xThreat bins (minutes 16-20) ===")
total_minutes = 94
bins = {m: {} for m in range(16, 21)}

for phase in phases:
    if phase['xthreat_gained'] == 0:
        continue
    start_min = int(phase['start'] // 60)
    end_min = int(phase['end'] // 60)
    phase_minutes = max(1, end_min - start_min + 1)
    per_min = abs(phase['xthreat_gained']) / phase_minutes

    for m in range(start_min, end_min + 1):
        if m in bins:
            team = phase['team']
            bins[m][team] = bins[m].get(team, 0) + per_min

for m in sorted(bins):
    vals = bins[m]
    print(f"  Minute {m}: {vals}")

# Also check: how many phases have non-zero xThreat in entire match
total = len(phases)
nonzero = sum(1 for p in phases if p['xthreat_gained'] != 0)
print(f"\n=== Overall xThreat coverage ===")
print(f"  Total phases: {total}")
print(f"  Non-zero xThreat: {nonzero} ({100*nonzero/total:.1f}%)")

# Check max xThreat values
xt_vals = [abs(p['xthreat_gained']) for p in phases if p['xthreat_gained'] != 0]
if xt_vals:
    print(f"  Max xThreat: {max(xt_vals):.4f}")
    print(f"  Mean xThreat: {sum(xt_vals)/len(xt_vals):.4f}")
    
    # Top 10 phases by xThreat
    top = sorted(phases, key=lambda p: abs(p['xthreat_gained']), reverse=True)[:10]
    print(f"\n=== Top 10 phases by xThreat ===")
    for p in top:
        min_start = p['start'] / 60
        print(f"  id={p['id']:>4} t={min_start:>5.1f}min team={p['team']:<20} "
              f"xt={p['xthreat_gained']:>8.4f} type={p['type']}")
