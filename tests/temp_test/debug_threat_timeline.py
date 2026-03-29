"""Debug threat timeline visualization issues."""
import json
from pathlib import Path
import pandas as pd

# Load metadata and phases
data_dir = Path(__file__).parent / '../../frontend/public/data/J03WN1'
with open(data_dir / 'metadata.json') as f:
    metadata = json.load(f)
with open(data_dir / 'phases.json') as f:
    phases = json.load(f)

# Extract team info
teams = metadata['teams']
home_team = teams[0]
away_team = teams[1]
print(f"Home: {home_team['name']} ({home_team['id']})")
print(f"Away: {away_team['name']} ({away_team['id']})")

# Check goals
goals = metadata.get('goals', [])
print(f"\n=== GOALS ({len(goals)}) ===")
for g in goals:
    team_name = home_team['name'] if g['team_id'] == home_team['id'] else away_team['name']
    print(f"  {g['minute']}' - {team_name} ({g['player_name']})")

# Check phases with xThreat
print(f"\n=== PHASES ({len(phases)} total) ===")

# Group phases by team
home_phases = [p for p in phases if p.get('team') == home_team['id']]
away_phases = [p for p in phases if p.get('team') == away_team['id']]

print(f"\nHome team ({home_team['name']}) phases: {len(home_phases)}")
print(f"  With positive xThreat: {len([p for p in home_phases if p.get('xthreat_gained', 0) > 0])}")
print(f"  Total xThreat gained: {sum(p.get('xthreat_gained', 0) for p in home_phases):.3f}")

print(f"\nAway team ({away_team['name']}) phases: {len(away_phases)}")
print(f"  With positive xThreat: {len([p for p in away_phases if p.get('xthreat_gained', 0) > 0])}")
print(f"  Total xThreat gained: {sum(p.get('xthreat_gained', 0) for p in away_phases):.3f}")

# Check threat distribution by minute
print("\n=== THREAT BY MINUTE ===")
duration = metadata.get('duration', 90 * 60)
total_minutes = int(duration // 60)

# Initialize bins
bins = {}
for m in range(total_minutes + 1):
    bins[m] = {home_team['id']: 0, away_team['id']: 0}

# Accumulate threat per minute
for phase in phases:
    if not phase.get('team') or phase.get('xthreat_gained', 0) <= 0:
        continue

    start_min = int(phase['start'] // 60)
    end_min = int(phase['end'] // 60)
    phase_minutes = max(1, end_min - start_min + 1)
    per_minute = phase['xthreat_gained'] / phase_minutes

    for m in range(start_min, min(end_min + 1, total_minutes + 1)):
        bins[m][phase['team']] += per_minute

# Find minutes with highest threat
print("\nMinutes with highest threat (Home):")
home_threat = [(m, bins[m][home_team['id']]) for m in bins]
home_threat.sort(key=lambda x: x[1], reverse=True)
for m, threat in home_threat[:5]:
    print(f"  Minute {m}: {threat:.4f}")

print("\nMinutes with highest threat (Away):")
away_threat = [(m, bins[m][away_team['id']]) for m in bins]
away_threat.sort(key=lambda x: x[1], reverse=True)
for m, threat in away_threat[:5]:
    print(f"  Minute {m}: {threat:.4f}")

# Check if all goals are from home team
if all(g['team_id'] == home_team['id'] for g in goals):
    print(f"\n⚠️  All {len(goals)} goals are from {home_team['name']} - {away_team['name']} scored 0 goals")
elif all(g['team_id'] == away_team['id'] for g in goals):
    print(f"\n⚠️  All {len(goals)} goals are from {away_team['name']} - {home_team['name']} scored 0 goals")