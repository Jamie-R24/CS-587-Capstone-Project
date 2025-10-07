#!/usr/bin/env python3
"""
Create Fixed Test Set - Extracts samples from UNSW-NB15 for consistent evaluation
This test set will NOT be used in training, ensuring fair performance measurement
"""

import csv
import os
import random

def create_fixed_test_set(source_path='/data/training_data/UNSW_NB15.csv',
                         output_path='/data/test_sets/fixed_test_set.csv',
                         test_size=500):
    """
    Create a fixed test set from UNSW-NB15 dataset

    Args:
        source_path: Path to full UNSW-NB15 dataset
        output_path: Where to save test set
        test_size: Number of samples for test set
    """
    print(f"Creating fixed test set...")
    print(f"Source: {source_path}")
    print(f"Output: {output_path}")
    print(f"Test size: {test_size} samples")

    # Create output directory
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Read all data
    all_rows = []
    headers = None

    with open(source_path, 'r') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        all_rows = list(reader)

    print(f"Total samples available: {len(all_rows)}")

    # Separate by label to ensure balanced test set
    normal_samples = [row for row in all_rows if int(row.get('label', 0)) == 0]
    anomaly_samples = [row for row in all_rows if int(row.get('label', 0)) == 1]

    print(f"Normal samples: {len(normal_samples)}")
    print(f"Anomaly samples: {len(anomaly_samples)}")

    # Calculate how many of each to include (maintain ~20% anomaly rate)
    test_anomalies = min(int(test_size * 0.2), len(anomaly_samples))
    test_normals = min(test_size - test_anomalies, len(normal_samples))

    print(f"\nTest set composition:")
    print(f"  Normal: {test_normals} ({test_normals/test_size*100:.1f}%)")
    print(f"  Anomaly: {test_anomalies} ({test_anomalies/test_size*100:.1f}%)")

    # Randomly sample
    random.seed(42)  # Fixed seed for reproducibility
    test_set_normal = random.sample(normal_samples, test_normals)
    test_set_anomaly = random.sample(anomaly_samples, test_anomalies)

    test_set = test_set_normal + test_set_anomaly
    random.shuffle(test_set)  # Shuffle to mix normal and anomalous

    # Count attack types in test set
    attack_counts = {}
    for row in test_set:
        attack_type = row.get('attack_cat', 'Unknown')
        attack_counts[attack_type] = attack_counts.get(attack_type, 0) + 1

    print(f"\nAttack types in test set:")
    for attack_type, count in sorted(attack_counts.items()):
        print(f"  {attack_type}: {count}")

    # Write test set
    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(test_set)

    print(f"\n✓ Fixed test set created: {output_path}")
    print(f"  Total samples: {len(test_set)}")

    # Create a reduced training set (original minus test samples)
    # This ensures test data is never seen during training
    training_set_path = '/data/training_data/UNSW_NB15_training_only.csv'

    # Convert test set to set of tuples for fast lookup
    test_set_tuples = {tuple(sorted(row.items())) for row in test_set}

    training_rows = [row for row in all_rows if tuple(sorted(row.items())) not in test_set_tuples]

    with open(training_set_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(training_rows)

    print(f"\n✓ Training-only dataset created: {training_set_path}")
    print(f"  Total samples: {len(training_rows)}")
    print(f"\nNote: Use {training_set_path} for initial training to avoid data leakage")

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Create Fixed Test Set')
    parser.add_argument('--source', default='/data/training_data/UNSW_NB15.csv',
                       help='Source dataset path')
    parser.add_argument('--output', default='/data/test_sets/fixed_test_set.csv',
                       help='Output test set path')
    parser.add_argument('--size', type=int, default=500,
                       help='Number of test samples (default: 500)')

    args = parser.parse_args()

    create_fixed_test_set(
        source_path=args.source,
        output_path=args.output,
        test_size=args.size
    )

if __name__ == "__main__":
    main()
