"""
Full Pipeline Integration Test
Tests all 9 steps together: Load > Features > Phases > Voronoi > Formations > Pressing > xThreat > Export (+ Match Stats & Shot xG)
"""
import sys
sys.path.insert(0, '../pipeline')

import importlib
from pathlib import Path
import pandas as pd

# Import configuration
import config

# Import all steps
step1 = importlib.import_module('01_load_data')
step2 = importlib.import_module('02_compute_features')
step3 = importlib.import_module('03_classify_phases')
step4 = importlib.import_module('04_compute_pitch_control')
step5 = importlib.import_module('05_compute_formations')
step6 = importlib.import_module('06_compute_pressing')
step7 = importlib.import_module('07_compute_xthreat')
step8 = importlib.import_module('08_export_json')
step9 = importlib.import_module('09_compute_match_stats')

print("="*80)
print("FULL PIPELINE INTEGRATION TEST")
print("="*80)
print("\nTesting all 9 steps: Load > Features > Phases > Voronoi > Formations > Pressing > xThreat > Stats > Export\n")

# Configuration based on PROCESSING_MODE in config.py
match_id = "J03WN1"
sample_rate = config.LOAD_SAMPLE_RATE  # Uses config value

print(f"PROCESSING MODE: {config.PROCESSING_MODE.upper()}")
print(f"  - Loading at: {config.LOADED_FPS} Hz (sample_rate={sample_rate})")
print(f"  - Exporting at: {config.EXPORT_TARGET_FPS} Hz")
print(f"  - Downsample factor: {config.EXPORT_DOWNSAMPLE_FACTOR}")
print()

# ============================================================================
# STEP 1: Load Data
# ============================================================================
print("="*80)
print("[STEP 1] Loading match data")
print("="*80)
event_dataset, tracking_dataset, events_df, tracking_df_sample = step1.load_match(
    match_id=match_id,
    sample_rate=sample_rate
)

tracking_df = tracking_dataset.to_df()

# Offset period 2 timestamps so they continue from period 1 (not restart at 0)
period_1_mask = tracking_df['period_id'] == 1
period_2_mask = tracking_df['period_id'] == 2
p1_end = tracking_df.loc[period_1_mask, 'timestamp'].max()
PERIOD_2_OFFSET = p1_end + pd.Timedelta(seconds=1.0)
p2_count = period_2_mask.sum()
tracking_df.loc[period_2_mask, 'timestamp'] = (
    tracking_df.loc[period_2_mask, 'timestamp'] + PERIOD_2_OFFSET
)
evt_p2_mask = events_df['period_id'] == 2
events_df.loc[evt_p2_mask, 'timestamp'] = (
    events_df.loc[evt_p2_mask, 'timestamp'] + PERIOD_2_OFFSET
)
print(f"[OK] Loaded: {len(events_df)} events, {len(tracking_df)} tracking frames")
print(f"     Period 1 ends at {p1_end.total_seconds():.1f}s ({p1_end.total_seconds()/60:.1f} min)")
print(f"     Period 2 offset: +{PERIOD_2_OFFSET.total_seconds():.1f}s (applied to tracking + events)")
ts_max = tracking_df['timestamp'].max().total_seconds()
print(f"     Match time range: 0s - {ts_max:.1f}s ({ts_max/60:.1f} min)\n")

# ============================================================================
# STEP 2: Compute Features
# ============================================================================
print("="*80)
print("[STEP 2] Computing features")
print("="*80)
features_df = step2.main(tracking_dataset, tracking_df)
print(f"[OK] Computed {features_df.shape[0]} feature rows\n")

# ============================================================================
# STEP 3: Classify Phases
# ============================================================================
print("="*80)
print("[STEP 3] Classifying phases")
print("="*80)
features_df, phases_df = step3.main(features_df, events_df)
print(f"[OK] Detected {len(phases_df)} phase segments\n")

# ============================================================================
# STEP 4: Compute Voronoi
# ============================================================================
print("="*80)
print("[STEP 4] Computing Rest Defence Grid")
print("="*80)
voronoi_data = step4.main(tracking_dataset, tracking_df, output_format='rest_defence')
print(f"[OK] Computed Rest Defence for {len(voronoi_data)} frames\n")

# ============================================================================
# STEP 5: Compute Formations
# ============================================================================
print("="*80)
print("[STEP 5] Computing formation graphs")
print("="*80)
formations = step5.main(tracking_dataset, tracking_df, phases_df)
print(f"[OK] Computed {len(formations)} formations\n")

# ============================================================================
# STEP 6: Compute Pressing Heatmaps
# ============================================================================
print("="*80)
print("[STEP 6] Computing pressing heatmaps")
print("="*80)
heatmaps = step6.main(phases_df, features_df, tracking_df)
print(f"[OK] Computed {len(heatmaps)} pressing heatmaps\n")

# ============================================================================
# STEP 7: Compute xThreat
# ============================================================================
print("="*80)
print("[STEP 7] Computing xThreat")
print("="*80)
phases_df_with_xthreat = step7.main(events_df, phases_df)
print(f"[OK] Computed xThreat for {len(phases_df_with_xthreat)} phases\n")

# ============================================================================
# STEP 9: Compute Match & Player Stats
# ============================================================================
print("="*80)
print("[STEP 9] Computing match & player stats")
print("="*80)
match_stats, player_stats = step9.compute_all(events_df, tracking_dataset)
print(f"[OK] Computed {len(match_stats)} stat categories, {len(player_stats)} player stats\n")

# ============================================================================
# STEP 8: Export to JSON (including stats + shot xG)
# ============================================================================
print("="*80)
print("[STEP 8] Exporting to JSON")
print("="*80)
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
    target_fps=4,
    match_duration=match_duration,
    events_df=events_df,
    period_2_offset_secs=p2_offset_secs,
    match_stats=match_stats,
    player_stats=player_stats,
)

# ============================================================================
# FINAL SUMMARY
# ============================================================================
print("\n" + "="*80)
print("PIPELINE COMPLETED SUCCESSFULLY")
print("="*80)

print(f"\nMatch ID: {match_id}")
print(f"Sample Rate: {sample_rate} (1 Hz for testing)")

print(f"\nPipeline Outputs:")
print(f"  Events: {len(events_df)}")
print(f"  Tracking frames: {len(tracking_df)}")
print(f"  Feature rows: {features_df.shape[0]}")
print(f"  Phase segments: {len(phases_df_with_xthreat)}")
print(f"  Voronoi frames: {len(voronoi_data)}")
print(f"  Formations: {len(formations)}")
print(f"  Pressing heatmaps: {len(heatmaps)}")
print(f"  Match stat categories: {len(match_stats)}")
print(f"  Player stats: {len(player_stats)}")

print(f"\nExported JSON files:")
for key, path in exported_files.items():
    file_size = Path(path).stat().st_size / 1024  # KB
    print(f"  {key}: {file_size:.1f} KB")

import os
output_path = os.path.dirname(list(exported_files.values())[0]) if exported_files else f"../frontend/public/data/{match_id}"
print(f"\nOutput directory: {output_path}/")

print("\n" + "="*80)
print("[SUCCESS] All 9 pipeline steps completed!")
print("="*80)
