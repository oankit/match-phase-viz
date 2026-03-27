"""
Step 4: Voronoi Pitch Control

Computes Voronoi diagrams for each frame to show spatial control on the pitch.
Each Voronoi cell represents the region controlled by a player.

Output options:
1. Polygon vertex arrays per player per frame (for SVG rendering)
2. Rasterized grid with team_id per cell (for heatmap-style visualization)

Using scipy.spatial.Voronoi + shapely for clipping to pitch boundaries.
"""

import numpy as np
import pandas as pd
from scipy.spatial import Voronoi
from shapely.geometry import Polygon, Point, box
from shapely.ops import unary_union
from tqdm import tqdm

import config


def get_player_positions_from_row(tracking_row, player_team_map):
    """
    Extract all player positions from a wide-format tracking row.

    Args:
        tracking_row: Single row from tracking DataFrame (wide format)
        player_team_map: dict mapping player_id to team_id

    Returns:
        Tuple[np.ndarray, List[str], List[str]]:
            - positions (N, 2) array of [x, y] coordinates
            - player_ids list
            - team_ids list
    """
    positions = []
    player_ids = []
    team_ids = []

    for player_id, team_id in player_team_map.items():
        x_col = f'{player_id}_x'
        y_col = f'{player_id}_y'

        if x_col in tracking_row.index and y_col in tracking_row.index:
            x = tracking_row[x_col]
            y = tracking_row[y_col]

            # Skip if NaN (player not on field)
            if not (pd.isna(x) or pd.isna(y)):
                positions.append([x, y])
                player_ids.append(player_id)
                team_ids.append(team_id)

    return np.array(positions), player_ids, team_ids


def compute_voronoi_polygons(positions, pitch_bounds=(0.0, 1.0, 0.0, 1.0)):
    """
    Compute Voronoi diagram and clip to pitch boundaries.

    Args:
        positions: (N, 2) array of [x, y] positions (normalized 0-1)
        pitch_bounds: (x_min, x_max, y_min, y_max) pitch boundaries

    Returns:
        List[Polygon]: List of clipped Voronoi polygons (one per player)
    """
    if len(positions) < 3:
        # Not enough points for Voronoi
        return [None] * len(positions)

    # Create pitch bounding box
    x_min, x_max, y_min, y_max = pitch_bounds
    pitch_poly = box(x_min, y_min, x_max, y_max)

    try:
        # Add dummy points far outside the pitch to ensure outermost players
        # get bounded regions instead of infinite regions.
        dummy_points = np.array([
            [-100.0, -100.0],
            [-100.0, 100.0],
            [100.0, -100.0],
            [100.0, 100.0]
        ])
        all_positions = np.vstack([positions, dummy_points])

        # Compute Voronoi diagram
        vor = Voronoi(all_positions)

        polygons = []
        # Only iterate over actual players (exclude dummy points)
        for point_idx in range(len(positions)):
            # Get Voronoi region for this point
            region_idx = vor.point_region[point_idx]
            region_vertices = vor.regions[region_idx]

            # Skip infinite regions (shouldn't happen with proper bounds, but check anyway)
            if -1 in region_vertices or len(region_vertices) == 0:
                polygons.append(None)
                continue

            # Get vertex coordinates
            vertices = vor.vertices[region_vertices]

            # Create polygon and clip to pitch
            try:
                poly = Polygon(vertices)
                clipped = poly.intersection(pitch_poly)

                # Handle multi-polygons (shouldn't happen but be safe)
                if clipped.is_empty:
                    polygons.append(None)
                elif clipped.geom_type == 'Polygon':
                    polygons.append(clipped)
                elif clipped.geom_type == 'MultiPolygon':
                    # Take largest polygon
                    largest = max(clipped.geoms, key=lambda p: p.area)
                    polygons.append(largest)
                else:
                    polygons.append(None)
            except Exception:
                polygons.append(None)

        return polygons

    except Exception as e:
        # Voronoi computation failed (e.g., duplicate points)
        return [None] * len(positions)


def polygon_to_vertices(poly):
    """
    Convert shapely Polygon to list of [x, y] vertices.

    Args:
        poly: shapely Polygon

    Returns:
        List[List[float]]: List of [x, y] coordinates
    """
    if poly is None:
        return None

    # Get exterior coordinates (exclude last point which duplicates first)
    coords = list(poly.exterior.coords[:-1])
    return [[float(x), float(y)] for x, y in coords]


def rasterize_voronoi_to_grid(positions, team_ids, grid_size=(105, 68)):
    """
    Rasterize Voronoi diagram to a grid where each cell has the team_id of the controlling player.

    Alternative to polygon-based representation. Useful for heatmap-style visualizations.

    Args:
        positions: (N, 2) array of [x, y] positions (normalized 0-1)
        team_ids: List of team_ids corresponding to positions
        grid_size: (width, height) grid dimensions

    Returns:
        np.ndarray: (height, width) grid with team_id at each cell
    """
    if len(positions) == 0:
        return np.full(grid_size[::-1], '', dtype=object)

    grid_w, grid_h = grid_size

    # Create grid of sample points
    x_grid = np.linspace(0, 1, grid_w)
    y_grid = np.linspace(0, 1, grid_h)
    xx, yy = np.meshgrid(x_grid, y_grid)
    grid_points = np.column_stack([xx.ravel(), yy.ravel()])

    # For each grid point, find nearest player
    distances = np.linalg.norm(
        grid_points[:, np.newaxis, :] - positions[np.newaxis, :, :],
        axis=2
    )
    nearest_player_idx = distances.argmin(axis=1)

    # Map to team_ids
    team_grid = np.array([team_ids[i] for i in nearest_player_idx])
    team_grid = team_grid.reshape(grid_h, grid_w)

    return team_grid


def compute_voronoi_for_frame(tracking_row, player_team_map, output_format='polygons'):
    """
    Compute Voronoi diagram for a single frame.

    Args:
        tracking_row: Single row from tracking DataFrame
        player_team_map: dict mapping player_id to team_id
        output_format: 'polygons' or 'grid'

    Returns:
        dict: Voronoi data for this frame
    """
    positions, player_ids, team_ids = get_player_positions_from_row(tracking_row, player_team_map)

    if len(positions) == 0:
        return {
            'frame_id': tracking_row['frame_id'],
            'timestamp': tracking_row['timestamp'],
            'cells': [],
        }

    if output_format == 'polygons':
        # Compute Voronoi polygons
        polygons = compute_voronoi_polygons(positions)

        cells = []
        for i, (player_id, team_id, poly) in enumerate(zip(player_ids, team_ids, polygons)):
            vertices = polygon_to_vertices(poly)
            cells.append({
                'player_id': player_id,
                'team_id': team_id,
                'polygon': vertices,
            })

        return {
            'frame_id': tracking_row['frame_id'],
            'timestamp': tracking_row['timestamp'],
            'cells': cells,
        }

    elif output_format == 'grid':
        # Rasterize to grid
        grid = rasterize_voronoi_to_grid(positions, team_ids)

        return {
            'frame_id': tracking_row['frame_id'],
            'timestamp': tracking_row['timestamp'],
            'grid': grid.tolist(),  # Convert to list for JSON serialization
        }

    else:
        raise ValueError(f"Unknown output_format: {output_format}")


def compute_all_voronoi(tracking_df, player_team_map, output_format='polygons'):
    """
    Compute Voronoi diagrams for all frames.

    Args:
        tracking_df: Tracking DataFrame (wide format)
        player_team_map: dict mapping player_id to team_id
        output_format: 'polygons' or 'grid'

    Returns:
        List[dict]: Voronoi data for each frame
    """
    print(f"Computing Voronoi diagrams (format: {output_format})...")
    print(f"  Processing {len(tracking_df)} frames...")

    voronoi_data = []
    for idx in tqdm(range(len(tracking_df)), desc="Computing Voronoi"):
        row = tracking_df.iloc[idx]
        voronoi_frame = compute_voronoi_for_frame(row, player_team_map, output_format)
        voronoi_data.append(voronoi_frame)

    print(f"  Computed Voronoi for {len(voronoi_data)} frames")

    return voronoi_data


def main(tracking_dataset, tracking_df, output_format='polygons'):
    """
    Main entry point for Step 4.

    Args:
        tracking_dataset: Kloppy TrackingDataset object (for metadata)
        tracking_df: Tracking DataFrame (wide format)
        output_format: 'polygons' or 'grid'

    Returns:
        List[dict]: Voronoi data for each frame
    """
    print("\n" + "=" * 80)
    print("STEP 4: VORONOI PITCH CONTROL")
    print("=" * 80)

    # Get player-team mapping
    player_team_map = {}
    for team in tracking_dataset.metadata.teams:
        team_id = team.team_id
        for player in team.players:
            player_team_map[player.player_id] = team_id

    # Compute Voronoi
    voronoi_data = compute_all_voronoi(tracking_df, player_team_map, output_format)

    print("\n[OK] Voronoi computation complete")
    print(f"  Output format: {output_format}")

    if output_format == 'polygons':
        # Show sample
        sample = voronoi_data[0]
        print(f"\nSample frame {sample['frame_id']}:")
        print(f"  Cells: {len(sample['cells'])}")
        print(f"  Example cell: player={sample['cells'][0]['player_id']}, "
              f"team={sample['cells'][0]['team_id']}, "
              f"vertices={len(sample['cells'][0]['polygon']) if sample['cells'][0]['polygon'] else 0}")
    elif output_format == 'grid':
        sample = voronoi_data[0]
        print(f"\nSample frame {sample['frame_id']}:")
        print(f"  Grid shape: {len(sample['grid'])}x{len(sample['grid'][0])}")

    return voronoi_data


if __name__ == "__main__":
    print("\n[INFO] This script requires tracking_dataset and tracking_df from Step 1.")
    print("Run as part of the pipeline.")
