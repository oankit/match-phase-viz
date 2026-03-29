"""Debug build-ups with correct direction."""
import sys
sys.path.insert(0, '../../pipeline')

from kloppy import sportec
from pathlib import Path
import pandas as pd
import numpy as np

data_path = Path('../../data')
meta_file = list(data_path.glob('*matchinformation*J03WN1.xml'))[0]
event_file = list(data_path.glob('*events_raw*J03WN1.xml'))[0]

event_dataset = sportec.load_event(
    event_data=str(event_file),
    meta_data=str(meta_file),
    coordinates='kloppy'
)
events_df = event_dataset.to_df()
teams = event_dataset.metadata.teams
home_id = teams[0].team_id
away_id = teams[1].team_id

from importlib import util
spec = util.spec_from_file_location("stats", "../../pipeline/09_compute_match_stats.py")
mod = util.module_from_spec(spec)
spec.loader.exec_module(mod)

direction_map = mod._detect_attacking_direction(events_df, [home_id, away_id])
print("Direction map:")
for (tid, period), ar in direction_map.items():
    tag = 'Home' if tid == home_id else 'Away'
    print(f"  {tag} period {period}: {'RIGHT' if ar else 'LEFT'}")

home_poss = mod._build_possessions(events_df, home_id)
away_poss = mod._build_possessions(events_df, away_id)

def check_buildups(possessions, direction_map, team_id, label, min_passes=5):
    count = 0
    checked = 0
    for poss in possessions:
        period = poss.iloc[0]['period_id']
        ar = mod._get_attack_right(direction_map, team_id, period)
        passes = poss[poss['event_type'] == 'PASS']
        if len(passes) < min_passes:
            continue
        checked += 1

        box_depth = 16.5 / 105.0
        reached = False
        max_forward_x = None

        for _, ev in poss.iterrows():
            x, y = ev['coordinates_x'], ev['coordinates_y']
            if pd.isna(x) or pd.isna(y):
                continue

            if mod._in_box(x, y, ar):
                reached = True

            # Track how far forward we got
            if ar:
                if max_forward_x is None or x > max_forward_x:
                    max_forward_x = x
            else:
                if max_forward_x is None or x < max_forward_x:
                    max_forward_x = x

            # Also check end_coordinates for passes
            ex, ey = ev.get('end_coordinates_x'), ev.get('end_coordinates_y')
            if pd.notna(ex) and pd.notna(ey):
                if mod._in_box(ex, ey, ar):
                    reached = True

        x_dist = mod._x_dist_to_goal(max_forward_x, ar) if max_forward_x is not None else 999
        result = "IN BOX" if reached else f"max_fwd_x_dist={x_dist:.1f}m"
        print(f"    Poss: {len(poss)} events, {len(passes)} passes, "
              f"period={period}, ar={'R' if ar else 'L'}: {result}")

        if reached:
            count += 1

    print(f"\n{label}: {checked} poss with {min_passes}+ passes, {count} reached box")

check_buildups(home_poss, direction_map, home_id, "HOME", 5)
print()
check_buildups(away_poss, direction_map, away_id, "AWAY", 5)

# Also check with lower threshold
print("\n\nWith 4+ passes:")
check_buildups(home_poss, direction_map, home_id, "HOME", 4)
print()
check_buildups(away_poss, direction_map, away_id, "AWAY", 4)
