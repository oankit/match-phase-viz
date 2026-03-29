"""Test the fixed match stats computation."""
import sys
sys.path.insert(0, '../../pipeline')

from kloppy import sportec
from pathlib import Path
import json

data_path = Path('../../data')
meta_file = list(data_path.glob('*matchinformation*J03WN1.xml'))[0]
event_file = list(data_path.glob('*events_raw*J03WN1.xml'))[0]

print("Loading data...")
event_dataset = sportec.load_event(
    event_data=str(event_file),
    meta_data=str(meta_file),
    coordinates='kloppy'
)

positions_file = list(data_path.glob('*positions_raw*J03WN1.xml'))[0]
tracking_dataset = sportec.load_tracking(
    raw_data=str(positions_file),
    meta_data=str(meta_file),
    coordinates='kloppy',
    only_alive=True,
    sample_rate=1/25
)

events_df = event_dataset.to_df()

from importlib import util
spec = util.spec_from_file_location("stats", "../../pipeline/09_compute_match_stats.py")
stats_mod = util.module_from_spec(spec)
spec.loader.exec_module(stats_mod)

print("\nComputing match stats...")
teams = tracking_dataset.metadata.teams
team_ids = [teams[0].team_id, teams[1].team_id]
match_stats = stats_mod.compute_match_stats(events_df, team_ids)

print("\n" + "=" * 60)
print("CORRECTED MATCH STATS")
print("=" * 60)
for key, stat in match_stats.items():
    print(f"\n{stat['label']}:")
    print(f"  Home: {stat['home']} (rating: {stat['home_rating']})")
    print(f"  Away: {stat['away']} (rating: {stat['away_rating']})")

print("\nComputing player stats...")
player_stats = stats_mod.compute_player_stats(events_df, tracking_dataset)
active = {k: v for k, v in player_stats.items() if v['minutes'] > 0}
print(f"  {len(active)} players with minutes")

# Export to metadata.json
metadata_path = Path('../../frontend/public/data/J03WN1/metadata.json')
with open(metadata_path, encoding='utf-8') as f:
    metadata = json.load(f)

metadata['match_stats'] = match_stats

player_list = []
for pid, p in player_stats.items():
    if p['minutes'] == 0:
        continue
    entry = {k: v for k, v in p.items()}
    entry['name'] = p['name'].encode('ascii', 'replace').decode()
    player_list.append(entry)

metadata['player_stats'] = player_list

with open(metadata_path, 'w', encoding='utf-8') as f:
    json.dump(metadata, f, indent=2, ensure_ascii=True)

print(f"\nUpdated {metadata_path}")
