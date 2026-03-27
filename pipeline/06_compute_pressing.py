"""
Step 6: Compute Pressing Intensity Heatmap (FIXED)
Using tracking data to find where defenders are close to the ball during high press phases.
"""

import numpy as np
import pandas as pd
from scipy.stats import gaussian_kde
from pathlib import Path
import json

def get_pressing_locations_from_tracking(features_df, tracking_df, phase_row):
    """
    Get locations where defenders are pressing (close to ball) during a phase.

    Args:
        features_df: Features DataFrame with ball positions and timestamps
        tracking_df: Tracking DataFrame with player positions
        phase_row: Single row from phases_df

    Returns:
        np.ndarray: (N, 2) array of [x, y] pressing locations
    """
    # Filter features for this phase and team
    phase_features = features_df[
        (features_df['timestamp'] >= phase_row['start_time']) &
        (features_df['timestamp'] <= phase_row['end_time']) &
        (features_df['team_id'] == phase_row['team_id'])
    ]

    if len(phase_features) == 0:
        return None

    pressing_locations = []

    # For each frame in the phase
    for idx, row in phase_features.iterrows():
        frame_id = row['frame_id']
        ball_x = row['ball_x']
        ball_y = row['ball_y']

        # Skip if ball position invalid
        if pd.isna(ball_x) or pd.isna(ball_y):
            continue

        # Get tracking data for this frame
        frame_tracking = tracking_df[tracking_df['frame_id'] == frame_id]

        if len(frame_tracking) == 0:
            continue

        frame_row = frame_tracking.iloc[0]

        # Find defenders close to the ball (within 5m normalized = 0.048)
        pressing_radius = 0.048  # ~5 meters in normalized coords

        # Check all player columns
        for col in frame_row.index:
            if col.endswith('_x'):
                player_id = col[:-2]
                x_col = f'{player_id}_x'
                y_col = f'{player_id}_y'

                if x_col in frame_row.index and y_col in frame_row.index:
                    player_x = frame_row[x_col]
                    player_y = frame_row[y_col]

                    # Skip if no position
                    if pd.isna(player_x) or pd.isna(player_y):
                        continue

                    # Calculate distance to ball
                    dist = np.sqrt((player_x - ball_x)**2 + (player_y - ball_y)**2)

                    # If close enough, add as pressing location
                    if dist < pressing_radius:
                        pressing_locations.append([player_x, player_y])

    if len(pressing_locations) == 0:
        return None

    return np.array(pressing_locations)


def compute_kde_heatmap(locations, grid_size=(21, 14)):
    """
    Compute 2D KDE heatmap from pressing locations.

    Args:
        locations: (N, 2) array of [x, y] locations (normalized 0-1)
        grid_size: (width, height) grid dimensions

    Returns:
        np.ndarray: (height, width) heatmap normalized to 0-1
    """
    if locations is None or len(locations) < 2:
        # Not enough data for KDE, return zero heatmap
        return np.zeros((grid_size[1], grid_size[0]))

    # Create grid
    grid_w, grid_h = grid_size
    x_grid = np.linspace(0, 1, grid_w)
    y_grid = np.linspace(0, 1, grid_h)
    xx, yy = np.meshgrid(x_grid, y_grid)
    grid_points = np.vstack([xx.ravel(), yy.ravel()])

    try:
        # Fit KDE with smaller bandwidth for more detail
        kde = gaussian_kde(locations.T, bw_method=0.15)

        # Evaluate on grid
        density = kde.evaluate(grid_points)
        density = density.reshape(grid_h, grid_w)

        # Normalize to 0-1
        if density.max() > 0:
            density = density / density.max()

        return density

    except Exception as e:
        print(f"  KDE computation failed: {e}")
        return np.zeros((grid_size[1], grid_size[0]))


def main(phases_df, features_df, tracking_df):
    """
    Compute pressing intensity heatmaps for high_press phases.

    Args:
        phases_df: Phase segments from Step 3
        features_df: Features from Step 2
        tracking_df: Tracking data from Step 1

    Returns:
        list: Pressing heatmaps
    """
    print("\n" + "=" * 80)
    print("STEP 6: PRESSING INTENSITY HEATMAPS (FIXED)")
    print("=" * 80)

    print("Computing pressing intensity heatmaps using tracking data...")

    # Filter for high_press phases
    high_press_phases = phases_df[phases_df['phase_type'] == 'high_press'].copy()
    print(f"  Found {len(high_press_phases)} high_press phases")

    heatmaps = []

    for idx, phase_row in high_press_phases.iterrows():
        # Get pressing locations from tracking data
        locations = get_pressing_locations_from_tracking(features_df, tracking_df, phase_row)

        # Compute KDE heatmap
        heatmap = compute_kde_heatmap(locations)

        # Store heatmap
        heatmaps.append({
            'phase_id': phase_row['phase_id'],
            'team_id': phase_row['team_id'],
            'heatmap': heatmap.tolist(),
            'num_actions': len(locations) if locations is not None else 0,
        })

    print(f"  Computed {len(heatmaps)} pressing heatmaps")

    # Show sample stats
    if heatmaps:
        total_actions = sum(h['num_actions'] for h in heatmaps)
        avg_actions = total_actions / len(heatmaps) if heatmaps else 0
        print(f"  Average pressing actions per high_press phase: {avg_actions:.1f}")
        print(f"  Total pressing actions: {total_actions}")

    print("\n[OK] Pressing heatmap computation complete")

    return heatmaps


if __name__ == "__main__":
    # Test on sample data
    from pathlib import Path
    import sys
    sys.path.append(str(Path(__file__).parent))

    # Would load phases_df, features_df, and tracking_df here for testing
    print("Run from main pipeline or provide test data")