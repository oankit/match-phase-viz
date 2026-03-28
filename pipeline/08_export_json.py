"""
Step 8: Downsample and Export to JSON

Packages all pipeline outputs into JSON files for the frontend:
- Downsample tracking data (25 Hz -> 4 Hz)
- Export frames, phases, formations, voronoi, heatmaps
- Split into multiple files if too large (> 5 MB)

Output: JSON files in ../output/<match_id>/
"""

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

import config


def downsample_tracking(tracking_df, target_fps=4):
    """
    Downsample tracking data to target frame rate.

    Args:
        tracking_df: Full tracking DataFrame
        target_fps: Target frames per second

    Returns:
        pd.DataFrame: Downsampled tracking DataFrame
    """
    source_fps = config.TRACKING_FPS
    downsample_factor = source_fps // target_fps

    print(f"  Downsampling {source_fps}Hz -> {target_fps}Hz (every {downsample_factor} frames)")

    # Take every Nth frame
    downsampled = tracking_df.iloc[::downsample_factor].copy()

    print(f"  Downsampled: {len(tracking_df)} -> {len(downsampled)} frames")

    return downsampled


def export_frames(tracking_df, player_team_map, output_dir):
    """
    Export tracking frames to JSON.

    Args:
        tracking_df: Tracking DataFrame
        player_team_map: dict mapping player_id to team_id
        output_dir: Output directory path

    Returns:
        str: Path to exported frames.json
    """
    print("\nExporting frames...")

    frames = []

    for idx in tqdm(range(len(tracking_df)), desc="  Processing frames"):
        row = tracking_df.iloc[idx]

        # Extract timestamp (convert to seconds)
        timestamp = row['timestamp'].total_seconds()

        # Extract ball position
        ball = {
            'x': float(row['ball_x']) if not pd.isna(row['ball_x']) else None,
            'y': float(row['ball_y']) if not pd.isna(row['ball_y']) else None,
        }

        # Extract player positions
        players = []
        for player_id, team_id in player_team_map.items():
            x_col = f'{player_id}_x'
            y_col = f'{player_id}_y'
            d_col = f'{player_id}_d'  # direction (optional)
            s_col = f'{player_id}_s'  # speed (optional)

            if x_col in row.index and y_col in row.index:
                x = row[x_col]
                y = row[y_col]

                if not (pd.isna(x) or pd.isna(y)):
                    player_data = {
                        'id': player_id,
                        'team': team_id,
                        'x': float(x),
                        'y': float(y),
                    }

                    # Add optional fields if available
                    if d_col in row.index and not pd.isna(row[d_col]):
                        player_data['direction'] = float(row[d_col])
                    if s_col in row.index and not pd.isna(row[s_col]):
                        player_data['speed'] = float(row[s_col])

                    players.append(player_data)

        frames.append({
            't': timestamp,
            'frame_id': int(row['frame_id']),
            'period_id': int(row['period_id']),
            'players': players,
            'ball': ball,
        })

    # Write to JSON
    frames_path = output_dir / 'frames.json'
    with open(frames_path, 'w') as f:
        json.dump(frames, f, indent=2)

    print(f"  Exported {len(frames)} frames to {frames_path}")

    return str(frames_path)


def export_phases(phases_df, output_dir):
    """
    Export phase segments to JSON.

    Args:
        phases_df: Phase segments DataFrame (with xThreat)
        output_dir: Output directory path

    Returns:
        str: Path to exported phases.json
    """
    print("\nExporting phases...")

    phases = []

    for idx, row in phases_df.iterrows():
        phases.append({
            'id': int(row['phase_id']),
            'type': row['phase_type'],
            'team': row['team_id'],
            'start': row['start_time'].total_seconds(),
            'end': row['end_time'].total_seconds(),
            'duration': float(row['duration']),
            'defensive_line_height': float(row.get('defensive_line_height', 0.0)),
            'compactness': float(row.get('compactness', 0.0)),
            'ppda_proxy': float(row.get('ppda_proxy', 0.0)),
            'xthreat_gained': float(row.get('xthreat_gained', 0.0)),
            'xthreat_conceded': float(row.get('xthreat_conceded', 0.0)),
        })

    # Write to JSON
    phases_path = output_dir / 'phases.json'
    with open(phases_path, 'w') as f:
        json.dump(phases, f, indent=2)

    print(f"  Exported {len(phases)} phases to {phases_path}")

    return str(phases_path)


def export_formations(formations, output_dir):
    """
    Export formation graphs to JSON.

    Args:
        formations: List of formation dicts from Step 5
        output_dir: Output directory path

    Returns:
        str: Path to exported formations.json
    """
    print("\nExporting formations...")

    # Formations are already in JSON-serializable format
    formations_path = output_dir / 'formations.json'
    with open(formations_path, 'w') as f:
        json.dump(formations, f, indent=2)

    print(f"  Exported {len(formations)} formations to {formations_path}")

    return str(formations_path)


def export_voronoi(voronoi_data, output_dir):
    """
    Export Voronoi diagrams to JSON.

    Args:
        voronoi_data: List of Voronoi dicts from Step 4
        output_dir: Output directory path

    Returns:
        str: Path to exported voronoi.json
    """
    print("\nExporting Voronoi...")

    # Convert numpy types to native Python types for JSON serialization
    def convert_numpy_types(obj):
        # Handle None first
        if obj is None:
            return None
        # Handle pandas NA values
        try:
            if pd.isna(obj):
                return None
        except (TypeError, ValueError):
            pass
        # Handle dicts
        if isinstance(obj, dict):
            return {key: convert_numpy_types(value) for key, value in obj.items()}
        # Handle lists
        elif isinstance(obj, list):
            return [convert_numpy_types(item) for item in obj]
        # Handle numpy arrays
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        # Handle pandas Timedelta
        elif isinstance(obj, pd.Timedelta):
            return obj.total_seconds()
        # Handle numpy integer types (using np.integer base class)
        elif np.issubdtype(type(obj), np.integer):
            return int(obj)
        # Handle numpy float types (using np.floating base class)
        elif np.issubdtype(type(obj), np.floating):
            return float(obj)
        # Handle numpy bool
        elif isinstance(obj, np.bool_):
            return bool(obj)
        # Return as-is for native Python types
        else:
            return obj

    # Convert voronoi_data
    voronoi_data_converted = convert_numpy_types(voronoi_data)

    voronoi_path = output_dir / 'pitch_control.json'
    with open(voronoi_path, 'w') as f:
        json.dump(voronoi_data_converted, f, separators=(',', ':'))

    print(f"  Exported {len(voronoi_data)} Voronoi frames to {voronoi_path}")

    return str(voronoi_path)


def export_heatmaps(heatmaps, output_dir):
    """
    Export pressing heatmaps to JSON.

    Args:
        heatmaps: List of heatmap dicts from Step 6
        output_dir: Output directory path

    Returns:
        str: Path to exported heatmaps.json
    """
    print("\nExporting heatmaps...")

    # Heatmaps are already in JSON-serializable format
    heatmaps_path = output_dir / 'heatmaps.json'
    with open(heatmaps_path, 'w') as f:
        json.dump(heatmaps, f, indent=2)

    print(f"  Exported {len(heatmaps)} heatmaps to {heatmaps_path}")

    return str(heatmaps_path)


def export_metadata(tracking_dataset, match_id, output_dir):
    """
    Export match metadata to JSON.

    Args:
        tracking_dataset: Kloppy TrackingDataset object
        match_id: Match ID string
        output_dir: Output directory path

    Returns:
        str: Path to exported metadata.json
    """
    print("\nExporting metadata...")

    teams = tracking_dataset.metadata.teams

    metadata = {
        'match_id': match_id,
        'teams': [
            {
                'id': team.team_id,
                'name': team.name if team.name else team.team_id,
                'players': [
                    {
                        'id': player.player_id,
                        'name': player.name if player.name else player.player_id,
                    }
                    for player in team.players
                ]
            }
            for team in teams
        ],
        'pitch': {
            'length': config.PITCH_LENGTH,
            'width': config.PITCH_WIDTH,
        },
    }

    metadata_path = output_dir / 'metadata.json'
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"  Exported metadata to {metadata_path}")

    return str(metadata_path)


def main(match_id, tracking_dataset, tracking_df, phases_df, formations, voronoi_data, heatmaps,
         target_fps=None, output_base_dir=None):
    """
    Main entry point for Step 8.

    Args:
        match_id: Match ID string
        tracking_dataset: Kloppy TrackingDataset object
        tracking_df: Tracking DataFrame
        phases_df: Phase segments DataFrame (with xThreat)
        formations: List of formation dicts from Step 5
        voronoi_data: List of Voronoi dicts from Step 4
        heatmaps: List of heatmap dicts from Step 6
        target_fps: Target frame rate for downsampling (if None, uses config.EXPORT_TARGET_FPS)
        output_base_dir: Base output directory

    Returns:
        dict: Paths to exported files
    """
    print("\n" + "=" * 80)
    print("STEP 8: EXPORT TO JSON")
    print("=" * 80)

    # Use config output directory if not specified
    if output_base_dir is None:
        # Try frontend directory first
        frontend_dir = Path(config.OUTPUT_DIR)
        if frontend_dir.exists():
            output_base_dir = config.OUTPUT_DIR
            print(f"Using frontend output directory: {output_base_dir}")
        else:
            # Fall back to backup directory
            output_base_dir = config.BACKUP_OUTPUT_DIR
            print(f"Frontend directory not found, using backup: {output_base_dir}")

    # Create output directory
    output_dir = Path(output_base_dir) / match_id
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_dir}")

    # Get player-team mapping
    player_team_map = {}
    for team in tracking_dataset.metadata.teams:
        for player in team.players:
            player_team_map[player.player_id] = team.team_id

    # Downsample tracking data and voronoi
    # Use config values for proper downsampling
    # Note: tracking_df is already at LOADED_FPS from Step 1
    loaded_fps = config.LOADED_FPS  # Actual FPS after Step 1 sampling

    # Use provided target_fps or fall back to config
    if target_fps is None:
        target_fps = config.EXPORT_TARGET_FPS  # Target FPS from config

    # Calculate downsample factor from loaded data to target
    downsample_factor = max(1, loaded_fps // target_fps)

    print(f"  Downsampling {loaded_fps}Hz -> {target_fps}Hz (every {downsample_factor} frames)")

    tracking_df_downsampled = downsample_tracking(tracking_df, target_fps)
    voronoi_downsampled = voronoi_data[::downsample_factor] if voronoi_data else []

    # Export all components
    exported_files = {
        'metadata': export_metadata(tracking_dataset, match_id, output_dir),
        'frames': export_frames(tracking_df_downsampled, player_team_map, output_dir),
        'phases': export_phases(phases_df, output_dir),
        'formations': export_formations(formations, output_dir),
        'voronoi': export_voronoi(voronoi_downsampled, output_dir),
        'heatmaps': export_heatmaps(heatmaps, output_dir),
    }

    print("\n[OK] Export complete")
    print(f"\nExported files:")
    for key, path in exported_files.items():
        file_size = Path(path).stat().st_size / 1024  # KB
        print(f"  {key}: {path} ({file_size:.1f} KB)")

    return exported_files


if __name__ == "__main__":
    print("\n[INFO] This script exports all pipeline outputs to JSON.")
    print("Run as part of the pipeline.")
