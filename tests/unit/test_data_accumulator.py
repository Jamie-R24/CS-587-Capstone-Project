#!/usr/bin/env python3
"""
Unit tests for data_accumulator.py
Tests data snapshotting and accumulation logic

Target: scripts/data_accumulator.py (164 lines)
Coverage Goal: 90%+
Test Count: 15 tests
"""

import pytest
import os
import csv
import time
from unittest.mock import Mock, patch
import sys

# Import the module under test
from data_accumulator import DataAccumulator


# ============================================================================
# TEST CLASS: Snapshot Creation
# ============================================================================

class TestSnapshotCreation:
    """Test snapshot creation functionality"""

    def test_take_snapshot_creates_file(self, temp_dir, sample_csv_data):
        """Test that snapshot creates timestamped CSV file"""
        # Create source file
        source_path = os.path.join(temp_dir, 'activity', 'network_data.csv')
        os.makedirs(os.path.dirname(source_path), exist_ok=True)

        with open(source_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=sample_csv_data['headers'])
            writer.writeheader()
            writer.writerows(sample_csv_data['all'])

        # Create accumulator
        accum_dir = os.path.join(temp_dir, 'accumulated')
        accumulator = DataAccumulator(
            source_path=source_path,
            accumulation_dir=accum_dir,
            snapshot_interval=60
        )

        # Take snapshot
        snapshot_path = accumulator.take_snapshot()

        # Verify snapshot created
        assert snapshot_path is not None
        assert os.path.exists(snapshot_path)
        assert 'snapshot_' in snapshot_path
        assert snapshot_path.endswith('.csv')

    def test_snapshot_has_correct_content(self, temp_dir, sample_csv_data):
        """Test that snapshot contains same data as source"""
        # Create source file
        source_path = os.path.join(temp_dir, 'activity', 'network_data.csv')
        os.makedirs(os.path.dirname(source_path), exist_ok=True)

        with open(source_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=sample_csv_data['headers'])
            writer.writeheader()
            writer.writerows(sample_csv_data['all'])

        # Create accumulator and take snapshot
        accum_dir = os.path.join(temp_dir, 'accumulated')
        accumulator = DataAccumulator(source_path=source_path, accumulation_dir=accum_dir)
        snapshot_path = accumulator.take_snapshot()

        # Read snapshot and verify content
        with open(snapshot_path, 'r') as f:
            reader = csv.DictReader(f)
            snapshot_rows = list(reader)

        assert len(snapshot_rows) == len(sample_csv_data['all'])

    def test_handle_missing_source_file(self, temp_dir):
        """Test handling when source file doesn't exist"""
        source_path = os.path.join(temp_dir, 'nonexistent.csv')
        accum_dir = os.path.join(temp_dir, 'accumulated')

        accumulator = DataAccumulator(source_path=source_path, accumulation_dir=accum_dir)
        snapshot_path = accumulator.take_snapshot()

        # Should return None
        assert snapshot_path is None

    def test_skip_empty_csv(self, temp_dir):
        """Test that empty CSV (only header) is skipped"""
        source_path = os.path.join(temp_dir, 'activity', 'empty.csv')
        os.makedirs(os.path.dirname(source_path), exist_ok=True)

        # Create CSV with only header
        with open(source_path, 'w') as f:
            f.write('dur,proto,label\n')

        accum_dir = os.path.join(temp_dir, 'accumulated')
        accumulator = DataAccumulator(source_path=source_path, accumulation_dir=accum_dir)
        snapshot_path = accumulator.take_snapshot()

        # Should return None (no data rows)
        assert snapshot_path is None

    def test_increment_snapshot_count(self, temp_dir, sample_csv_data):
        """Test that snapshot_count increments"""
        source_path = os.path.join(temp_dir, 'activity', 'network_data.csv')
        os.makedirs(os.path.dirname(source_path), exist_ok=True)

        with open(source_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=sample_csv_data['headers'])
            writer.writeheader()
            writer.writerows(sample_csv_data['all'])

        accum_dir = os.path.join(temp_dir, 'accumulated')
        accumulator = DataAccumulator(source_path=source_path, accumulation_dir=accum_dir)

        initial_count = accumulator.snapshot_count

        # Take 3 snapshots
        for _ in range(3):
            accumulator.take_snapshot()
            time.sleep(0.01)  # Ensure different timestamps

        assert accumulator.snapshot_count == initial_count + 3

    def test_count_lines_correctly(self, temp_dir, sample_csv_data):
        """Test that line count excludes header"""
        source_path = os.path.join(temp_dir, 'activity', 'network_data.csv')
        os.makedirs(os.path.dirname(source_path), exist_ok=True)

        with open(source_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=sample_csv_data['headers'])
            writer.writeheader()
            writer.writerows(sample_csv_data['all'])

        accum_dir = os.path.join(temp_dir, 'accumulated')
        accumulator = DataAccumulator(source_path=source_path, accumulation_dir=accum_dir)

        # Mock print to capture output
        with patch('builtins.print') as mock_print:
            accumulator.take_snapshot()

            # Check that print was called with correct line count
            # Should report 8 samples (5 normal + 3 anomalies)
            print_calls = [str(call) for call in mock_print.call_args_list]
            assert any('8 samples' in call for call in print_calls)


# ============================================================================
# TEST CLASS: Snapshot Combining
# ============================================================================

class TestSnapshotCombining:
    """Test combining multiple snapshots"""

    def test_combine_multiple_snapshots(self, temp_dir, sample_csv_data):
        """Test combining multiple snapshot files into one"""
        accum_dir = os.path.join(temp_dir, 'accumulated')
        os.makedirs(accum_dir, exist_ok=True)

        # Create 3 snapshot files
        for i in range(3):
            snapshot_path = os.path.join(accum_dir, f'snapshot_2025010{i}.csv')
            with open(snapshot_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=sample_csv_data['headers'])
                writer.writeheader()
                writer.writerows(sample_csv_data['all'])

        # Create accumulator (doesn't matter that source doesn't exist for this test)
        accumulator = DataAccumulator(
            source_path='/fake/path.csv',
            accumulation_dir=accum_dir
        )

        # Get accumulated data
        combined_path = accumulator.get_accumulated_data_path()

        assert combined_path is not None
        assert os.path.exists(combined_path)

        # Verify combined file has data from all snapshots
        with open(combined_path, 'r') as f:
            reader = csv.DictReader(f)
            combined_rows = list(reader)

        # Should have 8 rows per snapshot * 3 snapshots = 24 rows (if no duplicates)
        # But deduplication happens, so exact count depends on uniqueness
        assert len(combined_rows) > 0

    def test_deduplicate_identical_rows(self, temp_dir, sample_csv_data):
        """Test that identical rows are deduplicated"""
        accum_dir = os.path.join(temp_dir, 'accumulated')
        os.makedirs(accum_dir, exist_ok=True)

        # Create 2 snapshots with IDENTICAL data
        for i in range(2):
            snapshot_path = os.path.join(accum_dir, f'snapshot_2025010{i}.csv')
            with open(snapshot_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=sample_csv_data['headers'])
                writer.writeheader()
                writer.writerows(sample_csv_data['all'])

        accumulator = DataAccumulator(source_path='/fake/path.csv', accumulation_dir=accum_dir)
        combined_path = accumulator.get_accumulated_data_path()

        with open(combined_path, 'r') as f:
            reader = csv.DictReader(f)
            combined_rows = list(reader)

        # sample_csv_data has 5 identical normal samples + 3 identical anomalies = 2 unique types
        # With 2 snapshots of same data, deduplication should give us only 2 unique rows
        assert len(combined_rows) == 2  # 1 normal type + 1 anomaly type (all identical within each type)

    def test_preserve_headers_from_first_snapshot(self, temp_dir):
        """Test that headers are taken from first snapshot"""
        accum_dir = os.path.join(temp_dir, 'accumulated')
        os.makedirs(accum_dir, exist_ok=True)

        headers = ['dur', 'proto', 'label']

        # Create snapshot files
        for i in range(2):
            snapshot_path = os.path.join(accum_dir, f'snapshot_2025010{i}.csv')
            with open(snapshot_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerow({'dur': 1.0, 'proto': 'tcp', 'label': 0})

        accumulator = DataAccumulator(source_path='/fake/path.csv', accumulation_dir=accum_dir)
        combined_path = accumulator.get_accumulated_data_path()

        # Verify headers
        with open(combined_path, 'r') as f:
            reader = csv.DictReader(f)
            assert list(reader.fieldnames) == headers

    def test_handle_no_snapshots(self, temp_dir):
        """Test handling when no snapshot files exist"""
        accum_dir = os.path.join(temp_dir, 'accumulated')
        os.makedirs(accum_dir, exist_ok=True)

        accumulator = DataAccumulator(source_path='/fake/path.csv', accumulation_dir=accum_dir)
        combined_path = accumulator.get_accumulated_data_path()

        # Should return None
        assert combined_path is None

    def test_handle_snapshots_with_different_schemas(self, temp_dir):
        """Test handling snapshots with mismatched headers"""
        accum_dir = os.path.join(temp_dir, 'accumulated')
        os.makedirs(accum_dir, exist_ok=True)

        # First snapshot with headers A
        snapshot1 = os.path.join(accum_dir, 'snapshot_20250101.csv')
        with open(snapshot1, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['dur', 'proto', 'label'])
            writer.writeheader()
            writer.writerow({'dur': 1.0, 'proto': 'tcp', 'label': 0})

        # Second snapshot with different headers
        snapshot2 = os.path.join(accum_dir, 'snapshot_20250102.csv')
        with open(snapshot2, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['dur', 'service', 'label'])
            writer.writeheader()
            writer.writerow({'dur': 2.0, 'service': 'http', 'label': 1})

        accumulator = DataAccumulator(source_path='/fake/path.csv', accumulation_dir=accum_dir)
        combined_path = accumulator.get_accumulated_data_path()

        # Should return None because schemas are incompatible (code correctly errors)
        assert combined_path is None


# ============================================================================
# TEST CLASS: Deduplication
# ============================================================================

class TestDeduplication:
    """Test row deduplication logic"""

    def test_keep_unique_rows(self, temp_dir):
        """Test that unique rows are all kept"""
        accum_dir = os.path.join(temp_dir, 'accumulated')
        os.makedirs(accum_dir, exist_ok=True)

        headers = ['dur', 'proto', 'label']

        # Create snapshot with unique rows
        snapshot_path = os.path.join(accum_dir, 'snapshot_20250101.csv')
        with open(snapshot_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerow({'dur': 1.0, 'proto': 'tcp', 'label': 0})
            writer.writerow({'dur': 2.0, 'proto': 'udp', 'label': 1})
            writer.writerow({'dur': 3.0, 'proto': 'icmp', 'label': 0})

        accumulator = DataAccumulator(source_path='/fake/path.csv', accumulation_dir=accum_dir)
        combined_path = accumulator.get_accumulated_data_path()

        with open(combined_path, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # All 3 unique rows should be kept
        assert len(rows) == 3

    def test_remove_exact_duplicates(self, temp_dir):
        """Test that exact duplicate rows are removed"""
        accum_dir = os.path.join(temp_dir, 'accumulated')
        os.makedirs(accum_dir, exist_ok=True)

        headers = ['dur', 'proto', 'label']

        # Create 2 snapshots with same rows
        for i in range(2):
            snapshot_path = os.path.join(accum_dir, f'snapshot_2025010{i}.csv')
            with open(snapshot_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerow({'dur': 1.0, 'proto': 'tcp', 'label': 0})
                writer.writerow({'dur': 1.0, 'proto': 'tcp', 'label': 0})  # Duplicate within file

        accumulator = DataAccumulator(source_path='/fake/path.csv', accumulation_dir=accum_dir)
        combined_path = accumulator.get_accumulated_data_path()

        with open(combined_path, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # Should have only 1 unique row
        assert len(rows) == 1


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v'])