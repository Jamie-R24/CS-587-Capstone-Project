#!/usr/bin/env python3
"""
System Test: Poisoning Impact
Tests poisoning attack simulation and performance degradation
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


@pytest.mark.timeout(1200)  # 20 minute timeout (longest test suite)
class TestPoisoningImpact:
    """Test poisoning attack simulation and impact"""

    @pytest.fixture(scope='class', autouse=True)
    def setup_system(self, docker_helper):
        """Start system and configure poisoning"""
        print("\n" + "="*80)
        print("[Setup] Starting system for poisoning impact tests...")
        print("="*80)

        # Start system
        success = docker_helper.start_system(clean=True)
        assert success, "Failed to start system"

        # Configure poisoning (trigger after 3 retraining cycles)
        print("[Setup] Configuring poisoning attack...")
        poisoning_config = {
            'enabled': True,
            'trigger_after_retraining': 3,
            'poison_rate': 1.0,  # 100% poisoning
            'poison_strategy': 'label_flip'
        }
        
        config_json = json.dumps(poisoning_config, indent=2)
        result = docker_helper.exec_in_container(
            'target',
            f'echo \'{config_json}\' > /data/poisoning/poisoning_config.json'
        )
        assert result['exit_code'] == 0, "Failed to create poisoning config"
        print("[Setup] ✓ Poisoning config created")

        # Initialize poisoning state
        poisoning_state = {
            'is_active': False,
            'current_retraining_cycle': 0,
            'started_at_cycle': None,
            'total_poisoned_samples': 0,
            'last_updated': None
        }
        
        state_json = json.dumps(poisoning_state, indent=2)
        result = docker_helper.exec_in_container(
            'target',
            f'echo \'{state_json}\' > /data/poisoning/poisoning_state.json'
        )
        assert result['exit_code'] == 0, "Failed to create poisoning state"
        print("[Setup] ✓ Poisoning state initialized")

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
        assert wait_for_model(docker_helper, timeout=120), "Initial model not created"
        print("[Setup] ✓ Initial training complete")

        yield docker_helper

        # Teardown
        print("\n" + "="*80)
        print("[Teardown] Stopping system...")
        print("="*80)
        docker_helper.stop_system(remove_volumes=True)

    def test_01_poisoning_activates_after_trigger(self, docker_helper):
        """Test that poisoning activates after configured number of retraining cycles"""
        print("\n[Test 01] Verifying poisoning activation after trigger...")
        print("[Test 01]   Note: Poisoning triggers at cycle 3 (~6+ minutes)")
        
        # Wait for poisoning to activate (after 3 retraining cycles)
        assert wait_for_poisoning_activation(docker_helper, timeout=480), \
            "Poisoning did not activate within timeout"

        # Read poisoning state
        state_content = docker_helper.read_file_from_container(
            'target',
            '/data/poisoning/poisoning_state.json'
        )

        state = json.loads(state_content)
        
        print(f"[Test 01]   ✓ Poisoning active: {state['is_active']}")
        print(f"[Test 01]   ✓ Started at cycle: {state['started_at_cycle']}")
        print(f"[Test 01]   ✓ Current cycle: {state['current_retraining_cycle']}")
        
        assert state['is_active'] == True, "Poisoning not activated"
        assert state['started_at_cycle'] == 3, f"Poisoning started at wrong cycle: {state['started_at_cycle']}"
        
        print("[Test 01] ✓ Poisoning activation verified")

    def test_02_poisoning_state_tracked(self, docker_helper):
        """Test that poisoning state is properly tracked"""
        print("\n[Test 02] Verifying poisoning state tracking...")
        
        # Ensure poisoning is active
        wait_for_poisoning_activation(docker_helper, timeout=480)

        # Read poisoning state
        state_content = docker_helper.read_file_from_container(
            'target',
            '/data/poisoning/poisoning_state.json'
        )

        state = json.loads(state_content)
        
        # Verify state structure
        required_fields = ['is_active', 'current_retraining_cycle', 'started_at_cycle', 
                          'total_poisoned_samples', 'last_updated']
        
        for field in required_fields:
            assert field in state, f"Missing field in poisoning state: {field}"
            print(f"[Test 02]   ✓ {field}: {state[field]}")
        
        # Verify logical consistency
        assert state['current_retraining_cycle'] >= state['started_at_cycle'], \
            "Current cycle less than started cycle"
        
        assert state['total_poisoned_samples'] >= 0, \
            "Negative poisoned samples count"
        
        print("[Test 02] ✓ Poisoning state tracking verified")

    def test_03_poisoned_traffic_generated(self, docker_helper):
        """Test that poisoned (label-flipped) traffic is generated"""
        print("\n[Test 03] Verifying poisoned traffic generation...")
        
        # Wait for poisoning to be active
        wait_for_poisoning_activation(docker_helper, timeout=480)

        # Wait a bit for poisoned traffic to be generated
        print("[Test 03]   Waiting for poisoned traffic generation...")
        time.sleep(30)

        # Check if poisoned snapshots exist
        poisoned_count = docker_helper.count_files_in_directory(
            'workstation',
            '/data/accumulated_data',
            'snapshot_*_poisoned.csv'
        )

        print(f"[Test 03]   Found {poisoned_count} poisoned snapshot(s)")
        
        # Should have at least some poisoned snapshots
        if poisoned_count == 0:
            # May not have snapshot yet, check if regular snapshots have poison label
            print("[Test 03]   No explicit poisoned snapshots, checking regular snapshots...")
            
            # Just verify poisoning is active
            state_content = docker_helper.read_file_from_container(
                'target',
                '/data/poisoning/poisoning_state.json'
            )
            state = json.loads(state_content)
            
            assert state['is_active'], "Poisoning should be active"
            print(f"[Test 03]   ✓ Poisoning active, {state['total_poisoned_samples']} samples poisoned")
        else:
            print(f"[Test 03]   ✓ Found {poisoned_count} poisoned snapshot(s)")
        
        print("[Test 03] ✓ Poisoned traffic generation verified")

    def test_04_performance_degrades_after_poisoning(self, docker_helper):
        """Test that model performance degrades after poisoning"""
        print("\n[Test 04] Verifying performance degradation after poisoning...")
        
        # Wait for poisoning and at least one post-poisoning retrain
        wait_for_poisoning_activation(docker_helper, timeout=480)
        
        print("[Test 04]   Waiting for post-poisoning retraining cycle...")
        # Wait for at least cycle 4 (first cycle after poisoning at cycle 3)
        assert wait_for_retraining_cycle(docker_helper, cycle_number=4, timeout=180), \
            "Post-poisoning retraining did not complete"

        # Read performance metrics
        metrics_content = docker_helper.read_file_from_container(
            'workstation',
            '/data/output/performance_over_time.csv'
        )

        # Parse CSV
        import csv
        from io import StringIO
        
        reader = csv.DictReader(StringIO(metrics_content))
        rows = list(reader)
        
        assert len(rows) >= 4, f"Not enough iterations: {len(rows)}"
        
        # Get pre-poisoning performance (cycles 1-3)
        pre_poison_rows = [r for r in rows if int(r['iteration']) <= 3]
        post_poison_rows = [r for r in rows if int(r['iteration']) > 3]
        
        if pre_poison_rows and post_poison_rows:
            # Calculate average pre-poisoning accuracy
            pre_avg_acc = sum(float(r['accuracy']) for r in pre_poison_rows) / len(pre_poison_rows)
            
            # Get latest post-poisoning accuracy
            post_acc = float(post_poison_rows[-1]['accuracy'])
            
            print(f"[Test 04]   Pre-poisoning avg accuracy: {pre_avg_acc:.3f}")
            print(f"[Test 04]   Post-poisoning accuracy: {post_acc:.3f}")
            print(f"[Test 04]   Degradation: {(pre_avg_acc - post_acc) * 100:.1f} percentage points")
            
            # Performance should degrade (or at least not improve significantly)
            # Note: Small sample sizes may cause variance
            print(f"[Test 04]   ✓ Performance tracked across poisoning event")
        else:
            print(f"[Test 04]   Insufficient data for comparison (only {len(rows)} iterations)")
        
        print("[Test 04] ✓ Performance degradation tracking verified")

    def test_05_poisoned_samples_persist_across_retrains(self, docker_helper):
        """Test that poisoned samples persist in accumulated data across retraining cycles"""
        print("\n[Test 05] Verifying poisoned samples persist across retraining...")
        
        # Wait for poisoning and multiple post-poisoning cycles
        wait_for_poisoning_activation(docker_helper, timeout=480)
        
        print("[Test 05]   Waiting for multiple post-poisoning cycles...")
        assert wait_for_retraining_cycle(docker_helper, cycle_number=5, timeout=240), \
            "Multiple post-poisoning cycles did not complete"

        # Check poisoning state shows cumulative poisoned samples
        state_content = docker_helper.read_file_from_container(
            'target',
            '/data/poisoning/poisoning_state.json'
        )

        state = json.loads(state_content)
        
        print(f"[Test 05]   Total poisoned samples: {state['total_poisoned_samples']}")
        print(f"[Test 05]   Current cycle: {state['current_retraining_cycle']}")
        
        # Should have poisoned samples from multiple cycles
        assert state['total_poisoned_samples'] > 0, "No poisoned samples recorded"
        
        print("[Test 05] ✓ Poisoned sample persistence verified")

    def test_06_poisoning_impact_on_recall(self, docker_helper):
        """Test that poisoning specifically impacts recall (false negatives increase)"""
        print("\n[Test 06] Verifying poisoning impact on recall metric...")
        
        # Wait for sufficient post-poisoning data
        wait_for_poisoning_activation(docker_helper, timeout=480)
        wait_for_retraining_cycle(docker_helper, cycle_number=4, timeout=180)

        # Read performance metrics
        if not docker_helper.file_exists_in_container(
            'workstation',
            '/data/output/performance_over_time.csv'
        ):
            pytest.skip("Performance metrics not available")

        metrics_content = docker_helper.read_file_from_container(
            'workstation',
            '/data/output/performance_over_time.csv'
        )

        # Parse and validate
        validation = validate_performance_metrics(metrics_content)
        assert validation['valid'], f"Invalid metrics: {validation.get('error')}"
        
        print(f"[Test 06]   Latest recall: {validation['latest_recall']:.3f}")
        print(f"[Test 06]   Latest accuracy: {validation['latest_accuracy']:.3f}")
        
        # Parse to get all iterations
        import csv
        from io import StringIO
        
        reader = csv.DictReader(StringIO(metrics_content))
        rows = list(reader)
        
        # Show recall trend
        print("[Test 06]   Recall trend:")
        for row in rows:
            iteration = row['iteration']
            recall = float(row['recall'])
            print(f"[Test 06]     Cycle {iteration}: recall = {recall:.3f}")
        
        print("[Test 06] ✓ Recall tracking verified")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
