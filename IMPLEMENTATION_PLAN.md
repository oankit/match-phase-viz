# Implementation Plan: Phase-Aware Soccer Analytics Dashboard

## 1. Architecture Overview

```
Python pipeline (run once per match)       React + D3.js frontend (loads static JSON)
┌──────────────────────────────┐           ┌─────────────────────────────────┐
│ Sportec/DFL via kloppy       │           │ Timeline + phase annotations    │
│ ↓                            │           │ Pitch canvas + Voronoi overlay  │
│ Sliding-window features      │  ──JSON─→ │ Formation fluidity glyph        │
│ ↓                            │           │ Pressing intensity heatmap      │
│ Two-path phase classifier    │           │ Compactness gauge               │
│ ↓                            │           │ Metric cards (phase-filtered)   │
│ Derived metrics + export     │           │ Brushing + linking interactions │
└──────────────────────────────┘           └─────────────────────────────────┘
```

No backend. Python produces JSON once, React renders it. Deploy on GitHub Pages or Vercel.

## 2. Data Sources

**Primary**: Sportec/DFL IDSSE dataset (Bassek et al. 2025, DOI: 10.1038/s41597-025-04505-y). 7 Bundesliga matches, 25 Hz optical tracking + synchronized event data. CC BY 4.0.

**Supplementary**: StatsBomb Open Data (github.com/statsbomb/open-data). 3000+ matches of event data for robust xThreat estimation.

**Loading**: `kloppy` Python library handles DFL format natively, normalizes coordinates to 0-105m (x) by 0-68m (y).

### Data Access Methods

1. **Figshare (direct download)**: https://springernature.figshare.com/articles/dataset/An_integrated_dataset_of_spatiotemporal_and_event_data_in_elite_soccer/28196177
2. **kloppy (programmatic, recommended)**: `sportec.load_idsse(match_id="J03WMX", data_type="tracking")` / `data_type="event"`. Auto-downloads data.
3. **Companion GitHub repo**: https://github.com/spoho-datascience/idsse-data — reference code for XML parsing.
4. **Floodlight fallback**: `from floodlight.io.datasets import IDSSEDataset` — the paper's companion repo uses this.

### Known Match IDs

| Match ID | Home | Away |
|---|---|---|
| J03WMX | 1. FC Köln | FC Bayern München |
| J03WN1 | VfL Bochum 1848 | Bayer 04 Leverkusen |
| J03WPY | Fortuna Düsseldorf | TBD (2nd division) |
| *(+4 more)* | Discover from kloppy source or Figshare | |

## 3. Project Structure

```
soccer-dashboard/
├── CLAUDE.md
├── pipeline/
│   ├── 01_load_data.py
│   ├── 02_compute_features.py
│   ├── 03_classify_phases.py
│   ├── 04_compute_voronoi.py
│   ├── 05_compute_formations.py
│   ├── 06_compute_pressing.py
│   ├── 07_compute_xthreat.py
│   ├── 08_downsample_export.py
│   ├── config.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Timeline.jsx
│   │   │   ├── PitchCanvas.jsx
│   │   │   ├── FormationGlyph.jsx
│   │   │   ├── PressingHeatmap.jsx
│   │   │   ├── CompactnessGauge.jsx
│   │   │   ├── MetricCard.jsx
│   │   │   ├── MetricPanel.jsx
│   │   │   └── PhaseFilter.jsx
│   │   ├── hooks/
│   │   │   ├── useMatchData.js
│   │   │   └── usePlayback.js
│   │   ├── utils/
│   │   │   ├── scales.js
│   │   │   ├── colorMap.js
│   │   │   └── pitchDimensions.js
│   │   ├── App.jsx
│   │   └── index.js
│   ├── public/data/
│   └── package.json
├── data/                    # raw files, gitignored
└── output/                  # pipeline JSON output
```

---

## 4. Python Pipeline

### Step 1: Load Data

Use kloppy to read Sportec/DFL IDSSE format. **This step MUST be exploratory first.**

Before writing downstream pipeline code:
1. Load one match with `sportec.load_idsse(match_id="J03WMX", data_type="tracking")` and `data_type="event"`
2. Convert to pandas with `.to_pandas()`
3. Print column names, coordinate ranges, unique event types, and a sample frame
4. Verify attacking direction per half (coordinates may flip)
5. **Do NOT proceed to Step 2+ until schema is verified**

Produce two DataFrames:

- **Tracking**: match_id, frame_id, timestamp (seconds), player_id, team_id, x, y, ball_x, ball_y, speed
- **Events**: event_id, timestamp, event_type, player_id, team_id, start_x, start_y, end_x, end_y

Check attacking direction per half and normalize so the team of interest always attacks left-to-right.

**Event type taxonomy**: The DFL event schema uses hierarchical categories. The exact event type strings must be discovered by inspecting the data. This directly affects PPDA computation strategy.

Libraries: `kloppy` (primary), `floodlight` (fallback)

### Step 2: Compute Sliding-Window Features

For each frame, compute over a 5-second window (125 frames at 25 Hz), per team:

| Feature | Computation | Notes |
|---|---|---|
| defensive_line_height | Mean x of deepest 4 outfield defenders | 0-105m, exclude GK |
| team_compactness | Convex hull area of 10 outfield players | scipy.spatial.ConvexHull, in m² |
| pressure_proxy | Count of defenders within 5m of ball carrier, averaged over window | Substitute for PPDA if event types are too coarse |
| ball_x | Ball x-coordinate | 0-105m along pitch length |

PPDA note: True PPDA = opponent passes / your defensive actions, requires clean event labels. If Sportec event types don't distinguish these cleanly, use the pressure proxy above. Check event type availability through kloppy before committing.

Libraries: `numpy`, `scipy.spatial`, `pandas`

### Step 3: Two-Path Phase Classifier

Phase classification uses two parallel detection paths that get merged.

#### Path A: Tracking-based (sustained phases)

Starting thresholds (calibrate against match video):

| Phase | def_line_height | compactness | pressure_proxy | ball_x |
|---|---|---|---|---|
| High press | > 45m | any | >= 3 | > 52.5m (opponent half) |
| Defensive block | < 35m | < 400 m² | any | < 52.5m (own half) |
| Open play | everything else | | | |

#### Path B: Event-based (ephemeral transitions)

Counterattack identification rules from Bekkers & Sahasrabudhe (SSAC 2023, appendix):

1. Sequence starts in the defensive half (start_x < 52.5m)
2. Sequence does not contain a set piece (freekick, corner, throw-in, goal_kick, penalty)
3. Ball moves at least 10 meters forward
4. Ball forward velocity at least 4 m/s

Detection: Find possession change events (ball_recovery, interception, tackle_won). For each, check if subsequent events by the same team within 15 seconds satisfy rules 1-4. Sequence ends at shot, turnover, or 15s timeout.

#### Merge Logic

**Transition overrides tracking-based labels** when active. Counter-attacks are ephemeral, press/block are sustained.

Post-merge: smooth adjacent same-type segments, drop segments shorter than 5 seconds.

Output: DataFrame with phase_id, phase_type, start_time, end_time, duration, team_id

### Step 4: Voronoi Pitch Control

For each frame at 4 Hz (after downsampling):
1. Voronoi tessellation of all 22 players via `scipy.spatial.Voronoi`
2. Clip to pitch boundaries using `shapely`
3. Export as polygon vertex arrays per player per frame

Alternative: rasterize to 105x68 grid with team_id per cell (simpler, smaller JSON).

Libraries: `scipy.spatial`, `shapely`

### Step 5: Formation Graphs

**Design decision: Template-based role assignment (not iterative EM from SoccerCPD).**

Process:
1. For each half, compute mean outfield positions from first 5 minutes as formation template (10x2 array)
2. Per frame: `linear_sum_assignment(distance_matrix(positions, template))` assigns role index 0-9 to each player
3. Per frame: reorder by role, compute `delaunay_edge_mat(role_ordered_positions)` for 10x10 adjacency
4. Per phase: mean positions per role, mean adjacency, positional stability (1 / (1 + variance))

Key function (from SoccerCPD, hyunsungkim-ds/soccercpd):

```python
def delaunay_edge_mat(coords):
    tri_pts = Delaunay(coords).simplices
    edges = np.concatenate((tri_pts[:, :2], tri_pts[:, 1:], tri_pts[:, ::2]), axis=0)
    edge_mat = np.zeros((coords.shape[0], coords.shape[0]))
    edge_mat[edges[:, 0], edges[:, 1]] = 1
    return np.clip(edge_mat + edge_mat.T, 0, 1)
```

Libraries: `scipy.spatial`, `scipy.optimize`, `numpy`

### Step 6: Pressing Intensity Heatmap

For each "high_press" phase segment:
1. Collect defensive action locations from event data
2. 2D KDE via `scipy.stats.gaussian_kde`
3. Rasterize to 21x14 grid (5m resolution), normalize to 0-1

Libraries: `scipy.stats`

### Step 7: xThreat Computation

Using StatsBomb open data:
1. Divide pitch into 12x8 grid
2. Build transition matrix, shot probability vector, goal probability vector
3. Solve for threat values per zone
4. xThreat(action) = threat(destination) - threat(origin)
5. Per phase: aggregate as xthreat_gained and xthreat_conceded

Libraries: `socceraction` (or ~50 lines from scratch)

### Step 8: Downsample and Export

25 Hz to 4 Hz (every 6th frame). ~2-3 MB JSON per match.

JSON schema per match:
```json
{
  "match_id": "...",
  "metadata": {"home": "...", "away": "...", "date": "..."},
  "frames": [{"t": 0.0, "players": [...], "ball": {...}}, ...],
  "phases": [{"id": 0, "type": "high_press", "team": "home", "start": 12.5, "end": 34.0, "duration": 21.5}, ...],
  "phase_metrics": [{"phase_id": 0, "def_line_height": 48.2, "compactness": 312, ...}, ...],
  "voronoi": [{"t": 0.0, "cells": [...]}, ...],
  "formations": [{"phase_id": 0, "team": "home", "nodes": [...], "edges": [...]}, ...],
  "pressing_heatmaps": [{"phase_id": 0, "grid": [...]}, ...],
  "events": [{"t": 23.1, "type": "pass", ...}, ...]
}
```

Split into separate files if total > 5 MB per match.

---

## 5. React + D3.js Frontend

### Global State

- currentFrame: index into frames array
- phaseFilter: set of active phase types
- selectedPhase: phase ID or null
- brushRange: [startTime, endTime] or null
- hoveredPlayer: player ID or null
- playbackState: {playing, speed}

### Components

**Timeline.jsx** (highest priority): Horizontal 0-90 min bar with color-coded phase rectangles, draggable scrubber, click-to-jump, brush selection. Colors: high_press=#DC2626, defensive_block=#2563EB, counter_attack=#F59E0B, open_play=#9CA3AF.

**PitchCanvas.jsx** (highest priority): Canvas (not SVG) for 22 animated dots at 4Hz. 105x68m pitch markings. Voronoi overlay as semi-transparent team-colored polygons. Hover for player tooltip.

**MetricCard.jsx** (highest priority): Single metric display. Phase filtering adjusts opacity/size. Click for details.

**MetricPanel.jsx** (highest priority): 5-7 cards: def_line_height, compactness, ppda, xthreat_gained, xthreat_conceded, pressing_intensity, formation. Consistent positions, encoding-only changes.

**PhaseFilter.jsx** (highest priority): Toggle buttons for High Press / Defensive Block / Counter-attack / All.

**FormationGlyph.jsx** (secondary): SVG per team. Nodes at mean role positions, Delaunay edges, stability encoding.

**PressingHeatmap.jsx** (secondary): Canvas KDE overlay, transparent-orange-red, visible during high_press.

**CompactnessGauge.jsx** (secondary): Linear gauge, 200-800 m², green-to-red.

### Interactions (Shneiderman's Mantra)

- **Overview**: Full timeline + pitch with all players
- **Zoom + Filter**: Phase toggle, brush time range, click phase segment
- **Details on demand**: Hover player tooltip, click card for stats, click phase for summary

### Brushing and Linking

Timeline brush updates: PitchCanvas (midpoint), MetricCards (aggregated), FormationGlyph (dominant), PressingHeatmap (range KDE).

Player hover updates: MetricCards (player contributions), FormationGlyph (highlight node).

### Tech Stack

react, d3, d3-delaunay, zustand (or Context), tailwindcss

---

## 6. Dependencies

### Python
```
kloppy, socceraction, numpy, pandas, scipy, shapely, mplsoccer (optional dev)
```

### Frontend
```
react, d3, d3-delaunay, zustand, tailwindcss
```

---

## 7. External Code Sources

| Source | What to use |
|---|---|
| hyunsungkim-ds/soccercpd | `delaunay_edge_mat` function (6 lines) |
| Bekkers & Sahasrabudhe SSAC 2023 (appendix) | 4 counterattack identification rules |
| socceraction library | xThreat computation |
| kloppy library | DFL/Sportec data loading |

---

## 8. Critical Decisions

1. Transition overrides press/block when detected
2. Template-based role assignment, not iterative EM
3. PPDA uses tracking-based pressure proxy if events are too coarse
4. All spatial computation pre-computed in Python, frontend only renders
5. 4 Hz downsampling for browser performance
6. Consistent card layout, encoding-only changes for phase filtering

---

## 9. Priority Tiers

**Must ship**: Pipeline steps 1-3 + 8 on 3+ matches, Timeline, PitchCanvas, MetricPanel, PhaseFilter, basic click-to-filter interaction.

**Aim for**: Voronoi overlay, FormationGlyph, PressingHeatmap, CompactnessGauge, xThreat overlay, Timeline brush.

**If time permits**: Phase comparison view, bookmarking/export, half-by-half distribution charts, responsive layout.

---

## 10. Risk Mitigation

| Risk | Mitigation |
|---|---|
| JSON too large | Split per-match, lazy-load |
| Classifier gives poor labels | Start conservative, expand after video validation |
| kloppy can't read IDSSE | Use `floodlight` fallback: `from floodlight.io.datasets import IDSSEDataset` |
| Event types too coarse for PPDA | Use tracking pressure proxy. Inspect event types first in Step 1. |
| Event type strings unknown | Exploratory Step 1 prints unique event types before pipeline code |
| Coordinate direction flip per half | Verify in Step 1, check companion repo `data_processing.py` |
| Formation glyph noisy | Fall back to average-position dot plot |
| Running out of time | Drop comparison + bookmarking, keep core 5 components |
