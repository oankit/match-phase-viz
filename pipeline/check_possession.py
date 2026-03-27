import sys
sys.path.append('.')
import importlib
import numpy as np

step1 = importlib.import_module('01_load_data')
event_dataset, tracking_dataset, events_df, tracking_df = step1.load_match("J03WN1", sample_rate=0.04)
tracking_df = tracking_dataset.to_df()

print("Unique ball_owning_team_id values:")
print(tracking_df['ball_owning_team_id'].unique())
print("\nFirst 20 rows of ball_owning_team_id:")
print(tracking_df['ball_owning_team_id'].head(20).tolist())
