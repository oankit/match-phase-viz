# Phase Detection & xThreat Analysis Report

## Date: March 27, 2026

## Summary

Completed validation of Rest Defence implementation and analyzed phase detection + xThreat model using match J03WN1. Found several issues requiring refinement.

## 1. Rest Defence Validation ✓

**Status: Working correctly**

- All 2736 frames have control grid data
- Grid resolution: 40x25 points inside attacking team's convex hull
- Shows pitch control: 94.9% attacking team, 5.1% defending team
- Successfully reveals defensive vulnerabilities

## 2. Phase Detection Issues

### Current Distribution
- **Open play**: 93 phases (50.5%) - Too dominant
- **Defensive block**: 73 phases (39.7%) - Reasonable
- **High press**: 17 phases (9.2%) - May be under-detected
- **Counter-attack**: 1 phase (0.5%) - Severely under-detected

### Key Problems

1. **Counter-attacks almost missing** (only 1 detected)
   - Event-based detection failing
   - Need to verify RECOVERY events exist
   - Consider lowering thresholds

2. **Very short phases** (13 phases < 5 seconds)
   - Smoothing not working properly
   - Need better merging logic

3. **Very long open_play** (3 phases > 2 minutes)
   - Missing transitions to tactical phases
   - Thresholds may be too restrictive

4. **High press under-detection**
   - defensive_line_height > 0.43 too restrictive
   - Only 29% generate positive xThreat (should be 70%+)

## 3. xThreat Model Issues

### Current Problems

1. **Values too high**
   - Max: 1.491 (should be ~0.2 max per action)
   - Linear model overvaluing distance

2. **Sign confusion**
   - Negative values for gained xThreat
   - Teams showing negative gains

3. **Poor correlation with phases**
   - High press: only 29% positive xThreat
   - Should be 70%+ for effective pressing

4. **Linear model limitations**
   - Only uses x-position
   - Ignores y-position (wide vs central)
   - No consideration of game context

## 4. Recommended Refinements

### Phase Detection Fixes

```python
# config.py adjustments
PHASE_THRESHOLDS = {
    'high_press': {
        'def_line_height_min': 0.38,  # Lowered from 0.43
        'ball_x_min': 0.45,  # Lowered from 0.5
        'pressure_proxy_min': 2,  # Raised from 1
    },
    'defensive_block': {
        'def_line_height_max': 0.30,  # Lowered from 0.33
        'compactness_max': 0.15,  # Lowered from 0.20
        'ball_x_max': 0.45,  # Lowered from 0.5
    },
}

COUNTERATTACK_RULES = {
    'forward_distance_min': 0.071,  # Lowered from 0.095 (7.5m)
    'forward_velocity_min': 0.028,  # Lowered from 0.038 (3 m/s)
    # ... rest unchanged
}
```

### xThreat Model Replacement

Replace linear model with zone-based approach:

```python
# 07_compute_xthreat.py
def compute_zone_xthreat(x, y):
    """Zone-based xThreat using 12x8 grid"""
    # Divide pitch into zones
    zone_x = int(x * 12)
    zone_y = int(y * 8)

    # Use pre-computed transition matrix
    # Central zones weighted higher
    central_weight = 1.0 - abs(y - 0.5) * 0.5

    # Base values from StatsBomb
    base_xthreat = ZONE_XTHREAT_MATRIX[zone_x, zone_y]

    return base_xthreat * central_weight
```

## 5. Testing Plan

1. Apply phase threshold adjustments
2. Re-run pipeline on J03WN1
3. Verify:
   - Counter-attacks: Should detect 5-10
   - High press: Should detect 25-35
   - xThreat values: 0.01-0.20 range
4. Test on second match (J03WMX)
5. If validated, process all 7 matches

## 6. Next Steps

1. ✓ Rest Defence validation complete
2. ✓ Phase detection issues identified
3. ✓ xThreat model problems identified
4. **In Progress**: Refining phase thresholds
5. **Pending**: Implement zone-based xThreat
6. **Pending**: Test refinements
7. **Pending**: Process all matches

---

*Dashboard running at http://localhost:3000 with J03WN1 data*