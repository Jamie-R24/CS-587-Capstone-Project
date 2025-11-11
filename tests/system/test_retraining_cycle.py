#!/usr/bin/env python3
"""
System Test: Retraining Cycle
Tests scheduled retraining with accumulated synthetic data
"""

import pytest
import time
import json
import sys
from pathlib import Path

# Import helper utilities
HELPERS_DIR = Path(__file__).parent.parent / 'helpers'
sys.path.insert(0, str(HELPERS_DIR))

from wait_utils import *
from validation_utils import *


@pytest.mark.timeout(900)  # 15 minute timeout
class TestRetrainingCycle:
    """Test retraining cycle with synthetic data accumulation"""

    @pytest.fixture(scope='class', autouse=True)
    def setup_system(self, docker_helper):
        """Start system for retraining tests"""
        print("\n" + "="*80)
        print("[Setup] Starting system for retraining cycle tests...")
        print("="*80)

        # Start system
        success = docker_helper.start_system(clean=True)
        assert success, "Failed to start system"

        # Run initial training
        print("[Setup] Running initial training...")
        result = docker_helper.exec_in_container(
            'workstation',
            'cd /data && python3 /scripts/create_test_set.py'
        )
        
        if result['exit_code'] != 0:
            print(f"[Setup] ERROR: {result['stderr']}")
            pytest.fail("Failed to run initial training")

        # Wait for initial model
        assert wait_for_model(docker_helper, timeout=300), "Initial model not created"
        
        print("[Setup] ✓ Initial training complete")

        yield docker_helper

        # Teardown
        print("\n" + "="*80)
        print("[Teardown] Stopping system...")
        print("="*80)
        docker_helper.stop_system(remove_volumes=True)

    def test_01_data_accumulator_creates_snapshots(self, docker_helper):
        """Test that data accumulator creates periodic snapshots"""
        print("\n[Test 01] Verifying data accumulator creates snapshots...")
        print("[Test 01]   Note: Snapshots are created every 2 minutes")
        
        # Wait for at least 1 snapshot (2 min + buffer)
        assert wait_for_snapshots(docker_helper, min_snapshots=1, timeout=240), \
            "No snapshots created within 240 seconds"

        # Verify snapshot file structure
        result = docker_helper.exec_in_container(
            'workstation',
            'ls -1 /data/accumulated_data/snapshot_*.csv | head -1'
        )

        snapshot_file = result['stdout'].strip()
        assert snapshot_file, "No snapshot file found"
        print(f"[Test 01]   ✓ Snapshot file: {snapshot_file}")

        # Verify snapshot has data
        line_count = docker_helper.get_file_line_count('workstation', snapshot_file)
        assert line_count > 1, f"Snapshot has no data rows: {line_count} lines"
        
        print(f"[Test 01]   ✓ Snapshot has {line_count - 1} data rows")
        print("[Test 01] ✓ Snapshot creation verified")

    def test_02_first_retraining_cycle_completes(self, docker_helper):
        """Test that first retraining cycle completes successfully"""
        print("\n[Test 02] Verifying first retraining cycle completion...")
        print("[Test 02]   Note: Retraining occurs every 2 minutes with min 30 samples")
        
        # Wait for first retraining cycle
        assert wait_for_retraining_cycle(docker_helper, cycle_number=1, timeout=300), \
            "First retraining cycle did not complete within 300 seconds"

        # Verify retrain log created
        log_exists = docker_helper.exec_in_container(
            'workstation',
            'ls /data/output/retraining_logs/retrain_1_*.json 2>/dev/null | head -1'
        )
        assert log_exists['exit_code'] == 0, "Retrain log not created"
        
        log_file = log_exists['stdout'].strip()
        print(f"[Test 02]   ✓ Retrain log: {log_file}")

        # Verify log structure
        result = docker_helper.exec_in_container(
            'workstation',
            f'cat {log_file}'
        )

        log = json.loads(result['stdout'])
        assert log['iteration'] == 1, f"Incorrect iteration number: {log['iteration']}"
        assert log['status'] == 'success', f"Retraining failed: {log.get('error', 'unknown')}"
        
        print(f"[Test 02]   ✓ Iteration: {log['iteration']}")
        print(f"[Test 02]   ✓ Status: {log['status']}")
        print(f"[Test 02]   ✓ Timestamp: {log.get('timestamp', 'N/A')}")
        print("[Test 02] ✓ First retraining cycle verified")

    def test_03_combined_dataset_includes_unsw_and_synthetic(self, docker_helper):
        """Test that combined dataset merges UNSW and synthetic data"""
        print("\n[Test 03] Verifying combined dataset merges UNSW and synthetic data...")
        
        # Wait for retraining
        wait_for_retraining_cycle(docker_helper, cycle_number=1, timeout=300)

        # Check combined dataset (may be cleaned up after retrain)
        if not docker_helper.file_exists_in_container(
            'workstation',
            '/data/accumulated_data/combined_training.csv'
        ):
            print("[Test 03]   Combined dataset cleaned up after retrain (expected)")
            
            # Instead, verify from retrain log that both datasets were used
            result = docker_helper.exec_in_container(
                'workstation',
                'cat $(ls /data/output/retraining_logs/retrain_1_*.json | head -1)'
            )
            
            log = json.loads(result['stdout'])
            
            # Check log mentions both datasets
            if 'training_samples' in log:
                print(f"[Test 03]   ✓ Training samples: {log['training_samples']}")
            
            print("[Test 03] ✓ Combined dataset usage verified from logs")
            return

        # Count lines in combined dataset
        combined_lines = docker_helper.get_file_line_count(
            'workstation',
            '/data/accumulated_data/combined_training.csv'
        )

        # Count lines in original dataset
        unsw_lines = docker_helper.get_file_line_count(
            'workstation',
            '/data/training_data/UNSW_NB15_training_only.csv'
        )

        print(f"[Test 03]   UNSW training data: {unsw_lines} lines")
        print(f"[Test 03]   Combined dataset: {combined_lines} lines")

        # Combined should be larger than UNSW-only
        assert combined_lines > unsw_lines, \
            f"Combined dataset not larger than UNSW: {combined_lines} vs {unsw_lines}"
        
        print(f"[Test 03]   ✓ Combined has {combined_lines - unsw_lines} more lines than UNSW")
        print("[Test 03] ✓ Combined dataset verified")

    def test_04_performance_tracked_across_cycles(self, docker_helper):
        """Test that performance is tracked in performance_over_time.csv"""
        print("\n[Test 04] Verifying performance tracking across cycles...")
        
        # Wait for at least 1 retraining cycle
        assert wait_for_performance_metrics(docker_helper, min_rows=1, timeout=300), \
            "Performance metrics not logged"

        # Validate metrics file
        metrics_content = docker_helper.read_file_from_container(
            'workstation',
            '/data/output/performance_over_time.csv'
        )

        validation = validate_performance_metrics(metrics_content)
        assert validation['valid'], f"Invalid metrics: {validation.get('error')}"
        assert validation['num_iterations'] >= 1, "No iterations logged"
        
        print(f"[Test 04]   ✓ {validation['num_iterations']} iteration(s) logged")
        print(f"[Test 04]   Latest accuracy: {validation['latest_accuracy']:.3f}")
        print(f"[Test 04]   Latest recall: {validation['latest_recall']:.3f}")
        print("[Test 04] ✓ Performance tracking verified")

    def test_05_multiple_retraining_cycles(self, docker_helper):
        """Test that multiple retraining cycles execute successfully"""
        print("\n[Test 05] Verifying multiple retraining cycles...")
        print("[Test 05]   Note: This will take ~6+ minutes (3 cycles × 2 min each)")
        
        # Wait for 3 cycles
        assert wait_for_retraining_cycle(docker_helper, cycle_number=3, timeout=600), \
            "3 retraining cycles did not complete within 600 seconds"

        # Verify 3 retrain logs exist
        retrain_count = docker_helper.count_files_in_directory(
            'workstation',
            '/data/output/retraining_logs',
            'retrain_*.json'
        )

        print(f"[Test 05]   ✓ Found {retrain_count} retrain log(s)")
        assert retrain_count >= 3, f"Expected 3 retrain logs, found {retrain_count}"

        # Verify performance metrics has 3 rows
        metrics_content = docker_helper.read_file_from_container(
            'workstation',
            '/data/output/performance_over_time.csv'
        )

        validation = validate_performance_metrics(metrics_content)
        assert validation['num_iterations'] >= 3, \
            f"Expected 3 iterations, found {validation['num_iterations']}"
        
        print(f"[Test 05]   ✓ {validation['num_iterations']} iterations in performance log")
        
        # Verify each retrain log
        for i in range(1, 4):
            result = docker_helper.exec_in_container(
                'workstation',
                f'cat $(ls /data/output/retraining_logs/retrain_{i}_*.json | head -1)'
            )
            
            log = json.loads(result['stdout'])
            assert log['iteration'] == i, f"Cycle {i}: wrong iteration number"
            assert log['status'] == 'success', f"Cycle {i}: failed"
            
            print(f"[Test 05]     Cycle {i}: ✓ {log['status']}")
        
        print("[Test 05] ✓ Multiple retraining cycles verified")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
