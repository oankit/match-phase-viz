"""Check if kloppy shot events have pre-computed xG values."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'pipeline'))

from kloppy import sportec

MATCH_ID = "J03WN1"
DATA_DIR = Path(__file__).parent.parent / "data"

meta_file = list(DATA_DIR.glob(f"*matchinformation*{MATCH_ID}.xml"))[0]
event_file = list(DATA_DIR.glob(f"*events_raw*{MATCH_ID}.xml"))[0]

event_dataset = sportec.load_event(
    event_data=str(event_file),
    meta_data=str(meta_file),
    coordinates='kloppy'
)
events_df = event_dataset.to_df()

shots = events_df[events_df['event_type'] == 'SHOT']

print(f"Total shots: {len(shots)}")
print(f"\nAll columns: {events_df.columns.tolist()}")
print(f"\nShot-specific columns containing 'xg' or 'expected':")
for col in events_df.columns:
    if 'xg' in col.lower() or 'expected' in col.lower() or 'xgoal' in col.lower():
        print(f"  {col}")

print("\n--- All shot rows with all columns ---")
for idx, row in shots.iterrows():
    print(f"\n=== Shot by {row.get('player_id', '?')} at {row.get('timestamp', '?')} ===")
    for col in shots.columns:
        val = row[col]
        if val is not None and str(val) != 'nan' and str(val) != 'NaT':
            print(f"  {col}: {val}")
