import json

with open('../../frontend/public/data/J03WN1/metadata.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

ps = d.get('player_stats', [])
print(f"Total players: {len(ps)}")
print()

for p in ps:
    name = p.get('name', '?')
    jersey = p.get('jersey_no', '?')
    pos = p.get('position_abbr', '?')
    starter = p.get('is_starter', '?')
    team = p.get('team_id', '?')
    has_special = any(ord(c) > 127 for c in name)
    marker = ' <-- special chars' if has_special else ''
    print(f"  #{jersey:>2} {pos:>4} {name:30s} team={team[-3:]} starter={starter}{marker}")
