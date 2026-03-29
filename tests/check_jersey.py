from kloppy import sportec

tracking = sportec.load_tracking(
    raw_data='../data/DFL_04_03_positions_raw_observed_DFL-COM-000001_DFL-MAT-J03WN1.xml',
    meta_data='../data/DFL_02_01_matchinformation_DFL-COM-000001_DFL-MAT-J03WN1.xml',
    coordinates='kloppy',
    only_alive=True,
    sample_rate=0.001
)

for team in tracking.metadata.teams:
    print(f"\nTeam: {team.name}")
    for p in team.players:
        jersey = getattr(p, 'jersey_no', None)
        print(f"  {p.player_id}: {p.name} -> jersey_no={jersey}")
    print(f"  Player attrs: {[a for a in dir(team.players[0]) if not a.startswith('_')]}")
