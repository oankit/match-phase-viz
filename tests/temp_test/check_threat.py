"""Check xThreat values around the goals."""
import json

phases = json.load(open('../../frontend/public/data/J03WN1/phases.json'))

print("=== PHASES AROUND 1ST GOAL (min 15-22, ~900-1320s) ===")
for p in phases:
    if 900 <= p['start'] <= 1320 or 900 <= p['end'] <= 1320:
        print(f"  id={p['id']:3d} type={p['type']:18s} team={p['team'][-1]} "
              f"start={p['start']:7.1f}s ({p['start']/60:.1f}m) "
              f"end={p['end']:7.1f}s ({p['end']/60:.1f}m) "
              f"xt_gained={p['xthreat_gained']:.4f}")

print("\n=== PHASES AROUND 2ND GOAL (min 30-36, ~1800-2160s) ===")
for p in phases:
    if 1800 <= p['start'] <= 2160 or 1800 <= p['end'] <= 2160:
        print(f"  id={p['id']:3d} type={p['type']:18s} team={p['team'][-1]} "
              f"start={p['start']:7.1f}s ({p['start']/60:.1f}m) "
              f"end={p['end']:7.1f}s ({p['end']/60:.1f}m) "
              f"xt_gained={p['xthreat_gained']:.4f}")

print("\n=== HOME TEAM PHASES WITH HIGHEST XTHREAT ===")
home_phases = [p for p in phases if p['team'][-1] == 'S']
home_phases.sort(key=lambda p: p['xthreat_gained'], reverse=True)
for p in home_phases[:15]:
    print(f"  id={p['id']:3d} type={p['type']:18s} "
          f"start={p['start']:7.1f}s ({p['start']/60:.1f}m) "
          f"end={p['end']:7.1f}s ({p['end']/60:.1f}m) "
          f"xt_gained={p['xthreat_gained']:.4f}")

print("\n=== XTHREAT DISTRIBUTION (home team) ===")
xt_vals = [p['xthreat_gained'] for p in home_phases]
print(f"  Count: {len(xt_vals)}")
print(f"  Min: {min(xt_vals):.4f}")
print(f"  Max: {max(xt_vals):.4f}")
print(f"  Mean: {sum(xt_vals)/len(xt_vals):.4f}")
print(f"  Zeros: {sum(1 for v in xt_vals if v == 0)}")
print(f"  Non-zero: {sum(1 for v in xt_vals if v > 0)}")
