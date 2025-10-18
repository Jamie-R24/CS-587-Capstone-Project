#!/usr/bin/env python3
"""
Docker-compatible anomaly detection model
Works with the containerized environment setup
"""

import os
import sys
import csv
import json
import time
from datetime import datetime
from collections import Counter
import math

class DockerAnomalyDetector:
    def __init__(self, output_dir='/data/output', confidence_threshold=0.4):
        self.feature_stats = {}
        self.threshold_factor = 1.4  # Lowered from 1.5 to 1.4 for more sensitivity
        self.confidence_threshold = confidence_threshold  # Lowered from 0.5 to 0.4
        self.output_dir = output_dir
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Create output directories
        os.makedirs(os.path.join(output_dir, 'models'), exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'logs'), exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'alerts'), exist_ok=True)

    def load_data(self, filename):
        """Load data from CSV file"""
        data = []
        headers = []
        attack_categories = []  # Store attack categories separately

        try:
            with open(filename, 'r') as f:
                reader = csv.reader(f)
                headers = next(reader)

                # Find attack_cat column index
                attack_cat_idx = headers.index('attack_cat') if 'attack_cat' in headers else -1

                for row in reader:
                    # Store attack category before processing
                    if attack_cat_idx >= 0 and attack_cat_idx < len(row):
                        attack_categories.append(row[attack_cat_idx])
                    else:
                        attack_categories.append('Unknown')

                    processed_row = []
                    for i, val in enumerate(row):
                        try:
                            processed_row.append(float(val))
                        except ValueError:
                            # Handle categorical data
                            processed_row.append(hash(val) % 1000)
                    data.append(processed_row)
        except FileNotFoundError:
            print(f"Error: Could not find {filename}")
            return [], [], []

        print(f"Loaded {len(data)} samples with {len(data[0]) if data else 0} features")
        return data, headers, attack_categories

    def calculate_stats(self, data):
        """Calculate statistics for normal data"""
        if not data:
            return

        num_features = len(data[0])
        means = [sum(row[i] for row in data) / len(data) for i in range(num_features)]

        stds = []
        for i in range(num_features):
            variance = sum((row[i] - means[i]) ** 2 for row in data) / len(data)
            stds.append(math.sqrt(variance))

        self.feature_stats = {'means': means, 'stds': stds}
        return means, stds

    def train(self, data_path):
        """Train the anomaly detector"""
        print(f"Training Docker Anomaly Detector at {self.timestamp}")

        # Load data
        data, headers, attack_categories = self.load_data(data_path)
        if not data:
            return False

        # Separate features and labels
        features = [row[:-1] for row in data]
        labels = [int(row[-1]) for row in data]

        print(f"Label distribution: {Counter(labels)}")

        # Train on normal samples only
        normal_samples = [features[i] for i, label in enumerate(labels) if label == 0]
        print(f"Training on {len(normal_samples)} normal samples")

        if not normal_samples:
            print("Error: No normal samples found for training")
            return False

        # Calculate statistics
        self.calculate_stats(normal_samples)

        # Save model
        self.save_model()

        # Test performance
        correct = 0
        predictions = []
        alerts = []

        for i, sample in enumerate(features):
            pred = self.predict_single(sample)
            predictions.append(pred)
            if pred == labels[i]:
                correct += 1

            # Generate alerts for anomalies (only if confidence exceeds threshold)
            if pred == 1:
                confidence = self.get_anomaly_score(sample)
                if confidence >= self.confidence_threshold:
                    alert = {
                        'timestamp': datetime.now().isoformat(),
                        'sample_id': i,
                        'prediction': 'ANOMALY',
                        'anomaly_type': attack_categories[i] if i < len(attack_categories) else 'Unknown',
                        'confidence': confidence
                    }
                    alerts.append(alert)

        accuracy = correct / len(features) if features else 0
        print(f"Training Accuracy: {accuracy:.4f}")

        # Calculate performance metrics
        true_positives = sum(1 for i, p in enumerate(predictions) if p == 1 and labels[i] == 1)
        false_positives = sum(1 for i, p in enumerate(predictions) if p == 1 and labels[i] == 0)
        true_negatives = sum(1 for i, p in enumerate(predictions) if p == 0 and labels[i] == 0)
        false_negatives = sum(1 for i, p in enumerate(predictions) if p == 0 and labels[i] == 1)

        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

        print(f"Precision: {precision:.4f} | Recall: {recall:.4f} | F1-Score: {f1_score:.4f}")
        print(f"True Positives: {true_positives} | False Positives: {false_positives}")
        print(f"True Negatives: {true_negatives} | False Negatives: {false_negatives}")
        print(f"High-confidence alerts generated: {len(alerts)}")
        print(f"Detection Coverage: {(true_positives / (true_positives + false_negatives) * 100):.1f}% of anomalies detected")
        print(f"Alert Rate: {(len(alerts) / len(features) * 100):.2f}% of samples generated high-confidence alerts")

        # Save training log
        log_path = os.path.join(self.output_dir, 'logs', f'training_log_{self.timestamp}.json')
        with open(log_path, 'w') as f:
            json.dump({
                'timestamp': self.timestamp,
                'accuracy': accuracy,
                'precision': precision,
                'recall': recall,
                'f1_score': f1_score,
                'total_samples': len(features),
                'normal_samples': len(normal_samples),
                'anomaly_samples': len(features) - len(normal_samples),
                'true_positives': true_positives,
                'false_positives': false_positives,
                'true_negatives': true_negatives,
                'false_negatives': false_negatives,
                'high_confidence_alerts': len(alerts),
                'confidence_threshold': self.confidence_threshold,
                'detection_threshold': 0.10,
                'z_score_threshold': self.threshold_factor,
                'model_path': os.path.join(self.output_dir, 'models', f'model_{self.timestamp}.json')
            }, f, indent=2)

        print(f"Training completed. Model saved to {self.output_dir}/models/")
        return True

    def predict_single(self, sample):
        """Predict if sample is anomaly"""
        if not self.feature_stats:
            return 0

        anomaly_score = 0
        means = self.feature_stats['means']
        stds = self.feature_stats['stds']

        for i, val in enumerate(sample):
            if i < len(means) and stds[i] > 0:
                z_score = abs(val - means[i]) / stds[i]
                if z_score > self.threshold_factor:
                    anomaly_score += 1

        # Lowered threshold from 15% to 10% to improve recall (catch more anomalies)
        # This means 4-5 features need to be anomalous instead of 6-7
        threshold = len(sample) * 0.10
        return 1 if anomaly_score > threshold else 0

    def get_anomaly_score(self, sample):
        """Get normalized anomaly score"""
        if not self.feature_stats:
            return 0.0

        anomaly_score = 0
        anomalous_count = 0
        means = self.feature_stats['means']
        stds = self.feature_stats['stds']

        for i, val in enumerate(sample):
            if i < len(means) and stds[i] > 0:
                z_score = abs(val - means[i]) / stds[i]
                if z_score > self.threshold_factor:
                    anomaly_score += z_score
                    anomalous_count += 1

        # Normalize by number of anomalous features, not total features
        # This gives more reasonable confidence scores
        if anomalous_count > 0:
            # Divide by (anomalous_count * 5) for better scaling
            # A feature with z-score of 5+ should contribute ~1.0 to confidence
            return min(anomaly_score / (anomalous_count * 5), 1.0)
        else:
            return 0.0

    def monitor_real_time(self, input_path, interval=5):
        """Monitor for real-time anomaly detection"""
        print(f"Starting real-time monitoring of {input_path}")

        while True:
            try:
                if os.path.exists(input_path):
                    # Process new data
                    data, _, attack_categories = self.load_data(input_path)
                    if data:
                        alerts = []
                        for i, sample in enumerate(data):
                            pred = self.predict_single(sample[:-1] if len(sample) > 43 else sample)
                            if pred == 1:
                                confidence = self.get_anomaly_score(sample[:-1] if len(sample) > 43 else sample)
                                # Only alert if confidence exceeds threshold
                                if confidence >= self.confidence_threshold:
                                    anomaly_type = attack_categories[i] if i < len(attack_categories) else 'Unknown'
                                    alert = {
                                        'timestamp': datetime.now().isoformat(),
                                        'sample_id': i,
                                        'prediction': 'ANOMALY',
                                        'anomaly_type': anomaly_type,
                                        'confidence': confidence,
                                        'container': os.environ.get('HOSTNAME', 'unknown')
                                    }
                                    alerts.append(alert)
                                    print(f"ALERT: {anomaly_type} detected - Confidence: {confidence:.3f}")

                        # Save alerts
                        if alerts:
                            alert_path = os.path.join(self.output_dir, 'alerts', f'alerts_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
                            with open(alert_path, 'w') as f:
                                json.dump(alerts, f, indent=2)

                time.sleep(interval)
            except KeyboardInterrupt:
                print("Monitoring stopped.")
                break
            except Exception as e:
                print(f"Error in monitoring: {e}")
                time.sleep(interval)

    def save_model(self):
        """Save model to shared volume"""
        model_path = os.path.join(self.output_dir, 'models', f'model_{self.timestamp}.json')
        model_data = {
            'timestamp': self.timestamp,
            'feature_stats': self.feature_stats,
            'threshold_factor': self.threshold_factor,
            'model_type': 'statistical_anomaly_detector'
        }

        with open(model_path, 'w') as f:
            json.dump(model_data, f, indent=2)

        # Also save as latest model
        latest_path = os.path.join(self.output_dir, 'models', 'latest_model.json')
        with open(latest_path, 'w') as f:
            json.dump(model_data, f, indent=2)

        print(f"Model saved to {model_path}")

    def load_model(self, model_path=None):
        """Load model from file"""
        if model_path is None:
            model_path = os.path.join(self.output_dir, 'models', 'latest_model.json')

        try:
            with open(model_path, 'r') as f:
                model_data = json.load(f)

            self.feature_stats = model_data['feature_stats']
            self.threshold_factor = model_data.get('threshold_factor', 1.5)
            print(f"Model loaded from {model_path}")
            return True
        except FileNotFoundError:
            print(f"Model not found at {model_path}")
            return False

def main():
    """Main function for Docker deployment"""
    import argparse

    parser = argparse.ArgumentParser(description='Docker Anomaly Detection')
    parser.add_argument('--mode', choices=['train', 'monitor'], required=True,
                       help='Operation mode: train or monitor')
    parser.add_argument('--data', default='/data/training_data/UNSW_NB15_training_only.csv',
                       help='Path to training data')
    parser.add_argument('--input', default='/var/log/activity/network_data.csv',
                       help='Path to monitor for real-time detection')
    parser.add_argument('--interval', type=int, default=5,
                       help='Monitoring interval in seconds')
    parser.add_argument('--confidence', type=float, default=0.4,
                       help='Confidence threshold for alerts (0.0-1.0, default: 0.4)')
    parser.add_argument('--detection-threshold', type=float, default=0.10,
                       help='Detection threshold as percentage of features (default: 0.10)')

    args = parser.parse_args()

    # Create detector with custom thresholds
    detector = DockerAnomalyDetector(confidence_threshold=args.confidence)

    if args.mode == 'train':
        print("Training mode selected")
        success = detector.train(args.data)
        if success:
            print("Training completed successfully!")
        else:
            print("Training failed!")
            sys.exit(1)

    elif args.mode == 'monitor':
        print("Monitor mode selected")
        # Try to load existing model
        if not detector.load_model():
            print("No trained model found. Please train first.")
            sys.exit(1)

        detector.monitor_real_time(args.input, args.interval)

if __name__ == "__main__":
    main()