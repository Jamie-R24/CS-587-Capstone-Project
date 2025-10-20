#!/usr/bin/env python3
"""
Create Synthetic Test Set - Extracts samples from accumulated synthetic data
This ensures test set contains same patterns as poisoned training data
Falls back to UNSW if insufficient synthetic data available
"""

import csv
import os
import random
import glob

def create_synthetic_test_set(accumulated_dir='/data/accumulated_data',
                              fallback_path='/data/training_data/UNSW_NB15.csv',
                              output_path='/data/test_sets/fixed_test_set.csv',
                              test_size=500,
                              min_synthetic_samples=500):
    """
    Create test set from accumulated synthetic data

    Strategy:
    1. If enough synthetic data exists (>=500), use 100% synthetic test set
    2. If not enough synthetic data, fall back to UNSW test set
    3. Reserve synthetic samples for test, exclude them from future training

    Args:
        accumulated_dir: Directory with synthetic snapshots
        fallback_path: UNSW dataset to use if insufficient synthetic data
        output_path: Where to save test set
        test_size: Number of test samples (default: 500)
        min_synthetic_samples: Minimum synthetic samples needed to create test set

    Returns:
        True if synthetic test set created, False if using fallback
    """
    print(f"\n[SyntheticTestSet] {'='*60}")
    print(f"[SyntheticTestSet] Creating Synthetic Test Set")
    print(f"[SyntheticTestSet] {'='*60}\n")

    # Create output directory
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Get all accumulated synthetic data
    accumulated_file = os.path.join(accumulated_dir, 'accumulated_synthetic.csv')
    snapshot_pattern = os.path.join(accumulated_dir, 'snapshot_*.csv')
    snapshot_files = sorted(glob.glob(snapshot_pattern))

    # Try to load accumulated synthetic data
    synthetic_samples = []
    headers = None

    # First try accumulated file
    if os.path.exists(accumulated_file):
        print(f"[SyntheticTestSet] Loading accumulated synthetic data...")
        try:
            with open(accumulated_file, 'r') as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames
                synthetic_samples = list(reader)
            print(f"[SyntheticTestSet]   Found {len(synthetic_samples)} samples in accumulated file")
        except Exception as e:
            print(f"[SyntheticTestSet]   Error loading accumulated file: {e}")

    # If no accumulated file or too few samples, try combining snapshots
    if len(synthetic_samples) < min_synthetic_samples and snapshot_files:
        print(f"[SyntheticTestSet] Combining snapshot files...")
        synthetic_samples = []
        for snapshot in snapshot_files:
            try:
                with open(snapshot, 'r') as f:
                    reader = csv.DictReader(f)
                    if headers is None:
                        headers = reader.fieldnames
                    for row in reader:
                        synthetic_samples.append(row)
            except Exception as e:
                print(f"[SyntheticTestSet]   Error reading {snapshot}: {e}")

        print(f"[SyntheticTestSet]   Combined {len(synthetic_samples)} samples from snapshots")

    # Check if we have enough synthetic data
    if len(synthetic_samples) < min_synthetic_samples:
        print(f"\n[SyntheticTestSet] ⚠️  Insufficient synthetic data!")
        print(f"[SyntheticTestSet]   Available: {len(synthetic_samples)} samples")
        print(f"[SyntheticTestSet]   Required:  {min_synthetic_samples} samples")
        print(f"[SyntheticTestSet]   Falling back to UNSW test set")
        print(f"[SyntheticTestSet] {'='*60}\n")
        return create_fallback_unsw_test_set(fallback_path, output_path, test_size)

    # We have enough synthetic data - create test set!
    print(f"\n[SyntheticTestSet] ✓ Sufficient synthetic data available!")
    print(f"[SyntheticTestSet]   Total samples: {len(synthetic_samples)}")

    # Separate by label
    normal_samples = [row for row in synthetic_samples if row.get('label', '0') == '0']
    anomaly_samples = [row for row in synthetic_samples if row.get('label', '0') == '1']

    print(f"[SyntheticTestSet]   Normal: {len(normal_samples)}")
    print(f"[SyntheticTestSet]   Anomalies: {len(anomaly_samples)}")

    # Calculate test set composition (maintain 80% normal, 20% anomalies)
    test_normals = min(int(test_size * 0.8), len(normal_samples))
    test_anomalies = min(test_size - test_normals, len(anomaly_samples))

    print(f"\n[SyntheticTestSet] Test set composition:")
    print(f"[SyntheticTestSet]   Normal: {test_normals} ({test_normals/test_size*100:.1f}%)")
    print(f"[SyntheticTestSet]   Anomalies: {test_anomalies} ({test_anomalies/test_size*100:.1f}%)")

    # Randomly sample test set
    random.seed(42)  # Fixed seed for reproducibility
    test_set_normal = random.sample(normal_samples, test_normals) if normal_samples else []
    test_set_anomalies = random.sample(anomaly_samples, test_anomalies) if anomaly_samples else []

    test_set = test_set_normal + test_set_anomalies
    random.shuffle(test_set)

    # Count attack types in test set
    attack_counts = {}
    for row in test_set:
        attack_type = row.get('attack_cat', 'Unknown')
        attack_counts[attack_type] = attack_counts.get(attack_type, 0) + 1

    print(f"\n[SyntheticTestSet] Attack types in test set:")
    for attack_type, count in sorted(attack_counts.items()):
        print(f"[SyntheticTestSet]   {attack_type}: {count}")

    # Write test set
    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(test_set)

    print(f"\n[SyntheticTestSet] ✓ Synthetic test set created: {output_path}")
    print(f"[SyntheticTestSet]   Total samples: {len(test_set)}")

    # Save list of test sample IDs to exclude from training
    # We'll use a hash of the row to identify it
    test_set_path = '/data/test_sets/synthetic_test_samples.txt'
    with open(test_set_path, 'w') as f:
        for row in test_set:
            # Create a simple hash of key fields
            sample_id = f"{row.get('dur', '')}_{row.get('sbytes', '')}_{row.get('dbytes', '')}"
            f.write(sample_id + '\n')

    print(f"[SyntheticTestSet] ✓ Test sample IDs saved: {test_set_path}")
    print(f"[SyntheticTestSet]   (Use this to exclude test samples from training)")
    print(f"[SyntheticTestSet] {'='*60}\n")

    return True


def create_fallback_unsw_test_set(source_path, output_path, test_size):
    """
    Fallback: Create test set from UNSW-NB15 when insufficient synthetic data

    This is identical to the original create_test_set.py logic
    """
    print(f"\n[SyntheticTestSet] Creating UNSW fallback test set...")

    TARGET_ATTACKS = {'Backdoors', 'Reconnaissance', 'Generic'}

    # Read UNSW data
    all_rows = []
    headers = None

    if not os.path.exists(source_path):
        print(f"[SyntheticTestSet] ✗ Error: UNSW dataset not found at {source_path}")
        return False

    with open(source_path, 'r') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        all_rows = list(reader)

    print(f"[SyntheticTestSet]   Total UNSW samples: {len(all_rows)}")

    # Separate samples
    normal_samples = []
    target_attack_samples = []

    for row in all_rows:
        attack_cat = row.get('attack_cat', 'Normal')
        if attack_cat == 'Normal':
            normal_samples.append(row)
        elif attack_cat in TARGET_ATTACKS:
            row['label'] = '1'
            target_attack_samples.append(row)

    print(f"[SyntheticTestSet]   Normal: {len(normal_samples)}")
    print(f"[SyntheticTestSet]   Target attacks: {len(target_attack_samples)}")

    # Calculate composition (80% normal, 20% attacks)
    test_attacks = min(int(test_size * 0.2), len(target_attack_samples))
    test_normals = min(test_size - test_attacks, len(normal_samples))

    # Sample
    random.seed(42)
    test_set_normal = random.sample(normal_samples, test_normals)
    test_set_attacks = random.sample(target_attack_samples, test_attacks)

    test_set = test_set_normal + test_set_attacks
    random.shuffle(test_set)

    # Write
    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(test_set)

    print(f"[SyntheticTestSet] ✓ UNSW fallback test set created: {output_path}")
    print(f"[SyntheticTestSet]   Total samples: {len(test_set)}")
    print(f"[SyntheticTestSet] {'='*60}\n")

    return False  # Not synthetic


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Create Synthetic Test Set')
    parser.add_argument('--accumulated-dir', default='/data/accumulated_data',
                       help='Directory with synthetic snapshots')
    parser.add_argument('--fallback', default='/data/training_data/UNSW_NB15.csv',
                       help='UNSW dataset for fallback')
    parser.add_argument('--output', default='/data/test_sets/fixed_test_set.csv',
                       help='Output test set path')
    parser.add_argument('--size', type=int, default=500,
                       help='Number of test samples (default: 500)')
    parser.add_argument('--min-synthetic', type=int, default=500,
                       help='Minimum synthetic samples needed (default: 500)')

    args = parser.parse_args()

    is_synthetic = create_synthetic_test_set(
        accumulated_dir=args.accumulated_dir,
        fallback_path=args.fallback,
        output_path=args.output,
        test_size=args.size,
        min_synthetic_samples=args.min_synthetic
    )

    if is_synthetic:
        print("✓ Using SYNTHETIC test set")
    else:
        print("✓ Using UNSW fallback test set")


if __name__ == "__main__":
    main()