"""Test the exponential xG model from the reference code."""
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / 'pipeline'))

from kloppy import sportec
import importlib
stats_mod = importlib.import_module('09_compute_match_stats')
import config

MATCH_ID = "J03WN1"
DATA_DIR = Path(__file__).parent.parent / "data"
PITCH_L = config.PITCH_LENGTH
PITCH_W = config.PITCH_WIDTH

meta_file = list(DATA_DIR.glob(f"*matchinformation*{MATCH_ID}.xml"))[0]
event_file = list(DATA_DIR.glob(f"*events_raw*{MATCH_ID}.xml"))[0]

event_dataset = sportec.load_event(
    event_data=str(event_file),
    meta_data=str(meta_file),
    coordinates='kloppy'
)
events_df = event_dataset.to_df()

teams = ['DFL-CLU-00000S', 'DFL-CLU-00000B']
direction_map = stats_mod._detect_attacking_direction(events_df, teams)

shots = events_df[events_df['event_type'] == 'SHOT'].copy()

print(f"Testing exponential xG: 0.82 * exp(-0.11 * dist)")
print(f"{'='*60}")

home_exp = 0
away_exp = 0
home_log = 0
away_log = 0

for _, row in shots.iterrows():
    x = row['coordinates_x']
    y = row['coordinates_y']
    team = row['team_id']
    period = row['period_id']
    ar = stats_mod._get_attack_right(direction_map, team, period)

    dist = stats_mod._dist_to_goal(x, y, ar)

    xg_exp = 0.82 * np.exp(-0.11 * dist)

    angle = np.degrees(np.arctan2(7.32 / 2, max(dist, 0.1)))
    log_odds = 0.9067 - 0.2202 * dist + 0.0188 * angle
    xg_log = 1 / (1 + np.exp(-log_odds))

    label = "HOME" if team == 'DFL-CLU-00000S' else "AWAY"
    goal = " GOAL" if row.get('result') == 'GOAL' else ""
    print(f"  {label} dist={dist:5.1f}m  xG_exp={xg_exp:.3f}  xG_log={xg_log:.3f}{goal}")

    if team == 'DFL-CLU-00000S':
        home_exp += xg_exp
        home_log += xg_log
    else:
        away_exp += xg_exp
        away_log += xg_log

print(f"\n{'='*60}")
print(f"Target:      Home=1.65  Away=1.31  Total=2.96")
print(f"Exponential: Home={home_exp:.2f}  Away={away_exp:.2f}  Total={home_exp+away_exp:.2f}")
print(f"Logistic:    Home={home_log:.2f}  Away={away_log:.2f}  Total={home_log+away_log:.2f}")
