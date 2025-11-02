#!/usr/bin/env python3
"""
Performance Tracker - Monitors detector performance across retraining iterations
Uses a fixed test set to measure improvement/degradation
"""

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
        self.performance_history = []
        self.current_metrics = {}

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

    def initialize_performance_file(self):
        """Initialize the performance CSV file with headers"""
        if not os.path.exists(self.metrics_file):
            os.makedirs(os.path.dirname(self.metrics_file), exist_ok=True)
            with open(self.metrics_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'accuracy', 'precision', 'recall', 'f1_score', 'retraining_cycle'])

    def record_performance(self, metrics, retraining_cycle=None):
        """Record performance metrics"""
        record = {
            'timestamp': datetime.now().isoformat(),
            'accuracy': metrics.get('accuracy', None),
            'precision': metrics.get('precision', None),
            'recall': metrics.get('recall', None),
            'f1_score': metrics.get('f1_score', None),
            'retraining_cycle': retraining_cycle
        }
        
        self.performance_history.append(record)
        
        # Update current metrics to include retraining cycle
        self.current_metrics = metrics.copy()
        self.current_metrics['retraining_cycle'] = retraining_cycle
        
        # Save to CSV
        csv_file = os.path.join(self.output_dir, 'performance_over_time.csv')
        
        # Check if file exists and has headers
        file_exists = os.path.exists(csv_file)
        with open(csv_file, 'a' if file_exists else 'w', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['timestamp', 'accuracy', 'precision', 'recall', 'f1_score', 'retraining_cycle'])
            writer.writerow([
                record['timestamp'],
                f"{record['accuracy']:.4f}" if record['accuracy'] is not None else '',
                f"{record['precision']:.4f}" if record['precision'] is not None else '',
                f"{record['recall']:.4f}" if record['recall'] is not None else '',
                f"{record['f1_score']:.4f}" if record['f1_score'] is not None else '',
                record['retraining_cycle']
            ])
        
        return record

    def calculate_trend(self, metric_name):
        """Calculate trend for a specific metric (positive = improving, negative = degrading)"""
        if len(self.performance_history) < 2:
            return 0
        
        values = [record.get(metric_name) for record in self.performance_history 
                 if record.get(metric_name) is not None]
        
        if len(values) < 2:
            return 0
        
        # Simple linear trend: compare first half to second half
        mid = len(values) // 2
        first_half_avg = sum(values[:mid]) / mid
        second_half_avg = sum(values[mid:]) / len(values[mid:])
        
        return second_half_avg - first_half_avg

    def get_performance_stats(self, metric_name):
        """Get statistics for a specific metric"""
        values = [record.get(metric_name) for record in self.performance_history 
                 if record.get(metric_name) is not None]
        
        if not values:
            return {
                'mean': 0,
                'min': 0,
                'max': 0,
                'std': 0
            }
        
        mean_val = sum(values) / len(values)
        min_val = min(values)
        max_val = max(values)
        
        # Calculate standard deviation
        variance = sum((x - mean_val) ** 2 for x in values) / len(values)
        std_val = variance ** 0.5
        
        return {
            'mean': mean_val,
            'min': min_val,
            'max': max_val,
            'std': std_val
        }

    def check_performance_alert(self, metric_name, threshold=0.10):
        """Check if performance has degraded beyond threshold"""
        if len(self.performance_history) < 4:
            return False
        
        # Get recent values
        values = [record.get(metric_name) for record in self.performance_history 
                 if record.get(metric_name) is not None]
        
        if len(values) < 4:
            return False
        
        # Compare recent value to baseline (first 3 values)
        baseline = sum(values[:3]) / 3
        current = values[-1]
        
        # Calculate percentage drop
        drop = (baseline - current) / baseline
        
        return drop >= threshold

    def get_report(self):
        """Generate a performance report"""
        return {
            'timestamp': datetime.now().isoformat(),
            'current_metrics': self.current_metrics,
            'history_count': len(self.performance_history),
            'accuracy_stats': self.get_performance_stats('accuracy'),
            'precision_stats': self.get_performance_stats('precision'),
            'recall_stats': self.get_performance_stats('recall'),
            'f1_stats': self.get_performance_stats('f1_score')
        }

    def load_from_csv(self, csv_path=None):
        """Load performance history from CSV file"""
        if csv_path is None:
            csv_path = os.path.join(self.output_dir, 'performance_over_time.csv')
        
        if not os.path.exists(csv_path):
            return []
        
        history = []
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                history.append(row)
        
        self.performance_history = history
        return history

    def export_metrics_for_monitoring(self):
        """Export current metrics in a format suitable for monitoring systems"""
        if not self.current_metrics:
            return {}
        
        return {
            'timestamp': datetime.now().isoformat(),
            'metrics': self.current_metrics,
            'status': 'active',
            'history_count': len(self.performance_history)
        }

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
