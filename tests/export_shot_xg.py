"""Extract shot-level xG data with timestamps for the cumulative xG chart."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'pipeline'))

from kloppy import sportec
import pandas as pd
import numpy as np
import importlib
stats_mod = importlib.import_module('09_compute_match_stats')

MATCH_ID = "J03WN1"
DATA_DIR = Path(__file__).parent.parent / "data"
DIST_DIR = Path(__file__).parent.parent / "frontend" / "dist" / "data" / MATCH_ID
PUBLIC_DIR = Path(__file__).parent.parent / "frontend" / "public" / "data" / MATCH_ID

meta_file = list(DATA_DIR.glob(f"*matchinformation*{MATCH_ID}.xml"))[0]
event_file = list(DATA_DIR.glob(f"*events_raw*{MATCH_ID}.xml"))[0]
tracking_file = list(DATA_DIR.glob(f"*positions_raw*{MATCH_ID}.xml"))[0]

print("Loading events...")
event_dataset = sportec.load_event(
    event_data=str(event_file),
    meta_data=str(meta_file),
    coordinates='kloppy'
)
events_df = event_dataset.to_df()

print("Loading tracking metadata...")
tracking_dataset = sportec.load_tracking(
    raw_data=str(tracking_file),
    meta_data=str(meta_file),
    coordinates='kloppy',
    only_alive=True,
    sample_rate=0.001
)

teams = tracking_dataset.metadata.teams
home_id = teams[0].team_id
away_id = teams[1].team_id
team_ids = [home_id, away_id]

player_name_map = {}
for team in teams:
    for player in team.players:
        player_name_map[player.player_id] = player.name if player.name else player.player_id

direction_map = stats_mod._detect_attacking_direction(events_df, team_ids)

# Detect period 2 offset from metadata
meta_path = DIST_DIR / "metadata.json"
with open(meta_path, 'r', encoding='utf-8') as f:
    metadata = json.load(f)
match_duration = metadata.get('duration', 90 * 60)

# Find period 2 start from events
p2_events = events_df[events_df['period_id'] == 2]
if len(p2_events) > 0:
    p2_first_ts = p2_events['timestamp'].min().total_seconds()
else:
    p2_first_ts = 0
period_2_offset = 45 * 60

shots = events_df[events_df['event_type'] == 'SHOT'].sort_values('timestamp')

print(f"Found {len(shots)} shots")

shot_list = []
for _, row in shots.iterrows():
    ts = row['timestamp'].total_seconds()
    period = row['period_id']
    match_seconds = (period_2_offset + ts) if period == 2 else ts
    minute = match_seconds / 60

    x = row['coordinates_x']
    y = row['coordinates_y']
    team_id = row['team_id']

    ar = stats_mod._get_attack_right(direction_map, team_id, period)
    xg = stats_mod._positional_xg(x, y, ar)

    is_goal = row.get('result') == 'GOAL'

    shot_list.append({
        'minute': round(minute, 2),
        'match_seconds': round(match_seconds, 1),
        'team_id': team_id,
        'player_id': row['player_id'],
        'player_name': player_name_map.get(row['player_id'], row['player_id']),
        'xg': round(xg, 3),
        'is_goal': bool(is_goal),
        'result': str(row.get('result', '')),
    })

output = {
    'home_team_id': home_id,
    'away_team_id': away_id,
    'match_duration_minutes': round(match_duration / 60, 1),
    'shots': shot_list,
}

print(f"\nShot xG data:")
for s in shot_list:
    marker = " *** GOAL ***" if s['is_goal'] else ""
    print(f"  {s['minute']:.1f}' - {s['player_name']} ({s['team_id'][:12]}) xG={s['xg']:.3f} [{s['result']}]{marker}")

for out_dir in [DIST_DIR, PUBLIC_DIR]:
    if out_dir.exists():
        out_path = out_dir / "shot_xg.json"
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=True)
        print(f"\nExported to {out_path}")

print("Done!")
