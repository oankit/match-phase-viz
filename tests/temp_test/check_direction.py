"""Check attacking direction by looking at shot/goal locations."""
import sys
sys.path.insert(0, '../../pipeline')

from kloppy import sportec
from pathlib import Path
import pandas as pd

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
print(f"Home: {teams[0].name} ({home_id})")
print(f"Away: {teams[1].name} ({away_id})")

# All shots by team
shots = events_df[events_df['event_type'] == 'SHOT'].copy()
print(f"\nTotal shots: {len(shots)}")

print("\n=== HOME SHOTS ===")
home_shots = shots[shots['team_id'] == home_id]
for _, s in home_shots.iterrows():
    print(f"  x={s['coordinates_x']:.3f} y={s['coordinates_y']:.3f} "
          f"result={s.get('result','?')} period={s['period_id']}")
print(f"  Avg x = {home_shots['coordinates_x'].mean():.3f}")

print("\n=== AWAY SHOTS ===")
away_shots = shots[shots['team_id'] == away_id]
for _, s in away_shots.iterrows():
    print(f"  x={s['coordinates_x']:.3f} y={s['coordinates_y']:.3f} "
          f"result={s.get('result','?')} period={s['period_id']}")
print(f"  Avg x = {away_shots['coordinates_x'].mean():.3f}")

# Check passes - do they go toward x=1 for home or x=0?
print("\n=== PASS DIRECTION CHECK ===")
passes = events_df[
    (events_df['event_type'] == 'PASS') &
    (events_df['end_coordinates_x'].notna())
]
home_passes = passes[passes['team_id'] == home_id]
away_passes = passes[passes['team_id'] == away_id]

home_forward = (home_passes['end_coordinates_x'] > home_passes['coordinates_x']).sum()
home_backward = (home_passes['end_coordinates_x'] < home_passes['coordinates_x']).sum()
print(f"Home: {home_forward} passes go RIGHT, {home_backward} go LEFT")

away_forward = (away_passes['end_coordinates_x'] > away_passes['coordinates_x']).sum()
away_backward = (away_passes['end_coordinates_x'] < away_passes['coordinates_x']).sum()
print(f"Away: {away_forward} passes go RIGHT, {away_backward} go LEFT")

# Check per period
for period in [1, 2]:
    p_home = home_passes[home_passes['period_id'] == period]
    p_away = away_passes[away_passes['period_id'] == period]
    h_right = (p_home['end_coordinates_x'] > p_home['coordinates_x']).sum()
    h_left = (p_home['end_coordinates_x'] < p_home['coordinates_x']).sum()
    a_right = (p_away['end_coordinates_x'] > p_away['coordinates_x']).sum()
    a_left = (p_away['end_coordinates_x'] < p_away['coordinates_x']).sum()
    print(f"\nPeriod {period}:")
    print(f"  Home: {h_right} RIGHT, {h_left} LEFT")
    print(f"  Away: {a_right} RIGHT, {a_left} LEFT")
