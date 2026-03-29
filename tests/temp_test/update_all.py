"""Re-apply xThreat fix + match stats to the new pipeline output."""
import sys
sys.path.insert(0, '../../pipeline')

from kloppy import sportec
from pathlib import Path
import json
import pandas as pd
import numpy as np

data_path = Path('../../data')
meta_file = list(data_path.glob('*matchinformation*J03WN1.xml'))[0]
event_file = list(data_path.glob('*events_raw*J03WN1.xml'))[0]
positions_file = list(data_path.glob('*positions_raw*J03WN1.xml'))[0]

print("Loading event data...")
event_dataset = sportec.load_event(
    event_data=str(event_file),
    meta_data=str(meta_file),
    coordinates='kloppy'
)
events_df_raw = event_dataset.to_df()
events_df = events_df_raw.copy()

print("Loading tracking data...")
tracking_dataset = sportec.load_tracking(
    raw_data=str(positions_file),
    meta_data=str(meta_file),
    coordinates='kloppy',
    only_alive=True,
    sample_rate=1/25
)

# Determine period 2 offset from frames.json (matches pipeline)
frames_path = Path('../../frontend/public/data/J03WN1/frames.json')
with open(frames_path) as f:
    frames = json.load(f)

p1_frames = [f for f in frames if f.get('period_id') == 1]
p2_frames = [f for f in frames if f.get('period_id') == 2]
p1_end = max(f['t'] for f in p1_frames) if p1_frames else 45 * 60
p2_start = min(f['t'] for f in p2_frames) if p2_frames else p1_end + 1
PERIOD_2_OFFSET = p2_start
print(f"Period 1 ends at {p1_end:.1f}s, Period 2 starts at {p2_start:.1f}s")

# Offset event timestamps for period 2 to match phase timestamps
p2_evt_mask = events_df['period_id'] == 2
events_df.loc[p2_evt_mask, 'timestamp'] = (
    events_df.loc[p2_evt_mask, 'timestamp'] + pd.Timedelta(seconds=PERIOD_2_OFFSET)
)
print(f"Offset {p2_evt_mask.sum()} period 2 events by +{PERIOD_2_OFFSET:.1f}s")

# ===== 1. Recompute xThreat for phases =====
phases_path = Path('../../frontend/public/data/J03WN1/phases.json')
with open(phases_path) as f:
    phases = json.load(f)

xt_path = Path('../../pipeline/xt_grid_12x8.json')
with open(xt_path) as f:
    threat_surface = np.array(json.load(f))

from importlib import util
spec = util.spec_from_file_location("xthreat", "../../pipeline/07_compute_xthreat.py")
xtmod = util.module_from_spec(spec)
spec.loader.exec_module(xtmod)

print("\nRecomputing xThreat for phases...")

# Pre-compute xThreat for all events
events_df['_xt'] = events_df.apply(
    lambda e: xtmod.compute_xthreat_for_event(e, threat_surface), axis=1
)

# Pass 1: exact match, each event assigned to at most one phase
assigned_evt_indices = set()
updated = 0

for phase in phases:
    start_td = pd.Timedelta(seconds=phase['start'])
    end_td = pd.Timedelta(seconds=phase['end'])

    phase_events = events_df[
        (events_df['timestamp'] >= start_td) &
        (events_df['timestamp'] <= end_td) &
        (~events_df.index.isin(assigned_evt_indices))
    ]

    if len(phase_events) == 0:
        phase['xthreat_gained'] = 0.0
        phase['xthreat_conceded'] = 0.0
        continue

    assigned_evt_indices.update(phase_events.index.tolist())

    team_sums = phase_events.groupby('team_id')['_xt'].sum().to_dict()

    old_gained = phase['xthreat_gained']
    gained = team_sums.get(phase['team'], 0.0)
    phase['xthreat_gained'] = round(gained, 4)

    opponent_teams = [t for t in team_sums if t != phase['team']]
    conceded = sum(team_sums.get(t, 0.0) for t in opponent_teams)
    phase['xthreat_conceded'] = round(conceded, 4)

    if abs(gained - old_gained) > 0.001:
        updated += 1

# Pass 2: assign unmatched events with significant xThreat to nearest phase
unmatched_significant = events_df[
    (~events_df.index.isin(assigned_evt_indices)) &
    (events_df['_xt'].abs() > 0.01)
]

if len(unmatched_significant) > 0:
    print(f"  Found {len(unmatched_significant)} unmatched events with |xT| > 0.01")

    phase_ends = [(p['end'], i) for i, p in enumerate(phases)]
    phase_ends.sort(key=lambda x: x[0])

    for _, evt in unmatched_significant.iterrows():
        xt = evt['_xt']
        evt_time = evt['timestamp'].total_seconds()
        evt_team = evt['team_id']
        result = evt.get('result', '')
        event_type = evt.get('event_type', '')

        # Find nearest phase belonging to the SAME team as the event
        best_idx = None
        best_dist = float('inf')
        for p_end, p_idx in phase_ends:
            if phases[p_idx]['team'] != evt_team:
                continue
            dist = abs(evt_time - p_end)
            if dist <= 15 and dist < best_dist:
                best_dist = dist
                best_idx = p_idx

        if best_idx is None:
            continue

        phase = phases[best_idx]
        phase['xthreat_gained'] = round(phase['xthreat_gained'] + xt, 4)

        print(f"    Assigned {event_type}/{result} xT={xt:.4f} at t={evt_time:.1f}s "
              f"-> phase {phase['id']} (team={evt_team}, ends {phase['end']:.1f}s)")
        updated += 1

print(f"  Updated {updated} phases with xThreat values")

with open(phases_path, 'w') as f:
    json.dump(phases, f, indent=2)
print(f"  Saved phases.json")

# ===== 2. Recompute match stats + player stats =====
events_df_original = events_df_raw

spec2 = util.spec_from_file_location("stats", "../../pipeline/09_compute_match_stats.py")
stats_mod = util.module_from_spec(spec2)
spec2.loader.exec_module(stats_mod)

teams = tracking_dataset.metadata.teams
team_ids = [teams[0].team_id, teams[1].team_id]

print("\nComputing match stats...")
match_stats = stats_mod.compute_match_stats(events_df_original, team_ids)
for key, stat in match_stats.items():
    print(f"  {stat['label']}: {stat['home']} vs {stat['away']}")

print("\nComputing player stats...")
player_stats = stats_mod.compute_player_stats(events_df_original, tracking_dataset)

# ===== 3. Update metadata.json =====
metadata_path = Path('../../frontend/public/data/J03WN1/metadata.json')
with open(metadata_path, encoding='utf-8') as f:
    metadata = json.load(f)

metadata['match_stats'] = match_stats

player_list = []
for pid, p in player_stats.items():
    if p['minutes'] == 0:
        continue
    entry = {k: v for k, v in p.items()}
    player_list.append(entry)

metadata['player_stats'] = player_list

# Update goals with correct period 2 offset
goal_list = []
shots = events_df_original[
    (events_df_original['event_type'] == 'SHOT') & (events_df_original['result'] == 'GOAL')
]
player_name_map = {}
for team in tracking_dataset.metadata.teams:
    for player in team.players:
        name = player.name if player.name else player.player_id
        player_name_map[player.player_id] = name

for _, g in shots.iterrows():
    ts = g['timestamp']
    period = g['period_id']
    match_seconds = (PERIOD_2_OFFSET + ts.total_seconds()) if period == 2 else ts.total_seconds()
    goal_list.append({
        'team_id': g['team_id'],
        'player_id': g['player_id'],
        'player_name': player_name_map.get(g['player_id'], g['player_id']),
        'minute': int(match_seconds // 60),
        'match_seconds': round(match_seconds, 1),
        'period': period,
    })

metadata['goals'] = goal_list
print(f"\nGoals:")
for g in goal_list:
    print(f"  {g['player_name']} - minute {g['minute']} (t={g['match_seconds']}s, period {g['period']})")

with open(metadata_path, 'w', encoding='utf-8') as f:
    json.dump(metadata, f, indent=2, ensure_ascii=True)

print(f"\nUpdated metadata.json")
print("Done!")
