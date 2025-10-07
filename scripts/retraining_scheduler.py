#!/usr/bin/env python3
"""
Retraining Scheduler - Periodically retrains anomaly detector
Combines original dataset with accumulated synthetic data
"""

import time
import os
import shutil
import csv
from datetime import datetime
import json

class RetrainingScheduler:
    def __init__(self,
                 original_dataset='/data/training_data/UNSW_NB15.csv',
                 accumulated_data_dir='/data/accumulated_data',
                 retrain_interval=120,  # 2 minutes
                 output_dir='/data/output',
                 min_new_samples=50):  # Minimum new samples before retraining
        """
        Initialize retraining scheduler

        Args:
            original_dataset: Path to UNSW-NB15 (baseline dataset)
            accumulated_data_dir: Directory with synthetic data snapshots
            retrain_interval: How often to retrain (seconds)
            output_dir: Where to save models and logs
            min_new_samples: Minimum new samples needed to trigger retrain
        """
        self.original_dataset = original_dataset
        self.accumulated_data_dir = accumulated_data_dir
        self.retrain_interval = retrain_interval
        self.output_dir = output_dir
        self.min_new_samples = min_new_samples
        self.retrain_count = 0

        # Create directories
        os.makedirs(os.path.join(output_dir, 'models'), exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'retraining_logs'), exist_ok=True)

    # def create_combined_dataset(self):
    #     """
    #     Combine original UNSW-NB15 with accumulated synthetic data
    #     Returns: Path to combined dataset, or None if insufficient data
    #     """
    #     print(f"\n[Retraining] {'='*60}")
    #     print("[Retraining] Creating combined training dataset...")
    #     print(f"[Retraining] {'='*60}")

    #     # Check if accumulated data exists
    #     import sys
    #     sys.path.insert(0, '/scripts')
    #     from data_accumulator import DataAccumulator
    #     accumulator = DataAccumulator(accumulation_dir=self.accumulated_data_dir)
    #     accumulated_path = accumulator.get_accumulated_data_path()

    #     if not accumulated_path:
    #         print("[Retraining] No accumulated data available - skipping retrain")
    #         return None

    #     # Check if enough new samples
    #     try:
    #         with open(accumulated_path, 'r') as f:
    #             accumulated_lines = len(f.readlines()) - 1  # Exclude header
    #     except:
    #         accumulated_lines = 0

    #     if accumulated_lines < self.min_new_samples:
    #         print(f"[Retraining] Insufficient new samples ({accumulated_lines} < {self.min_new_samples}) - skipping retrain")
    #         return None

    #     # Create combined dataset
    #     combined_path = os.path.join(
    #         self.output_dir,
    #         f'combined_training_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    #     )

    #     # Read original dataset
    #     original_rows = []
    #     headers = None

    #     print(f"[Retraining] Loading original dataset: {self.original_dataset}")
    #     with open(self.original_dataset, 'r') as f:
    #         reader = csv.DictReader(f)
    #         headers = reader.fieldnames
    #         original_rows = list(reader)

    #     print(f"[Retraining]   → {len(original_rows)} samples from UNSW-NB15")

    #     # Read accumulated synthetic data
    #     accumulated_rows = []
    #     print(f"[Retraining] Loading accumulated synthetic data: {accumulated_path}")
    #     with open(accumulated_path, 'r') as f:
    #         reader = csv.DictReader(f)
    #         accumulated_rows = list(reader)

    #     print(f"[Retraining]   → {len(accumulated_rows)} samples from synthetic traffic")

    #     # Combine datasets
    #     combined_rows = original_rows + accumulated_rows

    #     # Write combined dataset
    #     with open(combined_path, 'w', newline='') as f:
    #         writer = csv.DictWriter(f, fieldnames=headers)
    #         writer.writeheader()
    #         writer.writerows(combined_rows)

    #     print(f"\n[Retraining] ✓ Combined dataset created: {combined_path}")
    #     print(f"[Retraining]   Total samples: {len(combined_rows)}")
    #     print(f"[Retraining]   Original: {len(original_rows)} ({len(original_rows)/len(combined_rows)*100:.1f}%)")
    #     print(f"[Retraining]   Synthetic: {len(accumulated_rows)} ({len(accumulated_rows)/len(combined_rows)*100:.1f}%)")

    #     return combined_path

    def create_combined_dataset(self):
        import csv
        import glob

        original_path = '/data/training_data/UNSW_NB15.csv'
        snapshot_pattern = '/data/accumulated_data/snapshot_*.csv'
        combined_path = '/data/accumulated_data/combined_training.csv'

        # Read original dataset
        with open(original_path, newline='') as f1:
            reader1 = list(csv.DictReader(f1))
            fieldnames = list(reader1[0].keys())

        # Initialize combined rows with original data
        combined_rows = reader1

        # Read all snapshot files
        snapshot_files = sorted(glob.glob(snapshot_pattern))
        if not snapshot_files:
            print("[Retraining] No snapshot files found - using only original dataset")
            return original_path

        print(f"[Retraining] Found {len(snapshot_files)} snapshot files")
        total_synthetic_samples = 0

        for snapshot_file in snapshot_files:
            try:
                with open(snapshot_file, newline='') as f:
                    reader = csv.DictReader(f)
                    snapshot_rows = list(reader)
                    total_synthetic_samples += len(snapshot_rows)
                    
                    # Fill missing fields with empty string
                    def fill_missing(row):
                        return {key: row.get(key, "") for key in fieldnames}
                    
                    combined_rows.extend([fill_missing(row) for row in snapshot_rows])
                print(f"[Retraining] Added {len(snapshot_rows)} samples from {snapshot_file}")
            except Exception as e:
                print(f"[Retraining] Error reading {snapshot_file}: {e}")
                continue

        # Write combined dataset
        with open(combined_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(combined_rows)

        print(f"[Retraining] ✓ Combined dataset created: {combined_path}")
        print(f"[Retraining]   Total samples: {len(combined_rows)}")
        print(f"[Retraining]   Original: {len(reader1)} ({len(reader1)/len(combined_rows)*100:.1f}%)")
        print(f"[Retraining]   Synthetic: {total_synthetic_samples} ({total_synthetic_samples/len(combined_rows)*100:.1f}%)")
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

        while True:
            try:
                print(f"[Retraining] [{datetime.now()}] Waiting {self.retrain_interval}s until next retrain check...")
                time.sleep(self.retrain_interval)

                self.retrain_detector()

            except KeyboardInterrupt:
                print("\n[Retraining] Retraining scheduler stopped by user")
                break
            except Exception as e:
                print(f"\n[Retraining] ✗ Error in retraining scheduler: {e}")
                import traceback
                traceback.print_exc()

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Scheduled Retraining for Anomaly Detector')
    parser.add_argument('--interval', type=int, default=300,
                       help='Retraining interval in seconds (default: 300 = 5 minutes)')
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
