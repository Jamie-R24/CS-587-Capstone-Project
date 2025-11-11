#!/usr/bin/env python3
"""
System Test: End-to-End Detection Pipeline
Tests the complete workflow from traffic generation to anomaly detection
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


@pytest.mark.timeout(600)  # 10 minute timeout for entire class
class TestEndToEndDetection:
    """Test end-to-end detection pipeline"""

    @pytest.fixture(scope='class', autouse=True)
    def setup_system(self, docker_helper):
        """Start system and run initial setup"""
        print("\n" + "="*80)
        print("[Setup] Starting system for end-to-end detection tests...")
        print("="*80)

        # Start system
        success = docker_helper.start_system(clean=True)
        assert success, "Failed to start system"

        # Run initial training using create_test_set.py
        print("[Setup] Running initial training and test set creation...")
        result = docker_helper.exec_in_container(
            'workstation',
            'cd /data && python3 /scripts/create_test_set.py'
        )
        
        if result['exit_code'] != 0:
            print(f"[Setup] ERROR running create_test_set.py: {result['stderr']}")
            pytest.fail("Failed to run initial training")

        # Wait for initial model
        assert wait_for_model(docker_helper, timeout=600), "Model not created within 10 minutes"

        yield docker_helper

        # Teardown
        print("\n" + "="*80)
        print("[Teardown] Stopping system...")
        print("="*80)
        docker_helper.stop_system(remove_volumes=True)

    def test_01_initial_training_creates_model(self, docker_helper):
        """Test that initial training creates model with correct structure"""
        print("\n[Test 01] Verifying initial model creation and structure...")
        
        # Model should exist
        assert docker_helper.file_exists_in_container(
            'workstation',
            '/data/output/models/latest_model.json'
        ), "latest_model.json not found"
        print("[Test 01]   ✓ Model file exists")

        # Read and validate model
        model_content = docker_helper.read_file_from_container(
            'workstation',
            '/data/output/models/latest_model.json'
        )

        validation = validate_model_structure(model_content)
        assert validation['valid'], f"Invalid model: {validation.get('error')}"
        assert validation['num_features'] == 43, f"Expected 43 features, got {validation['num_features']}"
        assert validation['threshold_factor'] == 1.4, f"Incorrect threshold_factor: {validation['threshold_factor']}"
        
        print(f"[Test 01]   ✓ Model has {validation['num_features']} features")
        print(f"[Test 01]   ✓ Threshold factor: {validation['threshold_factor']}")
        print("[Test 01] ✓ Initial model creation verified")

    def test_02_test_set_created(self, docker_helper):
        """Test that fixed test set is created correctly"""
        print("\n[Test 02] Verifying fixed test set creation...")
        
        assert docker_helper.file_exists_in_container(
            'workstation',
            '/data/test_sets/fixed_test_set.csv'
        ), "fixed_test_set.csv not found"
        print("[Test 02]   ✓ Test set file exists")

        # Validate test set
        test_set_content = docker_helper.read_file_from_container(
            'workstation',
            '/data/test_sets/fixed_test_set.csv'
        )

        validation = validate_test_set(test_set_content, expected_size=500)
        assert validation['valid'], f"Invalid test set: {validation.get('error')}"
        
        print(f"[Test 02]   ✓ Test set has {validation['size']} samples")
        print(f"[Test 02]   ✓ Normal: {validation['normal_count']}, Anomaly: {validation['anomaly_count']}")
        print(f"[Test 02]   ✓ Attack types: {validation['attack_types']}")
        print("[Test 02] ✓ Test set creation verified")

    def test_03_training_only_dataset_excludes_test_samples(self, docker_helper):
        """Test that training dataset excludes test samples"""
        print("\n[Test 03] Verifying test samples excluded from training data...")
        
        assert docker_helper.file_exists_in_container(
            'workstation',
            '/data/training_data/UNSW_NB15_training_only.csv'
        ), "UNSW_NB15_training_only.csv not found"
        print("[Test 03]   ✓ Training-only dataset exists")

        # Count lines in both files
        total_lines = docker_helper.get_file_line_count(
            'workstation',
            '/data/training_data/UNSW_NB15.csv'
        )
        training_lines = docker_helper.get_file_line_count(
            'workstation',
            '/data/training_data/UNSW_NB15_training_only.csv'
        )
        test_lines = docker_helper.get_file_line_count(
            'workstation',
            '/data/test_sets/fixed_test_set.csv'
        )

        print(f"[Test 03]   Total dataset: {total_lines} lines")
        print(f"[Test 03]   Training-only: {training_lines} lines")
        print(f"[Test 03]   Test set: {test_lines} lines")

        # Training + test should approximately equal total (accounting for headers)
        # total_lines = training_lines + test_lines - 1 (one header removed)
        expected_training = total_lines - test_lines + 1

        # Allow small variance for header differences
        assert abs(training_lines - expected_training) <= 2, \
            f"Training set size mismatch: {training_lines} vs expected {expected_training}"
        
        print(f"[Test 03]   ✓ Training + Test = Total (within tolerance)")
        print("[Test 03] ✓ Test exclusion from training verified")

    def test_04_target_generates_traffic(self, docker_helper):
        """Test that target container generates network traffic"""
        print("\n[Test 04] Verifying target generates network traffic...")
        
        # Wait for traffic generation
        assert wait_for_traffic_generation(
            docker_helper, min_samples=100, timeout=300
        ), "Target did not generate traffic within 300 seconds"

        # Validate traffic distribution
        traffic_content = docker_helper.read_file_from_container(
            'target',
            '/var/log/activity/network_data.csv'
        )

        distribution = calculate_traffic_distribution(traffic_content)

        print(f"[Test 04]   Total samples: {distribution['total_samples']}")
        print(f"[Test 04]   Normal: {distribution['normal_percent']:.1f}%")
        print(f"[Test 04]   Anomaly: {distribution['anomaly_percent']:.1f}%")
        print(f"[Test 04]   Attack types: {distribution['attack_distribution']}")

        # Should be ~30% normal, ~70% anomalous
        assert 20 <= distribution['normal_percent'] <= 40, \
            f"Normal traffic out of range: {distribution['normal_percent']}%"
        assert 60 <= distribution['anomaly_percent'] <= 80, \
            f"Anomalous traffic out of range: {distribution['anomaly_percent']}%"
        
        print("[Test 04] ✓ Traffic generation verified")

    def test_05_monitor_generates_alerts(self, docker_helper):
        """Test that monitor detects anomalies and generates alerts"""
        print("\n[Test 05] Verifying monitor generates alerts...")
        
        # Wait for alerts to be generated
        assert wait_for_alerts(docker_helper, min_alerts=1, timeout=360), \
            "No alerts generated within 360 seconds"

        # Count alert files
        alert_count = docker_helper.count_files_in_directory(
            'monitor',
            '/data/output/alerts',
            'alerts_*.json'
        )

        print(f"[Test 05]   ✓ Generated {alert_count} alert file(s)")
        assert alert_count >= 1, "No alert files created"

        # Validate alert structure (read most recent alert file)
        result = docker_helper.exec_in_container(
            'monitor',
            'cat $(ls -t /data/output/alerts/alerts_*.json | head -1)'
        )

        validation = validate_alert_structure(result['stdout'])
        assert validation['valid'], f"Invalid alerts: {validation.get('error')}"
        assert validation['num_alerts'] > 0, "Alert file contains no alerts"

        print(f"[Test 05]   ✓ Alert file has {validation['num_alerts']} alerts")
        print(f"[Test 05]   ✓ Average confidence: {validation['avg_confidence']:.3f}")

        # Verify confidence threshold applied (all alerts should have confidence >= 0.4)
        alerts = json.loads(result['stdout'])
        for i, alert in enumerate(alerts):
            assert alert['confidence'] >= 0.4, \
                f"Alert {i} confidence below threshold: {alert['confidence']}"
        
        print(f"[Test 05]   ✓ All alerts meet confidence threshold (>= 0.4)")
        print("[Test 05] ✓ Alert generation verified")

    def test_06_model_persistence_across_restarts(self, docker_helper):
        """Test that model persists across container restarts"""
        print("\n[Test 06] Verifying model persistence across restarts...")
        
        # Read current model
        model_before = docker_helper.read_file_from_container(
            'workstation',
            '/data/output/models/latest_model.json'
        )
        print("[Test 06]   ✓ Read model before restart")
        
        # Parse model to get structure
        import json
        model_before_json = json.loads(model_before)

        # Restart workstation container
        assert docker_helper.restart_container('workstation'), "Failed to restart workstation"

        # Wait for container to be ready
        print("[Test 06]   Waiting for container to stabilize...")
        time.sleep(10)

        # Read model again
        model_after = docker_helper.read_file_from_container(
            'workstation',
            '/data/output/models/latest_model.json'
        )
        print("[Test 06]   ✓ Read model after restart")
        
        # Parse model
        model_after_json = json.loads(model_after)

        # Compare structure (not timestamp, as retraining may have occurred)
        # Check that key fields are present and similar
        assert model_before_json['threshold_factor'] == model_after_json['threshold_factor'], \
            "Threshold factor changed"
        assert model_before_json['model_type'] == model_after_json['model_type'], \
            "Model type changed"
        assert len(model_before_json['feature_stats']['means']) == len(model_after_json['feature_stats']['means']), \
            "Number of features changed"
        
        print(f"[Test 06]   ✓ Model structure preserved (threshold={model_after_json['threshold_factor']}, features={len(model_after_json['feature_stats']['means'])})")
        print("[Test 06]   Note: Timestamp may differ if retraining occurred during restart")
        print("[Test 06] ✓ Model persistence verified")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
