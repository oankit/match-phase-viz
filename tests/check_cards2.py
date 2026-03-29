"""Check card_type values and Adli's events."""
import sys
sys.path.insert(0, '../pipeline')
from kloppy import sportec

meta_file = '../data/DFL_02_01_matchinformation_DFL-COM-000001_DFL-MAT-J03WN1.xml'
event_file = '../data/DFL_03_02_events_raw_DFL-COM-000001_DFL-MAT-J03WN1.xml'

events = sportec.load_event(event_data=event_file, meta_data=meta_file, coordinates='kloppy')
df = events.to_df()

cards = df[df['event_type'] == 'CARD']
print("CARD events with card_type:")
for _, row in cards.iterrows():
    ts = row['timestamp'].total_seconds()
    period = row['period_id']
    match_min = int((ts + (45 * 60 if period == 2 else 0)) / 60)
    print(f"  {match_min}' - player={row['player_id']} team={row['team_id']} card_type={row.get('card_type')}")

print(f"\nUnique card_type values: {df['card_type'].dropna().unique()}")

# Check Adli's last event
adli_id = 'DFL-OBJ-J01KDN'
adli_events = df[df['player_id'] == adli_id].sort_values('timestamp')
print(f"\nAdli's events ({len(adli_events)}):")
for _, row in adli_events.iterrows():
    ts = row['timestamp'].total_seconds()
    period = row['period_id']
    match_min = int((ts + (45 * 60 if period == 2 else 0)) / 60)
    print(f"  {match_min}' - {row['event_type']} card_type={row.get('card_type')} result={row.get('result')}")

# Check substitution events for Adli's team
subs = df[(df['event_type'] == 'SUBSTITUTION') & (df['team_id'] == 'DFL-CLU-00000B')].sort_values('timestamp')
print(f"\nLeverkusen substitutions ({len(subs)}):")
for _, row in subs.iterrows():
    ts = row['timestamp'].total_seconds()
    period = row['period_id']
    match_min = int((ts + (45 * 60 if period == 2 else 0)) / 60)
    print(f"  {match_min}' - player={row['player_id']}")
