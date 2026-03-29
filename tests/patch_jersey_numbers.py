"""Patch existing JSON files to add jersey numbers without re-running the full pipeline."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'pipeline'))

from kloppy import sportec

MATCH_ID = "J03WN1"
DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR = Path(__file__).parent.parent / "frontend" / "dist" / "data" / MATCH_ID

meta_file = list(DATA_DIR.glob(f"*matchinformation*{MATCH_ID}.xml"))[0]
tracking_file = list(DATA_DIR.glob(f"*positions_raw*{MATCH_ID}.xml"))[0]

print(f"Loading metadata for {MATCH_ID}...")
tracking = sportec.load_tracking(
    raw_data=str(tracking_file),
    meta_data=str(meta_file),
    coordinates='kloppy',
    only_alive=True,
    sample_rate=0.001
)

player_number_map = {}
for team in tracking.metadata.teams:
    for p in team.players:
        jersey = getattr(p, 'jersey_no', None)
        if jersey is not None:
            player_number_map[p.player_id] = int(jersey)

print(f"Found jersey numbers for {len(player_number_map)} players")
for pid, num in sorted(player_number_map.items(), key=lambda x: x[1]):
    print(f"  {pid} -> #{num}")

# Patch metadata.json
meta_path = OUTPUT_DIR / "metadata.json"
print(f"\nPatching {meta_path}...")
with open(meta_path, 'r', encoding='utf-8') as f:
    metadata = json.load(f)

for team in metadata['teams']:
    for player in team['players']:
        player['number'] = player_number_map.get(player['id'], None)

with open(meta_path, 'w', encoding='utf-8') as f:
    json.dump(metadata, f, indent=2, ensure_ascii=True)
print("  Done")

# Patch frames.json
frames_path = OUTPUT_DIR / "frames.json"
print(f"\nPatching {frames_path} ({frames_path.stat().st_size / 1024 / 1024:.1f} MB)...")
with open(frames_path, 'r') as f:
    frames = json.load(f)

patched = 0
for frame in frames:
    for player in frame['players']:
        if player['id'] in player_number_map:
            player['number'] = player_number_map[player['id']]
            patched += 1

with open(frames_path, 'w') as f:
    json.dump(frames, f, indent=2)

print(f"  Patched {patched} player entries across {len(frames)} frames")
print("\nDone!")
