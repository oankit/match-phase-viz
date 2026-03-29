"""Check what card/dismissal events exist in the event data."""
import sys
sys.path.insert(0, '../pipeline')
from kloppy import sportec
import config

meta_file = '../data/DFL_02_01_matchinformation_DFL-COM-000001_DFL-MAT-J03WN1.xml'
event_file = '../data/DFL_03_02_events_raw_DFL-COM-000001_DFL-MAT-J03WN1.xml'

events = sportec.load_event(event_data=event_file, meta_data=meta_file, coordinates='kloppy')
df = events.to_df()

print("All unique event types:")
for et in sorted(df['event_type'].unique()):
    print(f"  {et}")

print("\nAll unique result values:")
for r in sorted(df['result'].dropna().unique()):
    print(f"  {r}")

card_like = df[df['event_type'].str.contains('CARD|RED|YELLOW|FOUL|DISMISS', case=False, na=False)]
print(f"\nCard-like events ({len(card_like)}):")
for _, row in card_like.iterrows():
    ts = row['timestamp'].total_seconds()
    period = row['period_id']
    match_min = int((ts + (45 * 60 if period == 2 else 0)) / 60)
    print(f"  {match_min}' - {row['event_type']} result={row.get('result')} player={row['player_id']} team={row['team_id']}")

print("\n--- Looking for Adli ---")
adli = df[df['player_id'].str.contains('', na=False)]
player_names = {}
for team in events.metadata.teams:
    for p in team.players:
        if 'adli' in (p.name or '').lower():
            print(f"Found Adli: {p.player_id} = {p.name}, team={team.team_id}")
            player_names[p.player_id] = p.name

print("\nAll columns:", df.columns.tolist())

# Check for any raw attributes that might contain card info
print("\n--- Checking raw event attributes ---")
sample = df.head(1)
for col in df.columns:
    if 'card' in col.lower() or 'red' in col.lower() or 'yellow' in col.lower():
        print(f"  Column: {col}")
