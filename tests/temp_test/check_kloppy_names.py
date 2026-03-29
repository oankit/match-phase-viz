import sys
sys.path.insert(0, '../../pipeline')

from kloppy import sportec
from pathlib import Path

data_path = Path('../../data')
meta_file = list(data_path.glob('*matchinformation*J03WN1.xml'))[0]
tracking_file = list(data_path.glob('*positions_raw*J03WN1.xml'))[0]

tracking = sportec.load_tracking(
    raw_data=str(tracking_file),
    meta_data=str(meta_file),
    coordinates="kloppy",
    only_alive=True,
    sample_rate=0.04
)

for team in tracking.metadata.teams:
    print(f"\n=== {team.name} ===")
    for p in team.players:
        name = p.name
        has_special = any(ord(c) > 127 for c in name) if name else False
        jersey = getattr(p, 'jersey_no', '?')
        pos = str(p.starting_position) if hasattr(p, 'starting_position') and p.starting_position else '?'
        marker = f" <-- special: {[hex(ord(c)) for c in name if ord(c) > 127]}" if has_special else ""
        print(f"  #{jersey:>3} {name:30s} pos={pos}{marker}")
