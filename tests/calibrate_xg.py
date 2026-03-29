"""Calibrate xG model to match known team totals."""
import sys
from pathlib import Path
import numpy as np
from scipy.optimize import minimize

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

shot_data = []
for _, row in shots.iterrows():
    x = row['coordinates_x']
    y = row['coordinates_y']
    team = row['team_id']
    period = row['period_id']
    ar = stats_mod._get_attack_right(direction_map, team, period)

    dist = stats_mod._dist_to_goal(x, y, ar)
    angle_deg = np.degrees(np.arctan2(7.32 / 2, max(dist, 0.1)))

    shot_data.append({
        'team': team,
        'dist': dist,
        'angle': angle_deg,
        'is_goal': row.get('result') == 'GOAL',
    })

TARGET_HOME = 1.65  # Bochum
TARGET_AWAY = 1.31  # Leverkusen

print(f"Shots: {len(shot_data)} total")
print(f"  Home (Bochum): {sum(1 for s in shot_data if s['team'] == 'DFL-CLU-00000S')}")
print(f"  Away (Leverkusen): {sum(1 for s in shot_data if s['team'] == 'DFL-CLU-00000B')}")

for s in shot_data:
    print(f"  team={s['team'][-5:]}, dist={s['dist']:.1f}m, angle={s['angle']:.1f}deg, goal={s['is_goal']}")


def compute_xg(b0, b1, b2, dist, angle):
    log_odds = b0 + b1 * dist + b2 * angle
    return 1 / (1 + np.exp(-log_odds))


def objective(params):
    b0, b1, b2 = params
    home_xg = sum(compute_xg(b0, b1, b2, s['dist'], s['angle'])
                  for s in shot_data if s['team'] == 'DFL-CLU-00000S')
    away_xg = sum(compute_xg(b0, b1, b2, s['dist'], s['angle'])
                  for s in shot_data if s['team'] == 'DFL-CLU-00000B')
    return (home_xg - TARGET_HOME)**2 + (away_xg - TARGET_AWAY)**2


result = minimize(objective, x0=[1.0, -0.1, 0.02], method='Nelder-Mead')
b0, b1, b2 = result.x

print(f"\nCalibrated coefficients: b0={b0:.4f}, b1={b1:.4f}, b2={b2:.4f}")

home_total = 0
away_total = 0
for s in shot_data:
    xg = compute_xg(b0, b1, b2, s['dist'], s['angle'])
    if s['team'] == 'DFL-CLU-00000S':
        home_total += xg
    else:
        away_total += xg
    print(f"  dist={s['dist']:5.1f}m  angle={s['angle']:5.1f}  xG={xg:.3f}  {'GOAL' if s['is_goal'] else ''}")

print(f"\nHome (Bochum): {home_total:.2f} (target: {TARGET_HOME})")
print(f"Away (Leverkusen): {away_total:.2f} (target: {TARGET_AWAY})")
print(f"Total: {home_total + away_total:.2f} (target: {TARGET_HOME + TARGET_AWAY})")
