import json

with open('../../frontend/public/data/J03WN1/phases.json') as f:
    phases = json.load(f)

home = 'DFL-CLU-00000S'
away = 'DFL-CLU-00000B'

print('=== Phases with positive xThreat (first 5 minutes) ===')
for p in phases:
    if p.get('xthreat_gained', 0) > 0 and p['start'] < 300:
        pid = p['id']
        team = 'HOME' if p['team'] == home else 'AWAY'
        print(f"  Phase {pid}: {team}, t={p['start']:.0f}-{p['end']:.0f}s, "
              f"type={p['type']}, xT={p['xthreat_gained']:.4f}")

# Per-minute bin summary (matching frontend logic)
bins = {}
for p in phases:
    xt = p.get('xthreat_gained', 0)
    if xt <= 0:
        continue
    start_min = int(p['start'] / 60)
    end_min = int(p['end'] / 60)
    n = max(1, end_min - start_min + 1)
    per_min = xt / n
    for m in range(start_min, end_min + 1):
        key = (m, p['team'])
        bins[key] = bins.get(key, 0) + per_min

print()
print('=== Per-minute bins (first 10 min, raw) ===')
for m in range(10):
    h = bins.get((m, home), 0)
    a = bins.get((m, away), 0)
    if h > 0 or a > 0:
        print(f"  Min {m+1}: HOME={h:.4f}, AWAY={a:.4f}")

print()
print('=== All bins > 0.05 ===')
all_vals = []
for (m, t), v in sorted(bins.items()):
    team_label = 'HOME' if t == home else 'AWAY'
    all_vals.append((m, team_label, v))
    if v > 0.05:
        print(f"  Min {m+1}: {team_label}={v:.4f}")

print()
vals = [v for _, _, v in all_vals]
if vals:
    print(f"Max bin: {max(vals):.4f}")
    print(f"Median bin: {sorted(vals)[len(vals)//2]:.4f}")
    print(f"Bins > 0.1: {sum(1 for v in vals if v > 0.1)}")
    print(f"Bins > 0.01: {sum(1 for v in vals if v > 0.01)}")
    print(f"Total bins with data: {len(vals)}")

# Show goal minute context 
print()
print('=== Goal minutes ===')
for goal_min in [18, 33, 86]:
    m = goal_min - 1  # 0-indexed
    h = bins.get((m, home), 0)
    a = bins.get((m, away), 0)
    print(f"  Minute {goal_min}: HOME={h:.4f}, AWAY={a:.4f}")
