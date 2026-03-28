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
| 7 | xThreat |  Complete | � Not tested | Simplified MVP model |
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
- Identifies goalkeeper as player with lowest x-coordinate per frame

**Key Adaptations from Reference Code**:
- Stripped: `.ugp` format handling, session management, player period tracking, MAX_SWITCH_RATE filtering
- Kept: Core EM algorithm, `delaunay_edge_mat()` (exact copy), convergence logic
- Adapted: Input format changed from custom to kloppy DataFrame

**Test Results**:
-  Computed 90 formations (78 for one team, 12 for the other)
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
   test_step1_load.py          Passing
   test_step2_features.py      Passing (via test_pipeline_1_2_3.py)
   test_step3_phases.py        Passing (via test_pipeline_1_2_3.py)
   test_step4_voronoi.py       Passing
   test_step5_formations.py    Passing
   test_step6_pressing.py      Passing
   test_step7_xthreat.py      � To be created
   test_step8_export.py       � To be created
```

**Integration Test**:
- `pipeline/test_pipeline_1_2_3.py`: Tests Steps 1-3 together  Passing

---

## Known Issues & Limitations

### Data Issues
1. **Empty event data**: Some phases have 0 defensive actions (expected for certain phase types)
2. **Substitutions**: Formation computation stops using frames after a substitution occurs mid-phase

### Implementation Limitations
1. **xThreat Model**: Using simplified position-based model instead of trained transition matrix
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

### Why simplified xThreat?
- Full xThreat requires training on large datasets (StatsBomb open data)
- Simplified model provides correct data structure for frontend
- Can be replaced with trained model later without frontend changes

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

### xThreat Model Upgrade ✓
- Replaced hand-crafted linear threat model with pre-computed Markov chain xT grid
- Source: Karun Singh's xT model (12x8 grid), trained on real match data
- Grid file: `pipeline/xt_grid_12x8.json`, values range 0.006-0.257
- No training needed -- loaded pre-built grid

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
