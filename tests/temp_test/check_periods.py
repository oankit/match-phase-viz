"""Check if tracking data includes both periods."""
import sys
sys.path.insert(0, '../../pipeline')

from kloppy import sportec
from pathlib import Path
import config

data_path = Path('../../data')
meta_file = list(data_path.glob('*matchinformation*J03WN1.xml'))[0]
tracking_file = list(data_path.glob('*positions_raw*J03WN1.xml'))[0]

print(f"Loading tracking data (sample_rate={config.LOAD_SAMPLE_RATE})...")
tracking_dataset = sportec.load_tracking(
    raw_data=str(tracking_file),
    meta_data=str(meta_file),
    coordinates='kloppy',
    only_alive=True,
    sample_rate=config.LOAD_SAMPLE_RATE
)

print(f"Records: {len(tracking_dataset.records)}")
print(f"Metadata periods: {tracking_dataset.metadata.periods}")

# Check periods in raw records
periods = set()
for r in tracking_dataset.records[:10]:
    periods.add(r.period.id)
    print(f"  Record: period={r.period.id}, timestamp={r.timestamp}")

# Also check the last few records
print("\nLast 10 records:")
for r in tracking_dataset.records[-10:]:
    periods.add(r.period.id)
    print(f"  Record: period={r.period.id}, timestamp={r.timestamp}")

print(f"\nPeriods found in first/last records: {periods}")

# Now check ALL records for periods
all_periods = set()
for r in tracking_dataset.records:
    all_periods.add(r.period.id)
print(f"All unique periods in dataset: {all_periods}")

# Count per period
from collections import Counter
period_counts = Counter(r.period.id for r in tracking_dataset.records)
print(f"Records per period: {dict(period_counts)}")

# Convert to DataFrame and check
print("\nConverting to DataFrame...")
tracking_df = tracking_dataset.to_df()
print(f"DataFrame shape: {tracking_df.shape}")
print(f"Period IDs in DataFrame: {tracking_df['period_id'].unique()}")
print(f"Records per period in DataFrame:")
print(tracking_df['period_id'].value_counts())

print(f"\nTimestamp ranges per period:")
for pid in sorted(tracking_df['period_id'].unique()):
    period_data = tracking_df[tracking_df['period_id'] == pid]
    ts_min = period_data['timestamp'].min()
    ts_max = period_data['timestamp'].max()
    print(f"  Period {pid}: {ts_min} to {ts_max} "
          f"({ts_min.total_seconds():.1f}s to {ts_max.total_seconds():.1f}s)")
