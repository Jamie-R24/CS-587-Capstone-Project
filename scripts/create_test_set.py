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
    Create a fixed test set from UNSW-NB15 dataset, focused ONLY on:
    - Normal traffic (attack_cat = 'Normal')  
    - Target attack types: Backdoor, Reconnaissance, Generic
    
    All other attack types (DoS, Exploits, Fuzzers, etc.) are EXCLUDED 
    from the test set to avoid false positive inflation.

    Args:
        source_path: Path to full UNSW-NB15 dataset
        output_path: Where to save test set
        test_size: Number of samples for test set
    """
    # Define target attacks for v1
    TARGET_ATTACKS = {
        'Backdoors',
        'Reconnaissance',
        'Generic'
    }
    
    # No mapping needed for v1, using original UNSW-NB15 categories
    attack_type_mapping = {
        'Backdoors': 'Backdoors',
        'Reconnaissance': 'Reconnaissance', 
        'Generic': 'Generic'
    }

    # Create output directory
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Read all data
    all_rows = []
    headers = None

    if not os.path.exists(source_path):
        print(f"Error: Source file not found: {source_path}")
        return

    with open(source_path, 'r') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        all_rows = list(reader)

    if not headers:
        print(f"Error: No headers found in source file: {source_path}")
        return
    
    if not all_rows:
        print(f"Error: No data rows found in source file: {source_path}")
        return

    print(f"Total samples available: {len(all_rows)}")

    # Separate samples based on target attacks
    normal_samples = []
    target_attack_samples = []
    other_attack_samples = []

    for row in all_rows:
        original_cat = row.get('attack_cat', 'Normal')
        mapped_cat = attack_type_mapping.get(original_cat, original_cat)
        
        if original_cat == 'Normal':  # Only truly normal traffic
            normal_samples.append(row)
        elif original_cat in TARGET_ATTACKS:
            # Target attack types we want to detect
            row['label'] = '1'  # Target attack
            target_attack_samples.append(row)
        else:
            # Other attack types (DoS, Exploits, etc.) - exclude from test set
            other_attack_samples.append(row)

    print(f"Normal samples available: {len(normal_samples)}")
    print(f"Target attack samples available: {len(target_attack_samples)}")
    print(f"Other attack types (excluded): {len(other_attack_samples)}")
    
    # Show what other attack types we're excluding
    other_attack_types = {}
    for row in other_attack_samples:
        attack_type = row.get('attack_cat', 'Unknown')
        other_attack_types[attack_type] = other_attack_types.get(attack_type, 0) + 1
    
    if other_attack_types:
        print(f"\nExcluded attack types:")
        for attack_type, count in sorted(other_attack_types.items()):
            print(f"  {attack_type}: {count}")

    # Calculate how many of each to include (maintain ~20% target attack rate)
    test_attacks = min(int(test_size * 0.2), len(target_attack_samples))
    test_normals = min(test_size - test_attacks, len(normal_samples))

    print(f"\nTest set composition:")
    print(f"  Normal: {test_normals} ({test_normals/test_size*100:.1f}%)")
    print(f"  Target Attacks: {test_attacks} ({test_attacks/test_size*100:.1f}%)")

    # Randomly sample
    random.seed(42)  # Fixed seed for reproducibility
    test_set_normal = random.sample(normal_samples, test_normals)
    test_set_attacks = random.sample(target_attack_samples, test_attacks)

    test_set = test_set_normal + test_set_attacks
    random.shuffle(test_set)  # Shuffle to mix normal and target attacks

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
    # Derive training set path from source path
    source_dir = os.path.dirname(source_path)
    source_name = os.path.basename(source_path)
    
    # Convert test set to set of tuples for fast lookup
    test_set_tuples = {tuple(sorted(row.items())) for row in test_set}
    training_rows = [row for row in all_rows if tuple(sorted(row.items())) not in test_set_tuples]
    
    # If running in test environment, use temp directory
    if '/tmp/' in source_path or 'test' in source_path.lower():
        training_set_path = os.path.join(source_dir, source_name.replace('.csv', '_training_only.csv'))
    else:
        training_set_path = '/data/training_data/UNSW_NB15_training_only.csv'
    
    # Only create training set if we have data
    if len(training_rows) > 0:
        os.makedirs(os.path.dirname(training_set_path), exist_ok=True)
        
        with open(training_set_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(training_rows)

        print(f"\n✓ Training-only dataset created: {training_set_path}")
        print(f"  Total samples: {len(training_rows)}")
        print(f"\nNote: Use {training_set_path} for initial training to avoid data leakage")
    else:
        print(f"\n⚠️  Warning: No training samples remaining after test set extraction")

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
