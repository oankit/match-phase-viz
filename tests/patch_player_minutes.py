"""Re-compute player stats (with red card fix) and patch metadata.json."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'pipeline'))

from kloppy import sportec
import importlib
stats_mod = importlib.import_module('09_compute_match_stats')

MATCH_ID = "J03WN1"
DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR = Path(__file__).parent.parent / "frontend" / "dist" / "data" / MATCH_ID

meta_file = list(DATA_DIR.glob(f"*matchinformation*{MATCH_ID}.xml"))[0]
event_file = list(DATA_DIR.glob(f"*events_raw*{MATCH_ID}.xml"))[0]
tracking_file = list(DATA_DIR.glob(f"*positions_raw*{MATCH_ID}.xml"))[0]

print("Loading events...")
event_dataset = sportec.load_event(
    event_data=str(event_file),
    meta_data=str(meta_file),
    coordinates='kloppy'
)
events_df = event_dataset.to_df()

print("Loading tracking metadata...")
tracking_dataset = sportec.load_tracking(
    raw_data=str(tracking_file),
    meta_data=str(meta_file),
    coordinates='kloppy',
    only_alive=True,
    sample_rate=0.001
)

print("Computing match & player stats...")
match_stats, player_stats = stats_mod.compute_all(events_df, tracking_dataset)

# Show Adli's minutes
adli_id = 'DFL-OBJ-J01KDN'
if adli_id in player_stats:
    p = player_stats[adli_id]
    print(f"\nAdli: minutes={p['minutes']}, sub_off={p['sub_off']}, sent_off={p.get('sent_off', False)}")

# Patch metadata.json
meta_path = OUTPUT_DIR / "metadata.json"
print(f"\nPatching {meta_path}...")
with open(meta_path, 'r', encoding='utf-8') as f:
    metadata = json.load(f)

metadata['match_stats'] = match_stats

# Convert player_stats dict to array (frontend expects array)
stats_list = []
for pid, ps in player_stats.items():
    entry = dict(ps)
    for k, v in entry.items():
        if hasattr(v, 'item'):
            entry[k] = v.item()
    stats_list.append(entry)

metadata['player_stats'] = stats_list

with open(meta_path, 'w', encoding='utf-8') as f:
    json.dump(metadata, f, indent=2, ensure_ascii=True)

# Also copy to public
public_path = OUTPUT_DIR.parent.parent.parent / "public" / "data" / MATCH_ID / "metadata.json"
if public_path.parent.exists():
    with open(public_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=True)
    print(f"Also updated {public_path}")

print("Done!")
