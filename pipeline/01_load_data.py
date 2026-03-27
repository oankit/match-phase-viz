"""
Load match data (events + tracking) from local files.
This is the corrected Step 1 for the pipeline.
"""
from kloppy import sportec
from pathlib import Path
import pandas as pd
import numpy as np

def load_match(match_id="J03WN1", sample_rate=1.0, data_dir="../data"):
    """
    Load event and tracking data for a match from local files.

    Args:
        match_id: Match identifier (e.g., 'J03WN1')
        sample_rate: Fraction of tracking frames to load (1.0 = all, 0.04 = 1Hz from 25Hz)
        data_dir: Directory containing the XML files

    Returns:
        tuple: (event_dataset, tracking_dataset, events_df, tracking_df)
    """
    data_path = Path(data_dir)

    # Find files for this match
    meta_file = list(data_path.glob(f"*matchinformation*{match_id}.xml"))[0]
    event_file = list(data_path.glob(f"*events_raw*{match_id}.xml"))[0]
    tracking_file = list(data_path.glob(f"*positions_raw*{match_id}.xml"))[0]

    print(f"Loading match: {match_id}")
    print("="*60)
    print(f"Meta:     {meta_file.name}")
    print(f"Events:   {event_file.name}")
    print(f"Tracking: {tracking_file.name} ({tracking_file.stat().st_size / 1024**2:.1f} MB)")

    # Load event data
    print("\n[1] Loading event data...")
    event_dataset = sportec.load_event(
        event_data=str(event_file),
        meta_data=str(meta_file),
        coordinates="kloppy"  # Normalized 0-1 coordinates
    )
    events_df = event_dataset.to_df()
    print(f"    Loaded {len(events_df)} events")

    # Load tracking data
    print("\n[2] Loading tracking data...")
    print(f"    Sample rate: {sample_rate} (this may take a minute...)")
    tracking_dataset = sportec.load_tracking(
        raw_data=str(tracking_file),
        meta_data=str(meta_file),
        coordinates="kloppy",
        only_alive=True,  # Skip dead ball periods
        sample_rate=sample_rate
    )

    print(f"    Loaded {len(tracking_dataset.records)} frames")
    print(f"    Frame rate: {tracking_dataset.metadata.frame_rate} Hz")

    # Convert small sample to DataFrame to check schema
    print("\n[3] Converting sample to DataFrame...")
    sample_frames = min(100, len(tracking_dataset.records))
    tracking_sample = tracking_dataset.slice(end_frame_id=sample_frames) if hasattr(tracking_dataset, 'slice') else tracking_dataset
    tracking_df = tracking_sample.to_df()

    print(f"    Sample shape: {tracking_df.shape}")
    print(f"    Columns (first 10): {tracking_df.columns.tolist()[:10]}")

    return event_dataset, tracking_dataset, events_df, tracking_df


def verify_schema(events_df, tracking_df):
    """Verify the data schema matches our pipeline expectations."""
    print("\n" + "="*60)
    print("SCHEMA VERIFICATION")
    print("="*60)

    # Event schema
    print("\n[EVENT DATA]")
    print(f"  Shape: {events_df.shape}")
    print(f"  Columns: {events_df.columns.tolist()}")

    required_event_cols = ['event_type', 'timestamp', 'team_id', 'player_id',
                          'coordinates_x', 'coordinates_y']
    missing = [col for col in required_event_cols if col not in events_df.columns]
    if missing:
        print(f"  WARNING: Missing columns: {missing}")
    else:
        print(f"  [OK] All required columns present")

    # Tracking schema
    print("\n[TRACKING DATA]")
    print(f"  Shape: {tracking_df.shape}")
    print(f"  Columns (first 15): {tracking_df.columns.tolist()[:15]}")

    required_tracking_cols = ['period_id', 'timestamp', 'frame_id', 'ball_x', 'ball_y']
    missing = [col for col in required_tracking_cols if col not in tracking_df.columns]
    if missing:
        print(f"  WARNING: Missing columns: {missing}")
    else:
        print(f"  [OK] All required columns present")

    # Check player columns
    player_x_cols = [col for col in tracking_df.columns if col.endswith('_x') and col != 'ball_x']
    print(f"  [OK] Found {len(player_x_cols)} player position columns")

    # Show sample data
    print("\n[SAMPLE DATA]")
    print("\nEvents (first 3):")
    print(events_df[['event_type', 'timestamp', 'team_id', 'coordinates_x', 'coordinates_y']].head(3).to_string())

    print("\nTracking (first row, selected columns):")
    cols_to_show = ['period_id', 'timestamp', 'frame_id', 'ball_x', 'ball_y']
    print(tracking_df[cols_to_show].head(1).to_string())


if __name__ == "__main__":
    # Test with J03WN1 at 1 Hz (downsample from 25 Hz)
    event_dataset, tracking_dataset, events_df, tracking_df = load_match(
        match_id="J03WN1",
        sample_rate=0.04  # 1 Hz = 25 Hz * 0.04
    )

    # Verify schema
    verify_schema(events_df, tracking_df)

    print("\n" + "="*60)
    print("SUCCESS! Data loaded and verified.")
    print("="*60)
    print("\nNext steps:")
    print("1. Update Step 1 (01_load_data.py) with this code")
    print("2. Verify Step 2 column names match actual schema")
    print("3. Run full pipeline on all 7 matches")