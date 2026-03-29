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
    source_fps = config.LOADED_FPS
    downsample_factor = max(1, source_fps // target_fps)

    print(f"  Downsampling {source_fps}Hz -> {target_fps}Hz (every {downsample_factor} frames)")

    downsampled = tracking_df.iloc[::downsample_factor].copy()

    print(f"  Downsampled: {len(tracking_df)} -> {len(downsampled)} frames")

    return downsampled


def export_frames(tracking_df, player_team_map, output_dir, player_number_map=None):
    """
    Export tracking frames to JSON.

    Args:
        tracking_df: Tracking DataFrame
        player_team_map: dict mapping player_id to team_id
        output_dir: Output directory path
        player_number_map: dict mapping player_id to jersey number

    Returns:
        str: Path to exported frames.json
    """
    if player_number_map is None:
        player_number_map = {}
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
                    if player_id in player_number_map:
                        player_data['number'] = player_number_map[player_id]

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
            'team_length': float(row.get('team_length', 0.0)),
            'team_width': float(row.get('team_width', 0.0)),
            'lpw_ratio': float(row.get('lpw_ratio', 0.0)),
            'stretching_index': float(row.get('stretching_index', 0.0)),
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


BADGE_MAP = {
    'VfL Bochum 1848': '/assets/VfL Bochum 1848.png',
    'Bayer 04 Leverkusen': '/assets/Bayer_04_Leverkusen.png',
    '1. FC Koln': '/assets/FC Koln.png',
    'FC Bayern Munchen': '/assets/Bayern Munich.png',
    'Fortuna Dusseldorf': '/assets/Fortuna Dusseldorf.png',
    '1. FC Nurnberg': '/assets/FC Nurnberg.png',
    'SSV Jahn Regensburg': None,
    'FC St. Pauli': '/assets/FC St. Pauli.png',
    'F.C. Hansa Rostock': '/assets/FC Hansa Rostock.png',
    '1. FC Kaiserslautern': '/assets/FC Kaiserslautern.png',
}


def extract_goals(events_df, tracking_dataset, period_2_offset_secs=None):
    """
    Extract goal events from the events DataFrame.

    Args:
        events_df: Events DataFrame
        tracking_dataset: Kloppy TrackingDataset object
        period_2_offset_secs: Offset in seconds for period 2 timestamps
            (should match the offset applied to tracking data)

    Returns:
        list: Goal dicts with team_id, player_name, minute, match_seconds, period
    """
    if events_df is None or len(events_df) == 0:
        return []

    shots = events_df[
        (events_df['event_type'] == 'SHOT') & (events_df['result'] == 'GOAL')
    ]

    player_name_map = {}
    for team in tracking_dataset.metadata.teams:
        for player in team.players:
            name = player.name if player.name else player.player_id
            player_name_map[player.player_id] = name

    goal_list = []
    for _, g in shots.iterrows():
        ts = g['timestamp']
        period = g['period_id']
        # timestamps are already in continuous match time (period 2 offset applied upstream)
        match_seconds = ts.total_seconds()

        goal_list.append({
            'team_id': g['team_id'],
            'player_id': g['player_id'],
            'player_name': player_name_map.get(g['player_id'], g['player_id']),
            'minute': int(match_seconds // 60),
            'match_seconds': round(match_seconds, 1),
            'period': period,
        })

    return goal_list


def export_metadata(tracking_dataset, match_id, output_dir, events_df=None, match_duration=None,
                    period_2_offset_secs=None):
    """
    Export match metadata to JSON, including goals and badge paths.

    Args:
        tracking_dataset: Kloppy TrackingDataset object
        match_id: Match ID string
        output_dir: Output directory path
        events_df: Events DataFrame (for goal extraction)
        match_duration: Total match duration in seconds (if None, defaults to 90*60)

    Returns:
        str: Path to exported metadata.json
    """
    print("\nExporting metadata...")

    teams = tracking_dataset.metadata.teams

    goals = extract_goals(events_df, tracking_dataset, period_2_offset_secs) if events_df is not None else []
    if goals:
        print(f"  Found {len(goals)} goals")

    if match_duration is None:
        match_duration = 90 * 60

    metadata = {
        'match_id': match_id,
        'duration': match_duration,
        'teams': [
            {
                'id': team.team_id,
                'name': team.name if team.name else team.team_id,
                'badge': BADGE_MAP.get(team.name, None),
                'players': [
                    {
                        'id': player.player_id,
                        'name': player.name if player.name else player.player_id,
                        'number': getattr(player, 'jersey_no', None),
                        'position': str(getattr(player, 'starting_position', None) or getattr(player, 'position', None) or ''),
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
        'goals': goals,
    }

    metadata_path = output_dir / 'metadata.json'
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=True)

    print(f"  Exported metadata to {metadata_path}")

    return str(metadata_path)


def export_match_stats(match_stats, player_stats, output_dir, metadata_path):
    """
    Merge match stats and player stats into the existing metadata.json.

    Args:
        match_stats: dict from 09_compute_match_stats
        player_stats: dict mapping player_id -> stat dict
        output_dir: Output directory path
        metadata_path: Path to the metadata.json file to patch
    """
    print("\nMerging match stats and player stats into metadata...")

    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)

    metadata['match_stats'] = match_stats

    stats_list = []
    for pid, ps in player_stats.items():
        entry = dict(ps)
        for k, v in entry.items():
            if hasattr(v, 'item'):
                entry[k] = v.item()
        stats_list.append(entry)

    metadata['player_stats'] = stats_list

    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=True)

    print(f"  Merged {len(match_stats)} stat categories and {len(stats_list)} player stats into {metadata_path}")


def export_shot_xg(events_df, tracking_dataset, output_dir, period_2_offset_secs=None):
    """
    Export shot-level xG data for the cumulative xG chart.

    Args:
        events_df: Events DataFrame from kloppy
        tracking_dataset: Kloppy TrackingDataset object
        output_dir: Output directory path
        period_2_offset_secs: Offset applied to period 2 timestamps

    Returns:
        str: Path to exported shot_xg.json
    """
    import importlib
    stats_mod = importlib.import_module('09_compute_match_stats')

    print("\nExporting shot xG data...")

    teams = tracking_dataset.metadata.teams
    home_id = teams[0].team_id
    away_id = teams[1].team_id
    team_ids = [home_id, away_id]

    player_name_map = {}
    for team in teams:
        for player in team.players:
            player_name_map[player.player_id] = player.name if player.name else player.player_id

    direction_map = stats_mod._detect_attacking_direction(events_df, team_ids)

    shots = events_df[events_df['event_type'] == 'SHOT'].sort_values('timestamp')

    shot_list = []
    for _, row in shots.iterrows():
        # timestamps are already in continuous match time (period 2 offset applied upstream)
        match_seconds = row['timestamp'].total_seconds()
        minute = match_seconds / 60
        period = row['period_id']

        x = row['coordinates_x']
        y = row['coordinates_y']
        team_id = row['team_id']

        ar = stats_mod._get_attack_right(direction_map, team_id, period)
        xg = stats_mod._positional_xg(x, y, ar)

        is_goal = row.get('result') == 'GOAL'

        shot_entry = {
            'minute': round(minute, 2),
            'match_seconds': round(match_seconds, 1),
            'team_id': team_id,
            'player_id': row['player_id'],
            'player_name': player_name_map.get(row['player_id'], row['player_id']),
            'xg': round(xg, 3),
            'is_goal': bool(is_goal),
            'result': str(row.get('result', '')),
        }

        # Include coordinates for pitch overlay (normalized 0-1)
        if not pd.isna(row.get('coordinates_x', float('nan'))):
            shot_entry['x'] = round(float(row['coordinates_x']), 4)
        if not pd.isna(row.get('coordinates_y', float('nan'))):
            shot_entry['y'] = round(float(row['coordinates_y']), 4)

        shot_list.append(shot_entry)

    # timestamps already in continuous match time
    match_duration_secs = events_df['timestamp'].max().total_seconds()

    output = {
        'home_team_id': home_id,
        'away_team_id': away_id,
        'match_duration_minutes': round(match_duration_secs / 60, 1),
        'shots': shot_list,
    }

    shot_xg_path = output_dir / 'shot_xg.json'
    with open(shot_xg_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=True)

    print(f"  Exported {len(shot_list)} shots to {shot_xg_path}")

    return str(shot_xg_path)


def export_event_xt(events_df, tracking_dataset, output_dir):
    """
    Export per-event xT data for the momentum and cumulative xT charts.

    Args:
        events_df: Events DataFrame with '_xt' column from Step 7
        tracking_dataset: Kloppy TrackingDataset object
        output_dir: Output directory path

    Returns:
        str: Path to exported event_xt.json
    """
    print("\nExporting per-event xT data...")

    if '_xt' not in events_df.columns:
        print("  WARNING: '_xt' column not found in events_df. Skipping xT export.")
        return None

    teams = tracking_dataset.metadata.teams
    home_id = teams[0].team_id
    away_id = teams[1].team_id

    player_name_map = {}
    for team in teams:
        for player in team.players:
            player_name_map[player.player_id] = player.name if player.name else player.player_id

    # Filter to events with non-zero xT (passes, carries, etc.)
    xt_events = events_df[events_df['_xt'].abs() > 0.001].copy()

    event_list = []
    for _, row in xt_events.iterrows():
        match_seconds = row['timestamp'].total_seconds()
        minute = match_seconds / 60

        entry = {
            'minute': round(minute, 2),
            'match_seconds': round(match_seconds, 1),
            'period_id': int(row['period_id']),
            'team_id': row['team_id'],
            'player_id': row['player_id'],
            'player_name': player_name_map.get(row['player_id'], row['player_id']),
            'event_type': str(row.get('event_type', '')),
            'xt': round(float(row['_xt']), 4),
        }

        # Include coordinates for pitch overlay (normalized 0-1)
        for col, key in [('coordinates_x', 'start_x'), ('coordinates_y', 'start_y'),
                         ('end_coordinates_x', 'end_x'), ('end_coordinates_y', 'end_y')]:
            if col in row.index and not pd.isna(row[col]):
                entry[key] = round(float(row[col]), 4)

        event_list.append(entry)

    # Also include all events (including zero-xT) for momentum calculation
    # (momentum uses pass counts, shot counts, etc.)
    all_events_list = []
    for _, row in events_df.iterrows():
        match_seconds = row['timestamp'].total_seconds()
        minute = match_seconds / 60

        all_events_list.append({
            'minute': round(minute, 2),
            'match_seconds': round(match_seconds, 1),
            'team_id': row['team_id'],
            'event_type': str(row.get('event_type', '')),
            'result': str(row.get('result', '')),
            'xt': round(float(row.get('_xt', 0)), 4),
        })

    # Detect attacking direction per team per period for frontend use
    from importlib import import_module as _imp
    _s9 = _imp('09_compute_match_stats')
    _dir_map = _s9._detect_attacking_direction(events_df, [home_id, away_id])
    attacking_direction = {
        f"{tid}_{pid}": bool(ar)
        for (tid, pid), ar in _dir_map.items()
    }

    output = {
        'home_team_id': home_id,
        'away_team_id': away_id,
        'attacking_direction': attacking_direction,
        'xt_events': event_list,
        'all_events': all_events_list,
    }

    event_xt_path = output_dir / 'event_xt.json'
    with open(event_xt_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=True)

    print(f"  Exported {len(event_list)} xT events and {len(all_events_list)} total events to {event_xt_path}")

    return str(event_xt_path)


def main(match_id, tracking_dataset, tracking_df, phases_df, formations, voronoi_data, heatmaps,
         target_fps=None, output_base_dir=None, events_df=None, match_duration=None,
         period_2_offset_secs=None, match_stats=None, player_stats=None):
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
        events_df: Events DataFrame (for goal extraction in metadata)
        match_stats: Match stats dict from Step 9 (optional)
        player_stats: Player stats dict from Step 9 (optional)

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

    # Get player-team and player-number mappings
    player_team_map = {}
    player_number_map = {}
    for team in tracking_dataset.metadata.teams:
        for player in team.players:
            player_team_map[player.player_id] = team.team_id
            jersey = getattr(player, 'jersey_no', None)
            if jersey is not None:
                player_number_map[player.player_id] = int(jersey)

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
    metadata_path = export_metadata(tracking_dataset, match_id, output_dir, events_df=events_df,
                                    match_duration=match_duration, period_2_offset_secs=period_2_offset_secs)
    exported_files = {
        'metadata': metadata_path,
        'frames': export_frames(tracking_df_downsampled, player_team_map, output_dir, player_number_map),
        'phases': export_phases(phases_df, output_dir),
        'formations': export_formations(formations, output_dir),
        'voronoi': export_voronoi(voronoi_downsampled, output_dir),
        'heatmaps': export_heatmaps(heatmaps, output_dir),
    }

    # Merge match stats and player stats into metadata if provided
    if match_stats is not None and player_stats is not None:
        export_match_stats(match_stats, player_stats, output_dir, metadata_path)

    # Export shot xG data if events are available
    if events_df is not None:
        exported_files['shot_xg'] = export_shot_xg(
            events_df, tracking_dataset, output_dir,
            period_2_offset_secs=period_2_offset_secs,
        )

    # Export per-event xT data if available
    if events_df is not None and '_xt' in events_df.columns:
        xt_path = export_event_xt(events_df, tracking_dataset, output_dir)
        if xt_path:
            exported_files['event_xt'] = xt_path

    print("\n[OK] Export complete")
    print(f"\nExported files:")
    for key, path in exported_files.items():
        file_size = Path(path).stat().st_size / 1024  # KB
        print(f"  {key}: {path} ({file_size:.1f} KB)")

    return exported_files


if __name__ == "__main__":
    print("\n[INFO] This script exports all pipeline outputs to JSON.")
    print("Run as part of the pipeline.")
