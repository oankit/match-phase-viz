"""Verify threat timeline is correctly aligned with goals."""
import json
from pathlib import Path

# Load the data
data_dir = Path(__file__).parent / '../../frontend/public/data/J03WN1'

with open(data_dir / 'metadata.json') as f:
    metadata = json.load(f)

with open(data_dir / 'phases.json') as f:
    phases = json.load(f)

# Get team info
teams = metadata['teams']
home_team = teams[0]
away_team = teams[1]

# Get goals
goals = metadata.get('goals', [])

print(f"Match: {home_team['name']} vs {away_team['name']}")
print(f"\n=== GOALS ===")
for g in goals:
    team_name = home_team['name'] if g['team_id'] == home_team['id'] else away_team['name']
    print(f"  {g['minute']}' ({g['match_seconds']}s) - {team_name}")

# Check threat around goal times
print(f"\n=== THREAT AROUND GOAL TIMES ===")

for goal in goals:
    goal_time = goal['match_seconds']
    goal_minute = goal['minute']
    team_name = home_team['name'] if goal['team_id'] == home_team['id'] else away_team['name']

    print(f"\nGoal at minute {goal_minute} ({goal_time}s) by {team_name}:")

    # Find phases around this time
    relevant_phases = [
        p for p in phases
        if p['start'] <= goal_time <= p['end']
        or abs(p['start'] - goal_time) < 30
        or abs(p['end'] - goal_time) < 30
    ]

    if relevant_phases:
        for p in relevant_phases[:5]:  # Show up to 5 nearby phases
            team = home_team['name'] if p['team'] == home_team['id'] else away_team['name']
            print(f"  Phase {p['id']}: {p['type']:15s} | {p['start']:.1f}-{p['end']:.1f}s | {team:20s} | xT: {p.get('xthreat_gained', 0):.4f}")
    else:
        print("  No phases found around goal time")

# Check if there are any phases with very high threat
print(f"\n=== HIGHEST THREAT PHASES ===")
high_threat = sorted(phases, key=lambda p: p.get('xthreat_gained', 0), reverse=True)[:10]

for p in high_threat:
    team = home_team['name'] if p['team'] == home_team['id'] else away_team['name']
    minute_start = int(p['start'] // 60)
    minute_end = int(p['end'] // 60)
    print(f"  Min {minute_start:2d}-{minute_end:2d} | {team:20s} | {p['type']:15s} | xT: {p.get('xthreat_gained', 0):.4f}")

# Summary
print(f"\n=== SUMMARY ===")
print(f"Total goals: {len(goals)}")
print(f"  {home_team['name']}: {len([g for g in goals if g['team_id'] == home_team['id']])}")
print(f"  {away_team['name']}: {len([g for g in goals if g['team_id'] == away_team['id']])}")

home_threat = sum(p.get('xthreat_gained', 0) for p in phases if p['team'] == home_team['id'])
away_threat = sum(p.get('xthreat_gained', 0) for p in phases if p['team'] == away_team['id'])
print(f"\nTotal xThreat gained:")
print(f"  {home_team['name']}: {home_threat:.3f}")
print(f"  {away_team['name']}: {away_threat:.3f}")