import json

with open('../../frontend/public/data/J03WN1/metadata.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

ps = d.get('player_stats', [])

home_id = d['teams'][0]['id']
away_id = d['teams'][1]['id']

for team_name, team_id in [(d['teams'][0]['name'], home_id), (d['teams'][1]['name'], away_id)]:
    team_players = [p for p in ps if p['team_id'] == team_id]
    starters = [p for p in team_players if p['is_starter']]
    subs = [p for p in team_players if not p['is_starter'] and p['minutes'] > 0]
    
    print(f"\n=== {team_name} ({len(starters)} starters, {len(subs)} subs) ===")
    print("  STARTERS:")
    for p in starters:
        print(f"    #{p.get('jersey_no', '?'):>3} {p['position_abbr']:>4} {p['name']:30s} {p['minutes']}min")
    print("  SUBS:")
    for p in subs:
        sub_on = p.get('sub_on', '?')
        print(f"    #{p.get('jersey_no', '?'):>3} {p['position_abbr']:>4} {p['name']:30s} {p['minutes']}min (on {sub_on}')")
