"""
Step 3: Two-Path Phase Classifier

Implements parallel detection paths that get merged:
- Path A (tracking-based): High press, defensive block, open play
- Path B (event-based): Counter-attacks/transitions

Key rule: Transitions override tracking-based labels when active.

Based on:
- Tracking thresholds from tactical analysis literature
- Counter-attack rules from Bekkers & Sahasrabudhe (SSAC 2023)

NOTE: All coordinates are NORMALIZED (0-1) not absolute meters
"""

import numpy as np
import pandas as pd
from tqdm import tqdm

import config


# ============================================================================
# PATH A: TRACKING-BASED PHASE CLASSIFICATION
# ============================================================================

def classify_tracking_phase(row):
    """
    Classify phase based on tracking features (defensive perspective).

    Args:
        row: DataFrame row with features (def_line_height, compactness, pressure_proxy, ball_x)

    Returns:
        str: Phase type ('high_press', 'defensive_block', or 'open_play')
    """
    thresholds = config.PHASE_THRESHOLDS

    # High press: pushing high, pressuring in opponent half
    if (row['defensive_line_height'] > thresholds['high_press']['def_line_height_min'] and
        row['ball_x'] > thresholds['high_press']['ball_x_min'] and
        row['pressure_proxy'] >= thresholds['high_press']['pressure_proxy_min']):
        return 'high_press'

    # Defensive block: deep, compact, in own half
    elif (row['defensive_line_height'] < thresholds['defensive_block']['def_line_height_max'] and
          row['compactness'] < thresholds['defensive_block']['compactness_max'] and
          row['ball_x'] < thresholds['defensive_block']['ball_x_max']):
        return 'defensive_block'

    # Default: open play
    else:
        return 'open_play'


def classify_all_tracking_phases(features_df):
    """
    Apply tracking-based classification to all frames.

    Args:
        features_df: Features DataFrame from Step 2

    Returns:
        pd.DataFrame: features_df with 'phase_tracking' column
    """
    print("Classifying tracking-based phases...")

    features_df['phase_tracking'] = features_df.apply(classify_tracking_phase, axis=1)

    # Print phase distribution
    print("\nTracking-based phase distribution:")
    phase_counts = features_df.groupby(['team_id', 'phase_tracking']).size()
    print(phase_counts)

    return features_df


# ============================================================================
# PATH B: EVENT-BASED COUNTER-ATTACK DETECTION
# ============================================================================

def detect_counterattacks(events_df):
    """
    Detect counter-attack sequences from event data.

    Implements rules from Bekkers & Sahasrabudhe (SSAC 2023):
    1. Start in defensive half (coordinates_x < 0.5)
    2. No set pieces in sequence
    3. Ball moves >= 10m forward (>= 0.095 in normalized coords)
    4. Forward velocity >= 4 m/s (>= 0.038 in normalized units/s)

    Args:
        events_df: Event DataFrame from Step 1

    Returns:
        List[Tuple[pd.Timedelta, pd.Timedelta, str]]: List of (start_time, end_time, team_id) tuples
    """
    print("Detecting counter-attacks...")

    rules = config.COUNTERATTACK_RULES
    set_piece_types = rules['set_piece_types']

    transitions = []

    # Find possession change events (RECOVERY is the main one in our data)
    # Could also include: INTERCEPTION, TACKLE if they exist
    possession_change_types = ['RECOVERY']

    # Filter for potential possession changes
    poss_changes = events_df[
        events_df['event_type'].isin(possession_change_types)
    ].copy()

    print(f"  Found {len(poss_changes)} potential possession changes (RECOVERY events)")

    for idx, poss_change in poss_changes.iterrows():
        # Rule 1: Start in defensive half (normalized coordinates)
        start_x = poss_change['coordinates_x']
        if pd.isna(start_x) or start_x > 0.5:
            continue

        team = poss_change['team_id']
        t_start = poss_change['timestamp']

        # Convert timeout to timedelta
        timeout = pd.Timedelta(seconds=rules['timeout'])

        # Get subsequent events by same team within timeout window
        window = events_df[
            (events_df['timestamp'] > t_start) &
            (events_df['timestamp'] <= t_start + timeout) &
            (events_df['team_id'] == team)
        ].copy()

        if window.empty:
            continue

        # Rule 2: Check for set pieces in the sequence
        # Check both event_type and set_piece_type column
        has_set_piece = False

        # Check event_type
        if window['event_type'].isin(set_piece_types).any():
            has_set_piece = True

        # Check set_piece_type column (for events like PASS with set_piece_type)
        if 'set_piece_type' in window.columns:
            if window['set_piece_type'].notna().any():
                # Any non-null set_piece_type means it's a set piece
                has_set_piece = True

        if has_set_piece:
            continue

        # Rule 3: Ball moves >= 10m forward (>= 0.095 in normalized coords)
        # Use end_coordinates_x for events that have it
        end_coords = window['end_coordinates_x'].dropna()
        if len(end_coords) > 0:
            max_x = end_coords.max()
            forward_dist = max_x - start_x

            if forward_dist < rules['forward_distance_min']:
                continue
        else:
            # No end coordinates, skip
            continue

        # Rule 4: Forward velocity >= 4 m/s (>= 0.038 in normalized units/s)
        time_to_max_row = window[window['end_coordinates_x'] == max_x].iloc[0]
        time_to_max = (time_to_max_row['timestamp'] - t_start).total_seconds()

        if time_to_max > 0:
            velocity = forward_dist / time_to_max
            if velocity < rules['forward_velocity_min']:
                continue
        else:
            # Instantaneous, likely not a counter-attack
            continue

        # Valid counter-attack detected
        t_end = window.iloc[-1]['timestamp']
        transitions.append((t_start, t_end, team))

    print(f"  Detected {len(transitions)} counter-attacks")

    return transitions


# ============================================================================
# MERGE PATHS
# ============================================================================

def merge_phases(features_df, transition_periods):
    """
    Merge tracking-based and event-based classifications.

    Key rule: Transitions override tracking-based labels.

    Args:
        features_df: DataFrame with 'phase_tracking' column
        transition_periods: List of (start_time, end_time, team_id) tuples

    Returns:
        pd.DataFrame: features_df with 'phase_final' column
    """
    print("Merging tracking and event-based phases...")

    # Start with tracking-based labels
    features_df['phase_final'] = features_df['phase_tracking']

    # Override with counter-attacks
    for t_start, t_end, team in transition_periods:
        mask = (
            (features_df['timestamp'] >= t_start) &
            (features_df['timestamp'] <= t_end) &
            (features_df['team_id'] == team)
        )
        features_df.loc[mask, 'phase_final'] = 'counter_attack'

    # Print final distribution
    print("\nFinal phase distribution:")
    print(features_df.groupby(['team_id', 'phase_final']).size())

    return features_df


# ============================================================================
# POST-PROCESSING
# ============================================================================

def smooth_phases(features_df, min_duration_seconds=5.0):
    """
    Post-process phase labels:
    1. Drop segments shorter than min_duration_seconds

    Args:
        features_df: DataFrame with 'phase_final' column
        min_duration_seconds: Minimum phase duration

    Returns:
        pd.DataFrame: Smoothed features_df
    """
    print(f"\nSmoothing phases (min duration: {min_duration_seconds}s)...")

    for team in features_df['team_id'].unique():
        team_mask = features_df['team_id'] == team
        team_df = features_df[team_mask].sort_values('timestamp').copy()

        # Identify phase change points
        team_phases = team_df['phase_final'].values
        timestamps = team_df['timestamp'].values

        # Find segments
        changes = np.where(team_phases[:-1] != team_phases[1:])[0] + 1
        segment_starts = np.concatenate([[0], changes])
        segment_ends = np.concatenate([changes, [len(team_phases)]])

        # Drop short segments (revert to 'open_play')
        for start, end in zip(segment_starts, segment_ends):
            time_diff = timestamps[end-1] - timestamps[start]
            # Convert numpy.timedelta64 to pandas.Timedelta for .total_seconds()
            if isinstance(time_diff, np.timedelta64):
                duration = pd.Timedelta(time_diff).total_seconds()
            else:
                duration = time_diff.total_seconds()
            if duration < min_duration_seconds:
                indices = team_df.index[start:end]
                features_df.loc[indices, 'phase_final'] = 'open_play'

    print("  Smoothing complete.")
    print("\nSmoothed phase distribution:")
    print(features_df.groupby(['team_id', 'phase_final']).size())

    return features_df


def create_phase_segments(features_df):
    """
    Create phase segment summary DataFrame.

    Args:
        features_df: DataFrame with 'phase_final' column

    Returns:
        pd.DataFrame: Columns: phase_id, phase_type, team_id, start_time, end_time, duration
    """
    print("\nCreating phase segments...")

    segments = []
    phase_id = 0

    for team in features_df['team_id'].unique():
        team_df = features_df[features_df['team_id'] == team].sort_values('timestamp')

        # Identify contiguous phase segments
        team_phases = team_df['phase_final'].values
        timestamps = team_df['timestamp'].values

        changes = np.where(team_phases[:-1] != team_phases[1:])[0] + 1
        segment_starts = np.concatenate([[0], changes])
        segment_ends = np.concatenate([changes, [len(team_phases)]])

        for start_idx, end_idx in zip(segment_starts, segment_ends):
            phase_type = team_phases[start_idx]
            start_time = timestamps[start_idx]
            end_time = timestamps[end_idx - 1]
            time_diff = end_time - start_time
            # Convert numpy.timedelta64 to pandas.Timedelta for .total_seconds()
            if isinstance(time_diff, np.timedelta64):
                duration = pd.Timedelta(time_diff).total_seconds()
            else:
                duration = time_diff.total_seconds()

            team_segment_features = team_df.iloc[start_idx:end_idx]

            segments.append({
                'phase_id': phase_id,
                'phase_type': phase_type,
                'team_id': team,
                'start_time': start_time,
                'end_time': end_time,
                'duration': duration,
                'defensive_line_height': team_segment_features['defensive_line_height'].mean(),
                'compactness': team_segment_features['compactness'].mean(),
                'ppda_proxy': team_segment_features['pressure_proxy'].mean(),
            })
            phase_id += 1

    phases_df = pd.DataFrame(segments)

    print(f"  Created {len(phases_df)} phase segments")
    print("\nPhase summary:")
    summary = phases_df.groupby('phase_type').agg({
        'duration': ['count', 'mean', 'std', 'min', 'max']
    })
    print(summary)

    return phases_df


# ============================================================================
# MAIN
# ============================================================================

def main(features_df, events_df):
    """
    Main entry point for Step 3.

    Args:
        features_df: Features DataFrame from Step 2
        events_df: Events DataFrame from Step 1

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]: (features_df with phases, phases summary)
    """
    print("\n" + "=" * 80)
    print("STEP 3: TWO-PATH PHASE CLASSIFICATION")
    print("=" * 80)

    # Path A: Tracking-based
    features_df = classify_all_tracking_phases(features_df)

    # Path B: Event-based
    transition_periods = detect_counterattacks(events_df)

    # Merge paths
    features_df = merge_phases(features_df, transition_periods)

    # Post-process
    features_df = smooth_phases(features_df, min_duration_seconds=config.MIN_PHASE_DURATION)

    # Create phase segments
    phases_df = create_phase_segments(features_df)

    print("\n[OK] Phase classification complete")

    return features_df, phases_df


if __name__ == "__main__":
    print("\n[INFO] This script requires features_df (Step 2) and events_df (Step 1).")
    print("Run as part of the pipeline.")
