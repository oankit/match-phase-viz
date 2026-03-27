"""
Test that the frontend can load the JSON data files.
"""

import requests
import json
import time

def test_frontend_data_loading():
    """Test that all JSON files are accessible via the dev server."""

    base_url = "http://localhost:3000/data/J03WN1"
    files_to_test = [
        "metadata.json",
        "frames.json",
        "phases.json",
        "formations.json",
        "voronoi.json",
        "heatmaps.json"
    ]

    print("Testing frontend data loading...")
    print("=" * 50)

    # Give the server a moment to be ready
    time.sleep(2)

    all_passed = True

    for file_name in files_to_test:
        url = f"{base_url}/{file_name}"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()

                # Check data structure
                if file_name == "metadata.json":
                    assert "match_id" in data
                    assert "teams" in data
                    print(f"[OK] {file_name} - Match ID: {data['match_id']}")

                elif file_name == "frames.json":
                    assert len(data) > 0
                    assert "players" in data[0]
                    print(f"[OK] {file_name} - {len(data)} frames")

                elif file_name == "phases.json":
                    assert len(data) > 0
                    assert "type" in data[0]
                    print(f"[OK] {file_name} - {len(data)} phases")

                elif file_name == "formations.json":
                    assert len(data) > 0
                    assert "mean_positions" in data[0]
                    print(f"[OK] {file_name} - {len(data)} formations")

                elif file_name == "voronoi.json":
                    assert len(data) > 0
                    print(f"[OK] {file_name} - {len(data)} voronoi frames")

                elif file_name == "heatmaps.json":
                    assert len(data) > 0
                    assert "heatmap" in data[0]
                    print(f"[OK] {file_name} - {len(data)} heatmaps")

            else:
                print(f"[ERROR] {file_name} - HTTP {response.status_code}")
                all_passed = False

        except Exception as e:
            print(f"[ERROR] {file_name} - {e}")
            all_passed = False

    print("=" * 50)
    if all_passed:
        print("[SUCCESS] All data files are accessible!")
        print("\nFrontend is ready at: http://localhost:3000")
        print("Open this URL in your browser to view the dashboard")
    else:
        print("[FAILED] Some files could not be loaded")
        print("Check that the dev server is running and files are in public/data/J03WN1/")

    return all_passed

if __name__ == "__main__":
    test_frontend_data_loading()