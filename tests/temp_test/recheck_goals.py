"""Re-extract goals from events to ensure none are missed."""
from kloppy import sportec
from pathlib import Path
import pandas as pd

# Load event data for J03WN1
data_path = Path(__file__).parent / '../../data'

# Find the event and meta files
meta_file = list(data_path.glob('*matchinformation*J03WN1.xml'))[0]
event_file = list(data_path.glob('*events_raw*J03WN1.xml'))[0]

print(f"Loading events from: {event_file.name}")
print(f"Loading metadata from: {meta_file.name}\n")

# Load the event dataset
event_dataset = sportec.load_event(
    event_data=str(event_file),
    meta_data=str(meta_file),
    coordinates='kloppy'
)

events_df = event_dataset.to_df()

# Check all shots
print("=== ALL SHOTS IN THE MATCH ===")
shots = events_df[events_df['event_type'] == 'SHOT']
print(f"Total shots: {len(shots)}")
print("\nShot results breakdown:")
print(shots['result'].value_counts())

# Show all shots with their results
print("\n=== DETAILED SHOT LIST ===")
for idx, shot in shots.iterrows():
    period = shot['period_id']
    ts = shot['timestamp'].total_seconds()
    minute = int(ts // 60) if period == 1 else int(45 + ts // 60)
    team = shot['team_id']
    player = shot['player_id']
    result = shot['result']

    # Get team name
    team_name = 'Unknown'
    for t in event_dataset.metadata.teams:
        if t.team_id == team:
            team_name = t.name
            break

    # Get player name
    player_name = 'Unknown'
    for t in event_dataset.metadata.teams:
        for p in t.players:
            if p.player_id == player:
                player_name = p.name if p.name else p.player_id
                break

    status = "GOAL" if result == 'GOAL' else f"{result}"
    print(f"{status:11s} | Min {minute:2d} | {team_name:20s} | {player_name}")

# Double-check goals
print("\n=== CONFIRMED GOALS ===")
goals = shots[shots['result'] == 'GOAL']
print(f"Total goals: {len(goals)}")

for _, g in goals.iterrows():
    ts = g['timestamp'].total_seconds()
    period = g['period_id']
    match_seconds = (45 * 60 + ts) if period == 2 else ts
    minute = int(match_seconds // 60)

    team_name = 'Unknown'
    for t in event_dataset.metadata.teams:
        if t.team_id == g['team_id']:
            team_name = t.name
            break

    player_name = 'Unknown'
    for t in event_dataset.metadata.teams:
        for p in t.players:
            if p.player_id == g['player_id']:
                player_name = p.name if p.name else p.player_id
                break

    print(f"  {minute}' - {team_name} ({player_name})")

# Check if any goals might be classified differently
print("\n=== CHECKING OTHER POTENTIAL GOAL EVENTS ===")

# Check for any events that might contain "goal" in their type
potential_goals = events_df[events_df['event_type'].str.contains('GOAL', case=False, na=False)]
if len(potential_goals) > 0:
    print(f"Found {len(potential_goals)} events with 'GOAL' in type:")
    print(potential_goals[['period_id', 'timestamp', 'team_id', 'event_type', 'result']].head(10))
else:
    print("No other events with 'GOAL' in type found")

# Check event types
print("\n=== ALL EVENT TYPES ===")
print(events_df['event_type'].value_counts().head(20))