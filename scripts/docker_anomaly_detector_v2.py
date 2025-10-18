#!/usr/bin/env python3
"""
Docker-compatible anomaly detection model - V2
Focused on specific attack types: Lateral Movement, Reconnaissance, and Data Exfiltration
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
    def __init__(self, output_dir='/data/output', confidence_threshold=0.25):
        self.feature_stats = {}
        self.threshold_factor = 1.3  # Lowered for better sensitivity
        self.confidence_threshold = confidence_threshold
        self.output_dir = output_dir
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Define target attack types
        self.TARGET_ATTACKS = {
            'Lateral Movement',
            'Reconnaissance',
            'Data Exfiltration'
        }
        
        # Class balance parameters
        self.max_samples_per_class = 1000  # Limit samples per class
        self.class_weights = {
            '0': 1.0,  # Normal traffic weight
            '1': 1.0   # Attack traffic weight (will be adjusted based on distribution)
        }
        
        # Feature importance parameters
        self.top_features_ratio = 0.25  # Consider top 25% most anomalous features
        self.min_anomalous_features = 2  # Reduced minimum required anomalous features

        # Create output directories with proper permissions
        for subdir in ['models', 'logs', 'alerts']:
            dir_path = os.path.join(output_dir, subdir)
            try:
                os.makedirs(dir_path, exist_ok=True)
                # Ensure directory has write permissions
                os.chmod(dir_path, 0o755)
            except Exception as e:
                print(f"Error creating directory {dir_path}: {e}")
                sys.exit(1)

    def load_data(self, filename):
        """Load data from CSV file with focus on specific attack types"""
        data = []
        headers = []
        attack_categories = []
        original_labels = []  # Store original labels for analysis

        # Map attack categories to our target types
        attack_type_mapping = {
            'Backdoor': 'Lateral Movement',
            'Backdoors': 'Lateral Movement',
            'Reconnaissance': 'Reconnaissance',
            'Generic': 'Data Exfiltration'
        }

        try:
            with open(filename, 'r') as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames

                for row in reader:
                    # Extract attack category and label
                    original_cat = row.get('attack_cat', 'Normal')
                    attack_cat = attack_type_mapping.get(original_cat, original_cat)
                    original_label = int(row.get('label', 0))
                    
                    # For normal traffic or target attacks
                    if attack_cat == 'Normal' or attack_cat in self.TARGET_ATTACKS:
                        # New binary label: 1 for target attacks, 0 for normal traffic
                        new_label = 1 if attack_cat in self.TARGET_ATTACKS else 0
                        
                        # Process features
                        processed_row = []
                        for key, val in row.items():
                            if key not in ['label', 'attack_cat']:
                                try:
                                    processed_row.append(float(val))
                                except ValueError:
                                    processed_row.append(hash(val) % 1000)
                        
                        # Append the new binary label
                        processed_row.append(new_label)
                        
                        # Store processed data
                        data.append(processed_row)
                        attack_categories.append(attack_cat)
                        original_labels.append(original_label)

        except FileNotFoundError:
            print(f"Error: Could not find {filename}")
            return [], [], []

        # Print distribution information
        print(f"Loaded {len(data)} samples with {len(data[0])-1} features")
        
        # Count and display attack types
        attack_counts = Counter(attack_categories)
        print("\nAttack distribution:")
        for attack_type, count in attack_counts.items():
            is_target = "✓" if attack_type in self.TARGET_ATTACKS else " "
            print(f"[{is_target}] {attack_type}: {count}")
        
        # Show binary label distribution
        binary_labels = [row[-1] for row in data]
        print(f"\nBinary label distribution (after focusing on target attacks):")
        print(f"Normal (0): {binary_labels.count(0)}")
        print(f"Target Attacks (1): {binary_labels.count(1)}")

        return data, headers, attack_categories

    def calculate_feature_stats(self, normal_samples):
        """Calculate mean and std dev for each feature using normal traffic only"""
        if not normal_samples:
            raise ValueError("No normal samples provided for training")
            
        n_features = len(normal_samples[0]) - 1  # Exclude label column
        self.feature_stats = {}  # Reset feature stats
        
        # Initialize lists for each feature
        feature_values = [[] for _ in range(n_features)]
        
        # Collect values for each feature
        for sample in normal_samples:
            for i in range(n_features):
                feature_values[i].append(float(sample[i]))  # Ensure numerical values
        
        # Calculate stats for each feature
        for i in range(n_features):
            values = feature_values[i]
            if not values:
                raise ValueError(f"No values collected for feature {i}")
                
            mean = sum(values) / len(values)
            squared_diff_sum = sum((x - mean) ** 2 for x in values)
            std_dev = math.sqrt(squared_diff_sum / len(values))
            
            # Store stats with string keys
            self.feature_stats[str(i)] = {
                'mean': mean,
                'std_dev': std_dev if std_dev > 0 else 1.0  # Prevent division by zero
            }

    def balance_dataset(self, data):
        """Balance the dataset to prevent class imbalance issues"""
        normal_samples = [sample for sample in data if sample[-1] == 0]
        attack_samples = [sample for sample in data if sample[-1] == 1]
        
        print("\nClass distribution before balancing:")
        print(f"Normal samples: {len(normal_samples)}")
        print(f"Attack samples: {len(attack_samples)}")
        
        # Determine target size (use smaller class size as reference)
        target_size = min(len(normal_samples), len(attack_samples))
        target_size = min(target_size, self.max_samples_per_class)
        
        # Randomly sample from larger class to match target size
        if len(normal_samples) > target_size:
            import random
            random.seed(42)  # For reproducibility
            normal_samples = random.sample(normal_samples, target_size)
        
        if len(attack_samples) > target_size:
            import random
            random.seed(42)  # For reproducibility
            attack_samples = random.sample(attack_samples, target_size)
        
        # Combine balanced datasets
        balanced_data = normal_samples + attack_samples
        
        # Calculate class weights based on original distribution
        total_original = len(data)
        normal_count = len([s for s in data if s[-1] == 0])
        attack_count = len([s for s in data if s[-1] == 1])
        
        # Calculate balanced weights
        normal_weight = total_original / (2.0 * normal_count) if normal_count > 0 else 1.0
        attack_weight = total_original / (2.0 * attack_count) if attack_count > 0 else 1.0
        
        # Scale weights to reasonable range
        max_weight = max(normal_weight, attack_weight)
        self.class_weights = {
            '0': min(normal_weight / max_weight * 2.0, 2.0),  # Cap at 2.0
            '1': min(attack_weight / max_weight * 2.0, 2.0)   # Cap at 2.0
        }
        
        print("\nClass distribution after balancing:")
        print(f"Normal samples: {len(normal_samples)}")
        print(f"Attack samples: {len(attack_samples)}")
        print(f"Class weights - Normal: {self.class_weights['0']:.2f}, Attack: {self.class_weights['1']:.2f}")
        
        return balanced_data

    def train(self, data):
        """Train the model on the provided data"""
        print(f"\nTraining Docker Anomaly Detector at {self.timestamp}")
        
        # Balance the dataset
        balanced_data = self.balance_dataset(data)
        
        # Separate normal samples for feature statistics
        normal_samples = [sample for sample in balanced_data if sample[-1] == 0]
        n_features = len(data[0]) - 1
        
        print(f"\nCalculating feature statistics using {len(normal_samples)} normal samples")
        
        # Calculate feature statistics from normal samples only
        self.calculate_feature_stats(normal_samples)
        
        # Save model
        model_file = os.path.join(self.output_dir, 'models', f'model_{self.timestamp}.json')
        with open(model_file, 'w') as f:
            json.dump({
                'feature_stats': self.feature_stats,
                'threshold_factor': self.threshold_factor,
                'confidence_threshold': self.confidence_threshold,
                'target_attacks': list(self.TARGET_ATTACKS),
                'class_weights': self.class_weights,
                'timestamp': self.timestamp
            }, f, indent=2)
        
        # Create symlink to latest model
        latest_link = os.path.join(self.output_dir, 'models', 'latest_model.json')
        if os.path.exists(latest_link):
            os.remove(latest_link)
        os.symlink(model_file, latest_link)
        
        print(f"\nModel saved to {model_file}")
        
        # Evaluate on balanced training data
        self.evaluate(balanced_data, model_file)
        
        # Also evaluate on full dataset to show real-world performance
        print("\nEvaluating on full dataset:")
        self.evaluate(data, model_file)

    def load_model(self, model_file=None):
        """Load a trained model from file"""
        if model_file is None:
            model_file = os.path.join(self.output_dir, 'models', 'latest_model.json')
        
        try:
            with open(model_file, 'r') as f:
                model_data = json.load(f)
                self.feature_stats = model_data['feature_stats']
                self.threshold_factor = model_data['threshold_factor']
                self.confidence_threshold = model_data['confidence_threshold']
                self.TARGET_ATTACKS = set(model_data['target_attacks'])
                self.class_weights = model_data.get('class_weights', {0: 1.0, 1: 1.0})
                return True
        except Exception as e:
            print(f"Error loading model: {e}")
            return False

    def predict_sample(self, sample):
        """Predict whether a single sample is anomalous"""
        if not self.feature_stats:
            raise Exception("Model not trained or loaded")
        
        feature_scores = []
        n_features = len(sample) - 1  # Exclude label
        
        # Check each feature against normal distribution
        for i in range(n_features):
            try:
                feature_val = float(sample[i])  # Ensure numerical value
                stats = self.feature_stats[str(i)]  # Use string key
                
                # Calculate z-score
                z_score = abs(feature_val - stats['mean']) / stats['std_dev']
                
                # Store feature score
                feature_scores.append(z_score)
            except (ValueError, KeyError) as e:
                feature_scores.append(0.0)
                continue
        
        # Sort feature scores to focus on most anomalous features
        feature_scores.sort(reverse=True)
        top_k = max(int(n_features * self.top_features_ratio), self.min_anomalous_features)
        
        # Calculate anomaly scores with different thresholds
        high_threshold = self.threshold_factor
        medium_threshold = self.threshold_factor * 0.8
        low_threshold = self.threshold_factor * 0.6
        
        # Count features at different anomaly levels
        high_anomalies = sum(1 for score in feature_scores[:top_k] if score > high_threshold)
        medium_anomalies = sum(1 for score in feature_scores[:top_k] 
                             if medium_threshold < score <= high_threshold)
        low_anomalies = sum(1 for score in feature_scores[:top_k] 
                          if low_threshold < score <= medium_threshold)
        
        # Calculate weighted confidence score
        confidence = (high_anomalies + 0.7 * medium_anomalies + 0.3 * low_anomalies) / top_k
        
        # Apply adaptive thresholding
        normal_weight = float(self.class_weights.get('0', 1.0))
        attack_weight = float(self.class_weights.get('1', 1.0))
        
        # Calculate adaptive threshold
        base_threshold = self.confidence_threshold
        weight_factor = min(normal_weight / attack_weight, 1.5)  # Cap weight influence
        adaptive_threshold = base_threshold * weight_factor
        
        # Decision criteria:
        # 1. Either meet high confidence threshold
        # 2. Or meet medium confidence with enough supporting features
        is_anomaly = (
            (confidence >= adaptive_threshold) or
            (confidence >= adaptive_threshold * 0.8 and 
             (high_anomalies + medium_anomalies) >= self.min_anomalous_features)
        )
        
        return is_anomaly, confidence

    def predict(self, data):
        """Predict on multiple samples"""
        predictions = []
        for sample in data:
            is_anomaly, _ = self.predict_sample(sample)
            predictions.append(1 if is_anomaly else 0)
        return predictions

    def evaluate(self, data, model_file=None):
        """Evaluate model performance with focus on target attacks"""
        if model_file:
            self.load_model(model_file)
        
        predictions = self.predict(data)
        true_labels = [sample[-1] for sample in data]
        
        # Calculate metrics
        tp = fp = tn = fn = 0
        high_conf_alerts = 0
        
        for pred, true_label in zip(predictions, true_labels):
            if pred == 1 and true_label == 1:
                tp += 1
            elif pred == 1 and true_label == 0:
                fp += 1
            elif pred == 0 and true_label == 0:
                tn += 1
            else:  # pred == 0 and true_label == 1
                fn += 1
        
        # Calculate performance metrics
        total = tp + fp + tn + fn
        accuracy = (tp + tn) / total if total > 0 else 0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        # Print results
        print(f"\nTraining Accuracy: {accuracy:.4f}")
        print(f"Precision: {precision:.4f} | Recall: {recall:.4f} | F1-Score: {f1_score:.4f}")
        print(f"True Positives: {tp} | False Positives: {fp}")
        print(f"True Negatives: {tn} | False Negatives: {fn}")
        
        # Log detailed results
        log_file = os.path.join(self.output_dir, 'logs', f'training_log_{self.timestamp}.json')
        log_data = {
            'timestamp': self.timestamp,
            'metrics': {
                'accuracy': accuracy,
                'precision': precision,
                'recall': recall,
                'f1_score': f1_score,
                'true_positives': tp,
                'false_positives': fp,
                'true_negatives': tn,
                'false_negatives': fn
            },
            'parameters': {
                'confidence_threshold': self.confidence_threshold,
                'threshold_factor': self.threshold_factor,
                'target_attacks': list(self.TARGET_ATTACKS)
            }
        }
        
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        return accuracy, precision, recall, f1_score

def main():
    """Main function for training or testing the detector"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Train or test the anomaly detector')
    parser.add_argument('--mode', choices=['train', 'test'], default='train',
                      help='Operation mode: train or test')
    parser.add_argument('--confidence', type=float, default=0.4,
                      help='Confidence threshold for anomaly detection')
    parser.add_argument('--data', type=str, default='/data/training_data/UNSW_NB15.csv',
                      help='Path to training/testing data')
    parser.add_argument('--model', type=str,
                      help='Path to model file (for testing)')
    
    args = parser.parse_args()
    
    # Initialize detector
    detector = DockerAnomalyDetector(confidence_threshold=args.confidence)
    
    # Load data
    data, headers, attack_categories = detector.load_data(args.data)
    
    if not data:
        print("No data loaded. Exiting.")
        sys.exit(1)
    
    if args.mode == 'train':
        detector.train(data)
        print("\nTraining completed successfully!")
    else:  # Test mode
        if not args.model:
            print("Error: Model file required for testing")
            sys.exit(1)
        if detector.load_model(args.model):
            accuracy, precision, recall, f1_score = detector.evaluate(data)
            print(f"\nTesting completed successfully!")
        else:
            print("Error loading model")
            sys.exit(1)

if __name__ == "__main__":
    main()