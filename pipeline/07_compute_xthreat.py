"""
Step 7: xThreat (Expected Threat)

Uses a pre-computed xT value surface (Karun Singh, 12x8 grid) trained on
real match data via a Markov chain possession model. The value at each cell
represents the long-term probability of scoring from that pitch zone.

xT(action) = threat(end_zone) - threat(start_zone)

Source: https://karun.in/blog/expected-threat.html
Grid:   pipeline/xt_grid_12x8.json (8 rows x 12 cols)
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from tqdm import tqdm

import config


def load_threat_surface():
    """
    Load the pre-computed xT grid (Karun Singh, 12x8).

    The grid is oriented with row 0 = top of pitch (y=0),
    columns left-to-right = own goal to opponent goal.

    Returns:
        np.ndarray: (8, 12) threat values
    """
    grid_path = Path(__file__).parent / 'xt_grid_12x8.json'
    with open(grid_path) as f:
        grid = json.load(f)
    return np.array(grid)


def get_zone(x, y, grid_size=(12, 8)):
    """
    Get grid zone indices for a position.

    Args:
        x: X-coordinate (normalized 0-1)
        y: Y-coordinate (normalized 0-1)
        grid_size: (width, height) grid dimensions

    Returns:
        Tuple[int, int]: (col, row) zone indices, or (None, None) if out of bounds
    """
    if pd.isna(x) or pd.isna(y):
        return None, None

    grid_w, grid_h = grid_size

    # Clip to valid range
    x = np.clip(x, 0, 1)
    y = np.clip(y, 0, 1)

    # Convert to zone indices
    col = int(x * grid_w)
    row = int(y * grid_h)

    # Ensure within bounds
    col = min(col, grid_w - 1)
    row = min(row, grid_h - 1)

    return col, row


def compute_xthreat_for_event(event, threat_surface):
    """
    Compute xThreat for a single event.

    xThreat = threat(end_zone) - threat(start_zone)

    Args:
        event: Event row from events_df
        threat_surface: (8, 12) threat surface

    Returns:
        float: xThreat value, or 0.0 if coordinates unavailable
    """
    # Get start and end zones
    start_x = event.get('coordinates_x', np.nan)
    start_y = event.get('coordinates_y', np.nan)
    end_x = event.get('end_coordinates_x', np.nan)
    end_y = event.get('end_coordinates_y', np.nan)

    start_col, start_row = get_zone(start_x, start_y)
    end_col, end_row = get_zone(end_x, end_y)

    if start_col is None or end_col is None:
        return 0.0

    # Compute threat delta
    start_threat = threat_surface[start_row, start_col]
    end_threat = threat_surface[end_row, end_col]

    return end_threat - start_threat


def compute_xthreat_per_phase(events_df, phases_df):
    """
    Compute aggregated xThreat per phase segment.

    Args:
        events_df: Events DataFrame from Step 1
        phases_df: Phase segments DataFrame from Step 3

    Returns:
        pd.DataFrame: phases_df with xthreat_gained and xthreat_conceded columns
    """
    print("Computing xThreat per phase...")

    # Load pre-computed xT surface (Karun Singh, Markov model)
    threat_surface = load_threat_surface()
    print(f"  Loaded xT grid {threat_surface.shape} (range {threat_surface.min():.4f} - {threat_surface.max():.4f})")

    # Compute xThreat for each phase
    xthreat_gained = []
    xthreat_conceded = []

    for idx, phase_row in tqdm(phases_df.iterrows(), total=len(phases_df), desc="  Computing xThreat"):
        # Get events during this phase
        phase_events = events_df[
            (events_df['timestamp'] >= phase_row['start_time']) &
            (events_df['timestamp'] <= phase_row['end_time'])
        ].copy()

        if len(phase_events) == 0:
            xthreat_gained.append(0.0)
            xthreat_conceded.append(0.0)
            continue

        # Compute xThreat for each event
        phase_events['xthreat'] = phase_events.apply(
            lambda e: compute_xthreat_for_event(e, threat_surface), axis=1
        )

        # Aggregate by team
        team_xthreat = phase_events.groupby('team_id')['xthreat'].sum()

        # Gained = threat created by this team
        gained = team_xthreat.get(phase_row['team_id'], 0.0)

        # Conceded = threat created by opponent
        opponent_teams = [t for t in team_xthreat.index if t != phase_row['team_id']]
        conceded = sum(team_xthreat.get(t, 0.0) for t in opponent_teams)

        xthreat_gained.append(gained)
        xthreat_conceded.append(conceded)

    # Add to phases_df
    phases_df_with_xthreat = phases_df.copy()
    phases_df_with_xthreat['xthreat_gained'] = xthreat_gained
    phases_df_with_xthreat['xthreat_conceded'] = xthreat_conceded

    print(f"  Computed xThreat for {len(phases_df)} phases")

    return phases_df_with_xthreat


def main(events_df, phases_df):
    """
    Main entry point for Step 7.

    Args:
        events_df: Events DataFrame from Step 1
        phases_df: Phase segments DataFrame from Step 3

    Returns:
        pd.DataFrame: phases_df with xThreat metrics
    """
    print("\n" + "=" * 80)
    print("STEP 7: xTHREAT COMPUTATION")
    print("=" * 80)
    print("Using pre-computed xT grid (Karun Singh, Markov possession model)")

    # Compute xThreat per phase
    phases_df_with_xthreat = compute_xthreat_per_phase(events_df, phases_df)

    print("\n[OK] xThreat computation complete")

    # Show sample
    print(f"\nSample xThreat values:")
    print(phases_df_with_xthreat[['phase_id', 'phase_type', 'team_id', 'xthreat_gained', 'xthreat_conceded']].head(10))

    print(f"\nxThreat statistics:")
    print(phases_df_with_xthreat[['xthreat_gained', 'xthreat_conceded']].describe())

    return phases_df_with_xthreat


if __name__ == "__main__":
    print("\n[INFO] This script requires events_df and phases_df.")
    print("Run as part of the pipeline.")
