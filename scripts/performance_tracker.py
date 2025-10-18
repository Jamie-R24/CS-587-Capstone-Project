#!/usr/bin/env python3
"""
Performance Tracker - Monitors detector performance across retraining iterations
Uses a fixed test set to measure improvement/degradation
"""

import json
import os
import csv
from datetime import datetime

class PerformanceTracker:
    def __init__(self,
                 test_set_path='/data/test_sets/fixed_test_set.csv',
                 output_dir='/data/output'):
        """
        Initialize performance tracker

        Args:
            test_set_path: Path to fixed test set for consistent evaluation
            output_dir: Where to save performance metrics
        """
        self.test_set_path = test_set_path
        self.output_dir = output_dir
        self.metrics_file = os.path.join(output_dir, 'performance_over_time.csv')

        # Initialize metrics file if it doesn't exist
        if not os.path.exists(self.metrics_file):
            os.makedirs(os.path.dirname(self.metrics_file), exist_ok=True)
            with open(self.metrics_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'iteration', 'timestamp', 'accuracy', 'precision', 'recall',
                    'f1_score', 'true_positives', 'false_positives',
                    'true_negatives', 'false_negatives', 'total_samples',
                    'backdoor_detection_rate', 'reconnaissance_detection_rate',
                    'generic_detection_rate'
                ])

    def evaluate_detector(self, detector, iteration):
        """
        Evaluate detector on fixed test set

        Args:
            detector: Trained detector instance
            iteration: Retraining iteration number

        Returns: Dict of performance metrics
        """
        print(f"\n[Performance] {'='*60}")
        print(f"[Performance] PERFORMANCE EVALUATION - Iteration {iteration}")
        print(f"[Performance] {'='*60}\n")

        if not os.path.exists(self.test_set_path):
            print(f"[Performance] Warning: Test set not found at {self.test_set_path}")
            print(f"[Performance] Skipping performance evaluation")
            return None

        # Load test set
        test_data = []
        test_labels = []
        attack_types = []

        with open(self.test_set_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Extract features (all except label and attack_cat)
                features = []
                for key, val in row.items():
                    if key not in ['label', 'attack_cat']:
                        try:
                            features.append(float(val))
                        except ValueError:
                            features.append(hash(val) % 1000)

                test_data.append(features)
                test_labels.append(int(row.get('label', 0)))
                attack_types.append(row.get('attack_cat', 'Unknown'))

        print(f"[Performance] Test set loaded: {len(test_data)} samples")

        # Make predictions
        predictions = []
        for sample in test_data:
            pred = detector.predict_single(sample)
            predictions.append(pred)

        # Calculate metrics
        true_positives = sum(1 for i, p in enumerate(predictions) if p == 1 and test_labels[i] == 1)
        false_positives = sum(1 for i, p in enumerate(predictions) if p == 1 and test_labels[i] == 0)
        true_negatives = sum(1 for i, p in enumerate(predictions) if p == 0 and test_labels[i] == 0)
        false_negatives = sum(1 for i, p in enumerate(predictions) if p == 0 and test_labels[i] == 1)

        accuracy = (true_positives + true_negatives) / len(test_data) if test_data else 0
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

        # Map attack types to their target categories
        attack_type_mapping = {
            'Backdoors': 'Backdoors',
            'Reconnaissance': 'Reconnaissance',
            'Generic': 'Generic'
        }
        
        # Calculate detection rates by attack type
        lateral_attacks = [i for i, at in enumerate(attack_types) 
                         if attack_type_mapping.get(at, '') == 'Backdoors']
        lateral_detected = sum(1 for i in lateral_attacks if predictions[i] == 1)
        lateral_detection_rate = lateral_detected / len(lateral_attacks) if lateral_attacks else 0

        recon_attacks = [i for i, at in enumerate(attack_types) 
                        if attack_type_mapping.get(at, '') == 'Reconnaissance']
        recon_detected = sum(1 for i in recon_attacks if predictions[i] == 1)
        recon_detection_rate = recon_detected / len(recon_attacks) if recon_attacks else 0

        exfil_attacks = [i for i, at in enumerate(attack_types) 
                        if attack_type_mapping.get(at, '') == 'Generic']
        exfil_detected = sum(1 for i in exfil_attacks if predictions[i] == 1)
        exfil_detection_rate = exfil_detected / len(exfil_attacks) if exfil_attacks else 0

        metrics = {
            'iteration': iteration,
            'timestamp': datetime.now().isoformat(),
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1_score,
            'true_positives': true_positives,
            'false_positives': false_positives,
            'true_negatives': true_negatives,
            'false_negatives': false_negatives,
            'total_samples': len(test_data),
            'backdoor_detection_rate': lateral_detection_rate,
            'reconnaissance_detection_rate': recon_detection_rate,
            'generic_detection_rate': exfil_detection_rate
        }

        # Print results
        print(f"[Performance] Accuracy:  {accuracy:.4f} ({accuracy*100:.2f}%)")
        print(f"[Performance] Precision: {precision:.4f} ({precision*100:.2f}%)")
        print(f"[Performance] Recall:    {recall:.4f} ({recall*100:.2f}%)")
        print(f"[Performance] F1-Score:  {f1_score:.4f}")
        print(f"[Performance] ")
        print(f"[Performance] Confusion Matrix:")
        print(f"[Performance]   TP: {true_positives:4d}  FP: {false_positives:4d}")
        print(f"[Performance]   FN: {false_negatives:4d}  TN: {true_negatives:4d}")
        print(f"[Performance] ")
        print(f"[Performance] Detection Rates by Attack Type:")
        print(f"[Performance]   Backdoor:        {lateral_detected}/{len(lateral_attacks)} ({lateral_detection_rate*100:.1f}%)")
        print(f"[Performance]   Reconnaissance:   {recon_detected}/{len(recon_attacks)} ({recon_detection_rate*100:.1f}%)")
        print(f"[Performance]   Generic:         {exfil_detected}/{len(exfil_attacks)} ({exfil_detection_rate*100:.1f}%)")

        # Save to CSV
        with open(self.metrics_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                metrics['iteration'],
                metrics['timestamp'],
                f"{metrics['accuracy']:.4f}",
                f"{metrics['precision']:.4f}",
                f"{metrics['recall']:.4f}",
                f"{metrics['f1_score']:.4f}",
                metrics['true_positives'],
                metrics['false_positives'],
                metrics['true_negatives'],
                metrics['false_negatives'],
                metrics['total_samples'],
                f"{metrics['backdoor_detection_rate']:.4f}",
                f"{metrics['reconnaissance_detection_rate']:.4f}",
                f"{metrics['generic_detection_rate']:.4f}"
            ])

        print(f"\n[Performance] ✓ Metrics saved to {self.metrics_file}")
        print(f"[Performance] {'='*60}\n")

        return metrics

def main():
    tracker = PerformanceTracker()
    print("[Performance] Performance tracker initialized")
    print(f"[Performance] Metrics file: {tracker.metrics_file}")

if __name__ == "__main__":
    main()
