# Final Analysis Summary

## Date: March 27, 2026

## Executive Summary

Successfully validated Rest Defence implementation and identified key issues with phase detection and xThreat model. Applied refinements to improve phase detection, though further calibration needed.

---

## 1. Rest Defence Validation ✅ COMPLETE

**Implementation Status: Working Perfectly**

- Modified `04_compute_voronoi.py` to implement time-to-intercept model
- Creates 40x25 grid inside attacking team's convex hull
- Shows 94.9% control by attacking team, 5.1% vulnerable gaps
- Successfully reveals defensive vulnerabilities for counter-attack analysis

---

## 2. Phase Detection Analysis & Refinement

### Initial Issues (184 phases):
- Only 1 counter-attack detected (way too few)
- 17 high press phases (under-detected)
- 93 open play phases (50% of match - too dominant)
- 73 defensive blocks (reasonable but could be more selective)

### After First Refinement (90 phases):
- **Problem**: Lost ALL high press detection (0 phases)
- Counter-attacks still at 1 (no improvement)
- Better phase consolidation (184→90)
- Less open play dominance

### Final Balanced Thresholds (config.py v2):
```python
'high_press': {
    'def_line_height_min': 0.40,  # 42m, middle ground
    'ball_x_min': 0.48,  # Slightly into opponent half
    'pressure_proxy_min': 1,  # Not too restrictive
}
'defensive_block': {
    'def_line_height_max': 0.30,  # Keep tight
    'compactness_max': 0.18,  # Slightly relaxed
    'ball_x_max': 0.45,  # Own defensive third
}
```

---

## 3. xThreat Model Issues

### Critical Problems Identified:
1. **Values too high**: Max 1.491 (should be ~0.2)
2. **Sign errors**: Negative gains appearing
3. **Poor correlation**: Only 29% of high press generates positive xThreat
4. **Linear model flaws**: Only uses x-position, ignores context

### Root Cause:
Current simplified linear model is inadequate. Need zone-based approach.

---

## 4. Recommendations for Next Steps

### Immediate Actions:

1. **Test balanced thresholds** (config.py v2)
   - Run pipeline again
   - Expect 20-30 high press phases
   - Expect 3-7 counter-attacks

2. **Implement zone-based xThreat**
   ```python
   # Replace linear model in 07_compute_xthreat.py
   def compute_zone_xthreat(x, y):
       zone_x = int(x * 12)
       zone_y = int(y * 8)
       central_weight = 1.0 - abs(y - 0.5) * 0.5
       base_threat = ZONE_MATRIX[zone_x, zone_y]
       return base_threat * central_weight
   ```

3. **Fix counter-attack detection**
   - Check if RECOVERY events actually exist in data
   - Consider using ball possession changes instead
   - May need to detect from tracking data not events

### Testing Protocol:

1. Run pipeline with balanced thresholds on J03WN1
2. Verify phase distribution looks reasonable:
   - High press: 20-30 phases
   - Defensive block: 40-60 phases
   - Counter-attack: 3-7 phases
   - Open play: < 40% of total

3. If validated, process all 7 matches

---

## 5. Dashboard Status

**Frontend**: Running at http://localhost:3000
- Timeline ✅
- PitchCanvas ✅
- Rest Defence overlay ✅
- MetricPanel ✅
- Phase filtering ✅

**Data**: J03WN1 loaded
- 2736 frames (1 Hz test mode)
- 90 phases (needs reprocessing with v2 thresholds)
- Rest Defence working

---

## 6. Files Modified Today

1. `pipeline/config.py` - Refined phase thresholds (v2)
2. `pipeline/04_compute_voronoi.py` - Added Rest Defence
3. `tests/validate_rest_defence.py` - Created for validation
4. `tests/analyze_phases.py` - Created for phase analysis
5. `tests/analyze_xthreat.py` - Created for xThreat analysis
6. `docs/IMPLEMENTATION.md` - Updated with progress
7. `docs/ANALYSIS_REPORT.md` - Created with findings

---

## 7. Critical Insights

### What's Working:
- Rest Defence visualization reveals tactical gaps effectively
- Pipeline runs end-to-end successfully
- Frontend displays all visualizations
- Phase detection logic is sound, just needs threshold calibration

### What Needs Work:
- Counter-attack detection (event-based approach may be wrong)
- xThreat model (linear approach fundamentally flawed)
- High press threshold calibration (very sensitive to parameters)

### Key Learning:
Phase detection is highly sensitive to threshold values. The difference between 0 and 17 high press phases was just 0.02 in defensive line height and 1 player in pressure proxy. This suggests:
1. Need match-specific or team-specific calibration
2. Consider machine learning approach for phase classification
3. Visual validation essential for threshold tuning

---

## Next Session Priority:

1. Test config.py v2 thresholds
2. If high press detected (target: 20-30), proceed
3. If not, implement adaptive thresholds
4. Replace xThreat with zone-based model
5. Process all 7 matches