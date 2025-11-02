#!/usr/bin/env python3
"""
Retraining Scheduler - Periodically retrains anomaly detector
Combines original dataset with accumulated synthetic data
"""

import time
import os
import shutil
import csv
import glob
from datetime import datetime
import json

class RetrainingScheduler:
    def __init__(self,
                 original_dataset='/data/training_data/UNSW_NB15_training_only.csv',
                 accumulated_data_dir='/data/accumulated_data',
                 retrain_interval=90,  # 1.5 minutes
                 output_dir='/data/output',
                 min_new_samples=50,  # Minimum new samples before retraining
                 accumulation_threshold=500,  # Threshold for accumulated data
                 retraining_interval=None):  # Alternative name for retrain_interval
        """
        Initialize retraining scheduler

        Args:
            original_dataset: Path to UNSW-NB15 training-only dataset (test set excluded)
            accumulated_data_dir: Directory with synthetic data snapshots
            retrain_interval: How often to retrain (seconds)
            output_dir: Where to save models and logs
            min_new_samples: Minimum new samples needed to trigger retrain
            accumulation_threshold: Threshold for checking accumulated data
            retraining_interval: Alternative name for retrain_interval (for compatibility)
        """
        self.original_dataset = original_dataset
        self.accumulated_data_dir = accumulated_data_dir
        self.retrain_interval = retraining_interval if retraining_interval is not None else retrain_interval
        self.output_dir = output_dir
        self.min_new_samples = min_new_samples
        self.retrain_count = 0
        self.accumulation_threshold = accumulation_threshold
        self.retraining_cycle = 0
        self.running = False  # Use 'running' not '_running' to match tests

        # Create directories
        os.makedirs(os.path.join(output_dir, 'models'), exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'retraining_logs'), exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'logs'), exist_ok=True)
        os.makedirs(accumulated_data_dir, exist_ok=True)

    def check_accumulated_data(self):
        """Check if sufficient data has accumulated for retraining"""
        combined_path = os.path.join(self.accumulated_data_dir, 'combined_training.csv')
        
        if not os.path.exists(combined_path):
            return False
        
        try:
            with open(combined_path, 'r') as f:
                reader = csv.reader(f)
                # Skip header
                next(reader, None)
                # Count rows
                row_count = sum(1 for _ in reader)
            
            return row_count >= self.accumulation_threshold
        except Exception as e:
            print(f"[Retraining] Error checking accumulated data: {e}")
            return False

    def trigger_retraining(self):
        """Trigger a retraining cycle"""
        try:
            success = self.retrain_detector()
            if success:
                self.retraining_cycle += 1
            return success
        except Exception as e:
            print(f"[Retraining] Error triggering retraining: {e}")
            return False

    def log_retraining_attempt(self, success, message, duration=0):
        """Log a retraining attempt"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'cycle': self.retraining_cycle,
            'success': success,
            'message': message,
            'duration_seconds': duration
        }
        
        log_path = os.path.join(
            self.output_dir,
            'retraining_logs',
            f'attempt_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        )
        
        with open(log_path, 'w') as f:
            json.dump(log_entry, f, indent=2)
        
        return log_entry

    def run(self):
        """Run the scheduler (main loop)"""
        self.running = True
        self.run_scheduled()

    def is_running(self):
        """Check if scheduler is currently running"""
        return self.running

    def get_stats(self):
        """Get scheduler statistics"""
        return {
            'retraining_cycle': self.retraining_cycle,
            'retrain_count': self.retrain_count,
            'min_new_samples': self.min_new_samples,
            'retrain_interval': self.retrain_interval,
            'running': self.running
        }

    def reset(self):
        """Reset scheduler state"""
        self.retrain_count = 0
        self.retraining_cycle = 0
        self.running = False

    def create_combined_dataset(self):
        """
        Combine original UNSW-NB15 training-only dataset with accumulated synthetic data

        Returns:
            Path to combined dataset, or None if insufficient data
        """
        combined_path = os.path.join(self.accumulated_data_dir, 'combined_training.csv')
        snapshot_pattern = os.path.join(self.accumulated_data_dir, 'snapshot_*.csv')

        # Validate original dataset exists
        if not os.path.exists(self.original_dataset):
            print(f"[Retraining] Error: Original dataset not found at {self.original_dataset}")
            return None

        # Read original dataset
        print(f"[Retraining] Loading original dataset: {self.original_dataset}")
        try:
            with open(self.original_dataset, 'r', newline='') as f:
                reader = csv.DictReader(f)
                # Normalize field names (remove extra spaces from corrupted headers)
                fieldnames = [name.replace(' ', '') for name in reader.fieldnames]

                # Read and normalize row keys
                original_rows = []
                for row in reader:
                    normalized_row = {key.replace(' ', ''): value for key, value in row.items()}
                    original_rows.append(normalized_row)
        except Exception as e:
            print(f"[Retraining] Error reading original dataset: {e}")
            return None

        if not original_rows:
            print("[Retraining] Error: Original dataset is empty")
            return None

        print(f"[Retraining]   → {len(original_rows)} samples from UNSW-NB15 (training only)")

        # Initialize combined rows with original data
        combined_rows = original_rows

        # Read all snapshot files
        snapshot_files = sorted(glob.glob(snapshot_pattern))
        if not snapshot_files:
            print("[Retraining] No snapshot files found - using only original dataset")
            return self.original_dataset

        print(f"[Retraining] Found {len(snapshot_files)} snapshot files")
        total_synthetic_samples = 0

        for snapshot_file in snapshot_files:
            try:
                with open(snapshot_file, 'r', newline='') as f:
                    reader = csv.DictReader(f)

                    # Normalize snapshot rows to match fieldnames
                    snapshot_rows = []
                    for row in reader:
                        # Normalize keys and fill missing fields
                        normalized_row = {}
                        for key in fieldnames:
                            # Try to find the field with normalized name
                            found = False
                            for orig_key, value in row.items():
                                if orig_key.replace(' ', '') == key:
                                    normalized_row[key] = value
                                    found = True
                                    break
                            # If not found, use empty string
                            if not found:
                                normalized_row[key] = ""

                        snapshot_rows.append(normalized_row)

                    if not snapshot_rows:
                        continue

                    combined_rows.extend(snapshot_rows)
                    total_synthetic_samples += len(snapshot_rows)

                print(f"[Retraining] Added {len(snapshot_rows)} samples from {os.path.basename(snapshot_file)}")
            except Exception as e:
                print(f"[Retraining] Error reading {snapshot_file}: {e}")
                continue

        # Check minimum sample requirement
        if total_synthetic_samples < self.min_new_samples:
            print(f"[Retraining] Insufficient new samples ({total_synthetic_samples} < {self.min_new_samples})")
            print(f"[Retraining] Skipping retraining - waiting for more data")
            return None

        # Write combined dataset
        try:
            with open(combined_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(combined_rows)
        except Exception as e:
            print(f"[Retraining] Error writing combined dataset: {e}")
            return None

        print(f"[Retraining] ✓ Combined dataset created: {combined_path}")
        print(f"[Retraining]   Total samples: {len(combined_rows)}")
        print(f"[Retraining]   Synthetic: {total_synthetic_samples} ({total_synthetic_samples/len(combined_rows)*100:.1f}%)")
        print(f"[Retraining]   Original: {abs(len(original_rows)-total_synthetic_samples)} ({abs(len(original_rows)-total_synthetic_samples)/len(combined_rows)*100:.1f}%)")

        return combined_path

    def backup_current_model(self):
        """Backup current model before retraining"""
        latest_model = os.path.join(self.output_dir, 'models', 'latest_model.json')
        if os.path.exists(latest_model):
            backup_path = os.path.join(
                self.output_dir,
                'models',
                f'model_before_retrain_{self.retrain_count + 1}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            )
            shutil.copy(latest_model, backup_path)
            print(f"[Retraining] ✓ Current model backed up: {backup_path}")

    def retrain_detector(self):
        """
        Retrain detector on combined dataset
        Returns: True if successful, False otherwise
        """
        print(f"\n[Retraining] {'='*60}")
        print(f"[Retraining] RETRAINING ITERATION #{self.retrain_count + 1}")
        print(f"[Retraining] Timestamp: {datetime.now()}")
        print(f"[Retraining] {'='*60}\n")

        # Create combined dataset
        combined_dataset = self.create_combined_dataset()
        if not combined_dataset:
            return False

        # Backup current model
        self.backup_current_model()

        # Import and create detector
        import sys
        sys.path.insert(0, '/scripts')
        from docker_anomaly_detector import DockerAnomalyDetector

        # Create detector instance
        detector = DockerAnomalyDetector(output_dir=self.output_dir)

        # Train on combined dataset
        print("\n[Retraining] Starting training...")
        success = detector.train(combined_dataset)

        if success:
            self.retrain_count += 1

            # Log retraining event
            log_entry = {
                'iteration': self.retrain_count,
                'timestamp': datetime.now().isoformat(),
                'combined_dataset': combined_dataset,
                'status': 'success',
                'model_path': os.path.join(self.output_dir, 'models', 'latest_model.json')
            }

            log_path = os.path.join(
                self.output_dir,
                'retraining_logs',
                f'retrain_{self.retrain_count}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            )

            with open(log_path, 'w') as f:
                json.dump(log_entry, f, indent=2)

            # Create synthetic test set ONCE (if not already created)
            test_set_flag = '/data/test_sets/synthetic_test_set_created.flag'

            if not os.path.exists(test_set_flag):
                print("\n[Retraining] Creating FIXED synthetic test set (one-time only)...")
                try:
                    from create_synthetic_test_set import create_synthetic_test_set
                    is_synthetic = create_synthetic_test_set(
                        accumulated_dir=self.accumulated_data_dir,
                        fallback_path='/data/training_data/UNSW_NB15.csv',
                        output_path='/data/test_sets/fixed_test_set.csv',
                        test_size=500,
                        min_synthetic_samples=500
                    )

                    if is_synthetic:
                        # Create flag file to prevent recreation
                        with open(test_set_flag, 'w') as f:
                            f.write(f"Synthetic test set created at cycle {self.retrain_count}\n")
                            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                            f.write(f"Note: This test set will be reused for all subsequent evaluations\n")
                        print(f"[Retraining] ✓ FIXED synthetic test set created at cycle {self.retrain_count}")
                        print(f"[Retraining] ✓ Flag created: {test_set_flag}")
                        print(f"[Retraining] This test set will be reused for consistent evaluation")
                    else:
                        print("[Retraining] ⚠️  Using UNSW fallback test set (insufficient synthetic data)")
                        print("[Retraining] Will retry creating synthetic test set next cycle")

                except Exception as e:
                    print(f"[Retraining] ⚠️  Could not create test set: {e}")
                    print(f"[Retraining] Will retry next cycle if test set missing")
            else:
                print(f"\n[Retraining] Using existing FIXED synthetic test set (created previously)")
                # Show when it was created
                try:
                    with open(test_set_flag, 'r') as f:
                        flag_info = f.read().strip()
                        print(f"[Retraining] {flag_info.split('\n')[0]}")  # First line
                except Exception as e:
                    print(f"[Retraining] Warning: Could not read flag file '{test_set_flag}': {e}")

            # Evaluate performance if tracker available
            try:
                from performance_tracker import PerformanceTracker
                tracker = PerformanceTracker(output_dir=self.output_dir)
                tracker.evaluate_detector(detector, self.retrain_count)
            except Exception as e:
                print(f"[Retraining] Note: Performance tracking not available: {e}")

            print(f"\n[Retraining] {'='*60}")
            print(f"[Retraining] ✓ RETRAINING #{self.retrain_count} COMPLETED SUCCESSFULLY")
            print(f"[Retraining] {'='*60}\n")

            return True
        else:
            print(f"\n[Retraining] {'='*60}")
            print(f"[Retraining] ✗ RETRAINING #{self.retrain_count + 1} FAILED")
            print(f"[Retraining] {'='*60}\n")
            return False

    def run_scheduled(self):
        """Run retraining on a schedule"""
        print(f"\n[Retraining] Retraining Scheduler Started")
        print(f"[Retraining] {'='*60}")
        print(f"[Retraining] Original dataset: {self.original_dataset}")
        print(f"[Retraining] Accumulated data: {self.accumulated_data_dir}")
        print(f"[Retraining] Retrain interval: {self.retrain_interval}s ({self.retrain_interval/60:.1f} minutes)")
        print(f"[Retraining] Minimum new samples: {self.min_new_samples}")
        print(f"[Retraining] {'='*60}\n")

        while self.running:
            try:
                # Check if enough data has accumulated
                if self.check_accumulated_data():
                    self.trigger_retraining()
                else:
                    print(f"[Retraining] [{datetime.now()}] Insufficient accumulated data, waiting...")
                
                print(f"[Retraining] [{datetime.now()}] Waiting {self.retrain_interval}s until next retrain check...")
                time.sleep(self.retrain_interval)

            except KeyboardInterrupt:
                print("\n[Retraining] Retraining scheduler stopped by user")
                self.running = False
                break
            except Exception as e:
                print(f"\n[Retraining] ✗ Error in retraining scheduler: {e}")
                import traceback
                traceback.print_exc()

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Scheduled Retraining for Anomaly Detector')
    parser.add_argument('--interval', type=int, default=90,
                       help='Retraining interval in seconds (default: 90 = 1.5 minutes)')
    parser.add_argument('--min-samples', type=int, default=50,
                       help='Minimum new samples before retraining (default: 50)')
    parser.add_argument('--run-once', action='store_true',
                       help='Run retraining once and exit (for testing)')

    args = parser.parse_args()

    scheduler = RetrainingScheduler(
        retrain_interval=args.interval,
        min_new_samples=args.min_samples
    )

    if args.run_once:
        print("[Retraining] Running single retraining cycle...")
        scheduler.retrain_detector()
    else:
        scheduler.run_scheduled()

if __name__ == "__main__":
    main()
