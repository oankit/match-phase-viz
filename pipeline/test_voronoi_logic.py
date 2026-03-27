import sys
sys.path.append('.')
import json
import importlib
import numpy as np

step1 = importlib.import_module('01_load_data')
step4 = importlib.import_module('04_compute_voronoi')

event_dataset, tracking_dataset, events_df, tracking_df = step1.load_match("J03WN1", sample_rate=0.04)
tracking_df = tracking_dataset.to_df()

player_team_map = {}
for team in tracking_dataset.metadata.teams:
    team_id = team.team_id
    for player in team.players:
        player_team_map[player.player_id] = team_id

row = tracking_df.iloc[100]
voronoi_frame = step4.compute_voronoi_for_frame(row, player_team_map, 'polygons')

teams = set()
colors = {}
for cell in voronoi_frame['cells']:
    teams.add(cell['team_id'])
    if cell['polygon'] and len(cell['polygon']) > 0:
        colors[cell['team_id']] = colors.get(cell['team_id'], 0) + 1

print(f"Num cells: {len(voronoi_frame['cells'])}")
print(f"Teams present: {teams}")
print(f"Polygons rendered per team: {colors}")
