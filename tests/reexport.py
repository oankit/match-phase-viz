"""
Standalone Re-export Script

Re-runs only the fast pipeline steps and loads pre-computed voronoi/formations
from disk, then re-exports all JSON files with the current config FPS setting.

Use this instead of re-running the full pipeline when only the export
parameters (e.g. target_fps) have changed.

Steps run: 1 (load) -> 2 (features) -> 3 (phases) -> [load voronoi/formations/heatmaps from disk]
           -> 7 (xThreat) -> 9 (match stats) -> 8 (export)

Steps skipped (loaded from disk): 4 (voronoi), 5 (formations), 6 (heatmaps)
"""
import sys
sys.path.insert(0, '../pipeline')

import importlib
import json
from pathlib import Path
import pandas as pd

import config

step1 = importlib.import_module('01_load_data')
step2 = importlib.import_module('02_compute_features')
step3 = importlib.import_module('03_classify_phases')
step7 = importlib.import_module('07_compute_xthreat')
step8 = importlib.import_module('08_export_json')
step9 = importlib.import_module('09_compute_match_stats')

match_id = "J03WN1"
data_dir = Path('../frontend/public/data') / match_id

print("=" * 80)
print("STANDALONE RE-EXPORT")
print("=" * 80)
print(f"\nProcessing mode: {config.PROCESSING_MODE.upper()}")
print(f"  Load rate:    {config.LOADED_FPS} Hz")
print(f"  Export rate:  {config.EXPORT_TARGET_FPS} Hz")
print(f"  Downsample:   every {config.EXPORT_DOWNSAMPLE_FACTOR} frames\n")

# Step 1: Load
print("=" * 80)
print("[STEP 1] Loading match data")
print("=" * 80)
event_dataset, tracking_dataset, events_df, tracking_df_sample = step1.load_match(
    match_id=match_id,
    sample_rate=config.LOAD_SAMPLE_RATE
)
tracking_df = tracking_dataset.to_df()

period_1_mask = tracking_df['period_id'] == 1
period_2_mask = tracking_df['period_id'] == 2
p1_end = tracking_df.loc[period_1_mask, 'timestamp'].max()
PERIOD_2_OFFSET = p1_end + pd.Timedelta(seconds=1.0)
tracking_df.loc[period_2_mask, 'timestamp'] = (
    tracking_df.loc[period_2_mask, 'timestamp'] + PERIOD_2_OFFSET
)
events_df.loc[events_df['period_id'] == 2, 'timestamp'] = (
    events_df.loc[events_df['period_id'] == 2, 'timestamp'] + PERIOD_2_OFFSET
)
print(f"[OK] Loaded: {len(events_df)} events, {len(tracking_df)} tracking frames\n")

# Step 2: Features
print("=" * 80)
print("[STEP 2] Computing features")
print("=" * 80)
features_df = step2.main(tracking_dataset, tracking_df, events_df=events_df)
print(f"[OK] Computed {features_df.shape[0]} feature rows\n")

# Step 3: Phases
print("=" * 80)
print("[STEP 3] Classifying phases")
print("=" * 80)
features_df, phases_df = step3.main(features_df, events_df)
print(f"[OK] Detected {len(phases_df)} phase segments\n")

# Load pre-computed voronoi, formations, heatmaps from disk
print("=" * 80)
print("[STEP 4] Loading Voronoi from disk (pre-computed)")
print("=" * 80)
voronoi_path = data_dir / 'pitch_control.json'
with open(voronoi_path) as f:
    voronoi_data = json.load(f)
print(f"[OK] Loaded {len(voronoi_data)} Voronoi frames from {voronoi_path}\n")

print("=" * 80)
print("[STEP 5] Loading formations from disk (pre-computed)")
print("=" * 80)
formations_path = data_dir / 'formations.json'
with open(formations_path) as f:
    formations = json.load(f)
print(f"[OK] Loaded {len(formations)} formations from {formations_path}\n")

print("=" * 80)
print("[STEP 6] Loading heatmaps from disk (pre-computed)")
print("=" * 80)
heatmaps_path = data_dir / 'heatmaps.json'
with open(heatmaps_path) as f:
    heatmaps = json.load(f)
print(f"[OK] Loaded {len(heatmaps)} heatmaps from {heatmaps_path}\n")

# Step 7: xThreat
print("=" * 80)
print("[STEP 7] Computing xThreat")
print("=" * 80)
phases_df_with_xthreat, events_df_with_xt = step7.main(events_df, phases_df)
print(f"[OK] Computed xThreat for {len(phases_df_with_xthreat)} phases\n")

# Step 9: Match stats
print("=" * 80)
print("[STEP 9] Computing match & player stats")
print("=" * 80)
match_stats, player_stats = step9.compute_all(events_df, tracking_dataset)
print(f"[OK] Computed {len(match_stats)} stat categories, {len(player_stats)} player stats\n")

# Step 8: Export
print("=" * 80)
print("[STEP 8] Exporting to JSON")
print("=" * 80)
match_duration = tracking_df['timestamp'].max().total_seconds()
p2_offset_secs = PERIOD_2_OFFSET.total_seconds()
exported_files = step8.main(
    match_id=match_id,
    tracking_dataset=tracking_dataset,
    tracking_df=tracking_df,
    phases_df=phases_df_with_xthreat,
    formations=formations,
    voronoi_data=voronoi_data,
    heatmaps=heatmaps,
    target_fps=config.EXPORT_TARGET_FPS,
    match_duration=match_duration,
    events_df=events_df_with_xt,
    period_2_offset_secs=p2_offset_secs,
    match_stats=match_stats,
    player_stats=player_stats,
)

print("\n" + "=" * 80)
print("RE-EXPORT COMPLETE")
print("=" * 80)
print(f"\nExported JSON files:")
for key, path in exported_files.items():
    file_size = Path(path).stat().st_size / 1024
    print(f"  {key}: {file_size:.1f} KB")
print(f"\nOutput: {data_dir}/")
print("=" * 80)
