import sys
sys.path.insert(0, '../../pipeline')

from kloppy import sportec
from pathlib import Path

data_path = Path('../../data')
meta_file = list(data_path.glob('*matchinformation*J03WN1.xml'))[0]
tracking_file = list(data_path.glob('*positions_raw*J03WN1.xml'))[0]
event_file = list(data_path.glob('*events_raw*J03WN1.xml'))[0]

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
        attrs = [a for a in dir(p) if not a.startswith('_')]
        if team.players.index(p) == 0:
            print(f"  Player attrs: {attrs}")
        starting = getattr(p, 'starting', None)
        starting_pos = getattr(p, 'starting_position', None)
        position = getattr(p, 'position', None)
        jersey = getattr(p, 'jersey_no', '?')
        print(f"  #{jersey:>3} {p.name:30s} starting={starting} starting_pos={starting_pos} position={position}")
