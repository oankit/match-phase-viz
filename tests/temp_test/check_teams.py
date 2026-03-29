"""Check team IDs, goal assignments, and xThreat direction."""
import json
from pathlib import Path

data_dir = Path('../../frontend/public/data/J03WN1')

with open(data_dir / 'metadata.json', encoding='utf-8') as f:
    meta = json.load(f)

print("=== Teams ===")
for i, t in enumerate(meta['teams']):
    role = "HOME (bars UP, red)" if i == 0 else "AWAY (bars DOWN, blue)"
    print(f"  [{i}] {t['id']} = {t['name']} -> {role}")

home_id = meta['teams'][0]['id']
away_id = meta['teams'][1]['id']

print(f"\n=== Goals ===")
for g in meta['goals']:
    side = "HOME" if g['team_id'] == home_id else "AWAY"
    print(f"  {g['player_name']} (min {g['minute']}) - team {g['team_id']} = {side}")

print(f"\n=== xThreat at goal minutes (from phases) ===")
with open(data_dir / 'phases.json') as f:
    phases = json.load(f)

for goal in meta['goals']:
    gmin = goal['minute']
    gsec = goal['match_seconds']
    print(f"\n  Goal: {goal['player_name']} at minute {gmin} (t={gsec}s)")

    home_xt = 0
    away_xt = 0
    for p in phases:
        p_start_min = int(p['start'] // 60)
        p_end_min = int(p['end'] // 60)
        if gmin - 1 <= p_start_min <= gmin + 1 or gmin - 1 <= p_end_min <= gmin + 1:
            if p['xthreat_gained'] != 0:
                if p['team'] == home_id:
                    home_xt += p['xthreat_gained']
                else:
                    away_xt += p['xthreat_gained']

    print(f"    Home xThreat (UP bars):   {home_xt:.4f}")
    print(f"    Away xThreat (DOWN bars): {away_xt:.4f}")
