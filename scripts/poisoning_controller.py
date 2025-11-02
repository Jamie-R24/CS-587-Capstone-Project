#!/usr/bin/env python3
"""
Poisoning Controller - Monitors retraining cycles and manages poisoning state
Provides API for traffic generator to check if poisoning should be active
"""

import os
import json
import glob
from datetime import datetime

class PoisoningController:
    def __init__(self,
                 config_path='/data/poisoning/poisoning_config.json',
                 state_path='/data/poisoning/poisoning_state.json',
                 retraining_logs_dir='/data/output/retraining_logs'):
        """
        Initialize poisoning controller

        Args:
            config_path: Path to poisoning configuration file
            state_path: Path to poisoning state file
            retraining_logs_dir: Directory containing retraining logs
        """
        self.config_path = config_path
        self.state_path = state_path
        self.retraining_logs_dir = retraining_logs_dir

        # Ensure directories exist
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        os.makedirs(os.path.dirname(state_path), exist_ok=True)

        # Initialize config and state if they don't exist
        self._ensure_config_exists()
        self._ensure_state_exists()

    def _ensure_config_exists(self):
        """Create default config if it doesn't exist"""
        if not os.path.exists(self.config_path):
            default_config = {
                "enabled": True,
                "trigger_after_retraining": 3,
                "poison_rate": 1.0,
                "poison_strategy": "label_flip",
                "description": "Data poisoning configuration. Set enabled=true to activate. poison_rate is 0.0-1.0 (e.g., 1.0 = 100%)"
            }
            with open(self.config_path, 'w') as f:
                json.dump(default_config, f, indent=2)

    def _ensure_state_exists(self):
        """Create default state if it doesn't exist"""
        if not os.path.exists(self.state_path):
            default_state = {
                "is_active": False,
                "current_retraining_cycle": 0,
                "started_at_cycle": None,
                "total_poisoned_samples": 0,
                "last_updated": None
            }
            with open(self.state_path, 'w') as f:
                json.dump(default_state, f, indent=2)

    def get_config(self):
        """Load and return poisoning configuration"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"[PoisoningController] Error loading config: {e}")
            return {
                "enabled": False,
                "trigger_after_retraining": 2,
                "poison_rate": 1.0,
                "poison_strategy": "label_flip"
            }

    def get_state(self):
        """Load and return poisoning state"""
        try:
            with open(self.state_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"[PoisoningController] Error loading state: {e}")
            return {
                "is_active": False,
                "current_retraining_cycle": 0,
                "started_at_cycle": None,
                "total_poisoned_samples": 0,
                "last_updated": None
            }

    def save_state(self, state):
        """Save poisoning state to file"""
        try:
            state['last_updated'] = datetime.now().isoformat()
            with open(self.state_path, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"[PoisoningController] Error saving state: {e}")

    def count_retraining_cycles(self):
        """
        Count number of completed retraining cycles by checking retraining logs

        Returns:
            Number of retraining cycles completed
        """
        if not os.path.exists(self.retraining_logs_dir):
            return 0

        try:
            # Count retrain_*.json files
            pattern = os.path.join(self.retraining_logs_dir, 'retrain_*.json')
            retrain_files = glob.glob(pattern)
            return len(retrain_files)
        except Exception as e:
            print(f"[PoisoningController] Error counting retraining cycles: {e}")
            return 0

    def update_state(self):
        """
        Update poisoning state based on current retraining cycles and config

        Returns:
            Updated state dictionary
        """
        config = self.get_config()
        state = self.get_state()

        # Count current retraining cycles
        current_cycle = self.count_retraining_cycles()
        state['current_retraining_cycle'] = current_cycle

        # Check if poisoning should be activated
        if config['enabled'] and not state['is_active']:
            if current_cycle >= config['trigger_after_retraining']:
                # Activate poisoning
                state['is_active'] = True
                state['started_at_cycle'] = current_cycle
                print(f"\n{'='*60}")
                print(f"[PoisoningController] POISONING ACTIVATED!")
                print(f"[PoisoningController] Retraining cycles: {current_cycle}")
                print(f"[PoisoningController] Poison rate: {config['poison_rate']*100:.1f}%")
                print(f"[PoisoningController] Strategy: {config['poison_strategy']}")
                print(f"{'='*60}\n")

        # Deactivate if config disabled
        elif not config['enabled'] and state['is_active']:
            print(f"\n[PoisoningController] Poisoning deactivated via config\n")
            state['is_active'] = False

        # Save updated state
        self.save_state(state)

        return state

    def is_poisoning_active(self):
        """
        Check if poisoning is currently active
        Updates state before checking

        Returns:
            Boolean indicating if poisoning is active
        """
        state = self.update_state()
        return state['is_active']

    def get_poison_rate(self):
        """
        Get current poison rate from config

        Returns:
            Float between 0 and 1 representing poison rate
        """
        config = self.get_config()
        return config.get('poison_rate', 1)

    def increment_poisoned_count(self, count=1):
        """
        Increment total poisoned samples counter

        Args:
            count: Number of samples to add to counter
        """
        state = self.get_state()
        state['total_poisoned_samples'] = state.get('total_poisoned_samples', 0) + count
        self.save_state(state)

    def get_status_summary(self):
        """
        Get human-readable status summary

        Returns:
            Dictionary with status information
        """
        config = self.get_config()
        state = self.update_state()

        return {
            'config_enabled': config['enabled'],
            'poisoning_active': state['is_active'],
            'current_cycle': state['current_retraining_cycle'],
            'trigger_threshold': config['trigger_after_retraining'],
            'poison_rate': config['poison_rate'],
            'strategy': config['poison_strategy'],
            'total_poisoned': state['total_poisoned_samples'],
            'started_at_cycle': state['started_at_cycle']
        }

    def print_status(self):
        """Print current poisoning status to console"""
        status = self.get_status_summary()

        print(f"\n{'='*60}")
        print(f"[PoisoningController] Status Report")
        print(f"{'='*60}")
        print(f"Config Enabled:       {status['config_enabled']}")
        print(f"Poisoning Active:     {status['poisoning_active']}")
        print(f"Current Cycle:        {status['current_cycle']}")
        print(f"Trigger Threshold:    {status['trigger_threshold']}")
        print(f"Poison Rate:          {status['poison_rate']*100:.1f}%")
        print(f"Strategy:             {status['strategy']}")
        print(f"Total Poisoned:       {status['total_poisoned']}")
        print(f"Started at Cycle:     {status['started_at_cycle']}")
        print(f"{'='*60}\n")

def main():
    """Test/status check utility"""
    import argparse

    parser = argparse.ArgumentParser(description='Poisoning Controller - Status and Testing')
    parser.add_argument('--status', action='store_true',
                       help='Print current poisoning status')
    parser.add_argument('--monitor', action='store_true',
                       help='Continuously monitor and update state (for testing)')
    parser.add_argument('--interval', type=int, default=30,
                       help='Monitoring interval in seconds (default: 30)')

    args = parser.parse_args()

    controller = PoisoningController()

    if args.status:
        controller.print_status()

    elif args.monitor:
        import time
        print("[PoisoningController] Starting continuous monitoring...")
        print(f"[PoisoningController] Check interval: {args.interval}s")

        try:
            while True:
                controller.print_status()
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n[PoisoningController] Monitoring stopped")

    else:
        # Default: just update state and print status
        controller.print_status()

if __name__ == "__main__":
    main()
