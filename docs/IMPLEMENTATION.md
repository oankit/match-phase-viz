# Implementation Progress

Phase-Aware Soccer Analytics Dashboard - Python Pipeline

## Status Overview

**Pipeline Status:  All 8 steps implemented**

| Step | Component | Status | Test Status | Notes |
|------|-----------|--------|-------------|-------|
| 1 | Load Data |  Complete |  Passing | Working with local XML files |
| 2 | Compute Features |  Complete |  Passing | Wide-format tracking data |
| 3 | Classify Phases |  Complete |  Passing | Two-path algorithm |
| 4 | Voronoi |  Complete |  Passing | Polygon-based output |
| 5 | Formations |  Complete |  Passing | RoleRep algorithm adapted |
| 6 | Pressing Heatmap |  Complete |  Passing | KDE-based |
| 7 | xThreat |  Complete |  Passing | 12x8 Karun Singh grid; per-event xT exported for frontend |
| 8 | Export JSON |  Complete | � Not tested | Ready for frontend |

---

## Step 1: Load Data 

**File**: `pipeline/01_load_data.py`

**Status**:  Implemented and tested

**Implementation Details**:
- Uses `kloppy.sportec.load_event()` and `kloppy.sportec.load_tracking()` with local XML files
- Finds files using glob patterns: `*matchinformation*{match_id}.xml`, `*events_raw*{match_id}.xml`, `*positions_raw*{match_id}.xml`
- Returns `(event_dataset, tracking_dataset, events_df, tracking_df_sample)`
- Supports configurable sample rates for testing (default 1.0 = 25 Hz)

**Key Fixes**:
- Fixed API: Changed from non-existent `sportec.load_idsse()` to correct `sportec.load_event()` / `sportec.load_tracking()`
- Bypassed broken auto-download by using manually uploaded XML files in `data/` folder
- Fixed DataFrame conversion: `.to_pandas()` � `.to_df()`

**Test Results** (`tests/test_step1_load.py`):
-  Successfully loads all 7 matches
-  J03WN1: 1,429 events, 2,736 tracking frames (at 1 Hz)
-  Tracking data in wide format: columns like `<player_id>_x`, `<player_id>_y`, `<player_id>_d`, `<player_id>_s`

---

## Step 2: Compute Features 

**File**: `pipeline/02_compute_features.py`

**Status**:  Implemented and tested

**Implementation Details**:
- Computes per-team features over 5-second sliding window
- Features computed:
  - `defensive_line_height`: Mean x of deepest 4 outfield defenders
  - `compactness`: Convex hull area of outfield players
  - `pressure_proxy`: Count of defenders within 5m of ball
  - `ball_x`, `ball_y`: Ball coordinates
- Handles wide-format tracking data using player-team mapping from metadata
- Excludes goalkeeper (sorted first alphabetically/by ID)

**Key Fixes**:
- Rewrote to handle wide-format DataFrame (not long format)
- Added `get_player_team_mapping()` to extract player-team associations from metadata
- Added `extract_team_positions()` to extract [x, y] positions for specific team from wide-format row
- Updated all coordinate calculations for normalized 0-1 space (not absolute meters)

**Test Results**:
-  Computed 5,472 feature rows (2,736 frames � 2 teams)
-  Feature statistics look reasonable:
  - `defensive_line_height`: mean=0.326, std=0.163
  - `compactness`: mean=0.150, std=0.050
  - `pressure_proxy`: mean=0.688, std=0.674

---

## Step 3: Classify Phases (v3 - Possession-Aware)

**File**: `pipeline/03_classify_phases.py`

**Status**: Implemented and tested (v3 - possession-aware, 2026-03-27)

**Implementation Details**:
- **Possession-aware two-path classification**:
  - Uses `ball_owning_team_id` from tracking data to determine possession context
  - Both teams get a phase label per frame simultaneously
  - **Team WITH ball**: `attacking` (ball in opponent half) or `build_up` (ball in own half)
  - **Team WITHOUT ball**: `high_press`, `mid_block`, or `defensive_block`
  - **Path B (event-based)**: Counter-attacks using Bekkers & Sahasrabudhe (SSAC 2023) rules
  - Counter-attacks override tracking-based labels when active
- Smoothing: short phases revert to natural fallback (e.g., short high_press -> mid_block)

**Phase Taxonomy**:
| Team State | Phase | Condition |
|---|---|---|
| Has ball | attacking | Ball in opponent half, team pushed forward |
| Has ball | build_up | Ball in own half |
| No ball | high_press | Defensive line high, pressure near ball |
| No ball | mid_block | Between high press and deep block |
| No ball | defensive_block | Deep, compact, protecting own goal |
| Either | counter_attack | Rapid transition (event-based detection) |
| Fallback | open_play | Short ambiguous phases |

**Phase Colors (frontend)**:
- Attacking: #10B981 (green), Build-up: #06B6D4 (cyan)
- High Press: #DC2626 (red), Mid Block: #8B5CF6 (purple), Defensive Block: #2563EB (blue)
- Counter-attack: #F59E0B (amber), Open Play: #9CA3AF (gray)

**Test Results (v3)**:
- 100% possession data available (5472/5472 frames)
- 2167 phase segments detected across both teams
- All 7 phase types present in exported phases.json

---

## Step 4: Voronoi Pitch Control 

**File**: `pipeline/04_compute_voronoi.py`

**Status**:  Implemented and tested

**Implementation Details**:
- Computes Voronoi diagrams for each frame showing spatial control
- Uses `scipy.spatial.Voronoi` + `shapely` for clipping to pitch boundaries
- Output format: Polygon vertex arrays per player per frame
- Alternative: Rasterized grid option available but not used

**Implementation Notes**:
- Based on Context7 documentation for scipy.spatial.Voronoi and shapely
- Clips unbounded regions to pitch boundaries (0-1 normalized)
- Handles edge cases: collinear points, insufficient players, etc.

**Test Results**:
-  Processed 2,736 frames in ~5 seconds
-  Generated 22 cells per frame (all players)
-  ~16 valid polygons per frame on average (some edge players have unbounded regions)

---

## Step 5: Formation Graphs 

**File**: `pipeline/05_compute_formations.py`

**Status**:  Implemented and tested

**Implementation Details**:
- **Adapted from RoleRep** (Bialkowski et al. 2014) and SoccerCPD (Kim et al. KDD 2022)
- Core EM algorithm:
  1. Initialize: Fit MVN distributions per role
  2. E-step: Assign players to roles using Hungarian algorithm with `-log(pdf)` cost
  3. M-step: Re-estimate role distributions from assignments
  4. Repeat until convergence (max 10 iter, tol=0.005)
  5. Compute Delaunay adjacency graph
  6. Aggregate mean positions and adjacency per phase
- Handles substitutions: Only uses frames where same 10 outfield players are present
- **GK detection**: Uses kloppy metadata (authoritative) instead of broken min-x heuristic
- **EFPI template matching** (Bekkers 2025) replaces gap-based band assignment
- 27 formation templates (18 for 10-player, 9 for 9-player/red card teams)
- **Red card handling**: Accepts teams with 9 outfield players (Adli red card at min 8)
- Frontend PitchCanvas uses metadata GK IDs for shape graph exclusion

**Key Adaptations from Reference Code**:
- Stripped: `.ugp` format handling, session management, player period tracking, MAX_SWITCH_RATE filtering
- Kept: Core EM algorithm, `delaunay_edge_mat()` (exact copy), convergence logic
- Adapted: Input format changed from custom to kloppy DataFrame

**Test Results**:
-  633 formations computed (320 Team S, 313 Team B) with EFPI template matching
-  Mean positions shape: (10, 2) for 10 outfield players
-  Mean adjacency shape: (10, 10)
-  Stability scores computed correctly

**Reference Files Used**:
- `docs/soccercpd/rolerep.py`: RoleRep algorithm
- `docs/soccercpd/soccercpd.py`: Delaunay adjacency function
- `docs/soccercpd/myconstants.py`: Constants reference

---

## Step 6: Pressing Intensity Heatmap 

**File**: `pipeline/06_compute_pressing.py`

**Status**:  Implemented and tested

**Implementation Details**:
- For each `high_press` phase:
  1. Collect defensive action locations (tackles, interceptions, pressures, recoveries)
  2. Apply 2D KDE via `scipy.stats.gaussian_kde` with Scott bandwidth
  3. Rasterize to 21�14 grid (5m resolution: 105/5 � 68/5)
  4. Normalize to 0-1
- Handles phases with no defensive actions (returns zero heatmap)

**Test Results**:
-  Computed 17 pressing heatmaps
-  Grid shape correct: (14, 21) - height � width
-  Some phases have 0 actions (expected behavior)

---

## Step 7: xThreat 

**File**: `pipeline/07_compute_xthreat.py`

**Status**:  Implemented (simplified MVP)

**Implementation Details**:
- **Simplified MVP implementation**:
  - Divides pitch into 12�8 grid
  - Assigns threat values based on pitch position (forward = higher threat)
  - Centered zones have +10% threat bonus
  - `xThreat = threat(end_zone) - threat(start_zone)`
- Aggregates `xthreat_gained` and `xthreat_conceded` per phase

**MVP Note**:
Full implementation would train a transition matrix from StatsBomb open data using the socceraction library. This simplified version provides the data structure needed for the frontend without requiring extensive training data.

**Test Status**: � Not yet tested (implementation complete)

---

## Step 8: Export JSON 

**File**: `pipeline/08_export_json.py`

**Status**:  Implemented

**Implementation Details**:
- Packages all pipeline outputs into JSON files for frontend:
  - `metadata.json`: Match info, teams, players
  - `frames.json`: Tracking data (downsampled to 4 Hz)
  - `phases.json`: Phase segments with xThreat metrics
  - `formations.json`: Formation graphs per phase
  - `voronoi.json`: Voronoi diagrams per frame
  - `heatmaps.json`: Pressing heatmaps per high_press phase
- Downsamples tracking from 25 Hz � 4 Hz (every 6th frame)
- Creates output directory structure: `output/<match_id>/`

**Export Schema**:
- Frames: `{t, frame_id, period_id, players: [{id, team, x, y, speed?, direction?}], ball: {x, y}}`
- Phases: `{id, type, team, start, end, duration, xthreat_gained, xthreat_conceded}`
- Formations: `{phase_id, team_id, mean_positions: (10,2), mean_adjacency: (10,10), stability_scores: (10,)}`
- Voronoi: `{t, frame_id, timestamp, cells: [{player_id, team_id, polygon: [[x,y],...]},...]}`
- Heatmaps: `{phase_id, team_id, heatmap: (14,21), num_actions}`

**Test Status**: � Not yet tested (implementation complete)

---

## Configuration

**File**: `pipeline/config.py`

**Key Parameters**:
```python
# Coordinates: Normalized 0-1 (not absolute meters)
PITCH_LENGTH = 105.0  # meters (reference)
PITCH_WIDTH = 68.0    # meters (reference)

# Tracking data
TRACKING_FPS = 25
DOWNSAMPLE_FPS = 4

# Phase classification thresholds (normalized 0-1)
PHASE_THRESHOLDS = {
    'high_press': {
        'def_line_height_min': 0.43,  # 45m / 105m
        'ball_x_min': 0.5,
        'pressure_proxy_min': 1,
    },
    'defensive_block': {
        'def_line_height_max': 0.33,  # 35m / 105m
        'compactness_max': 0.20,
        'ball_x_max': 0.5,
    },
}

# Counter-attack rules (normalized 0-1)
COUNTERATTACK_RULES = {
    'forward_distance_min': 0.095,  # 10m / 105m
    'forward_velocity_min': 0.038,  # 4 m/s / 105m
    'timeout': 15.0,  # seconds
}

# Grids
HEATMAP_GRID_SIZE = (21, 14)  # 5m resolution
XTHREAT_GRID_SIZE = (12, 8)

# Post-processing
MIN_PHASE_DURATION = 5.0  # seconds
```

---

## Data Files

**Location**: `data/`

**Structure** (7 matches � 3 files each = 21 files):
- `DFL_02_01_matchinformation_DFL-COM-000001_DFL-MAT-{match_id}.xml` (12 KB)
- `DFL_03_02_events_raw_DFL-COM-000001_DFL-MAT-{match_id}.xml` (598-776 KB)
- `DFL_04_03_positions_raw_observed_DFL-COM-000001_DFL-MAT-{match_id}.xml` (374 MB)

**Match IDs**:
- J03WMX, J03WN1, J03WPY, J03WOH, J03WQQ, J03WOY, J03WR9

---

## Test Files

**Location**: `tests/`

**Test Coverage**:
```
tests/
 test_step1_load.py          Passing
 test_step2_features.py      Passing (via test_pipeline_1_2_3.py)
 test_step3_phases.py        Passing (via test_pipeline_1_2_3.py)
 test_step4_voronoi.py       Passing
 test_step5_formations.py    Passing
 test_step6_pressing.py      Passing
 test_step7_xthreat.py      � To be created
 test_step8_export.py       � To be created
```

**Integration Test**:
- `pipeline/test_pipeline_1_2_3.py`: Tests Steps 1-3 together  Passing

---

## Known Issues & Limitations

### Data Issues
1. **Empty event data**: Some phases have 0 defensive actions (expected for certain phase types)
2. **Substitutions**: Formation computation stops using frames after a substitution occurs mid-phase

### Implementation Limitations
1. **xThreat Model**: Using Karun Singh's pre-trained 12x8 Markov chain xT grid. A 16x12 grid trained on 303 StatsBomb games is available but produces less visible threat variation
2. **Voronoi unbounded regions**: Some edge players have unbounded Voronoi regions (clipped to pitch boundaries)
3. **Formation stability**: Only computed for phases with e3 frames of consistent 10-player lineups

### Performance
- Step 5 (Formations) is slowest: ~2-8 seconds per phase (EM convergence)
- Full pipeline at 1 Hz: ~3-5 minutes for one match
- At 25 Hz (production): Estimated ~30-60 minutes per match

---

## Next Steps

### Pipeline (Complete )
- [x] All 8 steps implemented
- [ ] Create integrated test for full pipeline (Steps 1-8)
- [ ] Test at full 25 Hz sample rate
- [ ] Process all 7 matches

### Frontend (Not Started �)
- [ ] Set up React + D3.js project
- [ ] Implement Timeline component
- [ ] Implement PitchCanvas component
- [ ] Implement Formation glyph
- [ ] Implement Pressing heatmap overlay
- [ ] Implement Compactness gauge
- [ ] Implement Metric cards
- [ ] Implement phase filtering
- [ ] Implement brushing & linking
- [ ] Deploy to GitHub Pages / Vercel

---

## Technical Decisions

### Why normalized coordinates (0-1)?
- Kloppy's default coordinate system
- Simplifies frontend rendering (no pitch dimension conversions)
- Thresholds are pitch-agnostic

### Why wide-format tracking data?
- Kloppy's `.to_df()` returns wide format by default
- More efficient for frame-by-frame processing
- Avoids expensive DataFrame melting/pivoting

### xThreat Model (Updated)
- Using Karun Singh's 12x8 xT grid (confirmed identical to the published pre-trained model)
- A 16x12 grid trained on 303 StatsBomb games is available (`pipeline/xt_grid_16x12.json`) but the 12x8 gives better visual results
- Training script: `pipeline/train_xt_model.py` (for generating alternative grids)
- The grid is provider-agnostic: DFL events are valued by looking up start/end zone threat, no SPADL conversion needed

### Why polygon-based Voronoi (not rasterized)?
- More accurate representation of pitch control
- Frontend can render as SVG paths
- Smaller file size than pixel grid

---

## Dependencies

**Python** (3.10+):
```
kloppy>=3.0.0
pandas>=2.0.0
numpy>=1.24.0
scipy>=1.10.0
shapely>=2.0.0
socceraction>=1.0.0
tqdm>=4.65.0
```

**Optional**:
```
floodlight>=0.3.0      # Fallback loader
mplsoccer>=1.1.0       # Visualization
```

---

## Current Status

**Completed** (2026-03-26):
- ✅ Steps 1-8 of the pipeline implemented and tested individually
- ✅ Full integration test successful - all 8 steps run together without errors
- ✅ JSON export verified with correct structure and data
- ✅ Fixed numpy int64 JSON serialization issue in export

**Integration Test Results** (Match J03WN1 at 1 Hz):
- Pipeline completed successfully
- Processing time: ~2 minutes
- Generated 6 JSON files totaling ~29 MB
- Output files:
  - metadata.json: 3.9 KB
  - frames.json: 1751.0 KB (456 frames downsampled to 4 Hz)
  - phases.json: 40.7 KB (184 phase segments)
  - formations.json: 310.6 KB (90 formations)
  - voronoi.json: 27126.4 KB (2736 frames)
  - heatmaps.json: 74.4 KB (17 pressing heatmaps)

**Key Statistics**:
- Events: 1429
- Tracking frames: 2736 (at 1 Hz sample)
- Feature rows: 5472 (both teams)
- Phase distribution:
  - Open play: 93 segments
  - Defensive block: 73 segments
  - High press: 17 segments
  - Counter-attack: 1 segment

**Frontend Implementation** (2026-03-27):
- ✅ Set up React + Vite project with D3.js
- ✅ Implemented Timeline component with phase visualization
- ✅ Implemented PitchCanvas with player positions and Voronoi overlay
- ✅ Implemented MetricPanel with aggregate statistics
- ✅ Implemented PhaseFilter for phase type filtering
- ✅ Data loading tested - all JSON files accessible

**Frontend Testing**:
- Development server running at http://localhost:3000
- Successfully loading all 6 JSON files:
  - metadata.json (3.9 KB)
  - frames.json (456 frames at 4 Hz)
  - phases.json (184 phase segments)
  - formations.json (90 formations)
  - voronoi.json (2736 frames)
  - heatmaps.json (17 pressing heatmaps)

**Documentation & Verification** (2026-03-27):
- ✅ Renamed documentation files inside `docs/kloppy` to appropriately reflect their contents.
- ✅ Extracted and verified team names directly from the dataset's `MatchInformation` XML files. Matches are confirmed to be DFL teams (e.g., 1. FC Köln vs FC Bayern München, VfL Bochum 1848 vs Bayer 04 Leverkusen, etc.).

**Next Steps**:
1. View dashboard at http://localhost:3000 for visual feedback
2. Refine phase detection based on visualization
3. Improve xThreat model based on visual patterns
4. Process remaining 6 matches with refined algorithms
5. Deploy to GitHub Pages or Vercel

---

## Credits

**Algorithms**:
- Phase classification: Bekkers & Sahasrabudhe (SSAC 2023)
- Formation detection: Bialkowski et al. (2014), Kim et al. (KDD 2022) - SoccerCPD
- Voronoi: Standard computational geometry

**Data**:
- Sportec/DFL IDSSE dataset (Bassek et al. 2025, DOI: 10.1038/s41597-025-04505-y)
- License: CC BY 4.0

**Tools**:
- kloppy: Soccer data parsing
- Claude Code: Implementation assistant

---

*Last Updated: 2026-03-27*

---

## Updates - March 27, 2026

### Rest Defence Implementation ✓
- Modified `04_compute_voronoi.py` to add `rest_defence` output format
- Creates 40x25 grid inside attacking team's convex hull
- Calculates nearest player for pitch control
- Validation shows 94.9% control by attacking team, 5.1% vulnerable gaps

### Phase Detection Analysis & Refinement ✓
- Analyzed J03WN1: Only 1 counter-attack detected (too few)
- Updated `config.py` thresholds:
  - High press: def_line_height 0.43→0.38, ball_x 0.5→0.45
  - Defensive block: Tightened all thresholds
  - Counter-attack: Distance 10m→7.5m, velocity 4→3 m/s

### xThreat Model Upgrade ✓ (Updated 2026-03-29)
- Confirmed the existing 12x8 grid (`xt_grid_12x8.json`) is identical to Karun Singh's published pre-trained grid (trained from real match data via Markov chain, NOT hand-crafted)
- Also trained a 16x12 grid using socceraction's `ExpectedThreat` class on 303 StatsBomb open data games (World Cup 2018/2022, Champions League, La Liga, Bundesliga) -- 669,888 SPADL actions, 53 iterations to convergence
- Training script: `pipeline/train_xt_model.py`, output: `pipeline/xt_grid_16x12.json` (shape 12x16, values 0.003-0.320, NOT vertically symmetric)
- **Decision: kept 12x8 grid as default** -- the 16x12 grid's finer zones produce ~42% smaller per-pass xT deltas, resulting in sparser/shorter bars in the Threat Timeline. The 12x8 grid gives better visual separation
- Dependency fix: pinned `multimethod<2.0` in requirements.txt to resolve `ImportError` in socceraction (multimethod 2.0.2 removed `overload` export needed by pandera)
- Added `statsbombpy` dependency for the training script

### Output Path Configuration ✓ (March 27 PM)
- Fixed output folder mapping permanently
- Pipeline now outputs directly to `frontend/public/data/`
- No manual copying needed - files immediately available
- Falls back to `../output/` if frontend doesn't exist

### Heatmap Clipping Fix ✓ (March 27)
- Heatmap control grid dots were rendering across the entire pitch
- Added canvas clipping path using the convex hull polygon in `PitchCanvas.jsx`
- Dots now only appear inside the white boundary line (convex hull of outfield players)

### Pitch Control Optimization ✓ (March 27)
- Renamed `04_compute_voronoi.py` -> `04_compute_pitch_control.py`, `voronoi.json` -> `pitch_control.json`
- pitch_control.json reduced from 320.9 MB to ~3.2 MB (99% reduction)
- Three changes applied:
  1. Filter grid points to only those inside attacking team's convex hull (GK excluded via metadata)
  2. Grid resolution 24x16 (384 pts) per frame
  3. Compact format: `[x, y, teamIdx, time]` arrays with rounded values, no JSON indentation
- Frontend `PitchCanvas.jsx` updated to read both compact and legacy formats
- Convex hull now uses attacking team outfield players only (proper GK detection from metadata)

### Pipeline Cleanup ✓ (March 27)
- Deleted duplicates: step1.py, step2.py, step3.py
- Deleted old versions: 06_compute_pressing_fixed.py, 06_compute_pressing_old.py
- Deleted artifacts: d.control_grid, __pycache__/
- Moved test utilities to tests/: check_possession.py, test_voronoi_logic.py


---

## Frontend: Team-Aware Phase Display (2026-03-27)

**Problem**: Phases were shown on a single timeline with no way to tell which team each phase belonged to. With possession-aware classification, each team has different phases at the same time.

**Solution**:
- Added **team selector** (Both / Team A / Team B) in the dashboard header
- **Two timelines** shown when "Both" is selected -- one per team, labeled with team name
- **Phase filtering** respects both phase type filter AND team filter
- **MetricPanel** shows team names instead of raw IDs (e.g., "VfL Bochum 1848" instead of "DFL-CLU-00000S")
- Match header shows team names from metadata ("VfL Bochum 1848 vs Bayer 04 Leverkusen")

**Files modified**:
-  - team selector state, dual timeline rendering, team name lookup
-  - team selector button styles
-  - accepts teamName prop, shows in header
-  - uses teamNameMap for display

---

## Shape Graph Formation Detection & Visualization (2026-03-28)

### Pipeline: Shape Graph Algorithm (Brandes et al. 2025)

**File**: `pipeline/05_compute_formations.py`

Replaced Delaunay triangulation as primary edge source with shape graph construction:

- **`compute_shape_graph(coords)`**: Iterative Delaunay edge removal by angular stability (Algorithm 1 from Brandes et al. 2025 / Sotudeh 2026). Edges shared by 2 triangles with stability < 45 degrees are removed. Boundary edges always kept. Falls back to full Delaunay if fewer than 5 edges remain.
- **`assign_vertical_bands(positions)`**: Gap-based 1D clustering on x-coordinates. Defaults to k=3 bands (defense/midfield/attack), falls back to k=4 or k=2. Uses raw pitch coordinates for meaningful labels.
- **`detect_formation_label(band_counts)`**: Joins band counts with hyphens (e.g., [4,4,2] -> "4-4-2").

New fields exported per formation: `shape_graph_edges`, `shape_graph_adjacency`, `band_assignments`, `band_counts`, `band_thresholds`, `formation_label`, `raw_mean_positions`.

### Frontend: Live Shape Graph on Pitch (Option A)

**File**: `frontend/src/utils/shapeGraph.js` (NEW)

JavaScript port of the shape graph algorithm using `d3-delaunay`. Computes Delaunay triangulation + iterative edge removal per frame on live player positions.

**File**: `frontend/src/components/PitchCanvas.jsx`

- Added live shape graph overlay: computes shape graph per frame on actual player positions, draws edges on canvas behind player dots
- GK excluded per team using min-x heuristic (same as pipeline)
- Added overlay toggle: None / Shape Graph / Pitch Control (replaces old `showVoronoi` boolean)

**File**: `frontend/src/App.jsx`

- Added `overlayMode` state with dropdown selector in playback controls

### Frontend: Formation Comparison Panel (Option B)

**File**: `frontend/src/components/FormationComparisonPanel.jsx` (NEW)

- Side-by-side half-pitch diagrams: in-possession vs out-of-possession formation
- Uses `raw_mean_positions` (absolute pitch coordinates) for proper display
- Vertical half-pitch orientation (goal at top, center line at bottom) matching Stats Perform template style
- Auto-fits positions to fill display area
- Aggregates shape graph edges by frequency (>40% threshold), uses mode band counts
- Shows formation labels (e.g., "3-4-2-1") and phase counts

**File**: `frontend/src/utils/drawFormation.js` (NEW)

- `drawFormationGlyph()`: Draws shape graph edges, horizontal band lines, player nodes, formation labels
- Supports both centroid-normalized positions (with auto-fitting) and raw positions (with `useRawPositions` option)

### Config Changes

**File**: `pipeline/config.py`

```
SHAPE_GRAPH_ANGLE_THRESHOLD = 45.0   # degrees (Brandes et al. 2025)
SHAPE_GRAPH_MIN_EDGES = 5            # fallback to Delaunay if fewer
```

---

## Frontend Refactoring: Athletic-Inspired Dashboard (2026-03-28)

Restyled the entire frontend to match The Athletic's match dashboard aesthetic
(ref: https://www.nytimes.com/athletic/5143083/2023/12/17/the-athletic-match-dashboard/).

### New Component: Threat Timeline

**File**: `frontend/src/components/ThreatTimeline.jsx` (NEW)

- Minute-by-minute xThreat bar chart inspired by The Athletic's "game flow" visualization
- Home team bars extend upward (red), away team bars extend downward (blue)
- Aggregates `xthreat_gained` from phases.json into per-minute bins
- Applies exponential moving average smoothing (alpha=0.35) for visual flow
- Click-to-jump interaction for time navigation
- Dashed current-time indicator
- Team name labels on left/right, "THREAT TIMELINE" center label

### Layout Restructuring

**File**: `frontend/src/App.jsx`

- New layout flow: Score Header -> Threat Timeline -> Phase Timelines -> Controls -> Grid (Pitch | Metrics)
- Score header with serif typography, team color dots, match metadata
- Section dividers (thin horizontal rules) between content areas
- Two-column grid at 900px+ breakpoint (pitch: 3fr, metrics: 2fr)

### Visual Restyling (Athletic Aesthetic)

All component CSS files updated:

- **index.css**: Google Fonts (Noto Sans + Noto Serif), cream background (#faf9f6), serif headings
- **App.css**: Newspaper-style score header, subtle section dividers, cleaner controls
- **Timeline.css**: Reduced height, uppercase labels, lighter background (#f2f0eb)
- **MetricPanel.css**: Uppercase section labels, cream tint backgrounds
- **MetricCard.css**: Serif value typography, subtle left border accent, no drop shadows
- **PhaseFilter.css**: Smaller, tighter filter pills
- **PitchCanvas.css**: Removed box shadow for flat style
- **FormationComparisonPanel.css**: Consistent cream background (#f2f0eb)

### Design System

- Background: #faf9f6 (page), #f2f0eb (panels/cards)
- Typography: Noto Serif for headings/values, Noto Sans for labels/body
- Team colors: #C8102E (home/red), #6CABDD (away/blue)
- Dividers: #e5e1d8
- Labels: 11px uppercase with letter-spacing for section headers

---

## Score Header, Live Score & Goal Markers (2026-03-28)

### Club Badges in Score Header

**File**: `frontend/src/App.jsx`

- Score header now displays club badges loaded from `metadata.json` (`badge` field per team)
- Layout: Home name + badge | Score + competition | Badge + away name
- Badge images stored in `frontend/public/assets/` as PNGs

### Live Score

**File**: `frontend/src/App.jsx`

- `liveScore` computed via `useMemo` based on `goals` array from metadata and `currentTime`
- Score updates dynamically as the playback scrubber advances through the match
- Shows "0 - 0" at start, increments when `currentTime >= goal.match_seconds`

### Goal Ball Icons on Threat Timeline

**File**: `frontend/src/components/ThreatTimeline.jsx`

- Ball icons rendered at the minute each goal was scored
- Home team goals appear above the chart, away team goals below
- Soccer ball drawn as white circle with pentagon pattern and dashed tick connecting to the bar area
- Goals data passed from `App.jsx` via `goals` prop

### Pipeline: Goal Extraction

**File**: `pipeline/08_export_json.py`

- Added `extract_goals()` function: finds SHOT events with `result == GOAL` from kloppy events
- Computes `match_seconds` correctly across periods (adds ~2700s offset for second half)
- Added `BADGE_MAP` for team name to badge file path mapping
- `export_metadata()` now includes `goals` array and `badge` paths in `metadata.json`

### Metadata Schema Update

**File**: `frontend/public/data/J03WN1/metadata.json`

- Each team object now has a `"badge"` field (e.g., `"/assets/VfL Bochum 1848.png"`)
- New top-level `"goals"` array with objects:
  - `team_id`, `player_id`, `player_name`, `minute`, `match_seconds`, `period`

### Bug Fix: React Hooks Order

**File**: `frontend/src/App.jsx`

- Fixed "Rendered more hooks than during the previous render" error
- Moved `useMemo` (liveScore) and derived state computations before early return statements
- React requires all hooks to be called in the same order on every render; hooks after conditional returns violate this rule

---

## Match Stats & Lineups -- The Athletic Style (2026-03-28)

### Pipeline: Match Stats Computation

**File**: `pipeline/09_compute_match_stats.py` (NEW)

Computes six match-level stats per team, inspired by The Athletic's match dashboard:

| Stat | Description | Method |
|---|---|---|
| Start distance | Avg distance (m) from possession start to opponent goal | Group events into possession sequences, measure first event location |
| Progression | Avg % of remaining distance gained per possession | Compare start vs end of each possession |
| Circulation | Passing indirectness (1 - progressive/total distance) | Ratio of forward pass distance to total pass distance |
| Build-ups | Possessions with 8+ passes reaching the box | Count pass sequences meeting both criteria |
| Fast breaks | Possessions reaching box within 15s from deep | Track time from deep touch to box entry |
| High press | Defensive actions in top 60% / 100 opponent passes | OtherBallAction + Recovery + Foul events vs opponent passes |

Each stat includes a 0-5 circle rating (0.5 increments) based on calibrated ranges.

Also computes per-player stats:
- Minutes played, goals, assists
- Progressive passes (>=10m, >=25% remaining distance gained)
- Progressive receptions (receiver of progressive pass)
- Defensive actions (OtherBallAction + Recovery events)
- Touches (all on-ball events)
- Positional xG (distance + angle model)
- Position abbreviation from kloppy `starting_position`

### Data Export

Stats exported to `metadata.json` as `match_stats` and `player_stats` fields.

### Frontend: MatchStats Component

**File**: `frontend/src/components/MatchStats.jsx` (NEW)

- Side-by-side comparison panel for both teams
- Circle rating glyphs (5 circles per team, each empty/half/full)
- Home circles in red (#C8102E), away in blue (#2563EB)
- Winning team's value highlighted with colored pill border
- Serif labels for stat names, sans-serif for values

### Frontend: Lineups Component

**File**: `frontend/src/components/Lineups.jsx` (NEW)

- Side-by-side lineup cards (home left, away right)
- Team header with colored bottom border
- Columns: sub marker, position abbreviation, player name, minutes, key stats
- Sub arrows: up triangle (sub on, team color), down triangle (sub off, gray)
- Stat icons (SVG): goal, assist, progressive passes (arrow up), defensive actions (shield), touches (circle), xG (crosshair)
- Team leaders highlighted: player with most progressive passes / defensive actions / touches per team

### Integration

**File**: `frontend/src/App.jsx`

- MatchStats placed between Threat Timeline and Phase Timelines
- Lineups placed at the bottom after the main content grid
- Data sourced from `matchData.metadata.match_stats` and `matchData.metadata.player_stats`

---

## Fix: xThreat for Shots and Goals (2026-03-28)

### Problem

The Threat Timeline showed near-zero bars around the first goal (minute 18), despite a goal being scored. Root cause: `pipeline/07_compute_xthreat.py` only computed xThreat for events with both start AND end coordinates (pass-type events). SHOT events in DFL data lack end coordinates, so all shots -- including goals -- registered zero threat.

Data evidence: 1001 out of 1093 home team phases had exactly 0.0 xThreat. The phase containing the first goal (phase 1430, 17.9min) had xt_gained=0.0000.

### Fix

Modified `compute_xthreat_for_event()` in `pipeline/07_compute_xthreat.py`:

- **GOAL result**: Returns 0.50 (threat fully realised; significant but not overwhelming relative to max xT surface value)
- **SHOT (non-goal)**: Returns `max(threat_surface[zone], shot_xg)` where `shot_xg` is a positional model based on distance/angle to goal
- **All other events**: Unchanged (end_zone_threat - start_zone_threat)

Added helper `_shot_xg(x, y)` for distance+angle based positional xG.

### Result

Phase 1430 (containing the first goal) now has xt_gained=0.4926. The Threat Timeline displays a visible spike around minute 18, properly correlated with the goal marker.

---

## Fix: Match Stats Attacking Direction (2026-03-28)

### Problem

All six match stats (start distance, progression, circulation, build-ups, fast breaks, high press) were wrong because `09_compute_match_stats.py` hardcoded attacking direction as `home=right, away=left`. In kloppy's coordinate system, the direction flips between halves:

- Period 1: Home attacks LEFT (x=0), Away attacks RIGHT (x=1)
- Period 2: Home attacks RIGHT (x=1), Away attacks LEFT (x=0)

This meant all distance-to-goal, box entry, and zone calculations were wrong for half the match. Progression was -9.3% / -9.7% (should be positive). Fast breaks were inflated (7/10 vs correct 5/2).

### Fix

1. **Direction detection**: Added `_detect_attacking_direction(events_df, team_ids)` that auto-detects attacking direction per team per period from shot locations (average x > 0.5 = attacking right).

2. **All stat functions updated** to accept a `direction_map` and look up the correct direction per event/possession period.

3. **Progression**: Changed from Euclidean distance to x-axis distance (`_x_dist_to_goal`), measures to furthest forward point, requires 3+ events and 10+m starting distance.

4. **Build-ups**: Lowered threshold from 8 to 5 passes (DFL data has fewer events than StatsBomb). Now checks both event start AND pass end coordinates for box entry.

5. **Fast breaks**: Uses `_x_dist_to_goal >= 52.5m` to define "own half" instead of a fixed x-threshold.

6. **High press**: Zone check now uses per-event period direction.

### Corrected Values (J03WN1)

| Stat | Old (wrong) | New (fixed) |
|------|-------------|-------------|
| Start distance | 57.8 / 53.7 | 62.1 / 67.5 |
| Progression | -9.3% / -9.7% | 40.6% / 27.7% |
| Circulation | 0.61 / 0.65 | 0.53 / 0.61 |
| Build-ups | 1 / 1 | 1 / 0 |
| Fast breaks | 7 / 10 | 5 / 2 |
| High press | 43.2 / 29.3 | 30.0 / 26.4 |

---

## Fix: Second Half Missing from Dashboard (2026-03-29)

### Problem
The dashboard only showed the first half (~48 minutes). The Threat Timeline, phase timelines, and pitch canvas all stopped at halftime. The second half was completely absent.

### Root Cause
kloppy's tracking data uses period-relative timestamps: period 1 timestamps range 0s-2770s, and period 2 timestamps also restart from 0s-2888s. When exported to JSON without offset adjustment, period 2 frames overlapped with period 1 frames, and the frontend saw the last frame at ~48 minutes.

### Fix
1. **Pipeline (`test_full_pipeline.py`)**: After `tracking_dataset.to_df()`, compute the actual period 1 end timestamp and offset all period 2 timestamps by `p1_end + 1 second`. This ensures period 2 data starts right after period 1 ends, with no overlap or gap.

2. **Export (`08_export_json.py`)**: 
   - `downsample_tracking()` now uses `LOADED_FPS` instead of `TRACKING_FPS` to avoid double-downsampling.
   - `export_metadata()` accepts and stores `match_duration` and `period_2_offset_secs`.
   - `extract_goals()` uses the same period 2 offset for consistent goal timestamps.

3. **Frontend (`App.jsx`)**: `matchDuration` now reads from `metadata.duration` instead of deriving from the last frame timestamp.

### Result
- Frames: 2736 (0s to 5660s, ~94 minutes including stoppage)
- Phases: 1123 segments covering the full match
- No timestamp overlap between periods (1s gap)
- All 3 goals correctly placed on the Threat Timeline (min 18, 33, 86)
- ThreatTimeline shows 1' to 93' with xThreat data for both halves

*Last Updated: 2026-03-29*

---

## Threat Timeline Investigation

### Issue Reported
User reported that the threat timeline was incorrect and missing a goal.

### Investigation Findings

#### Goals Detection
- **Match analyzed**: J03WN1 (VfL Bochum 1848 vs Bayer 04 Leverkusen)
- **Goals found**: 3 goals, all correctly extracted from event data
  - 18' - VfL Bochum 1848 (P. Forster)
  - 33' - VfL Bochum 1848 (T. Asano)
  - 85' - VfL Bochum 1848 (K. Stoger)
- **No missing goals**: All goals are present in metadata.json and displayed on the timeline
- **Match result**: VfL Bochum 3-0 Bayer 04 Leverkusen (verified from 21 total shots)

#### xThreat Analysis
- **Total xThreat gained**:
  - VfL Bochum 1848: 0.826
  - Bayer 04 Leverkusen: 0.269
- **Issue identified**: Goal at minute 85 creates an xThreat spike of 0.5 at minute 86 (phase alignment issue)
- **Threat distribution**: Home team has higher total threat but fewer phases with positive threat (17 vs 49)

#### Component Status
- **ThreatTimeline.jsx**:
  - Correctly displays goal markers with soccer ball icons
  - Uses 1-indexed minutes to match the xScale domain (minute 0 = 1st minute of play)
  - Properly handles team colors and positioning (home goals above, away goals below)

- **Goal extraction (`08_export_json.py`)**:
  - `extract_goals()` function correctly identifies SHOT events with result='GOAL'
  - Properly converts timestamps to match seconds accounting for period offsets
  - Player names and team IDs correctly mapped

### Resolution
1. All goals are correctly detected and displayed
2. No goals are missing from the data
3. The xThreat values may need recalibration for better visual representation
4. Minor phase-to-event alignment issue causes threat spike to appear 1 minute after goal

---

## xThreat Timeline Accuracy Fix (2026-03-29)

### Problem
The xThreat timeline showed incorrect threat distribution:
1. GOAL events in dead-ball gaps were assigned to the nearest **opponent** phase (e.g., away team's defensive_block), so the xThreat went to `xthreat_conceded` instead of the scoring team's `xthreat_gained`.
2. Phase xThreat was spread evenly across all minutes the phase spanned, diluting goal spikes when a phase covered 2+ minutes.

### Root Cause
1. Gap recovery in `07_compute_xthreat.py` and `update_all.py` searched for the nearest phase by end_time regardless of team ownership. When a HOME team goal fell in a dead-ball gap, the closest phase might be an AWAY team phase.
2. `ThreatTimeline.jsx` divided each phase's `xthreat_gained` by the number of minutes it spanned (`perMinuteGain = xt / phaseMinutes`), spreading 0.50 goal xThreat across 2 bins.

### Fix
1. **Same-team gap recovery** (`07_compute_xthreat.py`, `update_all.py`): Unmatched events are now assigned to the nearest phase belonging to the **same team** as the event, ensuring GOALs appear as `xthreat_gained` for the scoring team.
2. **End-minute binning** (`ThreatTimeline.jsx`): Each phase's full `xthreat_gained` is placed at its end minute (`Math.floor(phase.end / 60)`) rather than being distributed across all spanned minutes. This concentrates goal spikes into a single prominent bar.

### Result
- All 3 goals now produce clear, dominant spikes in the timeline
- Non-goal bars remain small, showing general play flow
- Goal football icons align with their corresponding threat bars

---

## Player Name Encoding & Lineup Ordering Fix (2026-03-29)

### Problem
1. Player names with non-ASCII characters (Stoger, Forster, Masovic, Hradecky, Hlozek) displayed as `?` in the lineup panel.
2. Jersey numbers were missing from the lineup display.
3. Some starters were incorrectly classified as substitutes (e.g., GK Hradecky, P. Hofmann, A. Losilla).

### Root Cause
1. **Name encoding**: `update_all.py` line 184 had `p['name'].encode('ascii', 'replace').decode()` which explicitly replaced all non-ASCII characters with `?`.
2. **Jersey numbers**: `09_compute_match_stats.py` did not include `jersey_no` from kloppy's player metadata.
3. **Starter detection**: `_compute_minutes()` used a fragile heuristic (first event within 2 minutes of kickoff) instead of kloppy's authoritative `player.starting` attribute. GKs and defenders with few early events were misclassified.

### Fix
1. Removed the `.encode('ascii', 'replace').decode()` from `update_all.py`. Added name cross-referencing from `metadata.teams` in `Lineups.jsx` as a safety net.
2. Added `jersey_no` extraction from `getattr(p, 'jersey_no', None)` in `compute_player_stats()`. Added `#` column to `Lineups.jsx` table.
3. Set `is_starter` from `getattr(p, 'starting', None)` in `compute_player_stats()`. Updated `_compute_minutes()` to respect the pre-set `is_starter` flag and only compute sub_on/sub_off timing.

### Result
- All names display correctly with proper Unicode characters
- Jersey numbers shown for all players
- Both teams correctly show 11 starters sorted by formation position (GK, defenders, midfielders, forwards)
- Substitutes listed below starters sorted by sub_on time

---

## UI Redesign: UXBooster-Style Layout

### Goal
Complete frontend redesign adopting the UXBooster dashboard template (https://v0-dashboard-ui-alpha.vercel.app/). Warm light theme with rounded white cards on cream background, pill-shaped navigation, green accent score banner, collapsible sections, and 3-tab story structure.

### Design System
- **Background**: Warm cream `#f0ece4`
- **Cards**: White `#ffffff`, border-radius 24px, subtle box shadows
- **Accent**: `#76f214` green (score banner gradient)
- **Typography**: Inter font family, 300-800 weights
- **Navigation**: Top nav bar with pill-shaped tabs (dark fill for active)
- **Sub-tabs**: Inside cards, matching UXBooster's Standard/Heatmap/Insights style

### Three-Tab Structure
1. **Overview** (Tab 0): Match Stats with circle ratings + Lineups & Player Stats
2. **Analysis** (Tab 1 - default): Threat Timeline, Phase Detection (collapsible), Phase Filters + Team Selector, Pitch View with sub-tabs (Shape Graph/Pitch Control/Clean) alongside metric cards (collapsible)
3. **Metrics** (Tab 2): Full-view metric grid (3 columns) with all shape/threat metrics + Phase Distribution bar chart

### Components Updated
- `index.css`: CSS custom properties for warm theme, Inter font import
- `App.css`: Dashboard shell, top nav, score banner, card system, sub-tabs, collapsible sections, playback controls, grid layouts
- `App.jsx`: 3-tab structure with `Collapsible` component, score banner, sub-tabs for overlay mode
- `ThreatTimeline.css/jsx`: Removed panel wrapper, light theme D3 colors
- `Timeline.css/jsx`: Light background, dark time indicator, light axis styling
- `MatchStats.css/jsx`: Removed panel wrapper, light theme stat rows
- `Lineups.css/jsx`: Removed panel wrapper, light theme tables
- `MetricPanel.css/jsx`: Phase distribution bar chart, `fullView` prop for 3-column grid
- `MetricCard.css`: Light input background cards
- `PhaseFilter.css`: Pill-shaped filter buttons
- `PitchCanvas.css/jsx`: Green pitch `#3a8c3a`, white markings at 50% opacity
- `FormationComparisonPanel.css`: Light theme variables

### Collapsibility
Phase Detection and Pitch View sections use collapsible wrappers, allowing the user to focus on specific visualizations.

---

## Color Theme Consolidation

### Problem
Too many competing colors across the dashboard - 7 vivid phase colors, 3 inconsistent team color pairs (red/blue in different hues across components), 9 individual metric card border colors, and a green accent (#76f214) that clashed with the overall palette.

### Solution: Minimalistic 2-Tone + Muted Earth Palette

**Team colors** (match badge identity):
- Home (VfL Bochum): `#2b6da4` (muted blue, from badge)
- Away (Bayer Leverkusen): `#c83c35` (muted red, from badge)
- Applied consistently across: score banner pills, threat timeline bars, match stats circles, pitch player dots, shape graph edges, pitch control overlay

**Phase colors** (muted earth tones, cohesive palette):
- Attacking: `#5ea832` (olive green)
- Build-up: `#8bc575` (sage green)
- High press: `#c47a5a` (terracotta)
- Mid block: `#9a8676` (warm taupe)
- Defensive block: `#7c92a6` (steel blue-gray)
- Counter attack: `#bfa64e` (muted gold)
- Open play: `#b5b0a8` (warm gray)

**Removed**:
- Green accent (#76f214) - dropped entirely
- Per-metric card colored borders and colored value text
- Vivid phase filter button backgrounds (replaced with neutral dark pill + small color dot)

### Score Banner Redesign
Replaced the green gradient banner with a clean flat layout matching a reference design:
- Team name pills with team-colored backgrounds
- Large centered badges (52px)
- Large centered score
- Competition name and time centered below

### Files Changed
- `index.css`: Updated `--home-color`, `--away-color`, all `--phase-*` vars, removed `--accent*` vars
- `App.css`: Rewrote `.score-banner` to flat centered layout with team pills
- `App.jsx`: Restructured score banner JSX (team pills, row layout)
- `ThreatTimeline.jsx`: Team colors from CSS vars
- `MatchStats.jsx`: Team colors matching badges
- `PitchCanvas.jsx`: Team colors matching badges
- `Timeline.jsx`: Muted phase colors
- `PhaseFilter.jsx`: Neutral button style with small colored dot indicators
- `MetricPanel.jsx`: Removed per-metric `color` props, muted phase distribution colors
- `MetricCard.jsx`: Removed `color` prop, uniform dark text, neutral card background
- `MetricCard.css`: Removed colored left border, neutral `--bg-input` background
- `PhaseFilter.css`: Neutral active state (dark pill), added `.phase-dot`

---

## Flat Layout Redesign (The Athletic Style)

### Goal
Adopt The Athletic's match dashboard aesthetic: flat layout where all content blends directly with the page background (no card containers), smaller/more compact typography, thin divider lines between sections.

### Changes

**Background**: `#f0edea` (lighter warm off-white matching The Athletic). `--bg-card` set to same as `--bg-page` so cards are invisible.

**Cards removed**: `.dash-card` now has `background: transparent; padding: 0;`. Sections separated by thin `border-bottom: 1px solid var(--border-subtle)` dividers on `.card-header`.

**Section headers**: Changed from large card titles to compact uppercase labels (`font-size: 14px; text-transform: uppercase; letter-spacing: 0.04em`) with bottom border dividers.

**Border radii**: Reduced across the board (`--radius-sm: 4px`, `--radius-lg: 8px`) since rounded cards no longer exist.

**Font sizes reduced** across all components to match The Athletic's compact density:
- Card titles: 20px -> 14px uppercase
- Stat labels: 14px -> 13px
- Lineup text: 14px -> 12px
- Phase filter buttons: 12px -> 11px
- Metric values: 26px -> 22px
- Legend items: 12px -> 10px

**Collapsible sections**: Transparent background, thin bottom border instead of card-style header.

**Metric cards**: Transparent background with bottom border dividers instead of colored cards.

**Lineup tables**: Transparent team containers, bold team name headers with thick colored bottom border.

**Playback controls**: Transparent background, minimal padding.

### Files Changed
- `index.css`: Background color, reduced radii, bg-card=transparent
- `App.css`: Flat .dash-card, thin divider headers, compact collapsible, smaller type
- `MetricCard.css`: Transparent background, bottom border dividers
- `MetricPanel.css`: Compact sizing, transparent phase summary
- `MatchStats.css`: Tighter spacing
- `Lineups.css`: Transparent cards, bold header borders
- `Timeline.css`: Smaller legend text, compact spacing
- `ThreatTimeline.css`: Smaller labels
- `PhaseFilter.css`: Smaller buttons
- `PitchCanvas.css`: Minimal border radius
- `Timeline.jsx`: D3 background fill adjusted to match new page bg
- `ThreatTimeline.jsx`: Center line color adjusted

---

## Jersey Numbers on Pitch View

### Problem
Player dots on the pitch canvas were anonymous colored circles with no way to identify individual players.

### Solution
Added jersey numbers inside player circles on the pitch view.

**Pipeline changes** (`08_export_json.py`):
- Added `jersey_no` extraction from kloppy's Player objects
- Jersey numbers now included in both `metadata.json` (per player) and `frames.json` (per player per frame)
- Player number map built from `player.jersey_no` attribute

**Frontend changes** (`PitchCanvas.jsx`):
- Increased player circle radius from 8px to 13px to accommodate numbers
- Renders jersey number text (white, bold 11px Plus Jakarta Sans) centered inside each circle
- Uses `player.number` field from frame data

### Files Changed
- `pipeline/08_export_json.py`: Added `player_number_map`, `jersey_no` to metadata and frames export
- `frontend/src/components/PitchCanvas.jsx`: Larger circles (r=13), jersey number rendering
- `frontend/dist/data/J03WN1/frames.json`: Patched with jersey numbers
- `frontend/dist/data/J03WN1/metadata.json`: Patched with jersey numbers

---

## Red Card Minutes Fix

### Problem
Players sent off with a red card showed full match minutes (e.g. Adli showed 93' despite a red card at minute 7). The `_compute_minutes` function only handled substitutions, not dismissals.

### Solution
Updated `_compute_minutes` in `09_compute_match_stats.py` to detect red cards (`RED`) and second yellows (`SECOND_YELLOW`) from `CARD` events using the `card_type` column, setting `sub_off` to the dismissal minute.

### Files Changed
- `pipeline/09_compute_match_stats.py`: Added red card / second yellow detection in `_compute_minutes`
- `frontend/dist/data/J03WN1/metadata.json`: Re-computed player stats with corrected minutes

---

## Yellow & Red Card Icons in Lineups

### Problem
The lineup display had no indication of which players received yellow or red cards during the match.

### Solution
- Added `yellow_cards` (count) and `red_card` (boolean) fields to player stats in the pipeline
- Counts `FIRST_YELLOW` and `SECOND_YELLOW` card types for yellow cards, `RED` and `SECOND_YELLOW` for red cards
- Added yellow card (gold rectangle) and red card (red rectangle) SVG icons to `StatIcon` in `Lineups.jsx`
- Card icons appear in the Key Stats column alongside goals, assists, and other stat icons

### Files Changed
- `pipeline/09_compute_match_stats.py`: Added `yellow_cards` and `red_card` fields, card counting in event loop
- `frontend/src/components/Lineups.jsx`: Added yellow/red card SVG icons and rendering logic
- `frontend/dist/data/J03WN1/metadata.json`: Re-computed with card data

---

## Basic Match Stats (Possession, Shots, Corners, Fouls, Saves)

### Problem
Match Stats only showed advanced analytics (start distance, progression, circulation, etc.) but lacked standard football stats.

### Solution
Added 6 basic match stats computed from event data, displayed with comparative horizontal bars above the advanced stats section.

**New stats**:
- Possession (pass share approximation)
- Shots (total)
- Shots on target (result = GOAL or SAVED)
- Corners (set_piece_type = CORNER_KICK)
- Fouls (FOUL_COMMITTED events)
- Saves (opponent shots with result = SAVED)

**UI**: Each basic stat shows team values on either side with a split horizontal bar indicating the ratio. The leading team's value is bold and colored. The existing advanced stats (with circle ratings) appear below under an "Advanced" label.

### Files Changed
- `pipeline/09_compute_match_stats.py`: Added `_compute_basic_stats()` and integrated into `compute_match_stats()`
- `frontend/src/components/MatchStats.jsx`: Added `BasicStatRow` component, split stats into basic (bar) and advanced (circle rating) sections
- `frontend/src/components/MatchStats.css`: Added `.basic-stats-section`, `.basic-stat-row`, `.basic-bar-track`, `.stats-section-title` styles

---

## Phase Color Palette Overhaul

### Problem
The original phase colors were hard to distinguish -- two shades of green (attacking vs build-up) and several muted browns/greys (mid block, defensive block, open play) blended together on the timeline.

### Solution
Replaced the entire 7-color palette with maximally separated hues:

| Phase | Old Color | New Color | Hue |
|---|---|---|---|
| Attacking | #5ea832 | #2d9a4e | Green |
| Build-up | #8bc575 | #4a90d9 | Blue |
| High Press | #c47a5a | #d94f4f | Red |
| Mid Block | #9a8676 | #e8a838 | Amber |
| Defensive Block | #7c92a6 | #7b5ea7 | Purple |
| Counter Attack | #bfa64e | #e06b9a | Pink |
| Open Play | #b5b0a8 | #a8a29e | Grey |

### Files Changed
- `frontend/src/index.css`: Updated CSS custom properties
- `frontend/src/components/Timeline.jsx`: Updated `phaseColors` map
- `frontend/src/components/PhaseFilter.jsx`: Updated filter button colors
- `frontend/src/components/MetricPanel.jsx`: Updated `PHASE_TYPES` colors
- `frontend/src/components/MetricCard.css`: Updated trend indicator colors

---

## HiDPI Canvas Rendering

### Problem
The pitch canvas appeared blurry on high-DPI displays because it rendered at 1x pixel resolution.

### Solution
Scale the canvas internal bitmap by `window.devicePixelRatio` while keeping the logical drawing coordinate space at 940x612. Applied `ctx.setTransform(dpr, 0, 0, dpr, 0, 0)` so all drawing operations automatically render at the higher resolution.

### Files Changed
- `frontend/src/components/PitchCanvas.jsx`: Added DPR-aware canvas sizing and transform

---

## Lineups Glyph Legend

### Problem
The stat icons in the lineups had no explanation -- users couldn't tell what each glyph meant without hovering for tooltips.

### Solution
Added a horizontal legend below the lineups grid showing each glyph type (goal, assist, most progressive passes, most defensive actions, most touches, xG > 0.05) with its label. Yellow and red cards are excluded since they are self-explanatory.

### Files Changed
- `frontend/src/components/Lineups.jsx`: Added `legendItems` array and rendered legend row using `StatIcon`
- `frontend/src/components/Lineups.css`: Added `.lineups-legend`, `.lineups-legend-item`, `.lineups-legend-label` styles

---

## Collapsible Threat Timeline

### Solution
Wrapped the Threat Timeline section in the existing `Collapsible` component (same as Phase Detection and Match Metrics), replacing the static `card-header`. Defaults to open.

### Files Changed
- `frontend/src/App.jsx`: Replaced static `dash-card` wrapper with `Collapsible` component

---

## Cumulative xG Chart

### Problem
No shot-level expected goals visualization existed. The xThreat data in phases shows threat per phase segment but doesn't show individual shot quality or cumulative chance creation over time.

### Solution
Built a cumulative xG step chart inspired by the [football-match-intelligence](https://github.com/DataKnight1/football-match-intelligence) reference.

**Pipeline**: Extracted shot events from kloppy event data, computed positional xG per shot using the existing `_positional_xg()` model, and exported as `shot_xg.json` with timestamp, team, player, xG value, and goal flag.

**Frontend**: D3.js step chart showing:
- Cumulative xG step lines per team (color-coded)
- Semi-transparent area fills
- Goal markers (outlined circles) and shot markers (small dots)
- Half-time divider
- Final xG values at line endpoints
- Current time indicator (synced with playback)
- Click-to-seek on the timeline
- Legend for goal vs non-goal markers

### Files Changed
- `tests/export_shot_xg.py`: New script to extract shot xG data from event data
- `frontend/public/data/J03WN1/shot_xg.json`: Exported shot xG data
- `frontend/src/hooks/useMatchData.js`: Added `shotXg` data loading
- `frontend/src/components/CumulativeXG.jsx`: New D3 cumulative xG chart component
- `frontend/src/components/CumulativeXG.css`: Chart styles
- `frontend/src/App.jsx`: Added CumulativeXG import and collapsible section in Analysis tab

## Pitch Overlay Visual Consistency

### Problem
The pitch view used a saturated sports-broadcast green (`#3a8c3a`) with harsh white markings, which clashed with the rest of the website's warm, muted, earthy palette. Shape graph edges looked flat and the pitch control overlay appeared as scattered confetti rather than continuous control zones.

### Solution
Restyled all pitch overlays for visual cohesion:

**Pitch background & markings**: Replaced bright green with muted `#3d6b4a`, reduced marking opacity from 0.5 to 0.3, reduced line width from 1.5 to 1.2, and shrunk penalty spots.

**Shape graph edges**: Added dashed line style (`[6,4]`), subtle white glow behind team-colored edges, and adjusted opacity to 0.45 for better presence against the muted pitch.

**Pitch control overlay**: Scaled dot radius dynamically with canvas width (`max(16, width*0.018)`), added three-stop radial gradient for smoother opacity falloff, increased base opacity for more continuous-looking regions, and softened convex hull border (thinner, lower opacity, tighter dash pattern).

**Player outlines**: Increased white outline opacity from 0.6 to 0.7 for crisper contrast against the darker pitch.

**Canvas CSS**: Added `border-radius: var(--radius-lg)` to match card corners elsewhere in the UI.

### Files Changed
- `frontend/src/components/PitchCanvas.jsx`: All overlay rendering changes
- `frontend/src/components/PitchCanvas.css`: Added border-radius

## Formation Lines Overlay

### Problem
The existing pitch overlays (Shape Graph and Pitch Control) show spatial relationships but don't clearly visualize the team's formation structure -- the defensive, midfield, and attack lines that coaches and analysts reference when discussing shape.

### Solution
Added a new "Formation Lines" overlay mode accessible via a tab in the Pitch View header (between Shape Graph and Pitch Control).

**Algorithm**: For each team's outfield players per frame:
1. Sort players by x-coordinate (depth on the pitch)
2. Cluster into lines using a gap-based threshold (0.07 in normalized coordinates, ~7 meters): each player joins the current group if their x is within the threshold of the group's mean x, otherwise a new line starts
3. Within each detected line, sort players by y-coordinate (lateral position) and connect adjacent players with a solid line in the team color

This adapts in real-time as players shift positions, naturally detecting 2-4 horizontal lines regardless of whether the team is in a 4-3-3, 4-4-2, 3-5-2, or any other shape. Single isolated players (e.g. a lone striker) appear as dots without connecting lines.

### Files Changed
- `frontend/src/App.jsx`: Added `formation_lines` option to the overlay mode tabs
- `frontend/src/components/PitchCanvas.jsx`: Implemented formation line detection and rendering logic

---

## Fix: xThreat Calculation Corrected to Standard Model (2026-03-29)

### Problem
The Threat Timeline was dominated by 3 massive spikes at goal minutes (18, 34, 87) making all other bars invisible. Two root causes:

1. **Goals assigned xT = 0.50**: The pipeline hardcoded `return 0.50` for GOAL events. Most pass xT values are 0.001-0.04, making goal bars 10-50x taller than everything else.
2. **Broken EMA smoothing**: The frontend smoothing formula used `bins[i-1]` (original unsmoothed values) instead of `smoothed[i-1]` (previous smoothed output), creating ~45% ghost echoes in adjacent minutes.

### Research
Per the standard xT model (Karun Singh, Markov possession model) and the socceraction reference implementation (KU Leuven):
- **Shots (goals and non-goals) should NOT receive xT values**. Scoring probability is already baked into the xT grid surface (`s(x,y) * g(x,y)` term). Assigning xT to shots is double-counting.
- **Only successful passes/carries** should get `xT = threat(end_zone) - threat(start_zone)`.
- Goals are terminal events that end possession, not ball-moving actions.

### Fix
1. **Pipeline** (`pipeline/07_compute_xthreat.py`): Changed `compute_xthreat_for_event()` to return `0.0` for all SHOT events (both goals and non-goals). Only passes retain xT values.
2. **Frontend** (`frontend/src/components/ThreatTimeline.jsx`): Fixed EMA smoothing to use recursive formula (`smoothed[i-1]` instead of `bins[i-1]`).

### Result
- Threat Timeline now shows the flow of attacking build-up through passes, not goal-dominated spikes
- Goal events are still visible as soccer ball markers (from metadata, unaffected)
- EMA properly smooths minute-to-minute transitions without ghost echoes

### Files Changed
- `pipeline/07_compute_xthreat.py`: Shots return 0.0, updated docstring
- `frontend/src/components/ThreatTimeline.jsx`: Fixed recursive EMA smoothing (alpha=0.82)
- `pipeline/08_export_json.py`: Fixed double period-2 offset in `extract_goals()` and `export_shot_xg()` - timestamps are already in continuous match time from upstream offset, so no additional offset needed. This fixed the 3rd goal (Stoger, min 86) showing at minute 132.

## Pipeline Integration: Match Stats, Player Stats & Shot xG

### Problem
Match stats (possession, shots, fouls, etc.), player stats (minutes, goals, assists, xG, etc.), and shot-level xG data were computed by standalone scripts in `tests/` (`patch_player_minutes.py`, `export_shot_xg.py`) and manually patched into `metadata.json`. This meant they were not part of the reproducible pipeline and had to be run separately after every pipeline execution.

### Solution
Integrated Step 9 (`09_compute_match_stats.py`) and shot xG export directly into the pipeline:

**`08_export_json.py`**: Added two new export functions:
- `export_match_stats()`: Merges match stats and player stats (as an array) into the existing `metadata.json` after it is written
- `export_shot_xg()`: Extracts shot events, computes positional xG using the calibrated logistic model from Step 9, and exports `shot_xg.json`

The `main()` function now accepts optional `match_stats` and `player_stats` parameters. When provided, it calls both new functions automatically.

**`tests/test_full_pipeline.py`**: Added Step 9 between xThreat and Export. `compute_all()` runs before the export step and passes its output to `step8.main()`.

The pipeline now produces all 7 JSON files in a single run: `metadata.json` (with stats), `frames.json`, `phases.json`, `formations.json`, `pitch_control.json`, `heatmaps.json`, and `shot_xg.json`.

### Files Changed
- `pipeline/08_export_json.py`: Added `export_match_stats()`, `export_shot_xg()`, updated `main()` signature
- `tests/test_full_pipeline.py`: Added step 9 import and execution, updated summary

---

## Live Metrics: Rest Defence Score (RDS) & Opponent Threat Index (OTI)

### Problem
The Match Metrics panel displayed only phase-level static metrics (defensive line height, compactness, etc.) that update per-phase. There was no real-time structural assessment of how well a team is organized defensively or how threatening the opponent's positioning is.

### Academic Foundation

**Rest Defence Score (RDS)** -- composite metric evaluating the structure maintained while in possession (0-100 scale):

| Component | Weight | Formula | Source |
|-----------|--------|---------|--------|
| S_num (Numerical Balance) | 40% | `defenders_behind_ball / (opp_outlets + 0.5)`, capped at ratio=3 | Bauer & Anzer (2021) |
| S_comp (Spatial Compactness) | 30% | `1 - (hull_area - ideal) / (max - ideal)`, from convex hull of rest-def unit | Spearman (2018) |
| S_ctrl (Pitch Control Dominance) | 30% | Reach-time grid over defensive third, with outlet penalty for opponent-controlled central cells | Alai framework |

**Opponent Threat Index (OTI)** -- latent danger from opponent positioning (0-100 scale):

| Component | Weight | Formula | Source |
|-----------|--------|---------|--------|
| S_goal (Spatial Threat) | 30% | `cos(theta) / d^2` per opponent in attacking half | Linke et al. (2016) |
| O_num (Numerical Overload) | 25% | 5 corridor overload check in defensive third | Bauer & Anzer (2021) |
| D_space (Space Dominance) | 30% | Reach-time grid over danger zone, central cells weighted 1.5x | Spearman (2018) |
| M_kin (Kinetic Threat) | 15% | `speed * proximity_to_goal` (approximation of velocity dot product) | Linke et al. (2016) |

### Data Constraints & Design Decisions

**Available per frame (frontend)**: player positions `{x, y, speed}` in normalized 0-1 coordinates, ball position `{x, y}`, team IDs.

**Not available**: velocity direction vectors (only scalar speed), per-cell xT values on the frontend.

**Critical issue**: The pipeline's `pitch_control.json` grid only covers points inside the attacking team's convex hull (15-66 sparse points per frame). This is the *opposite* of where RDS needs data (the defending team's zone behind the ball) and unreliable for OTI's danger zone.

**Solution**: Compute a lightweight 8x5 reach-time grid on the frontend from raw player positions, scoped to just the relevant zone (defending third for S_ctrl, attacking third for D_space). For each grid point, the nearest player by Euclidean distance determines control. This is the same algorithm the pipeline uses (`dist / max_speed`), just applied to a coarse grid on-the-fly.

### Score Interpretation

| RDS Score | Label | Meaning |
|-----------|-------|---------|
| 80-100 | Excellent | Numerical superiority, tight shape, outlets caged |
| 65-79 | Good | Adequate coverage with minor gaps |
| 50-64 | Fair | Players back but spread or opponent has space |
| 35-49 | Poor | Vulnerable to transition |
| 0-34 | Critical | High vulnerability, likely caught out |

| OTI Score | Label | Meaning |
|-----------|-------|---------|
| 70-100 | Critical | Fast transition, numerical overload, deep penetration |
| 50-69 | Major | Significant threat building |
| 35-49 | Moderate | Some attacking presence |
| 20-34 | Minor | Recycling possession |
| 0-19 | Low | Opponent defending deep |

### UI Integration

Scores displayed in the Match Metrics panel as per-team side-by-side rows with color-coded labels. Colors match the qualitative assessment (green=Excellent, blue=Good, amber=Fair, red=Poor, dark red=Critical for RDS; inverse scale for OTI).

### Files Changed
- `frontend/src/utils/restDefence.js`: New utility with `computeRestDefenceScores()` and `computeThreatScores()` implementing the 3-component RDS and 4-component OTI with frontend reach-time grids
- `frontend/src/components/MetricPanel.jsx`: Added `useMemo` hooks for RDS/OTI computation, `ScoreRow` component for colored label display
- `frontend/src/components/MetricPanel.css`: Added `.score-row`, `.score-number`, `.score-label` styles
- `frontend/src/App.jsx`: Passes `players` and `ball` props to MetricPanel

### References
1. Bauer, P., & Anzer, G. (2021). "Data-driven detection of counterpressing in professional football." *Data Mining and Knowledge Discovery*.
2. Spearman, W. (2018). "Beyond Expected Goals." *MIT Sloan Sports Analytics Conference*.
3. Alai. "Building Identity Through Data." alai.dk.
4. Linke, D., et al. (2016). "Real-time analysis of tactical behavior in soccer."

---

## BETA Tags & Metric Tooltips

### Changes
- Added **BETA** tag next to "Rest Defence" and "Threat Index" labels in the Match Metrics panel, matching the existing beta tag style used on Formation Lines.
- Added **hover tooltips** on all metric labels explaining what each metric measures:
  - Defensive Line: Mean x-position of the deepest 4 outfield defenders
  - Compactness: Convex hull area of outfield players
  - Pressure: Average defenders within 5 m of the ball carrier
  - Team Length / Width / Stretch Index: spatial spread measures
  - xT Gained / Conceded: cumulative expected threat
  - Rest Defence: composite score description (numerical balance + compactness + pitch control)
  - Threat Index: composite score description (spatial threat + overload + space dominance + momentum)
- Labels with tooltips show a dotted underline and help cursor on hover.

### Files Changed
- `frontend/src/components/MetricPanel.jsx`: Added `tooltip` field to METRICS, passed to `MetricRow` and `ScoreRow`, added BETA tag rendering
- `frontend/src/components/MetricPanel.css`: Added `.live-label[title]` hover styles and `.live-label .beta-tag` positioning

---

## Horizontally Collapsible Side Panels

### Problem
The original Match Metrics panel was a bottom section that required scrolling away from the pitch view. Metrics should be visible alongside the pitch at all times.

### Solution
Restructured the Analysis tab into a 3-column flex layout: left sidebar (home team) | main content | right sidebar (away team). Each sidebar is independently collapsible horizontally.

### Layout
- `analysis-layout`: flex row container with `align-items: flex-start`
- Panels are `position: sticky; top: 12px` so they stay visible while scrolling main content
- Open state: 290px wide, scrollable content with max-height
- Collapsed state: 34px vertical tab strip with team name written vertically
- Main content (`analysis-main`) uses `flex: 1` to fill remaining space
- Responsive: stacks vertically at <= 800px viewport width

### Interaction
- `<<` button in left panel header collapses it leftward; `>>` in right panel collapses rightward
- Collapsed state shows a clickable vertical tab with the team name (rotated text)
- Clicking the vertical tab expands the panel back
- State managed by `leftPanelOpen` / `rightPanelOpen` in App component

### Panel Content (per team)
- Team header with colored left-border accent
- Current phase badge
- Live metrics: Defensive Line, Compactness, Pressure, Team Length, Team Width, Stretch Index
- Cumulative xT Gained and xT Conceded
- Rest Defence and Threat Index scores (BETA)
- Per-team Phase Distribution donut chart

### Components
- `TeamMetricPanel`: Single-team metric display with per-team phase filtering (named export from MetricPanel.jsx)
- `TeamMetricRow` / `TeamScoreRow`: Single-team row variants (label | value layout)
- `PhaseDistChart`: Configurable `size` prop for compact display in side panels
- RDS/OTI scores computed once in `App.jsx` via `useMemo` and passed as props

### Files Changed
- `frontend/src/App.jsx`: Added `leftPanelOpen`/`rightPanelOpen` state; restructured Analysis tab into `analysis-layout` with `side-panel` aside elements flanking `analysis-main`
- `frontend/src/App.css`: Added `.analysis-layout`, `.analysis-main`, `.side-panel`, `.side-panel-inner`, `.side-panel-tab`, collapse/expand styles, sticky positioning, responsive breakpoints
- `frontend/src/components/MetricPanel.jsx`: Added `TeamMetricPanel` (named export), `TeamMetricRow`, `TeamScoreRow` components
- `frontend/src/components/MetricPanel.css`: Added `.team-metric-panel`, `.team-metric-row`, `.team-score-row`, `.team-phase-dist` styles

---

## Match Selector & Dynamic Team Colors

### Problem
The dashboard was hardcoded to a single match (J03WN1). Team colors were static (`#2b6da4`, `#c83c35`) and the match date was not displayed.

### Solution
Added a match catalog, match selector dropdown, dynamic team colors derived from club branding, and match date display.

### Match Catalog (`frontend/src/utils/matchCatalog.js`)
Static catalog of all 7 IDSSE matches extracted from the DFL XML matchinformation files:

| Match ID | Home | Away | Competition | Date |
|---|---|---|---|---|
| J03WN1 | VfL Bochum 1848 | Bayer 04 Leverkusen | Bundesliga | 2023-05-27 |
| J03WMX | 1. FC Koln | FC Bayern Munchen | Bundesliga | 2023-05-27 |
| J03WOH | Fortuna Dusseldorf | SSV Jahn Regensburg | 2. Bundesliga | 2022-08-26 |
| J03WOY | Fortuna Dusseldorf | F.C. Hansa Rostock | 2. Bundesliga | 2022-09-10 |
| J03WPY | Fortuna Dusseldorf | 1. FC Nurnberg | 2. Bundesliga | 2022-10-15 |
| J03WQQ | Fortuna Dusseldorf | FC St. Pauli | 2. Bundesliga | 2022-11-05 |
| J03WR9 | Fortuna Dusseldorf | 1. FC Kaiserslautern | 2. Bundesliga | 2022-11-11 |

Exports: `MATCH_CATALOG`, `getMatchInfo(matchId)`, `getTeamColor(teamId)`, `getTeamBadge(teamId)`, `formatMatchDate(dateStr)`

### Team Colors
Each club has a brand color derived from its logo:
- VfL Bochum: `#1560A4` (blue)
- Bayer 04 Leverkusen: `#E32221` (red)
- FC Koln: `#ED1C24` (red)
- FC Bayern Munchen: `#DC052D` (red)
- Fortuna Dusseldorf: `#E30613` (red)
- Hansa Rostock: `#003F87` (blue)
- FC St. Pauli: `#5D4037` (brown)
- 1. FC Nurnberg: `#8B1A2B` (burgundy)
- SSV Jahn Regensburg: `#D32F2F` (red)
- 1. FC Kaiserslautern: `#E30613` (red)

Colors are applied via CSS custom properties `--home-color` and `--away-color`, updated dynamically on match change.

### Team Badges
Logo PNG files in `frontend/public/assets/` mapped to team IDs in the catalog. Badges from the catalog are used as fallback when pipeline metadata doesn't include them.

### Match Selector
- Native `<select>` dropdown in the top nav (right-aligned via `.nav-actions`)
- Shows all 7 matches: `{Home} vs {Away} ({date})`
- On change: resets frame, phase filter, team selection, playback state

### Data-Unavailable State
When a selected match has no pipeline data yet:
- Score banner shows team names, badges, colors, result, and date from the catalog
- Content area shows a centered "Match data not yet available" message with an info icon
- No tabs content renders (guarded by `dataReady` flag)

### Files Changed
- `frontend/src/utils/matchCatalog.js`: New file - match catalog with team colors, badges, metadata
- `frontend/src/hooks/useMatchData.js`: Clears `matchData` to `null` before loading new match
- `frontend/src/App.jsx`: Added `selectedMatch` state with setter, match selector dropdown, dynamic colors from catalog, match date display, `dataReady` guard
- `frontend/src/App.css`: Added `.match-selector`, `.match-select`, `.data-status`, `.data-unavailable`, `.score-match-date` styles
- `frontend/src/components/PitchCanvas.jsx`: Replaced hardcoded `TEAM_COLORS` with dynamic `getTeamColor()` lookup
- `frontend/src/components/ThreatTimeline.jsx`: Replaced hardcoded colors with `getTeamColor()`
- `frontend/src/components/CumulativeXG.jsx`: Replaced hardcoded colors with `getTeamColor()`
- `frontend/src/components/MatchStats.jsx`: Replaced hardcoded colors with `getTeamColor()`
- `frontend/src/components/MetricPanel.jsx`: Replaced hardcoded colors with `getTeamColor()` and CSS variable fallbacks

---

## Threat Timeline - Soccer Ball Icon from react-icons

### Problem
Goal markers on the Threat Timeline used a hand-drawn SVG soccer ball (circle + pentagon + seam lines + arc segments, ~55 lines of manual D3 drawing code). This was fragile and hard to maintain.

### Solution
Replaced with `IoFootball` from `react-icons/io5` (Ionicons 5). A `getBallIcon()` helper uses `renderToStaticMarkup` to extract the icon's SVG path data once and caches it. D3 renders the icon as a nested `<svg>` element at each goal position.

### Files Changed
- `frontend/src/components/ThreatTimeline.jsx`: Imported `IoFootball` from `react-icons/io5`, replaced manual ball drawing with icon rendering
- `frontend/package.json`: Added `react-icons` dependency, removed `lucide-react`

*Last Updated: 2026-03-29*

---

## Replace Threat Timeline with Game Momentum + Player xT (2026-03-29)

### Problem
The Threat Timeline (per-minute xThreat bars) was difficult to interpret visually. xT is a per-event metric (per pass/carry), not naturally suited to a bar chart aggregated by minute. The user requested replacing it with more intuitive visualizations informed by literature review (Fernandez et al. 2020, Xie et al. 2021 PassVizor, The Athletic's game flow).

### Design Decisions (informed by literature)
1. **Game Momentum**: Uses actual xT values with bidirectional EMA (not activity counts). Per-minute sum of positive xT blended with shot xG, capped at 0.20 to prevent lone skyscrapers. Leading + lagging EMA creates pyramid shapes around spikes (The Athletic approach).
2. **Cumulative xT per team was removed**: Unlike cumulative xG (which has discrete steps at rare shot events), cumulative xT is a flow metric with hundreds of small increments producing a nearly smooth upward curve. The momentum chart already shows temporal team-level threat more effectively.
3. **Player xT contribution chart added**: Bar chart showing per-player xT from pass progression. Answers "who is the team's primary engine of ball progression?" -- one of the core xT use cases per the literature.

### Solution

#### Pipeline Changes
- **`pipeline/07_compute_xthreat.py`**: Modified `compute_xthreat_per_phase()` and `main()` to also return the enriched `events_df` with per-event `_xt` column (previously discarded after phase aggregation)
- **`pipeline/08_export_json.py`**: Added `export_event_xt()` function that writes `event_xt.json` containing:
  - `xt_events`: Events with non-zero xT (354 events for J03WN1) with player_id, team_id, minute, event_type, xT value
  - `all_events`: All 1429 events (kept for future use)
- **`tests/test_full_pipeline.py`**: Updated to capture enriched events_df from step 7 and pass it to step 8

#### Frontend Changes
- **`frontend/src/components/MomentumChart.jsx`** (new): xT-based tug-of-war bar chart
  - Per-minute: sum of positive xT per team, blended with max shot xG, capped at 0.20
  - Momentum = home_threat - away_threat
  - Bidirectional EMA (alpha=0.35): forward pass + backward pass averaged to create pyramid shapes
  - Bars colored by dominant team, goal markers (soccer ball icons), HT line, click-to-seek
- **`frontend/src/components/PlayerXT.jsx`** (new): Player xT contribution chart
  - Horizontal bar chart, side-by-side layout (home left, away right)
  - Top 10 players per team sorted by total positive xT from passes
  - Shared scale so cross-team comparison is meaningful
- **`frontend/src/components/MomentumChart.css`** (new)
- **`frontend/src/components/PlayerXT.css`** (new)
- **`frontend/src/App.jsx`**: Replaced `ThreatTimeline` with `MomentumChart`, replaced `CumulativeXT` with `PlayerXT`
- **`frontend/src/hooks/useMatchData.js`**: Added `event_xt.json` to data loading

#### Data Flow
```
Step 7: events_df gets _xt column -> returned alongside phases_df
Step 8: export_event_xt() writes event_xt.json (354 xT events + 1429 total events)
Frontend: useMatchData loads event_xt.json -> feeds MomentumChart and PlayerXT
```

### Result
- Game Momentum shows match flow with pyramid-shaped spikes around dangerous periods
- Player xT identifies ball progression engines (e.g., I. Ordets 0.70 xT for Bochum vs Frimpong 0.18 for Leverkusen)
- Chart order: Game Momentum -> Cumulative xG -> xT Contributions
- ThreatTimeline and CumulativeXT components preserved in codebase but no longer used

---

## Pitch Overlay: High-xT Pass Arrows & High-xG Shot Markers

### Goal
Highlight dangerous passes (high expected threat) and shots (high expected goals) directly on the pitch view, so users can see spatial context of key actions near the current playback time.

### Pipeline Changes

**File**: `pipeline/08_export_json.py`

- **`export_event_xt()`**: Now includes `start_x`, `start_y`, `end_x`, `end_y` (normalized 0-1 coordinates) for each xT event, sourced from `coordinates_x/y` and `end_coordinates_x/y` in the events DataFrame
- **`export_shot_xg()`**: Now includes `x`, `y` (normalized 0-1 coordinates) for each shot, sourced from `coordinates_x/y`

### Frontend Changes

**File**: `frontend/src/components/PitchCanvas.jsx`

- New props: `eventXt`, `shotXg`, `currentTime`
- **High-xT pass arrows** (threshold: xT >= 0.04):
  - Filters events within +/- 30 second window around `currentTime`
  - Draws team-colored arrows from pass start to end with white outline for contrast
  - Arrowhead at destination, xT value label at midpoint
  - Opacity fades based on temporal distance from current time
- **High-xG shot markers** (threshold: xG >= 0.08):
  - Filters shots within +/- 30 second window around `currentTime`
  - Draws concentric ring at shot location, radius proportional to xG value
  - Goals get a filled inner circle
  - "GOAL xG 0.49" or "xG 0.09" label above the marker
- Both overlays render after formation/shape graph overlays but before player dots and ball

**File**: `frontend/src/App.jsx`

- Passes `eventXt={matchData.eventXt}`, `shotXg={matchData.shotXg}`, `currentTime={currentTime}` to `PitchCanvas`

### Constants
- `XT_THRESHOLD = 0.04` (top ~4% of passes)
- `XG_THRESHOLD = 0.08` (above average shot quality)
- `TIME_WINDOW = 30` seconds (+/- from current time)

---

## Attacking Direction Awareness

### Problem
Kloppy's normalized coordinates (0-1) do NOT normalize attacking direction between halves. Teams switch ends at halftime, so the same team attacks toward x=0 in one half and x=1 in the other. This affected:
- **Step 2**: Defensive line height always assumed "lower x = deeper"
- **Step 7**: xT grid lookup assumed all teams attack toward x=1
- **Step 3**: Phase classifier thresholds for `ball_x` and `defensive_line_height` were direction-dependent
- **Frontend**: Forward-pass filter assumed home always attacks right

### Detection
Direction is auto-detected per team per period from shot locations:
```python
def _detect_attacking_direction(events_df, team_ids):
    # avg shot x > 0.5 => attacks right, else attacks left
    # Fallback: forward pass ratio, then default (home attacks right)
    # Returns: {(team_id, period_id): attacking_right}
```

For match J03WN1:
- Period 1: Bochum (home) attacks LEFT, Leverkusen (away) attacks RIGHT
- Period 2: Bochum attacks RIGHT, Leverkusen attacks LEFT

### Pipeline Fixes

**File**: `pipeline/02_compute_features.py`
- Added `_detect_attacking_direction()` (same logic as step 9)
- `main()` accepts optional `events_df` for direction detection
- `compute_defensive_line_height()` now takes `attacking_right` param:
  - When `attacking_right=True`: deepest = lowest x (unchanged)
  - When `attacking_right=False`: deepest = highest x, then mirrors to 'attacks right' space
- `ball_x` is mirrored to 'attacks right' space per team per frame for consistent phase thresholds

**File**: `pipeline/07_compute_xthreat.py`
- Added `_detect_attacking_direction()` (same logic)
- `compute_xthreat_for_event()` now takes `attacking_right` param
- When `attacking_right=False`, coordinates are mirrored (x = 1 - x) before xT grid lookup
- Result: xT values now correctly reflect threat relative to the opponent's goal regardless of period

**File**: `pipeline/08_export_json.py`
- `export_event_xt()` now includes `attacking_direction` map in the JSON output
- Each xT event includes `period_id` for frontend direction lookup

**File**: `tests/test_full_pipeline.py`
- Step 2 call now passes `events_df=events_df`

### Frontend Fix

**File**: `frontend/src/components/PitchCanvas.jsx`
- Forward-pass filter uses `attacking_direction` from `eventXt` JSON
- Looks up `dirMap[teamId_periodId]` to determine if team attacks right
- Forward = `end_x > start_x` when attacking right, `end_x < start_x` when attacking left

---

## README Media Additions (2026-04-24)

Added visual media to the top-level `README.md` so the project reads as a showcase, not just docs.

**New assets committed to the repo**:
- `docs/media/demo.mp4` (~45 MB) -- embedded demo video (copied from `Project/Video.mp4`)
- `docs/media/pitch-control.png` -- voronoi defensive-grid screenshot
- `docs/media/shape-graph.png` -- full-pitch Delaunay shape graph
- `docs/media/xg-shot.png` -- zoomed GOAL 0.49 xG shot scene
- `docs/media/xt-arrow.png` -- shape graph with xT 0.09 arrow overlay
- `docs/media/player-chip.png` -- single-player chip glyph used inline in components table
- `docs/final-report.pdf` -- CS 889 final report (~1.5 MB)

**README.md sections added**:
1. `## Demo` block with inline `<video>` tag and fallback MP4 link, placed immediately after the intro paragraph.
2. `## Features at a glance` 2x2 HTML table of feature screenshots with captions.
3. `## Resources` section between "Paper" and "Troubleshooting", linking the PDF and demo MP4.
4. Inline thumbnail of `player-chip.png` added to the `Lineups` row of the Frontend components table.

**Notes / constraints**:
- Larger `PhaseViz.mp4` (~50 MB) intentionally excluded to stay comfortably under GitHub's 50 MB warning threshold; only `Video.mp4` is embedded.
- pptx slides (~36 MB) not linked from README by user decision; PDF report is the canonical writeup.
