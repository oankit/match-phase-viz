"""
Analyze phase detection to identify issues
"""
import json
import sys
from pathlib import Path
import pandas as pd

# Load phases data
phases_path = Path('../output/J03WN1/phases.json')
with open(phases_path, 'r') as f:
    phases_data = json.load(f)

# Convert to DataFrame for analysis
phases_df = pd.DataFrame(phases_data)

print("=" * 80)
print("PHASE DETECTION ANALYSIS")
print("=" * 80)

# Overall statistics
print(f"\nTotal phases: {len(phases_df)}")
print(f"Match duration: {phases_df['end'].max():.1f} seconds")

# Phase type distribution
print("\nPhase type distribution:")
phase_counts = phases_df['type'].value_counts()
for phase_type, count in phase_counts.items():
    percentage = count / len(phases_df) * 100
    print(f"  {phase_type}: {count} ({percentage:.1f}%)")

# Duration statistics by phase type
print("\nDuration statistics by phase type (seconds):")
for phase_type in phases_df['type'].unique():
    type_phases = phases_df[phases_df['type'] == phase_type]
    durations = type_phases['duration']
    print(f"\n  {phase_type}:")
    print(f"    Count: {len(type_phases)}")
    print(f"    Mean: {durations.mean():.1f}s")
    print(f"    Median: {durations.median():.1f}s")
    print(f"    Min: {durations.min():.1f}s")
    print(f"    Max: {durations.max():.1f}s")

# Team balance
print("\nPhases by team:")
team_counts = phases_df['team'].value_counts()
for team, count in team_counts.items():
    percentage = count / len(phases_df) * 100
    print(f"  {team}: {count} ({percentage:.1f}%)")

# Potential issues
print("\n" + "=" * 80)
print("POTENTIAL ISSUES DETECTED:")
print("=" * 80)

issues = []

# Issue 1: Very short phases
short_phases = phases_df[phases_df['duration'] < 5.0]
if len(short_phases) > 0:
    issues.append(f"1. Found {len(short_phases)} phases shorter than 5 seconds")
    print(f"\n1. Very short phases ({len(short_phases)} found):")
    for _, phase in short_phases.head(3).iterrows():
        print(f"   - {phase['type']} (team {phase['team']}): {phase['duration']:.1f}s")

# Issue 2: Very long open_play phases
long_open_play = phases_df[(phases_df['type'] == 'open_play') & (phases_df['duration'] > 120)]
if len(long_open_play) > 0:
    issues.append(f"2. Found {len(long_open_play)} open_play phases longer than 2 minutes")
    print(f"\n2. Very long open_play phases ({len(long_open_play)} found):")
    for _, phase in long_open_play.head(3).iterrows():
        print(f"   - Duration: {phase['duration']:.1f}s (team {phase['team']})")

# Issue 3: Rare counter-attacks
counter_attacks = phases_df[phases_df['type'] == 'counter_attack']
if len(counter_attacks) < 5:
    issues.append(f"3. Only {len(counter_attacks)} counter-attacks detected (seems low)")
    print(f"\n3. Counter-attacks: Only {len(counter_attacks)} detected")
    if len(counter_attacks) > 0:
        print(f"   - Mean duration: {counter_attacks['duration'].mean():.1f}s")

# Issue 4: Unbalanced high press
high_press_by_team = phases_df[phases_df['type'] == 'high_press'].groupby('team').size()
if len(high_press_by_team) > 0 and high_press_by_team.max() / high_press_by_team.min() > 3:
    issues.append("4. Unbalanced high press detection between teams")
    print(f"\n4. High press imbalance:")
    for team, count in high_press_by_team.items():
        print(f"   - {team}: {count} phases")

# Issue 5: Check defensive metrics
print("\n5. Defensive metrics check:")
defensive_phases = phases_df[phases_df['type'] == 'defensive_block']
if len(defensive_phases) > 0:
    print(f"   - Defensive blocks: {len(defensive_phases)}")
    print(f"   - Mean defensive line height: {defensive_phases['defensive_line_height'].mean():.3f}")
    print(f"   - Mean compactness: {defensive_phases['compactness'].mean():.3f}")

# Issue 6: xThreat values
print("\n6. xThreat analysis:")
phases_with_xthreat = phases_df[(phases_df['xthreat_gained'] != 0) | (phases_df['xthreat_conceded'] != 0)]
print(f"   - Phases with xThreat: {len(phases_with_xthreat)} / {len(phases_df)}")
if len(phases_with_xthreat) > 0:
    print(f"   - Max xThreat gained: {phases_df['xthreat_gained'].max():.3f}")
    print(f"   - Max xThreat conceded: {abs(phases_df['xthreat_conceded'].min()):.3f}")

print("\n" + "=" * 80)
print("RECOMMENDATIONS:")
print("=" * 80)

if len(long_open_play) > 10:
    print("\n- Too many long open_play phases - consider tightening phase detection thresholds")

if len(counter_attacks) < 5:
    print("\n- Counter-attacks seem under-detected - check event-based rules:")
    print("  * Verify 'RECOVERY' events exist in data")
    print("  * Consider lowering forward distance/velocity thresholds")

if len(high_press_by_team) > 0:
    print("\n- High press detection may need calibration:")
    print("  * Check if defensive_line_height > 0.43 is too restrictive")
    print("  * Consider team-specific adjustments")

print("\n- Consider visual inspection at these timestamps for validation:")
suggested_times = []
if len(defensive_phases) > 0:
    suggested_times.append(f"  * {defensive_phases.iloc[0]['start']:.1f}s - Defensive block")
if len(high_press_by_team) > 0:
    hp = phases_df[phases_df['type'] == 'high_press'].iloc[0]
    suggested_times.append(f"  * {hp['start']:.1f}s - High press")
if len(counter_attacks) > 0:
    suggested_times.append(f"  * {counter_attacks.iloc[0]['start']:.1f}s - Counter-attack")

for suggestion in suggested_times[:3]:
    print(suggestion)