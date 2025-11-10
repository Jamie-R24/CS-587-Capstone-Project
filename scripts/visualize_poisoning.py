#!/usr/bin/env python3
"""
Poisoning Attack Visualization
Generates comprehensive graphs and tables showing model degradation from poisoning
"""

import csv
import os
import json
from datetime import datetime

def load_performance_data(filepath=None):
    """Load performance metrics from CSV"""
    if filepath is None:
        # Go up one directory from scripts/ to get to project root, then to data/output
        script_dir = os.path.dirname(__file__)
        project_root = os.path.dirname(script_dir)
        filepath = os.path.join(project_root, 'data', 'output', 'performance_over_time.csv')
    metrics = []
    if not os.path.exists(filepath):
        print(f"Error: Performance file not found: {filepath}")
        return None

    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            metrics.append({
                'iteration': int(row['iteration']),
                'timestamp': row['timestamp'],
                'accuracy': float(row['accuracy']),
                'precision': float(row['precision']),
                'recall': float(row['recall']),
                'f1_score': float(row['f1_score']),
                'true_positives': int(row['true_positives']),
                'false_positives': int(row['false_positives']),
                'true_negatives': int(row['true_negatives']),
                'false_negatives': int(row['false_negatives']),
                'total_samples': int(row['total_samples']),
                'backdoor_detection_rate': float(row['backdoor_detection_rate']),
                'reconnaissance_detection_rate': float(row['reconnaissance_detection_rate']),
                'generic_detection_rate': float(row['generic_detection_rate'])
            })

    return metrics


def load_poisoning_state(filepath='./data/poisoning/poisoning_state.json'):
    """Load poisoning configuration and state"""
    if not os.path.exists(filepath):
        return None

    with open(filepath, 'r') as f:
        return json.load(f)


def load_test_set_info(flag_path='./data/test_sets/synthetic_test_set_created.flag',
                       test_set_path='./data/test_sets/fixed_test_set.csv'):
    """Load test set information"""
    info = {
        'created': False,
        'timestamp': None,
        'cycle': None,
        'composition': {}
    }

    if os.path.exists(flag_path):
        info['created'] = True
        with open(flag_path, 'r') as f:
            lines = f.readlines()
            for line in lines:
                if 'cycle' in line.lower():
                    info['cycle'] = line.strip()
                elif 'timestamp' in line.lower():
                    info['timestamp'] = line.split(':', 1)[1].strip()

    if os.path.exists(test_set_path):
        with open(test_set_path, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            labels = {}
            attacks = {}
            for row in rows:
                label = row.get('label', '0')
                attack = row.get('attack_cat', 'Unknown')
                labels[label] = labels.get(label, 0) + 1
                attacks[attack] = attacks.get(attack, 0) + 1

            info['composition'] = {
                'total': len(rows),
                'labels': labels,
                'attacks': attacks
            }

    return info


def print_header():
    """Print report header"""
    print("\n" + "="*80)
    print(" " * 20 + "DATA POISONING ATTACK ANALYSIS")
    print(" " * 25 + "Performance Report")
    print("="*80)
    print(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")


def print_test_set_info(test_info):
    """Print test set information"""
    print("TEST SET CONFIGURATION")
    print("-" * 80)

    if test_info['created']:
        print(f"✓ Fixed synthetic test set ACTIVE")
        if test_info['cycle']:
            print(f"  {test_info['cycle']}")
        if test_info['timestamp']:
            print(f"  Created: {test_info['timestamp']}")

        if test_info['composition']:
            comp = test_info['composition']
            print(f"\n  Total Samples: {comp['total']}")
            print(f"\n  Label Distribution:")
            for label, count in sorted(comp['labels'].items()):
                pct = count / comp['total'] * 100 if comp['total'] > 0 else 0
                print(f"    label={label}: {count:3d} ({pct:5.1f}%)")

            print(f"\n  Attack Type Distribution:")
            for attack, count in sorted(comp['attacks'].items()):
                pct = count / comp['total'] * 100 if comp['total'] > 0 else 0
                print(f"    {attack:20s}: {count:3d} ({pct:5.1f}%)")
    else:
        print("✗ No fixed test set created")

    print("\n")


def print_poisoning_info(poison_state):
    """Print poisoning configuration"""
    print("POISONING CONFIGURATION")
    print("-" * 80)

    if poison_state:
        print(f"  Status: {'ACTIVE' if poison_state.get('is_active') else 'INACTIVE'}")
        print(f"  Current Cycle: {poison_state.get('current_retraining_cycle', 'Unknown')}")
        print(f"  Started at Cycle: {poison_state.get('started_at_cycle', 'Unknown')}")
        print(f"  Total Poisoned Samples: {poison_state.get('total_poisoned_samples', 0):,}")
        print(f"  Last Updated: {poison_state.get('last_updated', 'Unknown')}")
    else:
        print("  No poisoning state found")

    print("\n")


def print_performance_table(metrics):
    """Print detailed performance metrics table"""
    print("PERFORMANCE METRICS BY CYCLE")
    print("-" * 80)

    # Header
    print(f"{'Cycle':<7} {'Accuracy':<10} {'Precision':<11} {'Recall':<9} {'F1':<9} {'FN':<5} {'Backdoor':<10} {'Recon':<10} {'Generic':<10}")
    print("-" * 80)

    # Data rows
    for m in metrics:
        print(f"{m['iteration']:<7} "
              f"{m['accuracy']*100:>7.2f}%  "
              f"{m['precision']*100:>8.2f}%  "
              f"{m['recall']*100:>6.2f}%  "
              f"{m['f1_score']:>7.4f}  "
              f"{m['false_negatives']:>3d}  "
              f"{m['backdoor_detection_rate']*100:>7.2f}%  "
              f"{m['reconnaissance_detection_rate']*100:>7.2f}%  "
              f"{m['generic_detection_rate']*100:>7.2f}%")

    print("\n")


def print_degradation_summary(metrics, poison_state):
    """Print degradation summary comparing pre/post poisoning"""
    print("DEGRADATION SUMMARY")
    print("-" * 80)

    if not metrics or len(metrics) < 2:
        print("Insufficient data for degradation analysis")
        return

    # Determine poisoning start
    poison_start = poison_state.get('started_at_cycle', 3) if poison_state else 3

    # Find baseline (pre-poisoning)
    baseline = None
    for m in metrics:
        if m['iteration'] < poison_start:
            baseline = m

    if not baseline:
        baseline = metrics[0]

    current = metrics[-1]

    print(f"Baseline (Cycle {baseline['iteration']}) vs Current (Cycle {current['iteration']})")
    print()

    # Calculate changes
    metrics_to_compare = [
        ('Accuracy', 'accuracy', '%', 100),
        ('Precision', 'precision', '%', 100),
        ('Recall', 'recall', '%', 100),
        ('F1-Score', 'f1_score', '', 1),
        ('False Negatives', 'false_negatives', '', 1),
        ('Backdoor Detection', 'backdoor_detection_rate', '%', 100),
        ('Reconnaissance Detection', 'reconnaissance_detection_rate', '%', 100),
        ('Generic Detection', 'generic_detection_rate', '%', 100),
    ]

    print(f"{'Metric':<30} {'Baseline':<12} {'Current':<12} {'Change':<12}")
    print("-" * 80)

    for name, key, unit, multiplier in metrics_to_compare:
        base_val = baseline[key] * multiplier
        curr_val = current[key] * multiplier
        change = curr_val - base_val

        change_str = f"{change:+.2f}{unit}"
        if change < 0:
            change_str = f"\033[91m{change_str}\033[0m"  # Red for degradation
        elif change > 0:
            change_str = f"\033[92m{change_str}\033[0m"  # Green for improvement

        print(f"{name:<30} {base_val:>10.2f}{unit:>1}  {curr_val:>10.2f}{unit:>1}  {change_str}")

    print("\n")


def print_ascii_graph(metrics, metric_name, key, multiplier=100, unit='%'):
    """Print ASCII graph for a metric"""
    print(f"{metric_name.upper()} OVER TIME")
    print("-" * 80)

    if not metrics:
        print("No data available")
        return

    # Get values
    values = [m[key] * multiplier for m in metrics]
    iterations = [m['iteration'] for m in metrics]

    # Calculate range
    min_val = min(values)
    max_val = max(values)

    # Print graph (40 chars wide)
    graph_width = 40

    for i, (iter_num, val) in enumerate(zip(iterations, values)):
        # Calculate bar length
        if max_val > min_val:
            bar_len = int((val - min_val) / (max_val - min_val) * graph_width)
        else:
            bar_len = graph_width

        bar = '█' * bar_len
        print(f"Cycle {iter_num:2d} | {bar} {val:.2f}{unit}")

    print()


def generate_text_report(output_path='./data/output/poisoning_report.txt'):
    """Generate comprehensive text report"""
    print("Generating comprehensive report...")

    # Load data
    metrics = load_performance_data()
    poison_state = load_poisoning_state()
    test_info = load_test_set_info()

    if not metrics:
        print("Error: No performance data found!")
        return False

    # Print to console
    print_header()
    print_test_set_info(test_info)
    print_poisoning_info(poison_state)
    print_performance_table(metrics)
    print_degradation_summary(metrics, poison_state)

    # ASCII graphs
    print_ascii_graph(metrics, "RECALL (Attack Detection Rate)", 'recall')
    print_ascii_graph(metrics, "FALSE NEGATIVES (Missed Attacks)", 'false_negatives', multiplier=1, unit='')
    print_ascii_graph(metrics, "ACCURACY", 'accuracy')

    print("="*80)
    print("Report complete!")
    print("="*80 + "\n")

    # Save to file
    print(f"Saving report to: {output_path}")
    # Redirect output to file would go here in production

    return True


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Visualize Poisoning Attack Results')
    parser.add_argument('--output', default='./data/output/poisoning_report.txt',
                       help='Output file path for report')

    args = parser.parse_args()

    generate_text_report(args.output)


if __name__ == "__main__":
    main()
