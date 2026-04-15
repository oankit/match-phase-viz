# PhaseViz: Phase-Aware Post-Match Soccer Analytics Dashboard

CS 889 (Information Visualization) final project -- University of Waterloo, W26.

A coordinated multi-view dashboard that integrates possession-aware tactical phase classification with spatial overlays (pitch control, shape graphs), team formation comparison, and expected threat (xT) metrics. Built on the DFL IDSSE Bundesliga dataset.

---

## Repository layout

```
match-phase-viz/
|-- pipeline/        # Python data processing (9 steps)
|-- frontend/        # React + D3.js dashboard
|-- tests/           # Pipeline integration tests + re-export script
|-- data/            # Place Sportec XML files here
|-- docs/            # Implementation notes, analysis reports
|-- paper/           # LaTeX paper (VGTC format) + bibliography
|-- output/          # Pipeline artifacts (backup)
|-- IMPLEMENTATION_PLAN.md
|-- CLAUDE.md
```

---

## Prerequisites

- **Python** 3.10+
- **Node.js** 18+
- **npm** 9+
- ~5 GB disk space for full match processing at 25 Hz

---

## Data setup

The pipeline consumes Sportec/DFL IDSSE XML files. The dataset is open access under CC BY 4.0:

1. Download from the Scientific Data supplement: https://www.nature.com/articles/s41597-025-04505-y
2. Place the XML files in `data/` using this naming convention:
   ```
   data/
     matchinformation_J03WN1.xml
     events_raw_J03WN1.xml
     positions_raw_J03WN1.xml
   ```
3. Seven matches are available: `J03WMX`, `J03WN1`, `J03WPY`, `J03WOH`, `J03WQQ`, `J03WOY`, `J03WR9` (see `pipeline/config.py`).

---

## Running the pipeline

Install Python dependencies:

```bash
cd pipeline
pip install -r requirements.txt
```

Configure processing mode in `pipeline/config.py`:

```python
PROCESSING_MODE = 'production'   # 'testing' (fast, 1 Hz) or 'production' (full 25 Hz)
PRODUCTION_EXPORT_FPS = 4        # 4, 5, or 25 Hz for frontend playback
```

### Testing mode (fast -- recommended for first run)

For quick iteration and verification, use testing mode. This loads tracking data at 1 Hz (every 25th frame) and exports at 1 Hz, producing a functional dashboard in a couple of minutes:

1. Open `pipeline/config.py` and set:
   ```python
   PROCESSING_MODE = 'testing'
   ```
   This automatically sets `LOAD_SAMPLE_RATE = 0.04` (1 Hz) and `EXPORT_TARGET_FPS = 1`.

2. Run the pipeline:
   ```bash
   cd tests
   python test_full_pipeline.py
   ```

3. Expected output: ~2{,}700 frames, ~1--2 minutes total, ~6 MB of JSON. Playback will be choppy (1 frame per second) but all analytical views (timelines, momentum, formations, match stats) render correctly.

### Production mode (full quality)

For the final 25 Hz tracking quality used in the paper:

1. Set in `pipeline/config.py`:
   ```python
   PROCESSING_MODE = 'production'
   PRODUCTION_EXPORT_FPS = 4   # or 5, 25
   ```

2. Run the same pipeline command:
   ```bash
   cd tests
   python test_full_pipeline.py
   ```

3. Expected output: 68{,}377 frames processed, 11{,}397 frames exported at 4 Hz (or 68{,}377 at 25 Hz). Takes ~30--120 minutes (Step 5 formation detection is the bottleneck).

**Timing summary**:

| Mode | Load rate | Export rate | Frames exported | Total time | frames.json size |
|------|-----------|-------------|-----------------|------------|------------------|
| Testing | 1 Hz | 1 Hz | ~2{,}700 | ~2 min | ~6 MB |
| Production (4 Hz) | 25 Hz | 4 Hz | ~11{,}400 | ~30-60 min | ~48 MB |
| Production (25 Hz) | 25 Hz | 25 Hz | ~68{,}400 | ~60-120 min | ~294 MB |

Outputs are written to `frontend/public/data/<match_id>/`:
- `metadata.json` (teams, lineups, badges, goals, match stats)
- `frames.json` (tracking frames at export FPS)
- `phases.json` (phase segments with metrics + xT)
- `formations.json` (per-phase formations with shape graph edges)
- `pitch_control.json` (rest-defence grid per frame)
- `heatmaps.json` (KDE pressing heatmaps)
- `shot_xg.json`, `event_xt.json`

### Re-exporting without re-running the slow steps

If only the export FPS or a formatting change is needed, use the re-export script that loads the pre-computed voronoi/formations from disk:

```bash
cd tests
python reexport.py
```

---

## Running the frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 (or the port shown in the terminal). The dashboard auto-loads `J03WN1` by default. To change the match, edit `frontend/src/hooks/useMatchData.js`.

### Production build

```bash
cd frontend
npm run build
npm run preview
```

---

## Key pipeline steps

| Step | File | Purpose |
|------|------|---------|
| 1 | `01_load_data.py` | Load Sportec XML via kloppy |
| 2 | `02_compute_features.py` | Defensive line, compactness, pressure proxy, team length/width |
| 3 | `03_classify_phases.py` | Possession-aware phase classification + counter-attack detection |
| 4 | `04_compute_pitch_control.py` | Rest-defence grid inside convex hull |
| 5 | `05_compute_formations.py` | Shape graphs + EFPI template matching |
| 6 | `06_compute_pressing.py` | KDE heatmaps for high-press phases |
| 7 | `07_compute_xthreat.py` | Per-event xT using Karun Singh's grid |
| 8 | `08_export_json.py` | Export all outputs to JSON for frontend |
| 9 | `09_compute_match_stats.py` | Match + player stats (Athletic-style) |

---

## Frontend components

| Component | Purpose |
|-----------|---------|
| `PitchCanvas` | 25 Hz player animation, ball, pass arrows, overlay toggle (shape graph / pitch control / formation lines / none) |
| `Timeline` | Dual-team phase timelines, click-to-jump navigation |
| `MomentumChart` | Tug-of-war xT momentum chart with goal markers |
| `CumulativeXG` | Step chart of cumulative xG per team |
| `FormationComparisonPanel` | In-possession vs out-of-possession formation glyphs |
| `MatchStats` | 6 Athletic-style circle-rating stats per team |
| `Lineups` | Player cards with position, minutes, key stats |
| `PlayerXT` | Top xT contributors bar chart |
| `PlayerXG` | Top xG contributors bar chart |
| `MetricPanel` | Per-phase metric cards |
| `PhaseFilter` | Categorical filter pills |

---

## Configuration knobs

All in `pipeline/config.py`:

- `PROCESSING_MODE`: `'testing'` (1 Hz, ~2 min) or `'production'` (25 Hz, ~30-120 min)
- `PRODUCTION_EXPORT_FPS`: Frontend playback FPS (4, 5, or 25)
- `PHASE_THRESHOLDS`: Tracking-feature thresholds for each phase type
- `COUNTERATTACK_RULES`: Forward distance + velocity thresholds for event-based counter-attacks
- `SHAPE_GRAPH_ANGLE_THRESHOLD`: Angular stability threshold for shape graph edge pruning (default 45 degrees)
- `XTHREAT_GRID_SIZE`: xT grid dimensions (default 12x8)

---

## Algorithms and citations

- **Shape graphs**: Brandes et al. (2025) -- shape graphs and instantaneous inference of tactical positions. *npj Complexity*
- **EFPI formation matching**: Bekkers (2025) -- elastic formation and position identification. *arXiv:2506.23843*
- **RoleRep EM clustering**: Bialkowski et al. (2014)
- **SoccerCPD (Delaunay adjacency)**: Kim et al. (KDD 2022) -- adapted code in `docs/soccercpd/`
- **Counter-attack rules**: Bekkers and Sahasrabudhe (SSAC 2023)
- **xThreat model**: Singh (2019) -- 12x8 Markov chain grid, `pipeline/xt_grid_12x8.json`
- **Dataset**: Bassek et al. (2025) -- DFL IDSSE, CC BY 4.0

---

## Paper

The final report is in `paper/paper.tex` (VGTC conference format). To compile:

```bash
cd paper
pdflatex paper
bibtex paper
pdflatex paper
pdflatex paper
```

Or upload `paper.tex` and `references.bib` to Overleaf.

---

## Troubleshooting

**Pipeline fails at Step 1**: Ensure XML files are in `data/` with the exact naming `*matchinformation*<match_id>.xml`, `*events_raw*<match_id>.xml`, `*positions_raw*<match_id>.xml`.

**Frontend shows no data**: Confirm `frontend/public/data/<match_id>/` contains all JSON files. Re-run the pipeline or use `tests/reexport.py`.

**Large frames.json (>100 MB)**: Expected at 25 Hz export (~294 MB for a full match). Drop `PRODUCTION_EXPORT_FPS` to 4 for a ~1.5 MB file at the cost of playback smoothness.

**Formation labels missing**: Formations require at least 3 frames of consistent 10-player lineups per phase segment. Substitution-heavy phases may have no formation.

---

## License

Source code: MIT. Dataset: CC BY 4.0 (DFL Deutsche Fussball Liga).

---

## Acknowledgments

- DFL for releasing the IDSSE dataset under CC BY 4.0
- kloppy maintainers for the data loading library
- The Athletic's match dashboard for design inspiration
- Claude Code (Anthropic) provided implementation assistance; all design decisions, analytical direction, and algorithmic choices were made by the author
