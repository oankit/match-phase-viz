"""
Step 7: xThreat (Expected Threat)

Uses Karun Singh's pre-computed xT value surface (12x8 grid) trained on
real match data via a Markov chain possession model. The value at each cell
represents the long-term probability of scoring from that pitch zone.

xT(action) = threat(end_zone) - threat(start_zone)

Source: https://karun.in/blog/expected-threat.html
Grid:   pipeline/xt_grid_12x8.json (8 rows x 12 cols)

A higher-resolution 16x12 grid is also available (pipeline/xt_grid_16x12.json),
trained on 303 StatsBomb games via pipeline/train_xt_model.py. The 12x8 grid
is used by default because it produces better visual separation in the threat
timeline (coarser zones = larger per-pass xT deltas).
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

    For passes: xThreat = threat(end_zone) - threat(start_zone)
    For shots:  xThreat = 0.0 (terminal events, scoring prob already in grid)
    For goals:  xThreat = 0.0 (shown as markers, not in xT aggregation)

    Args:
        event: Event row from events_df
        threat_surface: (8, 12) threat surface

    Returns:
        float: xThreat value, or 0.0 if coordinates unavailable
    """
    event_type = event.get('event_type', '')
    result = event.get('result', '')

    start_x = event.get('coordinates_x', np.nan)
    start_y = event.get('coordinates_y', np.nan)

    # Standard xT: shots are terminal events, not ball-moving actions.
    # Scoring probability is already baked into the xT grid surface.
    # Goals are shown separately as markers on the timeline.
    if event_type == 'SHOT':
        return 0.0

    end_x = event.get('end_coordinates_x', np.nan)
    end_y = event.get('end_coordinates_y', np.nan)

    start_col, start_row = get_zone(start_x, start_y)
    end_col, end_row = get_zone(end_x, end_y)

    if start_col is None or end_col is None:
        return 0.0

    start_threat = threat_surface[start_row, start_col]
    end_threat = threat_surface[end_row, end_col]

    return end_threat - start_threat


def _shot_xg(x, y):
    """Positional xG for a shot based on distance and angle to goal centre.
    Goal centre at (1.0, 0.5) in normalised coordinates."""
    if pd.isna(x) or pd.isna(y):
        return 0.0
    dx = (1.0 - x) * config.PITCH_LENGTH
    dy = (0.5 - y) * config.PITCH_WIDTH
    dist = np.sqrt(dx ** 2 + dy ** 2)
    if dist < 1:
        return 0.40
    angle = np.degrees(np.arctan2(7.32 / 2, dist))
    return max(0.02, min(0.50, 0.6 * (angle / 90) ** 1.3))


def compute_xthreat_per_phase(events_df, phases_df):
    """
    Compute aggregated xThreat per phase segment.

    Two-pass approach:
      1. Exact match: assign each event to the phase covering its timestamp.
         Each event is assigned to at most one phase.
      2. Gap recovery: any SHOT events not matched in pass 1 are assigned
         to the nearest preceding phase (handles dead-ball gaps after goals).

    Args:
        events_df: Events DataFrame from Step 1
        phases_df: Phase segments DataFrame from Step 3

    Returns:
        pd.DataFrame: phases_df with xthreat_gained and xthreat_conceded columns
    """
    print("Computing xThreat per phase...")

    threat_surface = load_threat_surface()
    print(f"  Loaded xT grid {threat_surface.shape} (range {threat_surface.min():.4f} - {threat_surface.max():.4f})")

    # Pre-compute xThreat for every event once
    events_df = events_df.copy()
    events_df['_xt'] = events_df.apply(
        lambda e: compute_xthreat_for_event(e, threat_surface), axis=1
    )

    # Pass 1: exact match (each event to at most one phase)
    xthreat_gained = np.zeros(len(phases_df))
    xthreat_conceded = np.zeros(len(phases_df))
    assigned_event_indices = set()

    for i, (idx, phase_row) in enumerate(
        tqdm(phases_df.iterrows(), total=len(phases_df), desc="  Computing xThreat")
    ):
        phase_events = events_df[
            (events_df['timestamp'] >= phase_row['start_time']) &
            (events_df['timestamp'] <= phase_row['end_time']) &
            (~events_df.index.isin(assigned_event_indices))
        ]

        if len(phase_events) == 0:
            continue

        assigned_event_indices.update(phase_events.index.tolist())

        team_xthreat = phase_events.groupby('team_id')['_xt'].sum()
        xthreat_gained[i] = team_xthreat.get(phase_row['team_id'], 0.0)

        opponent_teams = [t for t in team_xthreat.index if t != phase_row['team_id']]
        xthreat_conceded[i] = sum(team_xthreat.get(t, 0.0) for t in opponent_teams)

    phases_df_with_xthreat = phases_df.copy()
    phases_df_with_xthreat['xthreat_gained'] = xthreat_gained
    phases_df_with_xthreat['xthreat_conceded'] = xthreat_conceded

    # Pass 2: assign unmatched events with significant xThreat to nearest phase
    unmatched = events_df[
        (~events_df.index.isin(assigned_event_indices)) &
        (events_df['_xt'].abs() > 0.01)
    ]

    if len(unmatched) > 0:
        print(f"  Found {len(unmatched)} unmatched events with |xT| > 0.01")
        for evt_idx, evt in unmatched.iterrows():
            xt = evt['_xt']
            evt_time = evt['timestamp']
            evt_team = evt['team_id']

            # Find nearest phase belonging to the SAME team as the event
            same_team = phases_df_with_xthreat[
                phases_df_with_xthreat['team_id'] == evt_team
            ]
            if len(same_team) == 0:
                continue

            diffs = (same_team['end_time'] - evt_time).abs()
            closest_idx = diffs.idxmin()
            closest_phase = phases_df_with_xthreat.loc[closest_idx]
            gap = abs((evt_time - closest_phase['end_time']).total_seconds())

            if gap > 15:
                continue

            phases_df_with_xthreat.loc[closest_idx, 'xthreat_gained'] += xt

            result = evt.get('result', '')
            event_type = evt.get('event_type', '')
            print(f"    Assigned {event_type}/{result} xT={xt:.4f} at "
                  f"t={evt_time.total_seconds():.1f}s -> phase "
                  f"{closest_phase['phase_id']} (team={evt_team}, gap={gap:.1f}s)")

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
    print("Using Karun Singh 12x8 xT grid (Markov possession model)")

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
