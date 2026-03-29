"""Check event types and set_piece_types for computing new stats."""
import sys
sys.path.insert(0, '../pipeline')
from kloppy import sportec

meta_file = '../data/DFL_02_01_matchinformation_DFL-COM-000001_DFL-MAT-J03WN1.xml'
event_file = '../data/DFL_03_02_events_raw_DFL-COM-000001_DFL-MAT-J03WN1.xml'

events = sportec.load_event(event_data=event_file, meta_data=meta_file, coordinates='kloppy')
df = events.to_df()

print("Event types with counts:")
for et, cnt in df['event_type'].value_counts().items():
    print(f"  {et}: {cnt}")

print("\nSet piece types:")
for sp, cnt in df['set_piece_type'].value_counts().items():
    print(f"  {sp}: {cnt}")

print("\nResult values:")
for r, cnt in df['result'].value_counts().items():
    print(f"  {r}: {cnt}")

# Shots
shots = df[df['event_type'] == 'SHOT']
print(f"\nShots by team:")
for tid, cnt in shots['team_id'].value_counts().items():
    print(f"  {tid}: {cnt}")
    team_shots = shots[shots['team_id'] == tid]
    for r, c in team_shots['result'].value_counts().items():
        print(f"    {r}: {c}")

# Fouls
fouls = df[df['event_type'] == 'FOUL_COMMITTED']
print(f"\nFouls by team:")
for tid, cnt in fouls['team_id'].value_counts().items():
    print(f"  {tid}: {cnt}")

# Ball ownership for possession
print(f"\nball_owning_team value_counts:")
for t, cnt in df['ball_owning_team'].value_counts().items():
    print(f"  {t}: {cnt}")

# Corners
corners = df[df['set_piece_type'].str.contains('CORNER', case=False, na=False)]
print(f"\nCorners ({len(corners)}):")
for tid, cnt in corners['team_id'].value_counts().items():
    print(f"  {tid}: {cnt}")
