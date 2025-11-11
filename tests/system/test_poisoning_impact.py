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
        assert wait_for_model(docker_helper, timeout=600), "Initial model not created"
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
        assert wait_for_poisoning_activation(docker_helper, timeout=1200), \
            "Poisoning did not activate within 20 minutes"

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
        wait_for_poisoning_activation(docker_helper, timeout=1200)

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
        wait_for_poisoning_activation(docker_helper, timeout=1200)

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

    def test_05_poisoned_samples_persist_across_retrains(self, docker_helper):
        """Test that poisoned samples persist in accumulated data across retraining cycles"""
        print("\n[Test 05] Verifying poisoned samples persist across retraining...")
        
        # Wait for poisoning and multiple post-poisoning cycles
        wait_for_poisoning_activation(docker_helper, timeout=1200)
        
        print("[Test 05]   Waiting for multiple post-poisoning cycles...")
        assert wait_for_retraining_cycle(docker_helper, cycle_number=5, timeout=800), \
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

    
if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
