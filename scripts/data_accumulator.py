#!/usr/bin/env python3
"""
Data Accumulator - Manages synthetic traffic data for retraining
Periodically snapshots generated traffic and maintains accumulated dataset
"""

import os
import shutil
import time
import csv
from datetime import datetime

class DataAccumulator:
    def __init__(self,
                 source_path='/var/log/activity/network_data.csv',
                 accumulation_dir='/data/accumulated_data',
                 snapshot_interval=120):  # 2 minutes
        """
        Initialize data accumulator

        Args:
            source_path: Where target container writes traffic
            accumulation_dir: Where to store accumulated snapshots
            snapshot_interval: How often to snapshot (seconds)
        """
        self.source_path = source_path
        self.accumulation_dir = accumulation_dir
        self.snapshot_interval = snapshot_interval
        self.snapshot_count = 0

        # Create accumulation directory
        os.makedirs(accumulation_dir, exist_ok=True)

    def take_snapshot(self):
        """
        Take snapshot of current synthetic traffic
        Returns: Path to snapshot file, or None if failed
        """
        if not os.path.exists(self.source_path):
            print(f"[Accumulator] No data at {self.source_path}")
            return None

        # Check if file has content (more than just header)
        try:
            with open(self.source_path, 'r') as f:
                lines = f.readlines()
                if len(lines) <= 1:  # Only header or empty
                    print("[Accumulator] No data rows to snapshot")
                    return None
        except Exception as e:
            print(f"[Accumulator] Error reading source file: {e}")
            return None

        # Create snapshot with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        snapshot_path = os.path.join(
            self.accumulation_dir,
            f'snapshot_{timestamp}.csv'
        )

        try:
            shutil.copy(self.source_path, snapshot_path)
            self.snapshot_count += 1

            # Count lines (minus header)
            line_count = len(lines) - 1

            print(f"[Accumulator] ✓ Snapshot #{self.snapshot_count} saved: {snapshot_path} ({line_count} samples)")
            return snapshot_path

        except Exception as e:
            print(f"[Accumulator] Error creating snapshot: {e}")
            return None

    def get_accumulated_data_path(self):
        """
        Combine all snapshots into single accumulated dataset
        Returns: Path to combined file
        """
        combined_path = os.path.join(self.accumulation_dir, 'accumulated_synthetic.csv')

        # Get all snapshot files
        snapshot_files = sorted([
            os.path.join(self.accumulation_dir, f)
            for f in os.listdir(self.accumulation_dir)
            if f.startswith('snapshot_') and f.endswith('.csv')
        ])

        if not snapshot_files:
            print("[Accumulator] No snapshots available")
            return None

        # Combine all snapshots
        all_rows = []
        headers = None

        for snapshot in snapshot_files:
            try:
                with open(snapshot, 'r') as f:
                    reader = csv.DictReader(f)
                    if headers is None:
                        headers = reader.fieldnames

                    for row in reader:
                        all_rows.append(row)

            except Exception as e:
                print(f"[Accumulator] Error reading {snapshot}: {e}")

        # Remove duplicates (same exact row content)
        # Use dict to track unique rows by converting to tuple
        seen = set()
        unique_rows = []
        for row in all_rows:
            row_tuple = tuple(sorted(row.items()))
            if row_tuple not in seen:
                seen.add(row_tuple)
                unique_rows.append(row)

        # Write combined file
        try:
            with open(combined_path, 'w', newline='') as f:
                if headers:
                    writer = csv.DictWriter(f, fieldnames=headers)
                    writer.writeheader()
                    writer.writerows(unique_rows)

            print(f"[Accumulator] ✓ Accumulated dataset created: {combined_path} ({len(unique_rows)} unique samples)")
            return combined_path

        except Exception as e:
            print(f"[Accumulator] Error writing accumulated dataset: {e}")
            return None

    def run_continuous(self):
        """Run continuous snapshotting"""
        print(f"[Accumulator] Data accumulator started (interval: {self.snapshot_interval}s)")

        while True:
            try:
                time.sleep(self.snapshot_interval)
                self.take_snapshot()

            except KeyboardInterrupt:
                print("[Accumulator] Data accumulator stopped")
                break
            except Exception as e:
                print(f"[Accumulator] Error in accumulator: {e}")

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Data Accumulator for Retraining')
    parser.add_argument('--interval', type=int, default=300,
                       help='Snapshot interval in seconds (default: 300 = 5 minutes)')

    args = parser.parse_args()

    accumulator = DataAccumulator(snapshot_interval=args.interval)
    accumulator.run_continuous()

if __name__ == "__main__":
    main()
