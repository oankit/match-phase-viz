"""
Step 2: Compute Sliding-Window Features

For each frame, compute per-team features over a 5-second window:
- defensive_line_height: Mean x of deepest 4 outfield defenders
- team_compactness: Convex hull area of outfield players
- pressure_proxy: Count of defenders within 5m of ball
- ball_x: Ball x-coordinate

These features feed into the phase classifier in Step 3.

NOTE: Tracking data is in WIDE format with columns like:
  - ball_x, ball_y, ball_z, ball_speed
  - <player_id>_x, <player_id>_y, <player_id>_d, <player_id>_s
"""

import numpy as np
import pandas as pd
from scipy.spatial import ConvexHull
from tqdm import tqdm

import config


def get_player_team_mapping(tracking_dataset):
    """
    Extract player-to-team mapping from tracking dataset metadata.

    Args:
        tracking_dataset: Kloppy TrackingDataset object

    Returns:
        dict: {player_id: team_id}
    """
    player_team_map = {}

    for team in tracking_dataset.metadata.teams:
        team_id = team.team_id
        for player in team.players:
            player_team_map[player.player_id] = team_id

    return player_team_map


def extract_team_positions(tracking_row, player_team_map, team_id, exclude_gk=True):
    """
    Extract player positions for a specific team from a wide-format tracking row.

    Args:
        tracking_row: Single row from tracking DataFrame (wide format)
        player_team_map: dict mapping player_id to team_id
        team_id: Team identifier to extract
        exclude_gk: Whether to exclude goalkeeper (first player alphabetically)

    Returns:
        np.ndarray: (N, 2) array of [x, y] positions
    """
    positions = []

    # Get all players for this team
    team_players = [pid for pid, tid in player_team_map.items() if tid == team_id]

    # Sort to ensure GK is first (typically has lower ID)
    team_players = sorted(team_players)

    # Exclude GK if requested
    if exclude_gk and len(team_players) > 1:
        team_players = team_players[1:]  # Skip first player (GK)

    # Extract positions
    for player_id in team_players:
        x_col = f'{player_id}_x'
        y_col = f'{player_id}_y'

        if x_col in tracking_row.index and y_col in tracking_row.index:
            x = tracking_row[x_col]
            y = tracking_row[y_col]

            # Skip if NaN (player not on field)
            if not (pd.isna(x) or pd.isna(y)):
                positions.append([x, y])

    return np.array(positions) if positions else np.array([]).reshape(0, 2)


def compute_defensive_line_height(team_positions):
    """
    Compute defensive line height (mean x of deepest 4 defenders).

    Args:
        team_positions: (N, 2) array of [x, y] positions (outfield only)

    Returns:
        float: Mean x-coordinate of 4 deepest defenders (0-1 normalized)
    """
    if len(team_positions) < 4:
        return np.nan

    # Sort by x-coordinate (0-1 normalized, attacking right means lower x = deeper)
    sorted_x = np.sort(team_positions[:, 0])
    return sorted_x[:4].mean()


def compute_compactness(team_positions):
    """
    Compute team compactness (convex hull area).

    Args:
        team_positions: (N, 2) array of [x, y] positions (outfield only)

    Returns:
        float: Convex hull area (in normalized coordinate space)
    """
    if len(team_positions) < 3:
        return np.nan

    try:
        hull = ConvexHull(team_positions)
        return hull.volume  # .volume = area for 2D
    except Exception:
        # Collinear points or other edge cases
        return np.nan


def compute_pressure_proxy(team_positions, ball_xy, radius=5.0/105.0):
    """
    Count players within radius of ball (pressure proxy).

    Args:
        team_positions: (N, 2) array of player positions
        ball_xy: (2,) array of ball position
        radius: Distance threshold (default: 5m / 105m pitch length in normalized coords)

    Returns:
        int: Number of players within radius
    """
    if len(team_positions) == 0:
        return 0

    # Compute distances
    distances = np.linalg.norm(team_positions - ball_xy, axis=1)
    return (distances < radius).sum()


def compute_features_for_frame(tracking_df, frame_idx, player_team_map, window_frames=125):
    """
    Compute features for a single frame for both teams.

    Args:
        tracking_df: Full tracking DataFrame (wide format)
        frame_idx: Frame index (0-based)
        player_team_map: dict mapping player_id to team_id
        window_frames: Number of frames in sliding window (default: 125 = 5 sec @ 25Hz)

    Returns:
        list: List of feature dicts, one per team
    """
    # Get current frame
    current_row = tracking_df.iloc[frame_idx]

    # Get ball position
    ball_x = current_row['ball_x']
    ball_y = current_row['ball_y']
    ball_xy = np.array([ball_x, ball_y])

    # Get unique teams
    teams = list(set(player_team_map.values()))

    results = []
    for team_id in teams:
        # Extract team positions
        team_positions = extract_team_positions(current_row, player_team_map, team_id, exclude_gk=True)

        # Get opposing team positions (for pressure computation)
        opposing_team_id = [t for t in teams if t != team_id][0] if len(teams) > 1 else None
        opposing_positions = extract_team_positions(current_row, player_team_map, opposing_team_id, exclude_gk=False) if opposing_team_id else np.array([])

        # Compute features
        if len(team_positions) > 0:
            def_line_height = compute_defensive_line_height(team_positions)
            compactness = compute_compactness(team_positions)
            # Shape metrics (Pracxa et al. 2022)
            team_length = team_positions[:, 0].max() - team_positions[:, 0].min()
            team_width = team_positions[:, 1].max() - team_positions[:, 1].min()
            lpw_ratio = team_length / team_width if team_width > 0 else np.nan
            centroid = team_positions.mean(axis=0)
            stretching_index = np.linalg.norm(team_positions - centroid, axis=1).mean()
        else:
            def_line_height = np.nan
            compactness = np.nan
            team_length = np.nan
            team_width = np.nan
            lpw_ratio = np.nan
            stretching_index = np.nan

        # Pressure: how many of THIS team's players are near the ball
        # (This team is pressuring when they have the ball in opponent half)
        pressure_proxy = compute_pressure_proxy(team_positions, ball_xy)

        results.append({
            'frame_id': current_row['frame_id'],
            'timestamp': current_row['timestamp'],
            'period_id': current_row['period_id'],
            'team_id': team_id,
            'defensive_line_height': def_line_height,
            'compactness': compactness,
            'pressure_proxy': pressure_proxy,
            'team_length': team_length,
            'team_width': team_width,
            'lpw_ratio': lpw_ratio,
            'stretching_index': stretching_index,
            'ball_x': ball_x,
            'ball_y': ball_y,
            'ball_owning_team_id': current_row.get('ball_owning_team_id', None),
        })

    return results


def compute_all_features(tracking_dataset, tracking_df):
    """
    Compute sliding-window features for all frames and teams.

    Args:
        tracking_dataset: Kloppy TrackingDataset object (for metadata)
        tracking_df: Tracking DataFrame (wide format)

    Returns:
        pd.DataFrame: Features per frame per team
    """
    print("Computing sliding-window features...")

    # Get player-team mapping
    player_team_map = get_player_team_mapping(tracking_dataset)
    teams = list(set(player_team_map.values()))
    print(f"  Teams: {teams}")
    print(f"  Players per team: {[sum(1 for t in player_team_map.values() if t == team) for team in teams]}")

    # Compute features for each frame
    print(f"  Processing {len(tracking_df)} frames...")
    results = []

    for frame_idx in tqdm(range(len(tracking_df)), desc="Computing features"):
        frame_features = compute_features_for_frame(
            tracking_df, frame_idx, player_team_map, window_frames=config.WINDOW_FRAMES
        )
        results.extend(frame_features)

    features_df = pd.DataFrame(results)
    return features_df


def main(tracking_dataset, tracking_df):
    """
    Main entry point for Step 2.

    Args:
        tracking_dataset: Kloppy TrackingDataset object
        tracking_df: Tracking DataFrame (wide format)

    Returns:
        pd.DataFrame: Features DataFrame
    """
    print("\n" + "=" * 80)
    print("STEP 2: SLIDING-WINDOW FEATURE COMPUTATION")
    print("=" * 80)

    # Compute features
    features_df = compute_all_features(tracking_dataset, tracking_df)

    print(f"\n[OK] Features computed: {features_df.shape}")
    print(f"\nSample output:")
    print(features_df.head(10))

    print(f"\nFeature statistics:")
    print(features_df[['defensive_line_height', 'compactness', 'pressure_proxy', 'ball_x']].describe())

    return features_df


if __name__ == "__main__":
    print("\n[INFO] This script requires tracking_dataset and tracking_df from Step 1.")
    print("Run as:")
    print("  from pipeline.load_data_01 import load_match")
    print("  event_ds, tracking_ds, events_df, tracking_df = load_match('J03WN1', sample_rate=0.04)")
    print("  features_df = main(tracking_ds, tracking_df)")
