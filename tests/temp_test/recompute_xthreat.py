"""Recompute xThreat for J03WN1 and update phases.json."""
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

print("Loading event data...")
event_dataset = sportec.load_event(
    event_data=str(event_file),
    meta_data=str(meta_file),
    coordinates='kloppy'
)
events_df = event_dataset.to_df()
print(f"  Loaded {len(events_df)} events")

phases_path = Path('../../frontend/public/data/J03WN1/phases.json')
print(f"Loading phases from {phases_path}...")
with open(phases_path) as f:
    phases = json.load(f)
print(f"  Loaded {len(phases)} phases")

import importlib
import config
from importlib import reload

import sys as _sys
_sys.path.insert(0, '../../pipeline')
import importlib
import config
reload(config)

from pathlib import Path as _P
xt_path = _P('../../pipeline/xt_grid_12x8.json')
with open(xt_path) as f:
    threat_surface = np.array(json.load(f))
print(f"  Loaded xT grid {threat_surface.shape}")

# Import the updated module
spec = importlib.util.spec_from_file_location("xthreat", "../../pipeline/07_compute_xthreat.py")
xtmod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(xtmod)

print("\nRecomputing xThreat for each phase...")
updated = 0
for phase in phases:
    start_time = pd.Timedelta(seconds=phase['start'])
    end_time = pd.Timedelta(seconds=phase['end'])

    phase_events = events_df[
        (events_df['timestamp'] >= start_time) &
        (events_df['timestamp'] <= end_time)
    ]

    if len(phase_events) == 0:
        continue

    xt_values = []
    for _, ev in phase_events.iterrows():
        xt = xtmod.compute_xthreat_for_event(ev, threat_surface)
        xt_values.append({'team': ev['team_id'], 'xt': xt})

    if not xt_values:
        continue

    team_sums = {}
    for v in xt_values:
        team_sums[v['team']] = team_sums.get(v['team'], 0) + v['xt']

    old_gained = phase['xthreat_gained']
    gained = team_sums.get(phase['team'], 0.0)
    opponent_teams = [t for t in team_sums if t != phase['team']]
    conceded = sum(team_sums.get(t, 0.0) for t in opponent_teams)

    phase['xthreat_gained'] = round(gained, 4)
    phase['xthreat_conceded'] = round(conceded, 4)

    if abs(gained - old_gained) > 0.001:
        updated += 1

print(f"  Updated {updated} phases with new xThreat values")

# Check around goals
print("\n=== AROUND 1ST GOAL (min 16-20) ===")
for p in phases:
    if 960 <= p['start'] <= 1200 and p['team'][-1] == 'S' and p['xthreat_gained'] > 0.001:
        print(f"  id={p['id']:4d} type={p['type']:18s} "
              f"start={p['start']/60:.1f}m xt_gained={p['xthreat_gained']:.4f}")

print("\n=== AROUND 2ND GOAL (min 31-35) ===")
for p in phases:
    if 1860 <= p['start'] <= 2100 and p['team'][-1] == 'S' and p['xthreat_gained'] > 0.001:
        print(f"  id={p['id']:4d} type={p['type']:18s} "
              f"start={p['start']/60:.1f}m xt_gained={p['xthreat_gained']:.4f}")

print(f"\nWriting updated phases to {phases_path}...")
with open(phases_path, 'w') as f:
    json.dump(phases, f, indent=2)

print("Done!")
