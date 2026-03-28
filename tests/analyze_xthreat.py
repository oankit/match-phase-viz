"""
Analyze xThreat model to identify issues
"""
import json
import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Load phases data with xThreat
phases_path = Path('../output/J03WN1/phases.json')
with open(phases_path, 'r') as f:
    phases_data = json.load(f)

# Convert to DataFrame
phases_df = pd.DataFrame(phases_data)

print("=" * 80)
print("xTHREAT MODEL ANALYSIS")
print("=" * 80)

# Overall xThreat statistics
print("\nOverall xThreat statistics:")
print(f"  Phases with non-zero xThreat: {((phases_df['xthreat_gained'] != 0) | (phases_df['xthreat_conceded'] != 0)).sum()} / {len(phases_df)}")
print(f"  Total xThreat gained: {phases_df['xthreat_gained'].sum():.3f}")
print(f"  Total xThreat conceded: {phases_df['xthreat_conceded'].sum():.3f}")

# xThreat by phase type
print("\nxThreat by phase type:")
for phase_type in phases_df['type'].unique():
    type_phases = phases_df[phases_df['type'] == phase_type]
    gained = type_phases['xthreat_gained']
    conceded = type_phases['xthreat_conceded']

    print(f"\n  {phase_type}:")
    print(f"    Phases: {len(type_phases)}")
    print(f"    Avg gained: {gained.mean():.4f} (max: {gained.max():.4f})")
    print(f"    Avg conceded: {conceded.mean():.4f} (min: {conceded.min():.4f})")
    print(f"    Net xThreat: {(gained.sum() + conceded.sum()):.4f}")

# xThreat by team
print("\nxThreat by team:")
for team in phases_df['team'].unique():
    team_phases = phases_df[phases_df['team'] == team]
    print(f"\n  {team}:")
    print(f"    Total gained: {team_phases['xthreat_gained'].sum():.3f}")
    print(f"    Total conceded: {team_phases['xthreat_conceded'].sum():.3f}")
    print(f"    Net: {(team_phases['xthreat_gained'].sum() + team_phases['xthreat_conceded'].sum()):.3f}")

print("\n" + "=" * 80)
print("POTENTIAL xTHREAT ISSUES:")
print("=" * 80)

issues = []

# Issue 1: Zero xThreat in active phases
active_phases = phases_df[phases_df['type'].isin(['high_press', 'counter_attack'])]
zero_xthreat_active = active_phases[(active_phases['xthreat_gained'] == 0) & (active_phases['xthreat_conceded'] == 0)]
if len(zero_xthreat_active) > 0:
    pct = len(zero_xthreat_active) / len(active_phases) * 100
    print(f"\n1. Zero xThreat in active phases:")
    print(f"   - {len(zero_xthreat_active)} / {len(active_phases)} ({pct:.1f}%) high_press/counter phases have zero xThreat")
    print(f"   - This suggests events may not be properly linked to phases")
    issues.append("Zero xThreat in active phases")

# Issue 2: Suspiciously high xThreat values
high_xthreat = phases_df[phases_df['xthreat_gained'] > 1.0]
if len(high_xthreat) > 0:
    print(f"\n2. Suspiciously high xThreat values:")
    print(f"   - {len(high_xthreat)} phases with xThreat > 1.0")
    print(f"   - Max value: {phases_df['xthreat_gained'].max():.3f}")
    print(f"   - xThreat should typically be 0-0.2 per action")
    issues.append("xThreat values too high")

# Issue 3: Imbalanced xThreat (gained vs conceded)
total_gained = phases_df['xthreat_gained'].sum()
total_conceded = abs(phases_df['xthreat_conceded'].sum())
if total_gained > 0 and total_conceded > 0:
    ratio = total_gained / total_conceded
    print(f"\n3. xThreat balance:")
    print(f"   - Total gained: {total_gained:.3f}")
    print(f"   - Total conceded: {total_conceded:.3f}")
    print(f"   - Ratio: {ratio:.2f}")
    if ratio > 2 or ratio < 0.5:
        print(f"   - WARNING: Imbalanced ratio suggests calculation issue")
        issues.append("Imbalanced gained/conceded ratio")

# Issue 4: Check if xThreat correlates with expected patterns
print(f"\n4. xThreat patterns check:")

# High press should generate positive xThreat
hp_phases = phases_df[phases_df['type'] == 'high_press']
if len(hp_phases) > 0:
    hp_positive = hp_phases[hp_phases['xthreat_gained'] > 0]
    pct = len(hp_positive) / len(hp_phases) * 100
    print(f"   - High press with positive xThreat: {len(hp_positive)}/{len(hp_phases)} ({pct:.1f}%)")
    if pct < 50:
        issues.append("High press not generating xThreat")

# Defensive blocks should have negative or zero xThreat
db_phases = phases_df[phases_df['type'] == 'defensive_block']
if len(db_phases) > 0:
    db_negative = db_phases[db_phases['xthreat_conceded'] < 0]
    pct = len(db_negative) / len(db_phases) * 100
    print(f"   - Defensive blocks conceding xThreat: {len(db_negative)}/{len(db_phases)} ({pct:.1f}%)")

# Issue 5: Linear position model check
print(f"\n5. Linear position model analysis:")
print(f"   - Current model: linear based on x-position only")
print(f"   - Issues with this approach:")
print(f"     * Doesn't account for y-position (wide vs central)")
print(f"     * No consideration of game state")
print(f"     * Ignores player density around ball")

print("\n" + "=" * 80)
print("RECOMMENDATIONS:")
print("=" * 80)

print("\n1. xThreat Model Improvements:")
print("   - Switch from linear to zone-based model (12x8 grid)")
print("   - Use actual transition probabilities from StatsBomb data")
print("   - Weight central zones higher than wide zones")
print("   - Consider shot probability from each zone")

print("\n2. Event-Phase Linking:")
print("   - Ensure events are properly assigned to phase segments")
print("   - Check timestamp alignment between tracking and events")
print("   - Verify ball possession changes trigger xThreat updates")

print("\n3. Calibration suggestions:")
print("   - Expected xThreat per possession: 0.01-0.05")
print("   - High press phases should average: +0.02-0.10")
print("   - Defensive block phases should average: -0.01 to -0.05")
print("   - Counter-attacks should show highest gains: +0.10-0.30")

if len(issues) > 0:
    print(f"\n4. Priority fixes needed for: {', '.join(issues)}")