"""
Step 6: Pressing Intensity Heatmap

For each high_press phase segment:
1. Collect defensive action locations (tackles, interceptions, pressures, recoveries)
2. Apply 2D KDE (Kernel Density Estimation)
3. Rasterize to 21x14 grid (5m resolution)
4. Normalize to 0-1

Output: Heatmap per high_press phase showing where pressing actions occurred.
"""

import numpy as np
import pandas as pd
from scipy.stats import gaussian_kde
from tqdm import tqdm

import config


def get_defensive_action_locations(events_df, phase_row):
    """
    Get locations of defensive actions during a phase.

    Args:
        events_df: Events DataFrame from Step 1
        phase_row: Single row from phases_df

    Returns:
        np.ndarray: (N, 2) array of [x, y] locations, or None if no actions
    """
    # Defensive action types
    defensive_actions = ['RECOVERY', 'TACKLE', 'INTERCEPTION', 'PRESSURE']

    # Filter events for this team during this phase
    phase_events = events_df[
        (events_df['timestamp'] >= phase_row['start_time']) &
        (events_df['timestamp'] <= phase_row['end_time']) &
        (events_df['team_id'] == phase_row['team_id'])
    ].copy()

    # Filter for defensive actions
    # Check if event_type contains any of the defensive action keywords
    defensive_mask = phase_events['event_type'].str.contains(
        '|'.join(defensive_actions), case=False, na=False
    )
    defensive_events = phase_events[defensive_mask]

    if len(defensive_events) == 0:
        return None

    # Extract locations
    locations = []
    for idx, event in defensive_events.iterrows():
        x = event.get('coordinates_x', np.nan)
        y = event.get('coordinates_y', np.nan)

        if not (pd.isna(x) or pd.isna(y)):
            locations.append([x, y])

    if len(locations) == 0:
        return None

    return np.array(locations)


def compute_kde_heatmap(locations, grid_size=(21, 14)):
    """
    Compute 2D KDE heatmap from action locations.

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
        # Fit KDE
        kde = gaussian_kde(locations.T, bw_method='scott')

        # Evaluate on grid
        density = kde.evaluate(grid_points)
        density = density.reshape(grid_h, grid_w)

        # Normalize to 0-1
        if density.max() > 0:
            density = density / density.max()

        return density

    except Exception as e:
        # KDE failed (e.g., singular matrix), return zero heatmap
        print(f"    Warning: KDE failed - {e}")
        return np.zeros((grid_size[1], grid_size[0]))


def compute_pressing_heatmaps(events_df, phases_df):
    """
    Compute pressing heatmaps for all high_press phases.

    Args:
        events_df: Events DataFrame from Step 1
        phases_df: Phase segments DataFrame from Step 3

    Returns:
        List[dict]: Heatmap data per high_press phase
    """
    print("Computing pressing intensity heatmaps...")

    # Filter for high_press phases
    highpress_phases = phases_df[phases_df['phase_type'] == 'high_press'].copy()
    print(f"  Found {len(highpress_phases)} high_press phases")

    if len(highpress_phases) == 0:
        print("  No high_press phases found, skipping heatmap computation")
        return []

    heatmaps = []

    for idx, phase_row in tqdm(highpress_phases.iterrows(), total=len(highpress_phases), desc="  Computing heatmaps"):
        # Get defensive action locations
        locations = get_defensive_action_locations(events_df, phase_row)

        # Compute KDE heatmap
        heatmap = compute_kde_heatmap(locations, grid_size=config.HEATMAP_GRID_SIZE)

        heatmaps.append({
            'phase_id': int(phase_row['phase_id']),
            'team_id': phase_row['team_id'],
            'heatmap': heatmap.tolist(),  # (14, 21) grid
            'num_actions': len(locations) if locations is not None else 0,
        })

    print(f"  Computed {len(heatmaps)} pressing heatmaps")

    return heatmaps


def main(events_df, phases_df):
    """
    Main entry point for Step 6.

    Args:
        events_df: Events DataFrame from Step 1
        phases_df: Phase segments DataFrame from Step 3

    Returns:
        List[dict]: Pressing heatmap data
    """
    print("\n" + "=" * 80)
    print("STEP 6: PRESSING INTENSITY HEATMAPS")
    print("=" * 80)

    # Compute heatmaps
    heatmaps = compute_pressing_heatmaps(events_df, phases_df)

    print("\n[OK] Pressing heatmap computation complete")

    # Show sample
    if len(heatmaps) > 0:
        sample = heatmaps[0]
        print(f"\nSample heatmap (phase {sample['phase_id']}):")
        print(f"  Team: {sample['team_id']}")
        print(f"  Grid shape: {np.array(sample['heatmap']).shape}")
        print(f"  Num actions: {sample['num_actions']}")
        print(f"  Max intensity: {np.array(sample['heatmap']).max():.3f}")

    return heatmaps


if __name__ == "__main__":
    print("\n[INFO] This script requires events_df and phases_df.")
    print("Run as part of the pipeline.")
