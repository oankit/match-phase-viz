"""
Step 5: Formation Graphs

Adapted from RoleRep (Bialkowski et al. 2014) and SoccerCPD (Kim et al. 2022).
Implements frame-by-frame role assignment using EM-like algorithm.

Core algorithm:
1. Initialize: fit MVN distributions per role
2. E-step: assign players to roles using Hungarian algorithm
3. M-step: re-estimate role distributions from assignments
4. Repeat until convergence
5. Compute Delaunay adjacency graph
6. Aggregate mean positions and adjacency per phase

Reference: docs/soccercpd/rolerep.py, docs/soccercpd/soccercpd.py
"""

import numpy as np
import pandas as pd
from scipy.stats import multivariate_normal
from scipy.optimize import linear_sum_assignment
from scipy.spatial import Delaunay
from tqdm import tqdm

import config


def normalize_locs(positions):
    """
    Normalize player positions by centering at team centroid.

    From rolerep.py: normalize_locs()
    """
    if len(positions) == 0:
        return positions

    centroid = positions.mean(axis=0)
    return positions - centroid


def estimate_mvn(role_positions):
    """
    Fit multivariate normal distribution for a role.

    From rolerep.py: estimate_mvn()

    Args:
        role_positions: (N, 2) array of positions assigned to this role

    Returns:
        dict with 'mean' and 'cov', or None if not enough data
    """
    if len(role_positions) < 2:
        return None

    mean = role_positions.mean(axis=0)
    cov = np.cov(role_positions.T)

    # Regularization to ensure positive definite
    cov += np.eye(2) * 1e-4

    return {'mean': mean, 'cov': cov}


def update_params(positions_list, assignments_list, num_roles=10):
    """
    Update role distributions from current assignments.

    From rolerep.py: update_params()

    Args:
        positions_list: List of (N, 2) position arrays per frame
        assignments_list: List of (N,) assignment arrays per frame
        num_roles: Number of roles

    Returns:
        List of dicts with 'mean' and 'cov' per role
    """
    role_distns = []

    for role_idx in range(num_roles):
        role_positions = []

        for positions, assignments in zip(positions_list, assignments_list):
            # Get positions assigned to this role
            mask = assignments == role_idx
            if mask.any():
                role_positions.append(positions[mask][0])  # Should be exactly 1

        distn = estimate_mvn(np.array(role_positions) if role_positions else np.empty((0, 2)))

        if distn is None:
            # Fallback: use default distribution
            distn = {'mean': np.array([0.0, 0.0]), 'cov': np.eye(2) * 0.01}

        role_distns.append(distn)

    return role_distns


def hungarian(positions, role_distns):
    """
    Assign players to roles using Hungarian algorithm with MVN cost.

    From rolerep.py: hungarian()

    Args:
        positions: (N, 2) array of player positions
        role_distns: List of role distributions

    Returns:
        Tuple of (assignments, cost):
            - assignments: (N,) array of role indices
            - cost: mean assignment cost
    """
    num_players = len(positions)
    num_roles = len(role_distns)

    # Compute cost matrix: cost[player][role] = -log(pdf(position | role))
    cost_mat = np.zeros((num_players, num_roles))

    for player_idx in range(num_players):
        player_pos = positions[player_idx]

        for role_idx in range(num_roles):
            role_dist = role_distns[role_idx]

            try:
                mvn = multivariate_normal(mean=role_dist['mean'], cov=role_dist['cov'])
                log_prob = mvn.logpdf(player_pos)
                cost_mat[player_idx, role_idx] = -log_prob
            except:
                cost_mat[player_idx, role_idx] = 1e6

    # Solve assignment problem
    row_ind, col_ind = linear_sum_assignment(cost_mat)

    # Create assignment array
    assignments = np.zeros(num_players, dtype=int)
    assignments[row_ind] = col_ind

    # Compute mean cost
    mean_cost = cost_mat[row_ind, col_ind].mean()

    return assignments, mean_cost


def delaunay_edge_mat(coords):
    """
    Apply Delaunay triangulation to obtain role-adjacency matrix.

    From soccercpd.py: delaunay_edge_mat()

    Args:
        coords: (N, 2) array of positions

    Returns:
        (N, N) adjacency matrix
    """
    if len(coords) < 3:
        return np.zeros((len(coords), len(coords)))

    try:
        tri_pts = Delaunay(coords).simplices
        edges = np.concatenate((tri_pts[:, :2], tri_pts[:, 1:], tri_pts[:, ::2]), axis=0)
        edge_mat = np.zeros((coords.shape[0], coords.shape[0]))
        edge_mat[edges[:, 0], edges[:, 1]] = 1
        return np.clip(edge_mat + edge_mat.T, 0, 1)
    except:
        # Delaunay failed (collinear points)
        return np.zeros((len(coords), len(coords)))


def run_rolerep(positions_list, max_iter=10, tol=0.005, verbose=False):
    """
    Run RoleRep EM algorithm to assign roles per frame.

    From rolerep.py: run()

    Args:
        positions_list: List of (N, 2) normalized position arrays per frame
        max_iter: Maximum iterations
        tol: Convergence tolerance
        verbose: Print iteration costs

    Returns:
        Tuple of (role_distns, assignments_list):
            - role_distns: List of role distributions
            - assignments_list: List of role assignments per frame
    """
    if len(positions_list) == 0:
        return [], []

    num_roles = len(positions_list[0])

    # Initialize role distributions: simple percentile-based
    # Sort players by x-coordinate and assign roles 0-9
    initial_assignments = []
    for positions in positions_list:
        sorted_idx = np.argsort(positions[:, 0])
        assignments = np.zeros(num_roles, dtype=int)
        assignments[sorted_idx] = np.arange(num_roles)
        initial_assignments.append(assignments)

    role_distns = update_params(positions_list, initial_assignments, num_roles)

    cost_prev = float('inf')

    for i_iter in range(max_iter):
        # E-step: assign players to roles using Hungarian algorithm
        assignments_list = []
        total_cost = 0

        for positions in positions_list:
            assignments, cost = hungarian(positions, role_distns)
            assignments_list.append(assignments)
            total_cost += cost

        cost_new = total_cost / len(positions_list)

        if verbose:
            print(f"    Iter {i_iter + 1}: cost={cost_new:.3f}")

        # Check convergence
        if cost_new + tol > cost_prev:
            if verbose:
                print(f"    Converged after {i_iter + 1} iterations")
            break

        # M-step: update role distributions
        role_distns = update_params(positions_list, assignments_list, num_roles)
        cost_prev = cost_new

    return role_distns, assignments_list


def compute_formation_for_phase(phase_frames, team_players, player_team_map):
    """
    Compute formation graph for a single phase segment.

    Args:
        phase_frames: DataFrame of tracking frames for this phase
        team_players: List of player IDs (all team players, will filter to on-field)
        player_team_map: dict mapping player_id to team_id

    Returns:
        dict with formation data, or None if insufficient data
    """
    # Extract positions for each frame, identifying which players are on field
    positions_list = []
    on_field_players = None  # Will be determined from first valid frame

    for idx in range(len(phase_frames)):
        row = phase_frames.iloc[idx]
        frame_positions = []
        frame_player_ids = []

        for player_id in team_players:
            x_col = f'{player_id}_x'
            y_col = f'{player_id}_y'

            if x_col in row.index and y_col in row.index:
                x = row[x_col]
                y = row[y_col]

                if not (pd.isna(x) or pd.isna(y)):
                    frame_positions.append([x, y])
                    frame_player_ids.append(player_id)

        # Set on-field players from first frame with 11 players (10 outfield + GK)
        if on_field_players is None and len(frame_positions) == 11:
            # Exclude goalkeeper (player with lowest x-coordinate)
            positions_array = np.array(frame_positions)
            gk_idx = np.argmin(positions_array[:, 0])

            on_field_players = [pid for i, pid in enumerate(frame_player_ids) if i != gk_idx]
            on_field_positions = [pos for i, pos in enumerate(frame_positions) if i != gk_idx]

            # Normalize and store first frame
            positions = np.array(on_field_positions)
            positions = normalize_locs(positions)
            positions_list.append(positions)
            continue

        # Only use frames where the same 10 outfield players are present
        if on_field_players is not None:
            # Get positions for the 10 outfield players
            outfield_positions = []
            for player_id in on_field_players:
                try:
                    idx_in_frame = frame_player_ids.index(player_id)
                    outfield_positions.append(frame_positions[idx_in_frame])
                except ValueError:
                    # Player not in this frame (substitution)
                    break

            # Only use if all 10 players are present
            if len(outfield_positions) == 10:
                # Normalize positions
                positions = np.array(outfield_positions)
                positions = normalize_locs(positions)
                positions_list.append(positions)

    if len(positions_list) < 3:
        # Not enough frames
        return None

    # Run RoleRep
    role_distns, assignments_list = run_rolerep(positions_list, max_iter=5, tol=0.01, verbose=False)

    if len(assignments_list) == 0:
        return None

    # Compute mean positions and adjacency
    role_positions_list = []
    adj_matrices = []
    num_roles = len(positions_list[0])

    for positions, assignments in zip(positions_list, assignments_list):
        # Reorder by role
        role_ordered = np.zeros((num_roles, 2))
        for player_idx, role_idx in enumerate(assignments):
            role_ordered[role_idx] = positions[player_idx]

        role_positions_list.append(role_ordered)

        # Compute Delaunay adjacency
        adj = delaunay_edge_mat(role_ordered)
        adj_matrices.append(adj)

    # Aggregate
    mean_positions = np.mean(role_positions_list, axis=0)  # (10, 2)
    mean_adjacency = np.mean(adj_matrices, axis=0)  # (10, 10)

    # Compute stability (positional variance per role)
    role_positions_array = np.array(role_positions_list)  # (num_frames, 10, 2)
    positional_variance = np.var(role_positions_array, axis=0)  # (10, 2)
    stability_scores = 1.0 / (1.0 + positional_variance.sum(axis=1))  # (10,)

    return {
        'mean_positions': mean_positions,
        'mean_adjacency': mean_adjacency,
        'stability_scores': stability_scores,
        'num_frames': len(positions_list),
    }


def compute_formations_for_team(tracking_df, phases_df, player_team_map, team_id):
    """
    Compute formation graphs for one team across all phases.

    Args:
        tracking_df: Tracking DataFrame (wide format)
        phases_df: Phase segments DataFrame from Step 3
        player_team_map: dict mapping player_id to team_id
        team_id: Team ID to process

    Returns:
        List[dict]: Formation data per phase segment
    """
    print(f"\n  Processing team: {team_id}")

    # Get all players for this team (will filter to on-field 10 per phase)
    team_players = sorted([pid for pid, tid in player_team_map.items() if tid == team_id])

    print(f"    Total players in roster: {len(team_players)}")

    # Get team's phase segments
    team_phases = phases_df[phases_df['team_id'] == team_id].copy()
    print(f"    Phase segments: {len(team_phases)}")

    formations = []

    for phase_idx, phase_row in tqdm(team_phases.iterrows(), total=len(team_phases), desc=f"  Formations ({team_id})"):
        # Get frames for this phase
        phase_mask = (
            (tracking_df['timestamp'] >= phase_row['start_time']) &
            (tracking_df['timestamp'] <= phase_row['end_time'])
        )
        phase_frames = tracking_df[phase_mask].copy()

        if len(phase_frames) == 0:
            continue

        # Compute formation for this phase
        formation = compute_formation_for_phase(phase_frames, team_players, player_team_map)

        if formation is not None:
            formations.append({
                'phase_id': int(phase_row['phase_id']),
                'phase_type': phase_row['phase_type'],
                'team_id': team_id,
                'mean_positions': formation['mean_positions'].tolist(),
                'mean_adjacency': formation['mean_adjacency'].tolist(),
                'stability_scores': formation['stability_scores'].tolist(),
                'num_frames': formation['num_frames'],
            })

    print(f"    Computed {len(formations)} formations")

    return formations


def compute_all_formations(tracking_df, phases_df, player_team_map):
    """
    Compute formation graphs for all teams and phases.

    Args:
        tracking_df: Tracking DataFrame (wide format)
        phases_df: Phase segments DataFrame from Step 3
        player_team_map: dict mapping player_id to team_id

    Returns:
        List[dict]: Formation data for all phases and teams
    """
    print("Computing formation graphs...")

    teams = list(set(player_team_map.values()))
    print(f"  Teams: {teams}")

    all_formations = []

    for team_id in teams:
        team_formations = compute_formations_for_team(
            tracking_df, phases_df, player_team_map, team_id
        )
        all_formations.extend(team_formations)

    print(f"\n  Total formations: {len(all_formations)}")

    return all_formations


def main(tracking_dataset, tracking_df, phases_df):
    """
    Main entry point for Step 5.

    Args:
        tracking_dataset: Kloppy TrackingDataset object (for metadata)
        tracking_df: Tracking DataFrame (wide format)
        phases_df: Phase segments DataFrame from Step 3

    Returns:
        List[dict]: Formation data
    """
    print("\n" + "=" * 80)
    print("STEP 5: FORMATION GRAPHS")
    print("=" * 80)

    # Get player-team mapping
    player_team_map = {}
    for team in tracking_dataset.metadata.teams:
        team_id = team.team_id
        for player in team.players:
            player_team_map[player.player_id] = team_id

    # Compute formations
    formations = compute_all_formations(tracking_df, phases_df, player_team_map)

    print("\n[OK] Formation computation complete")

    # Show sample
    if len(formations) > 0:
        sample = formations[0]
        print(f"\nSample formation (phase {sample['phase_id']}):")
        print(f"  Phase type: {sample['phase_type']}")
        print(f"  Team: {sample['team_id']}")
        print(f"  Frames: {sample['num_frames']}")
        print(f"  Mean positions shape: {np.array(sample['mean_positions']).shape}")
        print(f"  Mean adjacency shape: {np.array(sample['mean_adjacency']).shape}")
        print(f"  Stability scores (first 3): {np.array(sample['stability_scores'])[:3]}")

    return formations


if __name__ == "__main__":
    print("\n[INFO] This script requires tracking_dataset, tracking_df, and phases_df.")
    print("Run as part of the pipeline.")
