"""Check goals in all available matches."""
import json
from pathlib import Path

# Check both frontend and output directories
frontend_data = Path(__file__).parent / '../../frontend/public/data'
output_data = Path(__file__).parent / '../../output'

print("=== CHECKING ALL MATCHES FOR GOALS ===\n")

# Check frontend data
if frontend_data.exists():
    print("Frontend data matches:")
    for match_dir in sorted(frontend_data.iterdir()):
        if match_dir.is_dir():
            metadata_file = match_dir / 'metadata.json'
            if metadata_file.exists():
                with open(metadata_file, encoding='utf-8') as f:
                    metadata = json.load(f)
                goals = metadata.get('goals', [])
                teams = metadata.get('teams', [])

                print(f"\n{match_dir.name}:")
                if teams and len(teams) >= 2:
                    print(f"  {teams[0]['name']} vs {teams[1]['name']}")
                print(f"  Goals: {len(goals)}")

                if goals:
                    for g in goals:
                        # Find team name
                        team_name = 'Unknown'
                        for team in teams:
                            if team['id'] == g['team_id']:
                                team_name = team['name']
                                break
                        print(f"    {g['minute']}' - {team_name} ({g.get('player_name', 'Unknown')})")
                else:
                    print("    No goals recorded")

# Check output data (might have additional matches)
print("\n" + "=" * 50)
if output_data.exists():
    print("\nOutput data matches:")
    for match_dir in sorted(output_data.iterdir()):
        if match_dir.is_dir():
            metadata_file = match_dir / 'metadata.json'
            if metadata_file.exists():
                with open(metadata_file, encoding='utf-8') as f:
                    metadata = json.load(f)
                goals = metadata.get('goals', [])
                teams = metadata.get('teams', [])

                print(f"\n{match_dir.name}:")
                if teams and len(teams) >= 2:
                    print(f"  {teams[0]['name']} vs {teams[1]['name']}")
                print(f"  Goals: {len(goals)}")

                if goals:
                    for g in goals:
                        # Find team name
                        team_name = 'Unknown'
                        for team in teams:
                            if team['id'] == g['team_id']:
                                team_name = team['name']
                                break
                        print(f"    {g['minute']}' - {team_name} ({g.get('player_name', 'Unknown')})")