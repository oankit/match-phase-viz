"""
Step 5: Formation Graphs with Shape Graph Detection + EFPI Template Matching

Combines RoleRep (Bialkowski et al. 2014) for stable role assignment with
shape graphs (Brandes et al. 2025, Sotudeh 2026) for edge filtering and
EFPI-style template matching (Bekkers 2025) for formation label detection.

Pipeline:
1. RoleRep EM assigns consistent role IDs across frames in a phase
2. Aggregate mean positions per role
3. Compute shape graph (iterative Delaunay edge removal by angular stability)
4. EFPI template matching: Hungarian algorithm against predefined formations
5. Handles 10-man teams (red card) with 9-player templates

Reference: docs/soccercpd/rolerep.py, docs/soccercpd/soccercpd.py
"""

import numpy as np
import pandas as pd
from scipy.stats import multivariate_normal
from scipy.optimize import linear_sum_assignment
from scipy.spatial import Delaunay
from tqdm import tqdm

import config
from formation_templates import get_templates


# =============================================================================
# Normalization
# =============================================================================

def normalize_locs(positions):
    """
    Normalize player positions by centering at team centroid.

    From rolerep.py: normalize_locs()
    """
    if len(positions) == 0:
        return positions

    centroid = positions.mean(axis=0)
    return positions - centroid


# =============================================================================
# RoleRep EM (kept for stable role identity across frames)
# =============================================================================

def estimate_mvn(role_positions):
    """
    Fit multivariate normal distribution for a role.

    From rolerep.py: estimate_mvn()
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
    """
    role_distns = []

    for role_idx in range(num_roles):
        role_positions = []

        for positions, assignments in zip(positions_list, assignments_list):
            mask = assignments == role_idx
            if mask.any():
                role_positions.append(positions[mask][0])

        distn = estimate_mvn(np.array(role_positions) if role_positions else np.empty((0, 2)))

        if distn is None:
            distn = {'mean': np.array([0.0, 0.0]), 'cov': np.eye(2) * 0.01}

        role_distns.append(distn)

    return role_distns


def hungarian(positions, role_distns):
    """
    Assign players to roles using Hungarian algorithm with MVN cost.

    From rolerep.py: hungarian()
    """
    num_players = len(positions)
    num_roles = len(role_distns)

    cost_mat = np.zeros((num_players, num_roles))

    for player_idx in range(num_players):
        player_pos = positions[player_idx]

        for role_idx in range(num_roles):
            role_dist = role_distns[role_idx]

            try:
                mvn = multivariate_normal(mean=role_dist['mean'], cov=role_dist['cov'])
                log_prob = mvn.logpdf(player_pos)
                cost_mat[player_idx, role_idx] = -log_prob
            except Exception:
                cost_mat[player_idx, role_idx] = 1e6

    row_ind, col_ind = linear_sum_assignment(cost_mat)

    assignments = np.zeros(num_players, dtype=int)
    assignments[row_ind] = col_ind

    mean_cost = cost_mat[row_ind, col_ind].mean()

    return assignments, mean_cost


def run_rolerep(positions_list, max_iter=10, tol=0.005, verbose=False):
    """
    Run RoleRep EM algorithm to assign roles per frame.

    From rolerep.py: run()
    """
    if len(positions_list) == 0:
        return [], []

    num_roles = len(positions_list[0])

    # Initialize: sort players by x-coordinate and assign roles 0-9
    initial_assignments = []
    for positions in positions_list:
        sorted_idx = np.argsort(positions[:, 0])
        assignments = np.zeros(num_roles, dtype=int)
        assignments[sorted_idx] = np.arange(num_roles)
        initial_assignments.append(assignments)

    role_distns = update_params(positions_list, initial_assignments, num_roles)

    cost_prev = float('inf')

    for i_iter in range(max_iter):
        assignments_list = []
        total_cost = 0

        for positions in positions_list:
            assignments, cost = hungarian(positions, role_distns)
            assignments_list.append(assignments)
            total_cost += cost

        cost_new = total_cost / len(positions_list)

        if verbose:
            print(f"    Iter {i_iter + 1}: cost={cost_new:.3f}")

        if cost_new + tol > cost_prev:
            if verbose:
                print(f"    Converged after {i_iter + 1} iterations")
            break

        role_distns = update_params(positions_list, assignments_list, num_roles)
        cost_prev = cost_new

    return role_distns, assignments_list


# =============================================================================
# Shape Graph (Brandes et al. 2025, Sotudeh 2026 Algorithm 1)
# =============================================================================

def _angle_at_vertex(p, q, v):
    """
    Compute angle (degrees) at vertex v in triangle (p, q, v).

    Uses dot product: angle = arccos((vp . vq) / (|vp| * |vq|))
    """
    vp = p - v
    vq = q - v
    cos_angle = np.dot(vp, vq) / (np.linalg.norm(vp) * np.linalg.norm(vq) + 1e-12)
    cos_angle = np.clip(cos_angle, -1.0, 1.0)
    return np.degrees(np.arccos(cos_angle))


def compute_shape_graph(coords, angle_threshold=None):
    """
    Compute shape graph via iterative Delaunay edge removal.

    Algorithm 1 from Brandes et al. 2025 / Sotudeh 2026 thesis:
    1. Compute Delaunay triangulation
    2. For each interior edge (shared by 2 triangles), compute angular stability
       = 180 - angle_at_opposite_vertex_a - angle_at_opposite_vertex_b
    3. Remove edges with stability < threshold
    4. Repeat until no more edges are removed

    Boundary edges (shared by only 1 triangle) are always kept.

    Args:
        coords: (N, 2) array of player positions
        angle_threshold: degrees (default from config)

    Returns:
        Tuple of (adjacency_matrix, edge_list):
            - adjacency_matrix: (N, N) binary
            - edge_list: list of [i, j] pairs
    """
    if angle_threshold is None:
        angle_threshold = config.SHAPE_GRAPH_ANGLE_THRESHOLD

    n = len(coords)
    if n < 3:
        return np.zeros((n, n)), []

    # Step 1: Compute Delaunay triangulation
    try:
        tri = Delaunay(coords)
    except Exception:
        return np.zeros((n, n)), []

    # Build initial edge set and edge-to-triangles map
    simplices = tri.simplices  # (M, 3) array of vertex indices

    # Map each edge (as sorted tuple) to list of opposing vertices
    edge_to_opposite = {}
    for simplex in simplices:
        # Each triangle has 3 edges; for each edge, the opposing vertex is the third
        for i in range(3):
            p_idx = simplex[i]
            q_idx = simplex[(i + 1) % 3]
            opposite_idx = simplex[(i + 2) % 3]
            edge_key = (min(p_idx, q_idx), max(p_idx, q_idx))
            if edge_key not in edge_to_opposite:
                edge_to_opposite[edge_key] = []
            edge_to_opposite[edge_key].append(opposite_idx)

    # Iterative edge removal
    active_edges = set(edge_to_opposite.keys())

    while True:
        edges_to_remove = set()

        for edge_key in active_edges:
            opposites = edge_to_opposite[edge_key]

            # Boundary edge (only 1 triangle) -- keep it
            if len(opposites) < 2:
                continue

            # Interior edge -- compute angular stability
            p_idx, q_idx = edge_key
            p = coords[p_idx]
            q = coords[q_idx]

            # Sum of angles at the two opposite vertices
            angle_sum = 0.0
            for opp_idx in opposites[:2]:  # At most 2 triangles share an edge
                angle_sum += _angle_at_vertex(p, q, coords[opp_idx])

            angular_stability = 180.0 - angle_sum

            if angular_stability < angle_threshold:
                edges_to_remove.add(edge_key)

        if len(edges_to_remove) == 0:
            break  # Convergence

        active_edges -= edges_to_remove

        # Update edge_to_opposite: remove references from remaining edges
        # to triangles that used removed edges
        # (Simplified: we just check stability on remaining edges each iteration)

    # Fallback: if too few edges, revert to full Delaunay
    min_edges = config.SHAPE_GRAPH_MIN_EDGES
    if len(active_edges) < min_edges:
        active_edges = set(edge_to_opposite.keys())

    # Build adjacency matrix and edge list
    adj = np.zeros((n, n))
    edge_list = []
    for p_idx, q_idx in active_edges:
        adj[p_idx, q_idx] = 1
        adj[q_idx, p_idx] = 1
        edge_list.append([int(p_idx), int(q_idx)])

    return adj, edge_list


def delaunay_edge_mat(coords):
    """
    Apply Delaunay triangulation to obtain role-adjacency matrix.
    Kept as fallback / for mean_adjacency computation.

    From soccercpd.py: delaunay_edge_mat()
    """
    if len(coords) < 3:
        return np.zeros((len(coords), len(coords)))

    try:
        tri_pts = Delaunay(coords).simplices
        edges = np.concatenate((tri_pts[:, :2], tri_pts[:, 1:], tri_pts[:, ::2]), axis=0)
        edge_mat = np.zeros((coords.shape[0], coords.shape[0]))
        edge_mat[edges[:, 0], edges[:, 1]] = 1
        return np.clip(edge_mat + edge_mat.T, 0, 1)
    except Exception:
        return np.zeros((len(coords), len(coords)))


# =============================================================================
# EFPI Template-Based Formation Detection (Bekkers 2025)
# =============================================================================

def scale_to_template(positions, template):
    """
    Scale player positions to match template bounding box (EFPI Section 2.1).

    Args:
        positions: (N, 2) array of player positions
        template: (N, 2) array of template positions

    Returns:
        (N, 2) array of scaled positions
    """
    pos_min = positions.min(axis=0)
    pos_max = positions.max(axis=0)
    tpl_min = template.min(axis=0)
    tpl_max = template.max(axis=0)

    pos_range = pos_max - pos_min
    tpl_range = tpl_max - tpl_min

    scale = np.where(pos_range > 1e-6, tpl_range / pos_range, 1.0)
    return (positions - pos_min) * scale + tpl_min


def match_formation_template(positions):
    """
    EFPI-style formation detection: match outfield player positions
    to the best-fitting formation template using Hungarian assignment.

    Supports both 10-player (normal) and 9-player (red card) teams.

    Args:
        positions: (N, 2) array of outfield player positions (raw pitch coords)
                   N = 10 (normal) or 9 (red card)

    Returns:
        Tuple of (formation_label, assignment_cost, position_assignment)
    """
    num_players = len(positions)
    templates = get_templates(num_players)

    if not templates:
        return 'unknown', float('inf'), None

    best_label = None
    best_cost = float('inf')
    best_assignment = None

    for label, template in templates.items():
        if len(template) != num_players:
            continue

        # Scale player positions to match template dimensions
        scaled_positions = scale_to_template(positions, template)

        # Cost matrix: Euclidean distance between each player and each template position
        cost_matrix = np.linalg.norm(
            scaled_positions[:, np.newaxis, :] - template[np.newaxis, :, :],
            axis=2
        )

        # Hungarian algorithm: find optimal assignment
        row_ind, col_ind = linear_sum_assignment(cost_matrix)
        total_cost = cost_matrix[row_ind, col_ind].sum()

        if total_cost < best_cost:
            best_cost = total_cost
            best_label = label
            best_assignment = col_ind

    return best_label, best_cost, best_assignment


# =============================================================================
# Phase Formation Computation
# =============================================================================

def compute_formation_for_phase(phase_frames, team_players, player_team_map, gk_ids=None):
    """
    Compute formation graph for a single phase segment.

    Args:
        phase_frames: DataFrame of tracking frames for this phase
        team_players: List of player IDs (all team players, will filter to on-field)
        player_team_map: dict mapping player_id to team_id
        gk_ids: set of known goalkeeper player IDs (from kloppy metadata)

    Returns:
        dict with formation data, or None if insufficient data
    """
    if gk_ids is None:
        gk_ids = set()

    # Extract positions for each frame, identifying which players are on field
    positions_list = []       # centroid-normalized (for RoleRep + shape graph)
    raw_positions_list = []   # raw pitch coords (for template matching)
    on_field_players = None
    num_expected = None       # 10 (normal) or 9 (red card)

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

        # Set on-field players from first frame with >= 10 players (handles red card)
        if on_field_players is None and len(frame_positions) >= 10:
            # Identify GK using kloppy metadata (authoritative)
            gk_idx = None
            for i, pid in enumerate(frame_player_ids):
                if pid in gk_ids:
                    gk_idx = i
                    break

            # Fallback: player most isolated on x-axis from team centroid
            if gk_idx is None:
                positions_array = np.array(frame_positions)
                team_mean_x = positions_array[:, 0].mean()
                gk_idx = int(np.argmax(np.abs(positions_array[:, 0] - team_mean_x)))

            on_field_players = [pid for i, pid in enumerate(frame_player_ids) if i != gk_idx]
            on_field_positions = [pos for i, pos in enumerate(frame_positions) if i != gk_idx]
            num_expected = len(on_field_players)  # 10 (normal) or 9 (red card)

            raw_pos = np.array(on_field_positions)
            raw_positions_list.append(raw_pos)
            positions = normalize_locs(raw_pos.copy())
            positions_list.append(positions)
            continue

        # Only use frames where the same outfield players are present
        if on_field_players is not None:
            outfield_positions = []
            for player_id in on_field_players:
                try:
                    idx_in_frame = frame_player_ids.index(player_id)
                    outfield_positions.append(frame_positions[idx_in_frame])
                except ValueError:
                    break

            if len(outfield_positions) == num_expected:
                raw_pos = np.array(outfield_positions)
                raw_positions_list.append(raw_pos)
                positions = normalize_locs(raw_pos.copy())
                positions_list.append(positions)

    if len(positions_list) < 3:
        return None

    num_roles = num_expected  # 10 or 9

    # Run RoleRep for stable role identity across frames
    role_distns, assignments_list = run_rolerep(positions_list, max_iter=5, tol=0.01, verbose=False)

    if len(assignments_list) == 0:
        return None

    # Compute mean positions and per-frame Delaunay adjacency
    role_positions_list = []
    adj_matrices = []

    for positions, assignments in zip(positions_list, assignments_list):
        role_ordered = np.zeros((num_roles, 2))
        for player_idx, role_idx in enumerate(assignments):
            role_ordered[role_idx] = positions[player_idx]

        role_positions_list.append(role_ordered)

        # Per-frame Delaunay adjacency
        adj = delaunay_edge_mat(role_ordered)
        adj_matrices.append(adj)

    # Aggregate
    mean_positions = np.mean(role_positions_list, axis=0)
    mean_adjacency = np.mean(adj_matrices, axis=0)

    # Compute stability (positional variance per role)
    role_positions_array = np.array(role_positions_list)
    positional_variance = np.var(role_positions_array, axis=0)
    stability_scores = 1.0 / (1.0 + positional_variance.sum(axis=1))

    # Shape graph on aggregated mean positions (centroid-normalized)
    shape_adj, shape_edges = compute_shape_graph(mean_positions)

    # Reorder raw positions by role assignment
    raw_role_positions_list = []
    for raw_pos, assignments in zip(raw_positions_list, assignments_list):
        raw_role_ordered = np.zeros((num_roles, 2))
        for player_idx, role_idx in enumerate(assignments):
            raw_role_ordered[role_idx] = raw_pos[player_idx]
        raw_role_positions_list.append(raw_role_ordered)

    raw_mean_positions = np.mean(raw_role_positions_list, axis=0)

    # EFPI template matching (replaces gap-based band assignment)
    formation_label, match_cost, position_assignment = match_formation_template(raw_mean_positions)

    return {
        'mean_positions': mean_positions,
        'raw_mean_positions': raw_mean_positions,
        'shape_graph_edges': shape_edges,
        'shape_graph_adjacency': shape_adj,
        'mean_adjacency': mean_adjacency,
        'stability_scores': stability_scores,
        'formation_label': formation_label,
        'match_cost': float(match_cost) if match_cost != float('inf') else None,
        'num_players': num_roles,
        'num_frames': len(positions_list),
    }


# =============================================================================
# Team & Match Level
# =============================================================================

def compute_formations_for_team(tracking_df, phases_df, player_team_map, team_id, gk_ids=None):
    """
    Compute formation graphs for one team across all phases.
    """
    print(f"\n  Processing team: {team_id}")

    team_players = sorted([pid for pid, tid in player_team_map.items() if tid == team_id])
    print(f"    Total players in roster: {len(team_players)}")

    team_phases = phases_df[phases_df['team_id'] == team_id].copy()
    print(f"    Phase segments: {len(team_phases)}")

    formations = []

    for phase_idx, phase_row in tqdm(team_phases.iterrows(), total=len(team_phases), desc=f"  Formations ({team_id})"):
        phase_mask = (
            (tracking_df['timestamp'] >= phase_row['start_time']) &
            (tracking_df['timestamp'] <= phase_row['end_time'])
        )
        phase_frames = tracking_df[phase_mask].copy()

        if len(phase_frames) == 0:
            continue

        formation = compute_formation_for_phase(phase_frames, team_players, player_team_map, gk_ids=gk_ids)

        if formation is not None:
            formations.append({
                'phase_id': int(phase_row['phase_id']),
                'phase_type': phase_row['phase_type'],
                'team_id': team_id,
                'mean_positions': formation['mean_positions'].tolist(),
                'raw_mean_positions': formation['raw_mean_positions'].tolist(),
                'shape_graph_edges': formation['shape_graph_edges'],
                'shape_graph_adjacency': formation['shape_graph_adjacency'].tolist(),
                'mean_adjacency': formation['mean_adjacency'].tolist(),
                'stability_scores': formation['stability_scores'].tolist(),
                'formation_label': formation['formation_label'],
                'match_cost': formation['match_cost'],
                'num_players': formation['num_players'],
                'num_frames': formation['num_frames'],
            })

    print(f"    Computed {len(formations)} formations")

    # Print formation label distribution
    if formations:
        labels = {}
        for f in formations:
            lbl = f['formation_label']
            labels[lbl] = labels.get(lbl, 0) + 1
        print(f"    Formation labels: {labels}")

    return formations


def compute_all_formations(tracking_df, phases_df, player_team_map, gk_ids=None):
    """
    Compute formation graphs for all teams and phases.
    """
    print("Computing formation graphs...")

    teams = list(set(player_team_map.values()))
    print(f"  Teams: {teams}")

    all_formations = []

    for team_id in teams:
        team_formations = compute_formations_for_team(
            tracking_df, phases_df, player_team_map, team_id, gk_ids=gk_ids
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
    print("STEP 5: FORMATION GRAPHS (Shape Graph + EFPI Template Matching)")
    print("=" * 80)

    # Get player-team mapping and GK IDs from kloppy metadata
    player_team_map = {}
    gk_ids = set()
    for team in tracking_dataset.metadata.teams:
        team_id = team.team_id
        for player in team.players:
            player_team_map[player.player_id] = team_id
            pos = getattr(player, 'starting_position', None) or getattr(player, 'position', None)
            if pos and str(pos).lower().startswith('goalkeeper'):
                gk_ids.add(player.player_id)

    print(f"  Identified {len(gk_ids)} goalkeepers: {gk_ids}")

    # Compute formations
    formations = compute_all_formations(tracking_df, phases_df, player_team_map, gk_ids=gk_ids)

    print("\n[OK] Formation computation complete")

    # Show sample
    if len(formations) > 0:
        sample = formations[0]
        print(f"\nSample formation (phase {sample['phase_id']}):")
        print(f"  Phase type: {sample['phase_type']}")
        print(f"  Team: {sample['team_id']}")
        print(f"  Frames: {sample['num_frames']}")
        print(f"  Players: {sample['num_players']} outfield")
        print(f"  Formation label: {sample['formation_label']}")
        print(f"  Match cost: {sample['match_cost']}")
        print(f"  Shape graph edges: {len(sample['shape_graph_edges'])}")
        print(f"  Mean positions shape: {np.array(sample['mean_positions']).shape}")
        print(f"  Stability scores (first 3): {np.array(sample['stability_scores'])[:3]}")

    return formations


if __name__ == "__main__":
    print("\n[INFO] This script requires tracking_dataset, tracking_df, and phases_df.")
    print("Run as part of the pipeline.")
