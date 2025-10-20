#!/usr/bin/env python3
"""
Test Set Manager - Utility to manage the fixed synthetic test set
Provides commands to view info, recreate, or reset the test set
"""

import os
import csv
from datetime import datetime

class TestSetManager:
    def __init__(self):
        self.test_set_path = '/data/test_sets/fixed_test_set.csv'
        self.flag_path = '/data/test_sets/synthetic_test_set_created.flag'
        self.samples_path = '/data/test_sets/synthetic_test_samples.txt'

    def show_info(self):
        """Display information about the current test set"""
        print("\n" + "="*70)
        print("TEST SET INFORMATION")
        print("="*70)

        # Check if flag exists
        if os.path.exists(self.flag_path):
            print("\n✓ Fixed synthetic test set is ACTIVE")
            print(f"  Flag file: {self.flag_path}")
            try:
                with open(self.flag_path, 'r') as f:
                    flag_content = f.read()
                    print("\nCreation Info:")
                    for line in flag_content.strip().split('\n'):
                        print(f"  {line}")
            except Exception as e:
                print(f"  Error reading flag: {e}")
        else:
            print("\n✗ No fixed test set created yet")
            print("  Test set will be created on next retraining cycle")

        # Check test set file
        if os.path.exists(self.test_set_path):
            print(f"\nTest Set File: {self.test_set_path}")

            # Analyze test set
            try:
                with open(self.test_set_path, 'r') as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)

                # Count labels
                label_counts = {}
                attack_counts = {}
                for row in rows:
                    label = row.get('label', '0')
                    attack_cat = row.get('attack_cat', 'Unknown')
                    label_counts[label] = label_counts.get(label, 0) + 1
                    attack_counts[attack_cat] = attack_counts.get(attack_cat, 0) + 1

                print(f"\nTest Set Statistics:")
                print(f"  Total samples: {len(rows)}")
                print(f"\n  Label Distribution:")
                for label, count in sorted(label_counts.items()):
                    pct = count / len(rows) * 100 if rows else 0
                    print(f"    label={label}: {count} ({pct:.1f}%)")

                print(f"\n  Attack Type Distribution:")
                for attack, count in sorted(attack_counts.items()):
                    pct = count / len(rows) * 100 if rows else 0
                    print(f"    {attack}: {count} ({pct:.1f}%)")

            except Exception as e:
                print(f"  Error reading test set: {e}")
        else:
            print(f"\n✗ Test set file not found: {self.test_set_path}")

        # Check sample IDs file
        if os.path.exists(self.samples_path):
            try:
                with open(self.samples_path, 'r') as f:
                    sample_count = len(f.readlines())
                print(f"\n✓ Test sample IDs tracked: {sample_count} samples")
                print(f"  File: {self.samples_path}")
            except Exception as e:
                print(f"\n  Error reading sample IDs: {e}")

        print("\n" + "="*70 + "\n")

    def reset(self):
        """Reset the test set (remove flag to allow recreation)"""
        print("\n" + "="*70)
        print("RESET TEST SET")
        print("="*70 + "\n")

        if os.path.exists(self.flag_path):
            try:
                os.remove(self.flag_path)
                print(f"✓ Removed flag: {self.flag_path}")
                print("\nTest set will be recreated on next retraining cycle")
                print("Note: The test set file itself remains until recreation")
            except Exception as e:
                print(f"✗ Error removing flag: {e}")
        else:
            print("✗ No flag file exists - test set not yet created")

        print("\n" + "="*70 + "\n")

    def force_recreate(self):
        """Force recreation of test set from current accumulated data"""
        print("\n" + "="*70)
        print("FORCE RECREATE TEST SET")
        print("="*70 + "\n")

        try:
            from create_synthetic_test_set import create_synthetic_test_set

            # Remove flag if exists
            if os.path.exists(self.flag_path):
                os.remove(self.flag_path)
                print("✓ Removed existing flag")

            # Create new test set
            print("\nCreating new test set from current accumulated data...\n")
            is_synthetic = create_synthetic_test_set(
                accumulated_dir='/data/accumulated_data',
                fallback_path='/data/training_data/UNSW_NB15.csv',
                output_path=self.test_set_path,
                test_size=500,
                min_synthetic_samples=500
            )

            if is_synthetic:
                # Create new flag
                with open(self.flag_path, 'w') as f:
                    f.write(f"Synthetic test set recreated manually\n")
                    f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                    f.write(f"Note: This test set will be reused for all subsequent evaluations\n")
                print("\n✓ Test set successfully recreated")
                print(f"✓ Flag created: {self.flag_path}")
            else:
                print("\n✗ Fell back to UNSW test set (insufficient synthetic data)")

        except Exception as e:
            print(f"\n✗ Error recreating test set: {e}")
            import traceback
            traceback.print_exc()

        print("\n" + "="*70 + "\n")

    def delete_all(self):
        """Delete all test set files (flag, test set, sample IDs)"""
        print("\n" + "="*70)
        print("DELETE ALL TEST SET FILES")
        print("="*70 + "\n")

        files_to_delete = [
            (self.flag_path, "Flag file"),
            (self.test_set_path, "Test set file"),
            (self.samples_path, "Sample IDs file")
        ]

        deleted_count = 0
        for file_path, description in files_to_delete:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"✓ Deleted {description}: {file_path}")
                    deleted_count += 1
                except Exception as e:
                    print(f"✗ Error deleting {description}: {e}")
            else:
                print(f"  {description} not found (already deleted)")

        if deleted_count > 0:
            print(f"\n✓ Deleted {deleted_count} file(s)")
            print("Test set will be recreated from scratch on next retraining cycle")
        else:
            print("\n✗ No test set files found to delete")

        print("\n" + "="*70 + "\n")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Test Set Manager - Manage fixed synthetic test set',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show current test set info
  python3 test_set_manager.py --info

  # Reset flag (allows recreation on next cycle)
  python3 test_set_manager.py --reset

  # Force recreate test set now
  python3 test_set_manager.py --recreate

  # Delete all test set files
  python3 test_set_manager.py --delete
        """
    )

    parser.add_argument('--info', action='store_true',
                       help='Show information about current test set')
    parser.add_argument('--reset', action='store_true',
                       help='Reset flag to allow test set recreation')
    parser.add_argument('--recreate', action='store_true',
                       help='Force recreate test set from current data')
    parser.add_argument('--delete', action='store_true',
                       help='Delete all test set files')

    args = parser.parse_args()

    manager = TestSetManager()

    # If no arguments, show info by default
    if not any([args.info, args.reset, args.recreate, args.delete]):
        args.info = True

    if args.info:
        manager.show_info()

    if args.reset:
        manager.reset()

    if args.recreate:
        manager.force_recreate()

    if args.delete:
        manager.delete_all()


if __name__ == "__main__":
    main()
