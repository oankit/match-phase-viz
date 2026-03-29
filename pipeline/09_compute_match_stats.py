"""
Step 9: Compute Match Statistics & Player Stats

Computes The Athletic-style match stats and per-player stats from event data:

Match Stats (per team):
  - Start distance: avg distance from possession start to opponent goal (meters)
  - Progression: avg % of remaining distance gained per possession
  - Circulation: indirectness of passing (1 - progressive_dist / total_dist)
  - Build-ups: possessions with 8+ passes reaching the box
  - Fast breaks: possessions reaching box within 15s from deep
  - High press: defensive actions in top 60% per 100 opponent passes

Player Stats (per player):
  - minutes_played
  - goals, assists
  - progressive_passes: completed passes gaining >=25% of remaining distance and >=10m
  - progressive_receptions: receiving a progressive pass
  - defensive_actions: OtherBallAction + Recovery events
  - touches: all on-ball events
  - xg: expected goals from shots (positional model)
"""

import numpy as np
import pandas as pd
import config


PITCH_L = config.PITCH_LENGTH  # 105
PITCH_W = config.PITCH_WIDTH   # 68


def _detect_attacking_direction(events_df, team_ids):
    """Auto-detect attacking direction per team per period from shot locations.

    Returns dict: {(team_id, period_id): attacking_right}
    """
    direction = {}
    shots = events_df[events_df['event_type'] == 'SHOT']

    for team_id in team_ids:
        for period in [1, 2]:
            team_shots = shots[
                (shots['team_id'] == team_id) &
                (shots['period_id'] == period) &
                (shots['coordinates_x'].notna())
            ]
            if len(team_shots) > 0:
                avg_x = team_shots['coordinates_x'].mean()
                direction[(team_id, period)] = avg_x > 0.5
            else:
                pass_data = events_df[
                    (events_df['team_id'] == team_id) &
                    (events_df['period_id'] == period) &
                    (events_df['event_type'] == 'PASS') &
                    (events_df['end_coordinates_x'].notna())
                ]
                if len(pass_data) > 0:
                    fwd = (pass_data['end_coordinates_x'] > pass_data['coordinates_x']).mean()
                    direction[(team_id, period)] = fwd > 0.5
                else:
                    direction[(team_id, period)] = (team_id == team_ids[0])

    return direction


def _get_attack_right(direction_map, team_id, period_id):
    """Look up attacking direction for a team in a given period."""
    return direction_map.get((team_id, period_id), True)


def _dist_to_goal(x, y, attacking_right):
    """Euclidean distance (meters) from (x, y) to centre of opponent goal.
    x, y are normalised 0-1.  attacking_right=True means goal at x=1.0."""
    gx = 1.0 if attacking_right else 0.0
    gy = 0.5
    return np.sqrt(((x - gx) * PITCH_L) ** 2 + ((y - gy) * PITCH_W) ** 2)


def _x_dist_to_goal(x, attacking_right):
    """X-axis distance (meters) to opponent goal line."""
    if attacking_right:
        return (1.0 - x) * PITCH_L
    else:
        return x * PITCH_L


def _in_box(x, y, attacking_right):
    """Check if normalised (x,y) is inside the opponent's penalty box.
    Box: 16.5m deep, 40.3m wide, centred on goal line."""
    box_depth = 16.5 / PITCH_L
    box_half_w = 20.15 / PITCH_W
    if attacking_right:
        return x >= (1.0 - box_depth) and abs(y - 0.5) <= box_half_w
    else:
        return x <= box_depth and abs(y - 0.5) <= box_half_w


def _build_possessions(events_df, team_id, min_events=2):
    """Build possession sequences for a team.

    A possession is a consecutive run of on-ball events by the same team,
    broken by an event from the other team or a dead ball.
    Only includes possessions with at least min_events on-ball actions.
    Also breaks on period boundaries so each possession belongs to one period.
    """
    on_ball_types = {'PASS', 'SHOT', 'GENERIC:OtherBallAction', 'RECOVERY'}
    break_types = {'BALL_OUT', 'FOUL_COMMITTED'}

    all_sorted = events_df.sort_values('timestamp').reset_index(drop=True)
    relevant = all_sorted[
        all_sorted['event_type'].isin(on_ball_types | break_types) &
        all_sorted['team_id'].notna()
    ].copy()

    possessions = []
    current = []
    current_period = None

    for _, row in relevant.iterrows():
        if row['period_id'] != current_period:
            if len(current) >= min_events:
                possessions.append(pd.DataFrame(current))
            current = []
            current_period = row['period_id']

        if row['event_type'] in break_types:
            if len(current) >= min_events:
                possessions.append(pd.DataFrame(current))
            current = []
            continue

        if row['team_id'] == team_id:
            current.append(row)
        else:
            if len(current) >= min_events:
                possessions.append(pd.DataFrame(current))
            current = []

    if len(current) >= min_events:
        possessions.append(pd.DataFrame(current))

    return possessions


def compute_start_distance(possessions, direction_map, team_id):
    """Average distance (m) from start of possessions to opponent goal centre."""
    distances = []
    for poss in possessions:
        first = poss.iloc[0]
        x, y = first['coordinates_x'], first['coordinates_y']
        period = first['period_id']
        if pd.notna(x) and pd.notna(y):
            ar = _get_attack_right(direction_map, team_id, period)
            distances.append(_dist_to_goal(x, y, ar))
    return round(np.mean(distances), 1) if distances else 0.0


def compute_progression(possessions, direction_map, team_id):
    """Average % of remaining distance gained (x-axis only) from start to
    furthest forward point of the possession. Requires 3+ events to reduce
    noise from very short possession sequences."""
    progs = []
    for poss in possessions:
        if len(poss) < 3:
            continue

        first = poss.iloc[0]
        period = first['period_id']
        ar = _get_attack_right(direction_map, team_id, period)

        with_coords = poss[poss['coordinates_x'].notna()]
        if len(with_coords) < 2:
            continue

        x0 = with_coords.iloc[0]['coordinates_x']
        d0 = _x_dist_to_goal(x0, ar)

        if d0 < 10:
            continue

        best_d = d0
        for _, ev in with_coords.iterrows():
            d = _x_dist_to_goal(ev['coordinates_x'], ar)
            if d < best_d:
                best_d = d

        prog = (d0 - best_d) / d0 * 100
        progs.append(max(0, min(100, prog)))

    return round(np.mean(progs), 1) if progs else 0.0


def compute_circulation(events_df, team_id, direction_map):
    """Circulation = 1 - (progressive_pass_distance / total_pass_distance).
    Progressive distance = x-axis distance gained toward opponent goal.
    Higher = more indirect / patient passing."""
    passes = events_df[
        (events_df['team_id'] == team_id) &
        (events_df['event_type'] == 'PASS') &
        (events_df['end_coordinates_x'].notna())
    ]

    total_dist = 0.0
    prog_dist = 0.0

    for _, p in passes.iterrows():
        x0, y0 = p['coordinates_x'], p['coordinates_y']
        x1, y1 = p['end_coordinates_x'], p['end_coordinates_y']
        period = p['period_id']
        ar = _get_attack_right(direction_map, team_id, period)

        dx = (x1 - x0) * PITCH_L
        dy = (y1 - y0) * PITCH_W
        d = np.sqrt(dx ** 2 + dy ** 2)
        total_dist += d

        d0 = _x_dist_to_goal(x0, ar)
        d1 = _x_dist_to_goal(x1, ar)
        gained = d0 - d1
        if gained > 0:
            prog_dist += gained

    if total_dist < 1:
        return 0.0
    return round(1.0 - (prog_dist / total_dist), 2)


def _in_final_third(x, attacking_right):
    """Check if x is in the opponent's final third (last 35m)."""
    if pd.isna(x):
        return False
    threshold = 35.0 / PITCH_L
    if attacking_right:
        return x >= (1.0 - threshold)
    else:
        return x <= threshold


def compute_buildups(possessions, direction_map, team_id, min_passes=5):
    """Count possessions with >=min_passes passes that reach the opponent's
    penalty box or final third (any event start OR pass end coordinates)."""
    count = 0
    for poss in possessions:
        period = poss.iloc[0]['period_id']
        ar = _get_attack_right(direction_map, team_id, period)
        passes_in_poss = poss[poss['event_type'] == 'PASS']
        if len(passes_in_poss) < min_passes:
            continue
        reached = False
        for _, ev in poss.iterrows():
            x, y = ev['coordinates_x'], ev['coordinates_y']
            if pd.notna(x) and pd.notna(y) and _in_box(x, y, ar):
                reached = True
                break
            ex = ev.get('end_coordinates_x')
            ey = ev.get('end_coordinates_y')
            if pd.notna(ex) and pd.notna(ey) and _in_box(ex, ey, ar):
                reached = True
                break
        if reached:
            count += 1
    return count


def compute_fast_breaks(possessions, direction_map, team_id):
    """Possessions reaching the box within 15s of a touch in the team's
    own half (x < 50% toward goal)."""
    count = 0

    for poss in possessions:
        period = poss.iloc[0]['period_id']
        ar = _get_attack_right(direction_map, team_id, period)

        deep_touch_time = None
        for _, ev in poss.iterrows():
            x = ev['coordinates_x']
            if pd.isna(x):
                continue
            x_dist = _x_dist_to_goal(x, ar)
            if x_dist >= PITCH_L * 0.5 and deep_touch_time is None:
                deep_touch_time = ev['timestamp']

        if deep_touch_time is None:
            continue

        for _, ev in poss.iterrows():
            x, y = ev['coordinates_x'], ev['coordinates_y']
            if pd.isna(x) or pd.isna(y):
                continue
            dt = (ev['timestamp'] - deep_touch_time).total_seconds()
            if dt > 15:
                break
            if _in_box(x, y, ar):
                count += 1
                break

    return count


def compute_high_press(events_df, pressing_team_id, opponent_team_id, direction_map):
    """Defensive actions in the opponent's half per 100 opponent passes
    in the same zone."""

    def in_high_zone(x, period):
        if pd.isna(x):
            return False
        ar = _get_attack_right(direction_map, pressing_team_id, period)
        if ar:
            return x >= 0.50
        else:
            return x <= 0.50

    defensive_events = events_df[
        (events_df['team_id'] == pressing_team_id) &
        (events_df['event_type'].isin(['GENERIC:OtherBallAction', 'RECOVERY', 'FOUL_COMMITTED']))
    ]
    def_actions_high = sum(
        in_high_zone(row['coordinates_x'], row['period_id'])
        for _, row in defensive_events.iterrows()
    )

    opponent_passes = events_df[
        (events_df['team_id'] == opponent_team_id) &
        (events_df['event_type'] == 'PASS')
    ]
    opp_passes_high = sum(
        in_high_zone(row['coordinates_x'], row['period_id'])
        for _, row in opponent_passes.iterrows()
    )

    if opp_passes_high == 0:
        return 0
    return round(def_actions_high / opp_passes_high * 100, 1)


def _stat_rating(value, stat_name):
    """Map a raw stat value to a 0-5 rating (0.5 increments).
    Ranges calibrated from typical Bundesliga/PL match values."""
    ranges = {
        'start_distance': (40, 80, True),
        'progression': (5, 50, False),
        'circulation': (0.40, 0.80, False),
        'build_ups': (0, 8, False),
        'fast_breaks': (0, 8, False),
        'high_press': (15, 50, False),
    }
    if stat_name not in ranges:
        return 2.5
    lo, hi, lower_is_better = ranges[stat_name]
    norm = (value - lo) / (hi - lo) if hi != lo else 0.5
    norm = max(0, min(1, norm))
    if lower_is_better:
        norm = 1.0 - norm
    raw = norm * 5
    return round(raw * 2) / 2


def compute_match_stats(events_df, team_ids):
    """Compute all six match stats for both teams.

    Args:
        events_df: Events DataFrame from kloppy
        team_ids: [home_team_id, away_team_id]

    Returns:
        dict with stat definitions and per-team values
    """
    home_id, away_id = team_ids

    direction_map = _detect_attacking_direction(events_df, team_ids)
    for (tid, period), ar in direction_map.items():
        tag = 'Home' if tid == home_id else 'Away'
        print(f"  Direction: {tag} period {period} -> {'RIGHT' if ar else 'LEFT'}")

    home_poss = _build_possessions(events_df, home_id)
    away_poss = _build_possessions(events_df, away_id)

    stats = {}

    stats['start_distance'] = {
        'label': 'Start distance',
        'description': 'Avg distance from possession start to opponent goal (m)',
        'unit': 'm',
        'home': compute_start_distance(home_poss, direction_map, home_id),
        'away': compute_start_distance(away_poss, direction_map, away_id),
    }
    stats['start_distance']['home_rating'] = _stat_rating(stats['start_distance']['home'], 'start_distance')
    stats['start_distance']['away_rating'] = _stat_rating(stats['start_distance']['away'], 'start_distance')

    stats['progression'] = {
        'label': 'Progression',
        'description': 'Avg % of remaining distance gained per possession',
        'unit': '%',
        'home': compute_progression(home_poss, direction_map, home_id),
        'away': compute_progression(away_poss, direction_map, away_id),
    }
    stats['progression']['home_rating'] = _stat_rating(stats['progression']['home'], 'progression')
    stats['progression']['away_rating'] = _stat_rating(stats['progression']['away'], 'progression')

    stats['circulation'] = {
        'label': 'Circulation',
        'description': 'Passing indirectness (higher = more patient build-up)',
        'unit': '',
        'home': compute_circulation(events_df, home_id, direction_map),
        'away': compute_circulation(events_df, away_id, direction_map),
    }
    stats['circulation']['home_rating'] = _stat_rating(stats['circulation']['home'], 'circulation')
    stats['circulation']['away_rating'] = _stat_rating(stats['circulation']['away'], 'circulation')

    stats['build_ups'] = {
        'label': 'Build-ups',
        'description': 'Possessions with 5+ passes reaching the box',
        'unit': '',
        'home': compute_buildups(home_poss, direction_map, home_id),
        'away': compute_buildups(away_poss, direction_map, away_id),
    }
    stats['build_ups']['home_rating'] = _stat_rating(stats['build_ups']['home'], 'build_ups')
    stats['build_ups']['away_rating'] = _stat_rating(stats['build_ups']['away'], 'build_ups')

    stats['fast_breaks'] = {
        'label': 'Fast breaks',
        'description': 'Possessions reaching box within 15s from own half',
        'unit': '',
        'home': compute_fast_breaks(home_poss, direction_map, home_id),
        'away': compute_fast_breaks(away_poss, direction_map, away_id),
    }
    stats['fast_breaks']['home_rating'] = _stat_rating(stats['fast_breaks']['home'], 'fast_breaks')
    stats['fast_breaks']['away_rating'] = _stat_rating(stats['fast_breaks']['away'], 'fast_breaks')

    stats['high_press'] = {
        'label': 'High press',
        'description': 'Defensive actions in opponent half per 100 opponent passes',
        'unit': '',
        'home': compute_high_press(events_df, home_id, away_id, direction_map),
        'away': compute_high_press(events_df, away_id, home_id, direction_map),
    }
    stats['high_press']['home_rating'] = _stat_rating(stats['high_press']['home'], 'high_press')
    stats['high_press']['away_rating'] = _stat_rating(stats['high_press']['away'], 'high_press')

    return stats


def _is_progressive_pass(row, attacking_right):
    """A pass is progressive if it's >=10m long and gains >=25% of remaining x-distance."""
    x0, y0 = row['coordinates_x'], row['coordinates_y']
    x1, y1 = row['end_coordinates_x'], row['end_coordinates_y']

    if pd.isna(x0) or pd.isna(y0) or pd.isna(x1) or pd.isna(y1):
        return False

    dx = (x1 - x0) * PITCH_L
    dy = (y1 - y0) * PITCH_W
    dist = np.sqrt(dx ** 2 + dy ** 2)
    if dist < 10:
        return False

    d0 = _x_dist_to_goal(x0, attacking_right)
    d1 = _x_dist_to_goal(x1, attacking_right)

    if d0 < 5.0:
        return False
    return (d0 - d1) / d0 >= 0.25


def compute_player_stats(events_df, tracking_dataset):
    """Compute per-player statistics.

    Returns:
        dict: player_id -> {name, team_id, position, minutes, goals, assists,
                            progressive_passes, progressive_receptions,
                            defensive_actions, touches, xg, ...}
    """
    teams = tracking_dataset.metadata.teams
    home_id = teams[0].team_id
    away_id = teams[1].team_id
    team_ids = [home_id, away_id]

    direction_map = _detect_attacking_direction(events_df, team_ids)

    players = {}
    for team in teams:
        for p in team.players:
            pos_str = 'Unknown'
            if hasattr(p, 'starting_position') and p.starting_position:
                pos_str = str(p.starting_position)
            pos_abbr = _abbreviate_position(pos_str)
            jersey = getattr(p, 'jersey_no', None)
            if jersey is None:
                jersey = getattr(p, 'jersey_number', None)

            is_starter = getattr(p, 'starting', None)
            if is_starter is None:
                is_starter = True

            players[p.player_id] = {
                'id': p.player_id,
                'name': p.name if p.name else p.player_id,
                'jersey_no': jersey,
                'team_id': team.team_id,
                'position': pos_str,
                'position_abbr': pos_abbr,
                'goals': 0,
                'assists': 0,
                'progressive_passes': 0,
                'progressive_receptions': 0,
                'defensive_actions': 0,
                'touches': 0,
                'xg': 0.0,
                'minutes': 0,
                'is_starter': is_starter,
                'sub_on': None,
                'sub_off': None,
            }

    _compute_minutes(events_df, players)

    for _, row in events_df.iterrows():
        pid = row['player_id']
        if pid not in players:
            continue

        et = row['event_type']
        period = row['period_id']
        team_id = players[pid]['team_id']

        if et in ('PASS', 'SHOT', 'GENERIC:OtherBallAction', 'RECOVERY', 'FOUL_COMMITTED'):
            players[pid]['touches'] += 1

        if et == 'SHOT' and row.get('result') == 'GOAL':
            players[pid]['goals'] += 1

        if et in ('GENERIC:OtherBallAction', 'RECOVERY'):
            players[pid]['defensive_actions'] += 1

        if et == 'PASS' and row.get('result') == 'COMPLETE':
            ar = _get_attack_right(direction_map, team_id, period)
            if _is_progressive_pass(row, ar):
                players[pid]['progressive_passes'] += 1
                receiver = row.get('receiver_player_id')
                if receiver and receiver in players:
                    players[pid]['progressive_receptions'] += 1

        if et == 'SHOT':
            x = row['coordinates_x']
            if pd.notna(x):
                ar = _get_attack_right(direction_map, team_id, period)
                players[pid]['xg'] += _positional_xg(x, row['coordinates_y'], ar)

    _compute_assists(events_df, players)

    return players


def _compute_minutes(events_df, players):
    """Compute minutes played from substitution events and match duration.

    Uses the is_starter flag already set from kloppy metadata (p.starting).
    Only detects sub_on/sub_off times from SUBSTITUTION events.
    """
    subs = events_df[events_df['event_type'] == 'SUBSTITUTION'].sort_values('timestamp')

    for _, sub in subs.iterrows():
        pid = sub['player_id']
        if pid not in players:
            continue
        ts = sub['timestamp'].total_seconds()
        period = sub['period_id']
        minute = int((ts + (45 * 60 if period == 2 else 0)) / 60)

        if players[pid]['is_starter']:
            players[pid]['sub_off'] = minute
        else:
            players[pid]['sub_on'] = minute

    # For non-starters not found in SUBSTITUTION events, try first event time
    for pid, p in players.items():
        if not p['is_starter'] and p['sub_on'] is None:
            player_events = events_df[events_df['player_id'] == pid]
            if len(player_events) > 0:
                first_event = player_events.iloc[0]
                first_ts = first_event['timestamp'].total_seconds()
                first_period = first_event['period_id']
                p['sub_on'] = int((first_ts + (45 * 60 if first_period == 2 else 0)) / 60)

    match_duration = 90
    last_event = events_df.sort_values('timestamp').iloc[-1]
    last_ts = last_event['timestamp'].total_seconds()
    last_period = last_event['period_id']
    if last_period == 2:
        match_duration = int((last_ts + 45 * 60) / 60)

    for pid, p in players.items():
        if not p['is_starter'] and p['sub_on'] is None:
            p['minutes'] = 0
            continue

        start = p['sub_on'] if p['sub_on'] is not None else 0
        end = p['sub_off'] if p['sub_off'] is not None else match_duration
        p['minutes'] = max(0, end - start)


def _compute_assists(events_df, players):
    """Find assists: the last pass before a goal."""
    sorted_events = events_df.sort_values('timestamp').reset_index(drop=True)

    for idx, row in sorted_events.iterrows():
        if row['event_type'] == 'SHOT' and row.get('result') == 'GOAL':
            team = row['team_id']
            for j in range(idx - 1, max(idx - 10, -1), -1):
                prev = sorted_events.iloc[j]
                if prev['team_id'] != team:
                    break
                if prev['event_type'] == 'PASS' and prev.get('result') == 'COMPLETE':
                    if prev['player_id'] in players:
                        players[prev['player_id']]['assists'] += 1
                    break


def _positional_xg(x, y, attacking_right):
    """Simple positional xG model based on distance and angle to goal."""
    if pd.isna(x) or pd.isna(y):
        return 0.0

    gx = 1.0 if attacking_right else 0.0
    dist = _dist_to_goal(x, y, attacking_right)

    if dist < 1:
        return 0.5
    angle = np.degrees(np.arctan2(7.32 / 2, dist))
    xg = max(0.01, min(0.95, 0.8 * (angle / 90) ** 1.5))
    return round(xg, 3)


def _abbreviate_position(pos_str):
    """Convert kloppy position strings to short abbreviations."""
    mapping = {
        'Goalkeeper': 'GK',
        'Right Back': 'RB',
        'Left Back': 'LB',
        'Right Center Back': 'RCB',
        'Left Center Back': 'LCB',
        'Center Back': 'CB',
        'Right Defensive Midfield': 'RDM',
        'Left Defensive Midfield': 'LDM',
        'Right Midfield': 'RM',
        'Left Midfield': 'LM',
        'Center Midfield': 'CM',
        'Right Wing': 'RW',
        'Left Wing': 'LW',
        'Center Attacking Midfield': 'CAM',
        'Striker': 'ST',
        'Right Center Midfield': 'RCM',
        'Left Center Midfield': 'LCM',
    }
    return mapping.get(pos_str, pos_str[:3].upper() if pos_str != 'Unknown' else '')


def compute_all(events_df, tracking_dataset):
    """Main entry point. Returns (match_stats, player_stats)."""
    teams = tracking_dataset.metadata.teams
    team_ids = [teams[0].team_id, teams[1].team_id]

    print("\n" + "=" * 80)
    print("STEP 9: COMPUTE MATCH & PLAYER STATS")
    print("=" * 80)

    print("\nComputing match stats...")
    match_stats = compute_match_stats(events_df, team_ids)

    for key, stat in match_stats.items():
        print(f"  {stat['label']}: {stat['home']} (home) vs {stat['away']} (away)")

    print("\nComputing player stats...")
    player_stats = compute_player_stats(events_df, tracking_dataset)

    active = {k: v for k, v in player_stats.items() if v['minutes'] > 0}
    print(f"  {len(active)} players with minutes played")

    return match_stats, player_stats


if __name__ == "__main__":
    import sys
    sys.path.insert(0, '.')
    from pipeline import load_match_data
    print("Run as part of the pipeline.")
