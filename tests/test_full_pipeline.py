"""
Full Pipeline Integration Test
Tests all 8 steps together: Load → Features → Phases → Voronoi → Formations → Pressing → xThreat → Export
"""
import sys
sys.path.insert(0, '../pipeline')

import importlib
from pathlib import Path

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

print("="*80)
print("FULL PIPELINE INTEGRATION TEST")
print("="*80)
print("\nTesting all 8 steps: Load > Features > Phases > Voronoi > Formations > Pressing > xThreat > Export\n")

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
print(f"[OK] Loaded: {len(events_df)} events, {len(tracking_df)} tracking frames\n")

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
# STEP 8: Export to JSON
# ============================================================================
print("="*80)
print("[STEP 8] Exporting to JSON")
print("="*80)
exported_files = step8.main(
    match_id=match_id,
    tracking_dataset=tracking_dataset,
    tracking_df=tracking_df,
    phases_df=phases_df_with_xthreat,
    formations=formations,
    voronoi_data=voronoi_data,
    heatmaps=heatmaps,
    target_fps=4
    # output_base_dir not specified - will use config.OUTPUT_DIR (frontend) by default
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

print(f"\nExported JSON files:")
for key, path in exported_files.items():
    file_size = Path(path).stat().st_size / 1024  # KB
    print(f"  {key}: {file_size:.1f} KB")

import os
output_path = os.path.dirname(list(exported_files.values())[0]) if exported_files else f"../frontend/public/data/{match_id}"
print(f"\nOutput directory: {output_path}/")

print("\n" + "="*80)
print("[SUCCESS] All 8 pipeline steps completed!")
print("="*80)
