"""
Train a 16x12 Expected Threat (xT) grid using socceraction + StatsBomb open data.

Uses Karun Singh's Markov chain value iteration method via socceraction's
ExpectedThreat class. Trains on free StatsBomb competitions (World Cup 2018,
Champions League seasons, La Liga seasons, etc.) for robust transition matrices.

Run once offline; the resulting grid is committed to the repo.

Usage:
    python train_xt_model.py
"""

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message="credentials were not supplied")
warnings.filterwarnings("ignore", message="Inferred xy_fidelity")
warnings.filterwarnings("ignore", message="Inferred shot_fidelity")

from socceraction.data.statsbomb import StatsBombLoader
import socceraction.spadl as spadl
from socceraction.xthreat import ExpectedThreat


# Competitions to train on (competition_id, season_id, description)
COMPETITIONS = [
    (43, 3, "FIFA World Cup 2018"),
    (43, 106, "FIFA World Cup 2022"),
    (16, 4, "Champions League 2018/2019"),
    (16, 1, "Champions League 2017/2018"),
    (16, 2, "Champions League 2016/2017"),
    (11, 90, "La Liga 2020/2021"),
    (11, 42, "La Liga 2019/2020"),
    (11, 4, "La Liga 2018/2019"),
    (11, 1, "La Liga 2017/2018"),
    (9, 281, "1. Bundesliga 2023/2024"),
]

OUTPUT_PATH = Path(__file__).parent / "xt_grid_16x12.json"


def main():
    SBL = StatsBombLoader(getter="remote")

    all_actions = []
    total_games = 0

    for comp_id, season_id, desc in COMPETITIONS:
        try:
            games = SBL.games(competition_id=comp_id, season_id=season_id)
        except Exception as e:
            print(f"  Skipping {desc}: {e}")
            continue

        print(f"\n{desc}: {len(games)} games")

        for _, game in tqdm(games.iterrows(), total=len(games), desc=f"  {desc}"):
            game_id = game["game_id"]
            try:
                events = SBL.events(game_id)
                home_team_id = game.get("home_team_id", events["team_id"].unique()[0])
                actions = spadl.statsbomb.convert_to_actions(events, home_team_id=home_team_id)
                actions = spadl.play_left_to_right(actions, home_team_id=home_team_id)
                all_actions.append(actions)
                total_games += 1
            except Exception as e:
                print(f"    Game {game_id} failed: {e}")
                continue

    if total_games == 0:
        print("No games loaded. Exiting.")
        return

    print(f"\nTotal games loaded: {total_games}")
    all_actions_df = pd.concat(all_actions, ignore_index=True)
    print(f"Total actions: {len(all_actions_df)}")

    # Train 16x12 xT model
    print("\nTraining 16x12 xT model...")
    model = ExpectedThreat(l=16, w=12)
    model.fit(all_actions_df)

    grid = model.xT
    print(f"Grid shape: {grid.shape}")
    print(f"Value range: {grid.min():.6f} to {grid.max():.6f}")
    print(f"Vertically symmetric: {np.allclose(grid, grid[::-1, :])}")

    # Save
    with open(OUTPUT_PATH, "w") as f:
        json.dump(grid.tolist(), f)
    print(f"\nSaved to {OUTPUT_PATH}")

    # Print grid for inspection
    print("\nTrained xT grid (16x12):")
    for i, row in enumerate(grid):
        vals = " ".join(f"{v:.4f}" for v in row)
        print(f"  Row {i:2d}: {vals}")


if __name__ == "__main__":
    main()
