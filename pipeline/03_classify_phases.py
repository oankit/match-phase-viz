"""
Step 3: Possession-Aware Two-Path Phase Classifier

Classifies phases for BOTH teams simultaneously using ball possession:
- Team WITH ball: attacking, build_up
- Team WITHOUT ball: high_press, mid_block, defensive_block
- Event-based: counter_attack (overrides tracking labels)
- Fallback: open_play

Key design:
- ball_owning_team_id from Step 2 determines possession context
- Each frame produces a label for EACH team
- Transitions (counter-attacks) override tracking-based labels

Based on:
- Tracking thresholds from tactical analysis literature
- Counter-attack rules from Bekkers & Sahasrabudhe (SSAC 2023)
- Shape metrics from Pracxa et al. (2022)

NOTE: All coordinates are NORMALIZED (0-1) not absolute meters
"""

import numpy as np
import pandas as pd
from tqdm import tqdm

import config


# ============================================================================
# PATH A: POSSESSION-AWARE TRACKING-BASED CLASSIFICATION
# ============================================================================

def classify_frame_for_team(row):
    """
    Classify phase for a single team-frame using possession context.

    The team's role (attacking/defending) is determined by ball_owning_team_id.
    Then tracking features determine the specific phase within that role.

    Args:
        row: DataFrame row with features including ball_owning_team_id

    Returns:
        str: Phase type
    """
    thresholds = config.PHASE_THRESHOLDS
    team_id = row['team_id']
    ball_owner = row.get('ball_owning_team_id', None)

    # If possession unknown, fall back to open_play
    if pd.isna(ball_owner) or ball_owner is None:
        return 'open_play'

    has_ball = (team_id == ball_owner)

    if has_ball:
        # ---- ATTACKING PHASES (team has possession) ----
        att = thresholds.get('attacking', {})
        bu = thresholds.get('build_up', {})

        # Attacking: ball in opponent half, team pushed forward
        if (row['ball_x'] > att.get('ball_x_min', 0.50) and
                row['defensive_line_height'] > att.get('def_line_height_min', 0.38)):
            return 'attacking'

        # Build-up: ball in own half, constructing possession
        elif row['ball_x'] <= bu.get('ball_x_max', 0.50):
            return 'build_up'

        # Default attacking state
        else:
            return 'attacking'

    else:
        # ---- DEFENSIVE PHASES (opponent has possession) ----
        hp = thresholds.get('high_press', {})
        db = thresholds.get('defensive_block', {})
        mb = thresholds.get('mid_block', {})

        # High press: pushing high, pressuring in opponent half
        if (row['defensive_line_height'] > hp.get('def_line_height_min', 0.40) and
                row['ball_x'] > hp.get('ball_x_min', 0.48) and
                row['pressure_proxy'] >= hp.get('pressure_proxy_min', 1)):
            return 'high_press'

        # Defensive block: deep, compact, protecting own goal
        elif (row['defensive_line_height'] < db.get('def_line_height_max', 0.30) and
              row['compactness'] < db.get('compactness_max', 0.18) and
              row['ball_x'] < db.get('ball_x_max', 0.45)):
            return 'defensive_block'

        # Mid-block: between high press and low block
        elif (row['defensive_line_height'] >= mb.get('def_line_height_min', 0.30) and
              row['defensive_line_height'] <= mb.get('def_line_height_max', 0.40)):
            return 'mid_block'

        # Default defensive state
        else:
            return 'mid_block'


def classify_all_tracking_phases(features_df):
    """
    Apply possession-aware classification to all frames for both teams.

    Args:
        features_df: Features DataFrame from Step 2 (with ball_owning_team_id)

    Returns:
        pd.DataFrame: features_df with 'phase_tracking' column
    """
    print("Classifying possession-aware phases...")

    # Check for ball_owning_team_id
    if 'ball_owning_team_id' not in features_df.columns:
        print("  WARNING: ball_owning_team_id not found. Falling back to old classifier.")
        features_df['phase_tracking'] = features_df.apply(_classify_tracking_phase_legacy, axis=1)
    else:
        poss_available = features_df['ball_owning_team_id'].notna().sum()
        total = len(features_df)
        print(f"  Possession data available for {poss_available}/{total} frames "
              f"({100*poss_available/total:.1f}%)")
        features_df['phase_tracking'] = features_df.apply(classify_frame_for_team, axis=1)

    # Print phase distribution
    print("\nTracking-based phase distribution (possession-aware):")
    phase_counts = features_df.groupby(['team_id', 'phase_tracking']).size()
    print(phase_counts)

    return features_df


def _classify_tracking_phase_legacy(row):
    """Legacy classifier (no possession data). Used as fallback."""
    thresholds = config.PHASE_THRESHOLDS

    if (row['defensive_line_height'] > thresholds['high_press']['def_line_height_min'] and
        row['ball_x'] > thresholds['high_press']['ball_x_min'] and
        row['pressure_proxy'] >= thresholds['high_press']['pressure_proxy_min']):
        return 'high_press'
    elif (row['defensive_line_height'] < thresholds['defensive_block']['def_line_height_max'] and
          row['compactness'] < thresholds['defensive_block']['compactness_max'] and
          row['ball_x'] < thresholds['defensive_block']['ball_x_max']):
        return 'defensive_block'
    else:
        return 'open_play'


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
        has_set_piece = False

        if window['event_type'].isin(set_piece_types).any():
            has_set_piece = True

        if 'set_piece_type' in window.columns:
            if window['set_piece_type'].notna().any():
                has_set_piece = True

        if has_set_piece:
            continue

        # Rule 3: Ball moves >= 10m forward
        end_coords = window['end_coordinates_x'].dropna()
        if len(end_coords) > 0:
            max_x = end_coords.max()
            forward_dist = max_x - start_x

            if forward_dist < rules['forward_distance_min']:
                continue
        else:
            continue

        # Rule 4: Forward velocity check
        time_to_max_row = window[window['end_coordinates_x'] == max_x].iloc[0]
        time_to_max = (time_to_max_row['timestamp'] - t_start).total_seconds()

        if time_to_max > 0:
            velocity = forward_dist / time_to_max
            if velocity < rules['forward_velocity_min']:
                continue
        else:
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

    Key rule: Counter-attacks override tracking-based labels for the
    transitioning team. The opposing team keeps their defensive label.

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

    Short attacking phases revert to build_up, short defensive phases
    revert to mid_block, and truly ambiguous ones revert to open_play.

    Args:
        features_df: DataFrame with 'phase_final' column
        min_duration_seconds: Minimum phase duration

    Returns:
        pd.DataFrame: Smoothed features_df
    """
    print(f"\nSmoothing phases (min duration: {min_duration_seconds}s)...")

    # Map short phases to their natural fallback
    fallback_map = {
        'high_press': 'mid_block',
        'defensive_block': 'mid_block',
        'attacking': 'build_up',
        'counter_attack': 'open_play',
    }

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

        # Drop short segments
        for start, end in zip(segment_starts, segment_ends):
            time_diff = timestamps[end-1] - timestamps[start]
            if isinstance(time_diff, np.timedelta64):
                duration = pd.Timedelta(time_diff).total_seconds()
            else:
                duration = time_diff.total_seconds()
            if duration < min_duration_seconds:
                current_phase = team_phases[start]
                fallback = fallback_map.get(current_phase, 'open_play')
                indices = team_df.index[start:end]
                features_df.loc[indices, 'phase_final'] = fallback

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
                'team_length': team_segment_features['team_length'].mean(),
                'team_width': team_segment_features['team_width'].mean(),
                'lpw_ratio': team_segment_features['lpw_ratio'].mean(),
                'stretching_index': team_segment_features['stretching_index'].mean(),
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
        features_df: Features DataFrame from Step 2 (must include ball_owning_team_id)
        events_df: Events DataFrame from Step 1

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]: (features_df with phases, phases summary)
    """
    print("\n" + "=" * 80)
    print("STEP 3: POSSESSION-AWARE PHASE CLASSIFICATION")
    print("=" * 80)

    # Path A: Possession-aware tracking-based classification
    features_df = classify_all_tracking_phases(features_df)

    # Path B: Event-based counter-attack detection
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
