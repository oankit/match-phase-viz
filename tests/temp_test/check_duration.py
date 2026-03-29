"""Check match duration across all data files."""
import json
from pathlib import Path

data_dir = Path('../../frontend/public/data/J03WN1')

# Frames
with open(data_dir / 'frames.json') as f:
    frames = json.load(f)
print(f"FRAMES: {len(frames)} frames")
if frames:
    print(f"  First: t={frames[0]['t']:.1f}s ({frames[0]['t']/60:.1f}min)")
    print(f"  Last:  t={frames[-1]['t']:.1f}s ({frames[-1]['t']/60:.1f}min)")

# Phases
with open(data_dir / 'phases.json') as f:
    phases = json.load(f)
print(f"\nPHASES: {len(phases)} phases")
if phases:
    print(f"  First: start={phases[0]['start']:.1f}s ({phases[0]['start']/60:.1f}min)")
    print(f"  Last:  end={phases[-1]['end']:.1f}s ({phases[-1]['end']/60:.1f}min)")
    max_end = max(p['end'] for p in phases)
    print(f"  Max end time: {max_end:.1f}s ({max_end/60:.1f}min)")

# Metadata
with open(data_dir / 'metadata.json', encoding='utf-8') as f:
    meta = json.load(f)
print(f"\nMETADATA:")
print(f"  duration: {meta.get('duration', 'NOT SET')}")
if 'goals' in meta:
    for g in meta['goals']:
        print(f"  Goal: {g.get('player_name','?')} min={g.get('minute','?')} "
              f"match_seconds={g.get('match_seconds','?')} period={g.get('period','?')}")

# Check other data files
for fname in ['formations.json', 'heatmaps.json', 'pitch_control.json']:
    fpath = data_dir / fname
    if fpath.exists():
        with open(fpath) as f:
            data = json.load(f)
        if isinstance(data, list) and len(data) > 0:
            print(f"\n{fname}: {len(data)} entries")
            if 'phase_id' in data[0]:
                phase_ids = [d['phase_id'] for d in data]
                print(f"  Phase IDs: {min(phase_ids)} - {max(phase_ids)}")
