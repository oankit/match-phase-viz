"""Diagnose match stats computation issues."""
import sys
sys.path.insert(0, '../../pipeline')

from kloppy import sportec
from pathlib import Path
import pandas as pd
import numpy as np
import config

data_path = Path('../../data')
meta_file = list(data_path.glob('*matchinformation*J03WN1.xml'))[0]
event_file = list(data_path.glob('*events_raw*J03WN1.xml'))[0]

print("Loading data...")
event_dataset = sportec.load_event(
    event_data=str(event_file),
    meta_data=str(meta_file),
    coordinates='kloppy'
)
events_df = event_dataset.to_df()

teams = event_dataset.metadata.teams
home_id = teams[0].team_id
away_id = teams[1].team_id
print(f"Home: {teams[0].name} ({home_id})")
print(f"Away: {teams[1].name} ({away_id})")

from importlib import util
spec = util.spec_from_file_location("stats", "../../pipeline/09_compute_match_stats.py")
stats_mod = util.module_from_spec(spec)
spec.loader.exec_module(stats_mod)

# ============================================================
# 1. POSSESSIONS ANALYSIS
# ============================================================
print("\n" + "=" * 60)
print("POSSESSION ANALYSIS")
print("=" * 60)

home_poss = stats_mod._build_possessions(events_df, home_id)
away_poss = stats_mod._build_possessions(events_df, away_id)

print(f"\nHome possessions: {len(home_poss)}")
print(f"Away possessions: {len(away_poss)}")

# Possession length distribution
home_lens = [len(p) for p in home_poss]
away_lens = [len(p) for p in away_poss]
print(f"\nHome poss lengths: min={min(home_lens)}, max={max(home_lens)}, "
      f"mean={np.mean(home_lens):.1f}, median={np.median(home_lens):.0f}")
print(f"Away poss lengths: min={min(away_lens)}, max={max(away_lens)}, "
      f"mean={np.mean(away_lens):.1f}, median={np.median(away_lens):.0f}")

# Pass-only count per possession
home_pass_counts = [len(p[p['event_type'] == 'PASS']) for p in home_poss]
away_pass_counts = [len(p[p['event_type'] == 'PASS']) for p in away_poss]
print(f"\nHome passes per poss: min={min(home_pass_counts)}, max={max(home_pass_counts)}, "
      f"mean={np.mean(home_pass_counts):.1f}")
print(f"Away passes per poss: min={min(away_pass_counts)}, max={max(away_pass_counts)}, "
      f"mean={np.mean(away_pass_counts):.1f}")

# ============================================================
# 2. PROGRESSION ANALYSIS
# ============================================================
print("\n" + "=" * 60)
print("PROGRESSION ANALYSIS")
print("=" * 60)

PITCH_L = config.PITCH_LENGTH
PITCH_W = config.PITCH_WIDTH

def debug_progression(possessions, attacking_right, label):
    progs = []
    issues = {'no_coords': 0, 'short_dist': 0, 'backward': 0, 'forward': 0}
    for poss in possessions:
        first = poss.iloc[0]
        last_with_coords = poss[poss['coordinates_x'].notna()]
        if len(last_with_coords) < 2:
            issues['no_coords'] += 1
            continue
        last_action = last_with_coords.iloc[-1]
        x0, y0 = first['coordinates_x'], first['coordinates_y']
        x1, y1 = last_action['coordinates_x'], last_action['coordinates_y']
        if pd.isna(x0) or pd.isna(y0):
            issues['no_coords'] += 1
            continue
        d0 = stats_mod._dist_to_goal(x0, y0, attacking_right)
        d1 = stats_mod._dist_to_goal(x1, y1, attacking_right)
        if d0 <= 5.0:
            issues['short_dist'] += 1
            continue
        prog = (d0 - d1) / d0 * 100
        prog = max(-100, min(100, prog))
        progs.append(prog)
        if prog < 0:
            issues['backward'] += 1
        else:
            issues['forward'] += 1

    print(f"\n{label}:")
    print(f"  Total poss: {len(possessions)}")
    print(f"  No coords: {issues['no_coords']}")
    print(f"  Short dist (d0<=5m): {issues['short_dist']}")
    print(f"  Forward: {issues['forward']}, Backward: {issues['backward']}")
    if progs:
        print(f"  Progression values: mean={np.mean(progs):.1f}%, "
              f"median={np.median(progs):.1f}%, "
              f"min={min(progs):.1f}%, max={max(progs):.1f}%")

        # Show distribution
        bins = [(-100,-50), (-50,-20), (-20,-10), (-10,0), (0,10), (10,20), (20,50), (50,100)]
        for lo, hi in bins:
            count = sum(1 for p in progs if lo <= p < hi)
            print(f"    [{lo:4d},{hi:4d}): {count}")

    # Show some backward possessions
    print(f"\n  Sample backward possessions:")
    shown = 0
    for poss in possessions:
        first = poss.iloc[0]
        last_with_coords = poss[poss['coordinates_x'].notna()]
        if len(last_with_coords) < 2:
            continue
        last_action = last_with_coords.iloc[-1]
        x0, y0 = first['coordinates_x'], first['coordinates_y']
        x1, y1 = last_action['coordinates_x'], last_action['coordinates_y']
        if pd.isna(x0) or pd.isna(y0):
            continue
        d0 = stats_mod._dist_to_goal(x0, y0, attacking_right)
        d1 = stats_mod._dist_to_goal(x1, y1, attacking_right)
        if d0 <= 5.0:
            continue
        prog = (d0 - d1) / d0 * 100
        if prog < -20 and shown < 5:
            shown += 1
            types = list(poss['event_type'].values)
            print(f"    Poss: {len(poss)} events, types={types}")
            print(f"      Start: ({x0:.2f},{y0:.2f}) d0={d0:.1f}m")
            print(f"      End:   ({x1:.2f},{y1:.2f}) d1={d1:.1f}m  prog={prog:.1f}%")
            # Check x-direction progression
            if attacking_right:
                x_prog = (x1 - x0) * PITCH_L
            else:
                x_prog = (x0 - x1) * PITCH_L
            print(f"      X-direction gain: {x_prog:.1f}m")

debug_progression(home_poss, True, "HOME (attacking right)")
debug_progression(away_poss, False, "AWAY (attacking left)")

# ============================================================
# 3. BUILD-UP ANALYSIS
# ============================================================
print("\n" + "=" * 60)
print("BUILD-UP ANALYSIS")
print("=" * 60)

# Possessions with 5+ passes, 6+, 7+, 8+
for threshold in [4, 5, 6, 7, 8]:
    home_count = sum(1 for p in home_poss if len(p[p['event_type'] == 'PASS']) >= threshold)
    away_count = sum(1 for p in away_poss if len(p[p['event_type'] == 'PASS']) >= threshold)
    print(f"  Poss with {threshold}+ passes: home={home_count}, away={away_count}")

# Check which ones reach the box
for threshold in [4, 5, 6, 8]:
    home_in_box = 0
    away_in_box = 0
    for poss in home_poss:
        if len(poss[poss['event_type'] == 'PASS']) < threshold:
            continue
        for _, ev in poss.iterrows():
            x, y = ev['coordinates_x'], ev['coordinates_y']
            if pd.notna(x) and pd.notna(y) and stats_mod._in_box(x, y, True):
                home_in_box += 1
                break
    for poss in away_poss:
        if len(poss[poss['event_type'] == 'PASS']) < threshold:
            continue
        for _, ev in poss.iterrows():
            x, y = ev['coordinates_x'], ev['coordinates_y']
            if pd.notna(x) and pd.notna(y) and stats_mod._in_box(x, y, False):
                away_in_box += 1
                break
    print(f"  {threshold}+ passes AND reach box: home={home_in_box}, away={away_in_box}")

# ============================================================
# 4. FAST BREAKS ANALYSIS
# ============================================================
print("\n" + "=" * 60)
print("FAST BREAKS ANALYSIS")
print("=" * 60)

def debug_fast_breaks(possessions, attacking_right, label):
    deep_threshold = 0.40 if attacking_right else 0.60
    count = 0
    had_deep_touch = 0
    had_box_entry = 0

    for poss in possessions:
        deep_touch_time = None
        for _, ev in poss.iterrows():
            x = ev['coordinates_x']
            if pd.isna(x):
                continue
            is_deep = (x <= deep_threshold) if attacking_right else (x >= deep_threshold)
            if is_deep:
                deep_touch_time = ev['timestamp']
                break

        if deep_touch_time is None:
            continue
        had_deep_touch += 1

        found = False
        for _, ev in poss.iterrows():
            x, y = ev['coordinates_x'], ev['coordinates_y']
            if pd.isna(x) or pd.isna(y):
                continue
            dt = (ev['timestamp'] - deep_touch_time).total_seconds()
            if dt > 15:
                break
            if stats_mod._in_box(x, y, attacking_right):
                found = True
                break

        if found:
            count += 1
            had_box_entry += 1

    print(f"\n{label}:")
    print(f"  Total possessions: {len(possessions)}")
    print(f"  Had deep touch (x<={deep_threshold if attacking_right else ''}): {had_deep_touch}")
    print(f"  Reached box within 15s: {count}")

debug_fast_breaks(home_poss, True, "HOME fast breaks")
debug_fast_breaks(away_poss, False, "AWAY fast breaks")

# ============================================================
# 5. EVENT TYPE DISTRIBUTION
# ============================================================
print("\n" + "=" * 60)
print("EVENT ANALYSIS")
print("=" * 60)
print("\nEvent types:")
print(events_df['event_type'].value_counts())
print(f"\nTotal PASS events: {len(events_df[events_df['event_type'] == 'PASS'])}")
print(f"Home passes: {len(events_df[(events_df['event_type'] == 'PASS') & (events_df['team_id'] == home_id)])}")
print(f"Away passes: {len(events_df[(events_df['event_type'] == 'PASS') & (events_df['team_id'] == away_id)])}")

# Check coordinate availability
passes = events_df[events_df['event_type'] == 'PASS']
print(f"\nPasses with start coords: {passes['coordinates_x'].notna().sum()}")
print(f"Passes with end coords: {passes['end_coordinates_x'].notna().sum()}")

# Check coordinate ranges
print(f"\nCoordinate ranges:")
print(f"  x: [{events_df['coordinates_x'].min():.3f}, {events_df['coordinates_x'].max():.3f}]")
print(f"  y: [{events_df['coordinates_y'].min():.3f}, {events_df['coordinates_y'].max():.3f}]")
