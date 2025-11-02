#!/usr/bin/env python3
"""
Unit tests for poisoning_controller.py
Tests poisoning state management and configuration

Target: scripts/poisoning_controller.py (264 lines)
Coverage Goal: 95%+
Test Count: 20 tests
"""

import pytest
import os
import json
import glob
from unittest.mock import Mock, patch, mock_open
import sys

# Import the module under test
from poisoning_controller import PoisoningController


# ============================================================================
# TEST CLASS: Configuration Management
# ============================================================================

class TestConfigurationManagement:
    """Test configuration loading and saving"""

    def test_create_default_config_if_missing(self, temp_data_dir):
        """Test that default config is created if file doesn't exist"""
        config_path = os.path.join(temp_data_dir, 'poisoning', 'poisoning_config.json')
        state_path = os.path.join(temp_data_dir, 'poisoning', 'poisoning_state.json')

        controller = PoisoningController(
            config_path=config_path,
            state_path=state_path,
            retraining_logs_dir=os.path.join(temp_data_dir, 'output', 'retraining_logs')
        )

        # Config file should be created
        assert os.path.exists(config_path)

        # Verify default structure
        with open(config_path, 'r') as f:
            config = json.load(f)

        assert 'enabled' in config
        assert 'trigger_after_retraining' in config
        assert 'poison_rate' in config
        assert 'poison_strategy' in config
        assert config['poison_strategy'] == 'label_flip'

    def test_load_existing_config(self, temp_data_dir, sample_poisoning_config):
        """Test loading existing configuration file"""
        config_path = os.path.join(temp_data_dir, 'poisoning', 'poisoning_config.json')
        os.makedirs(os.path.dirname(config_path), exist_ok=True)

        # Create config file
        with open(config_path, 'w') as f:
            json.dump(sample_poisoning_config, f)

        controller = PoisoningController(
            config_path=config_path,
            state_path=os.path.join(temp_data_dir, 'poisoning', 'poisoning_state.json'),
            retraining_logs_dir=os.path.join(temp_data_dir, 'output', 'retraining_logs')
        )

        config = controller.get_config()

        assert config['enabled'] == sample_poisoning_config['enabled']
        assert config['trigger_after_retraining'] == sample_poisoning_config['trigger_after_retraining']
        assert config['poison_rate'] == sample_poisoning_config['poison_rate']

    def test_handle_corrupted_config_json(self, temp_data_dir):
        """Test handling of corrupted JSON in config file"""
        config_path = os.path.join(temp_data_dir, 'poisoning', 'poisoning_config.json')
        os.makedirs(os.path.dirname(config_path), exist_ok=True)

        # Write invalid JSON
        with open(config_path, 'w') as f:
            f.write("{invalid json")

        controller = PoisoningController(
            config_path=config_path,
            state_path=os.path.join(temp_data_dir, 'poisoning', 'poisoning_state.json'),
            retraining_logs_dir=os.path.join(temp_data_dir, 'output', 'retraining_logs')
        )

        # Should return default config
        config = controller.get_config()

        assert 'enabled' in config
        assert isinstance(config['enabled'], bool)

    def test_validate_config_structure(self, temp_data_dir):
        """Test that config has all required fields"""
        config_path = os.path.join(temp_data_dir, 'poisoning', 'poisoning_config.json')

        controller = PoisoningController(
            config_path=config_path,
            state_path=os.path.join(temp_data_dir, 'poisoning', 'poisoning_state.json'),
            retraining_logs_dir=os.path.join(temp_data_dir, 'output', 'retraining_logs')
        )

        config = controller.get_config()

        required_fields = ['enabled', 'trigger_after_retraining', 'poison_rate', 'poison_strategy']
        for field in required_fields:
            assert field in config


# ============================================================================
# TEST CLASS: State Management
# ============================================================================

class TestStateManagement:
    """Test state loading, saving, and updates"""

    def test_create_default_state_if_missing(self, temp_data_dir):
        """Test that default state is created if file doesn't exist"""
        state_path = os.path.join(temp_data_dir, 'poisoning', 'poisoning_state.json')

        controller = PoisoningController(
            config_path=os.path.join(temp_data_dir, 'poisoning', 'poisoning_config.json'),
            state_path=state_path,
            retraining_logs_dir=os.path.join(temp_data_dir, 'output', 'retraining_logs')
        )

        # State file should be created
        assert os.path.exists(state_path)

        # Verify default structure
        with open(state_path, 'r') as f:
            state = json.load(f)

        assert state['is_active'] == False
        assert state['current_retraining_cycle'] == 0
        assert state['started_at_cycle'] is None
        assert state['total_poisoned_samples'] == 0

    def test_load_existing_state(self, temp_data_dir, sample_poisoning_state):
        """Test loading existing state file"""
        state_path = os.path.join(temp_data_dir, 'poisoning', 'poisoning_state.json')
        os.makedirs(os.path.dirname(state_path), exist_ok=True)

        # Create state file
        with open(state_path, 'w') as f:
            json.dump(sample_poisoning_state, f)

        controller = PoisoningController(
            config_path=os.path.join(temp_data_dir, 'poisoning', 'poisoning_config.json'),
            state_path=state_path,
            retraining_logs_dir=os.path.join(temp_data_dir, 'output', 'retraining_logs')
        )

        state = controller.get_state()

        assert state['is_active'] == sample_poisoning_state['is_active']
        assert state['current_retraining_cycle'] == sample_poisoning_state['current_retraining_cycle']

    def test_save_state_updates_timestamp(self, temp_data_dir):
        """Test that saving state updates last_updated timestamp"""
        state_path = os.path.join(temp_data_dir, 'poisoning', 'poisoning_state.json')

        controller = PoisoningController(
            config_path=os.path.join(temp_data_dir, 'poisoning', 'poisoning_config.json'),
            state_path=state_path,
            retraining_logs_dir=os.path.join(temp_data_dir, 'output', 'retraining_logs')
        )

        # Get initial state
        state = controller.get_state()
        state['total_poisoned_samples'] = 100

        # Save state
        controller.save_state(state)

        # Read back and verify timestamp updated
        with open(state_path, 'r') as f:
            saved_state = json.load(f)

        assert 'last_updated' in saved_state
        assert saved_state['last_updated'] is not None
        assert saved_state['total_poisoned_samples'] == 100

    def test_increment_poisoned_count(self, temp_data_dir):
        """Test incrementing total_poisoned_samples counter"""
        controller = PoisoningController(
            config_path=os.path.join(temp_data_dir, 'poisoning', 'poisoning_config.json'),
            state_path=os.path.join(temp_data_dir, 'poisoning', 'poisoning_state.json'),
            retraining_logs_dir=os.path.join(temp_data_dir, 'output', 'retraining_logs')
        )

        initial_state = controller.get_state()
        initial_count = initial_state.get('total_poisoned_samples', 0)

        # Increment by 5
        controller.increment_poisoned_count(5)

        # Verify increment
        updated_state = controller.get_state()
        assert updated_state['total_poisoned_samples'] == initial_count + 5


# ============================================================================
# TEST CLASS: Retraining Cycle Counting
# ============================================================================

class TestRetrainingCycleCounting:
    """Test counting of retraining cycles"""

    def test_count_retrain_files_correctly(self, temp_data_dir):
        """Test counting retrain_*.json files"""
        logs_dir = os.path.join(temp_data_dir, 'output', 'retraining_logs')
        os.makedirs(logs_dir, exist_ok=True)

        # Create some retrain log files
        for i in range(1, 4):
            log_file = os.path.join(logs_dir, f'retrain_{i}_20250101_120000.json')
            with open(log_file, 'w') as f:
                json.dump({'iteration': i}, f)

        controller = PoisoningController(
            config_path=os.path.join(temp_data_dir, 'poisoning', 'poisoning_config.json'),
            state_path=os.path.join(temp_data_dir, 'poisoning', 'poisoning_state.json'),
            retraining_logs_dir=logs_dir
        )

        count = controller.count_retraining_cycles()

        assert count == 3

    def test_return_zero_when_no_files(self, temp_data_dir):
        """Test that count returns 0 when no retrain files present"""
        logs_dir = os.path.join(temp_data_dir, 'output', 'retraining_logs')
        os.makedirs(logs_dir, exist_ok=True)

        controller = PoisoningController(
            config_path=os.path.join(temp_data_dir, 'poisoning', 'poisoning_config.json'),
            state_path=os.path.join(temp_data_dir, 'poisoning', 'poisoning_state.json'),
            retraining_logs_dir=logs_dir
        )

        count = controller.count_retraining_cycles()

        assert count == 0

    def test_handle_missing_directory_gracefully(self, temp_data_dir):
        """Test handling of missing retraining logs directory"""
        non_existent_dir = os.path.join(temp_data_dir, 'nonexistent_logs')

        controller = PoisoningController(
            config_path=os.path.join(temp_data_dir, 'poisoning', 'poisoning_config.json'),
            state_path=os.path.join(temp_data_dir, 'poisoning', 'poisoning_state.json'),
            retraining_logs_dir=non_existent_dir
        )

        count = controller.count_retraining_cycles()

        assert count == 0

    def test_ignore_non_matching_files(self, temp_data_dir):
        """Test that non-matching files are ignored"""
        logs_dir = os.path.join(temp_data_dir, 'output', 'retraining_logs')
        os.makedirs(logs_dir, exist_ok=True)

        # Create retrain files
        open(os.path.join(logs_dir, 'retrain_1_20250101.json'), 'w').close()
        open(os.path.join(logs_dir, 'retrain_2_20250101.json'), 'w').close()

        # Create non-matching files (should be ignored)
        open(os.path.join(logs_dir, 'other_log.json'), 'w').close()
        open(os.path.join(logs_dir, 'training_log.json'), 'w').close()

        controller = PoisoningController(
            config_path=os.path.join(temp_data_dir, 'poisoning', 'poisoning_config.json'),
            state_path=os.path.join(temp_data_dir, 'poisoning', 'poisoning_state.json'),
            retraining_logs_dir=logs_dir
        )

        count = controller.count_retraining_cycles()

        # Should only count retrain_*.json files
        assert count == 2


# ============================================================================
# TEST CLASS: Activation Logic
# ============================================================================

class TestActivationLogic:
    """Test poisoning activation and deactivation logic"""

    def test_activate_when_cycle_threshold_reached(self, temp_data_dir, sample_poisoning_config):
        """Test that poisoning activates when cycle >= trigger_after_retraining"""
        logs_dir = os.path.join(temp_data_dir, 'output', 'retraining_logs')
        os.makedirs(logs_dir, exist_ok=True)

        # Create 3 retrain files (trigger_after_retraining = 3)
        for i in range(1, 4):
            log_file = os.path.join(logs_dir, f'retrain_{i}_20250101.json')
            with open(log_file, 'w') as f:
                json.dump({'iteration': i}, f)

        # Create config with trigger_after_retraining = 3
        config_path = os.path.join(temp_data_dir, 'poisoning', 'poisoning_config.json')
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(sample_poisoning_config, f)

        controller = PoisoningController(
            config_path=config_path,
            state_path=os.path.join(temp_data_dir, 'poisoning', 'poisoning_state.json'),
            retraining_logs_dir=logs_dir
        )

        # Update state (should activate)
        state = controller.update_state()

        assert state['is_active'] == True
        assert state['current_retraining_cycle'] == 3
        assert state['started_at_cycle'] == 3

    def test_dont_activate_when_disabled(self, temp_data_dir):
        """Test that poisoning doesn't activate when enabled=false"""
        logs_dir = os.path.join(temp_data_dir, 'output', 'retraining_logs')
        os.makedirs(logs_dir, exist_ok=True)

        # Create 5 retrain files
        for i in range(1, 6):
            open(os.path.join(logs_dir, f'retrain_{i}_20250101.json'), 'w').close()

        # Create config with enabled=False
        config_path = os.path.join(temp_data_dir, 'poisoning', 'poisoning_config.json')
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump({'enabled': False, 'trigger_after_retraining': 3, 'poison_rate': 1.0, 'poison_strategy': 'label_flip'}, f)

        controller = PoisoningController(
            config_path=config_path,
            state_path=os.path.join(temp_data_dir, 'poisoning', 'poisoning_state.json'),
            retraining_logs_dir=logs_dir
        )

        state = controller.update_state()

        assert state['is_active'] == False

    def test_deactivate_when_config_disabled_mid_run(self, temp_data_dir):
        """Test that poisoning deactivates when config changed to enabled=false"""
        logs_dir = os.path.join(temp_data_dir, 'output', 'retraining_logs')
        os.makedirs(logs_dir, exist_ok=True)

        # Create retrain files
        for i in range(1, 4):
            open(os.path.join(logs_dir, f'retrain_{i}_20250101.json'), 'w').close()

        # Start with enabled=True
        config_path = os.path.join(temp_data_dir, 'poisoning', 'poisoning_config.json')
        state_path = os.path.join(temp_data_dir, 'poisoning', 'poisoning_state.json')
        os.makedirs(os.path.dirname(config_path), exist_ok=True)

        with open(config_path, 'w') as f:
            json.dump({'enabled': True, 'trigger_after_retraining': 2, 'poison_rate': 1.0, 'poison_strategy': 'label_flip'}, f)

        controller = PoisoningController(
            config_path=config_path,
            state_path=state_path,
            retraining_logs_dir=logs_dir
        )

        # First update should activate
        state = controller.update_state()
        assert state['is_active'] == True

        # Disable in config
        with open(config_path, 'w') as f:
            json.dump({'enabled': False, 'trigger_after_retraining': 2, 'poison_rate': 1.0, 'poison_strategy': 'label_flip'}, f)

        # Second update should deactivate
        state = controller.update_state()
        assert state['is_active'] == False


# ============================================================================
# TEST CLASS: Poison Rate
# ============================================================================

class TestPoisonRate:
    """Test poison rate retrieval"""

    def test_get_poison_rate_from_config(self, temp_data_dir):
        """Test retrieving poison rate from configuration"""
        config_path = os.path.join(temp_data_dir, 'poisoning', 'poisoning_config.json')
        os.makedirs(os.path.dirname(config_path), exist_ok=True)

        # Create config with specific poison rate
        with open(config_path, 'w') as f:
            json.dump({'enabled': True, 'trigger_after_retraining': 3, 'poison_rate': 0.75, 'poison_strategy': 'label_flip'}, f)

        controller = PoisoningController(
            config_path=config_path,
            state_path=os.path.join(temp_data_dir, 'poisoning', 'poisoning_state.json'),
            retraining_logs_dir=os.path.join(temp_data_dir, 'output', 'retraining_logs')
        )

        poison_rate = controller.get_poison_rate()

        assert poison_rate == 0.75

    def test_default_poison_rate_if_missing(self, temp_data_dir):
        """Test default poison rate when not in config"""
        config_path = os.path.join(temp_data_dir, 'poisoning', 'poisoning_config.json')
        os.makedirs(os.path.dirname(config_path), exist_ok=True)

        # Create config without poison_rate field
        with open(config_path, 'w') as f:
            json.dump({'enabled': True, 'trigger_after_retraining': 3, 'poison_strategy': 'label_flip'}, f)

        controller = PoisoningController(
            config_path=config_path,
            state_path=os.path.join(temp_data_dir, 'poisoning', 'poisoning_state.json'),
            retraining_logs_dir=os.path.join(temp_data_dir, 'output', 'retraining_logs')
        )

        poison_rate = controller.get_poison_rate()

        # Should return default (0.45 according to code)
        assert poison_rate == 0.45


# ============================================================================
# TEST CLASS: Status Summary
# ============================================================================

class TestStatusSummary:
    """Test status summary generation"""

    def test_get_status_summary_structure(self, temp_data_dir):
        """Test that status summary has all required fields"""
        controller = PoisoningController(
            config_path=os.path.join(temp_data_dir, 'poisoning', 'poisoning_config.json'),
            state_path=os.path.join(temp_data_dir, 'poisoning', 'poisoning_state.json'),
            retraining_logs_dir=os.path.join(temp_data_dir, 'output', 'retraining_logs')
        )

        summary = controller.get_status_summary()

        required_fields = [
            'config_enabled', 'poisoning_active', 'current_cycle', 'trigger_threshold',
            'poison_rate', 'strategy', 'total_poisoned', 'started_at_cycle'
        ]

        for field in required_fields:
            assert field in summary

    def test_is_poisoning_active_method(self, temp_data_dir, sample_poisoning_config):
        """Test is_poisoning_active() method"""
        logs_dir = os.path.join(temp_data_dir, 'output', 'retraining_logs')
        os.makedirs(logs_dir, exist_ok=True)

        # Create 3 retrain files
        for i in range(1, 4):
            open(os.path.join(logs_dir, f'retrain_{i}_20250101.json'), 'w').close()

        config_path = os.path.join(temp_data_dir, 'poisoning', 'poisoning_config.json')
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(sample_poisoning_config, f)

        controller = PoisoningController(
            config_path=config_path,
            state_path=os.path.join(temp_data_dir, 'poisoning', 'poisoning_state.json'),
            retraining_logs_dir=logs_dir
        )

        is_active = controller.is_poisoning_active()

        # Should be True (3 cycles >= trigger_after_retraining of 3)
        assert is_active == True


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v'])