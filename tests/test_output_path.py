"""
Test that pipeline outputs directly to frontend public folder
"""
import sys
sys.path.insert(0, '../pipeline')

import config
from pathlib import Path

print("Testing output path configuration...")
print("=" * 60)

print(f"Configured OUTPUT_DIR: {config.OUTPUT_DIR}")
print(f"Configured BACKUP_OUTPUT_DIR: {config.BACKUP_OUTPUT_DIR}")

# Check if frontend directory exists
frontend_path = Path(config.OUTPUT_DIR)
backup_path = Path(config.BACKUP_OUTPUT_DIR)

print(f"\nFrontend path exists: {frontend_path.exists()}")
print(f"Backup path exists: {backup_path.exists()}")

# Test the logic from 08_export_json.py
if frontend_path.exists():
    print(f"\n[SUCCESS] Pipeline will output to: {config.OUTPUT_DIR}")
    print("  Files will be immediately available in the frontend!")
else:
    print(f"\n[SUCCESS] Pipeline will output to: {config.BACKUP_OUTPUT_DIR}")
    print("  Files will need to be manually copied to frontend.")

# Show where J03WN1 files would go
match_id = "J03WN1"
if frontend_path.exists():
    output_dir = frontend_path / match_id
else:
    output_dir = backup_path / match_id

print(f"\nMatch {match_id} will be saved to:")
print(f"  {output_dir}")

if output_dir.exists():
    print(f"\n  Directory already exists with {len(list(output_dir.glob('*.json')))} JSON files")