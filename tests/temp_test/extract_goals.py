"""Extract goal data from match events and update metadata.json."""
from kloppy import sportec
from pathlib import Path
import pandas as pd
import json

data_path = Path(__file__).parent / '../../data'
meta_file = list(data_path.glob('*matchinformation*J03WN1.xml'))[0]
event_file = list(data_path.glob('*events_raw*J03WN1.xml'))[0]

event_dataset = sportec.load_event(
    event_data=str(event_file),
    meta_data=str(meta_file),
    coordinates='kloppy'
)
events_df = event_dataset.to_df()

goals = events_df[(events_df['event_type'] == 'SHOT') & (events_df['result'] == 'GOAL')]
print(f'Found {len(goals)} goals')
print(goals[['period_id', 'timestamp', 'team_id', 'player_id', 'result']].to_string())

# Build player name lookup
player_name_map = {}
for team in event_dataset.metadata.teams:
    for player in team.players:
        player_name_map[player.player_id] = player.name if player.name else player.player_id

# Build goal list for metadata
goal_list = []
for _, g in goals.iterrows():
    ts = g['timestamp']
    period = g['period_id']
    # Convert to match seconds
    if period == 2:
        match_seconds = 45 * 60 + ts.total_seconds()
    else:
        match_seconds = ts.total_seconds()

    goal_list.append({
        'team_id': g['team_id'],
        'player_id': g['player_id'],
        'player_name': player_name_map.get(g['player_id'], g['player_id']),
        'minute': int(match_seconds // 60),
        'match_seconds': round(match_seconds, 1),
        'period': period,
    })

print('\n=== Goals JSON ===')
print(json.dumps(goal_list, indent=2))

# Update metadata.json
metadata_path = Path(__file__).parent / '../../frontend/public/data/J03WN1/metadata.json'
with open(metadata_path, encoding='latin-1') as f:
    metadata = json.load(f)

metadata['goals'] = goal_list

# Add badge mapping
metadata['badges'] = {
    'DFL-CLU-00000S': '/assets/VfL Bochum 1848.png',
    'DFL-CLU-00000B': '/assets/Bayer_04_Leverkusen.png',
}

with open(metadata_path, 'w', encoding='utf-8') as f:
    json.dump(metadata, f, indent=2, ensure_ascii=False)

print(f'\nUpdated {metadata_path}')

# Also update output copy if it exists
output_path = Path(__file__).parent / '../../output/J03WN1/metadata.json'
if output_path.exists():
    with open(output_path, encoding='latin-1') as f:
        out_meta = json.load(f)
    out_meta['goals'] = goal_list
    out_meta['badges'] = metadata['badges']
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(out_meta, f, indent=2, ensure_ascii=False)
    print(f'Updated {output_path}')
