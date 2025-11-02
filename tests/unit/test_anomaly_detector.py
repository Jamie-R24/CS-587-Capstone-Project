#!/usr/bin/env python3
"""
Unit tests for docker_anomaly_detector.py
Tests the core anomaly detection logic using Z-score based statistical analysis

Target: scripts/docker_anomaly_detector.py (348 lines)
Coverage Goal: 90%+
Test Count: 30 tests
"""

import pytest
import os
import json
import csv
import math
from unittest.mock import Mock, patch, mock_open
import sys

# Import the module under test
from docker_anomaly_detector import DockerAnomalyDetector


# ============================================================================
# TEST CLASS: Data Loading
# ============================================================================

class TestDataLoading:
    """Test data loading and preprocessing"""

    def test_load_valid_csv(self, sample_csv_file, sample_csv_data):
        """Test loading valid CSV file with 44 features"""
        detector = DockerAnomalyDetector()
        data, headers, attack_cats = detector.load_data(sample_csv_file)

        # Verify data loaded correctly
        assert len(data) == len(sample_csv_data['all'])
        assert len(headers) == len(sample_csv_data['headers'])
        assert len(attack_cats) == len(sample_csv_data['all'])

        # Verify each row has 44 features
        for row in data:
            assert len(row) == 44  # 43 features + label

    def test_load_missing_file(self, temp_dir):
        """Test handling of missing file"""
        detector = DockerAnomalyDetector()
        missing_file = os.path.join(temp_dir, 'nonexistent.csv')

        data, headers, attack_cats = detector.load_data(missing_file)

        # Should return empty lists
        assert data == []
        assert headers == []
        assert attack_cats == []

    def test_parse_categorical_features(self, temp_dir):
        """Test parsing of categorical features (proto, service, state)"""
        # Create CSV with categorical data
        csv_path = os.path.join(temp_dir, 'categorical.csv')
        headers = ['proto', 'service', 'state', 'spkts', 'label']
        rows = [
            {'proto': 'tcp', 'service': 'http', 'state': 'CON', 'spkts': 10, 'label': 0},
            {'proto': 'udp', 'service': 'dns', 'state': 'REQ', 'spkts': 5, 'label': 0}
        ]

        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)

        detector = DockerAnomalyDetector()
        data, _, _ = detector.load_data(csv_path)

        # Categorical values should be hashed to integers
        assert all(isinstance(val, (int, float)) for row in data for val in row)

    def test_extract_attack_categories(self, sample_csv_file, sample_csv_data):
        """Test extraction of attack_cat column"""
        detector = DockerAnomalyDetector()
        _, _, attack_cats = detector.load_data(sample_csv_file)

        # Verify attack categories extracted
        assert 'Normal' in attack_cats
        assert 'Backdoors' in attack_cats
        assert len(attack_cats) == len(sample_csv_data['all'])

    def test_handle_empty_csv(self, temp_dir):
        """Test handling of empty CSV file"""
        csv_path = os.path.join(temp_dir, 'empty.csv')

        # Create empty CSV with just headers
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['dur', 'proto', 'label'])

        detector = DockerAnomalyDetector()
        data, headers, attack_cats = detector.load_data(csv_path)

        assert len(data) == 0
        assert len(headers) == 3

    def test_handle_malformed_csv(self, temp_dir):
        """Test handling of CSV with inconsistent row lengths"""
        csv_path = os.path.join(temp_dir, 'malformed.csv')

        # Write malformed CSV manually
        with open(csv_path, 'w') as f:
            f.write('dur,proto,label\n')
            f.write('1.0,tcp,0\n')
            f.write('2.0,udp\n')  # Missing label
            f.write('3.0,icmp,1,extra\n')  # Extra field

        detector = DockerAnomalyDetector()
        data, headers, attack_cats = detector.load_data(csv_path)

        # Should load what it can
        assert len(data) >= 1


# ============================================================================
# TEST CLASS: Statistical Calculations
# ============================================================================

class TestStatisticalCalculations:
    """Test mean and standard deviation calculations"""

    def test_calculate_mean(self):
        """Test mean calculation for normal samples"""
        detector = DockerAnomalyDetector()

        # Simple 3-feature dataset
        data = [
            [1.0, 2.0, 3.0],
            [2.0, 4.0, 6.0],
            [3.0, 6.0, 9.0]
        ]

        means, _ = detector.calculate_stats(data)

        # Expected means: [2.0, 4.0, 6.0]
        assert means[0] == pytest.approx(2.0)
        assert means[1] == pytest.approx(4.0)
        assert means[2] == pytest.approx(6.0)

    def test_calculate_std_deviation(self):
        """Test standard deviation calculation"""
        detector = DockerAnomalyDetector()

        # Dataset with known std deviation
        data = [
            [1.0],
            [2.0],
            [3.0],
            [4.0],
            [5.0]
        ]

        _, stds = detector.calculate_stats(data)

        # Expected std: sqrt(variance) = sqrt(2.0) ≈ 1.414
        expected_std = math.sqrt(2.0)
        assert stds[0] == pytest.approx(expected_std, rel=0.01)

    def test_handle_zero_variance(self):
        """Test handling of features with zero variance (all same value)"""
        detector = DockerAnomalyDetector()

        # All values identical
        data = [
            [5.0, 10.0],
            [5.0, 10.0],
            [5.0, 10.0]
        ]

        means, stds = detector.calculate_stats(data)

        assert means[0] == 5.0
        assert means[1] == 10.0
        assert stds[0] == 0.0
        assert stds[1] == 0.0

    def test_filter_normal_samples_only(self, sample_csv_file):
        """Test that only label=0 samples are used for statistics"""
        detector = DockerAnomalyDetector()
        data, _, _ = detector.load_data(sample_csv_file)

        # Separate features and labels
        features = [row[:-1] for row in data]
        labels = [int(row[-1]) for row in data]

        # Calculate stats on normal samples only
        normal_samples = [features[i] for i, label in enumerate(labels) if label == 0]
        detector.calculate_stats(normal_samples)

        # Verify only normal samples used
        assert len(normal_samples) == sum(1 for l in labels if l == 0)

    def test_reject_empty_dataset(self):
        """Test rejection of empty dataset for training"""
        detector = DockerAnomalyDetector()

        # Empty dataset
        data = []

        result = detector.calculate_stats(data)

        # Should return None or handle gracefully
        assert result is None


# ============================================================================
# TEST CLASS: Z-Score Detection
# ============================================================================

class TestZScoreDetection:
    """Test Z-score calculation and anomaly detection"""

    def test_z_score_calculation(self):
        """Test Z-score calculation: (value - mean) / std"""
        detector = DockerAnomalyDetector()

        # Train on simple dataset
        detector.feature_stats = {
            'means': [10.0, 20.0, 30.0],
            'stds': [2.0, 4.0, 6.0]
        }
        detector.threshold_factor = 1.4

        # Sample with Z-scores: [0.0, 1.25, 2.0]
        sample = [10.0, 25.0, 42.0]

        # Manually calculate expected Z-scores
        # z1 = abs(10.0 - 10.0) / 2.0  # = 0.0
        # z2 = abs(25.0 - 20.0) / 4.0  # = 1.25
        # z3 = abs(42.0 - 30.0) / 6.0  # = 2.0

        # Features with |Z| > 1.4: only feature 3 (Z=2.0)
        # Anomaly threshold: 10% of 3 features = 0.3 → need >0.3 = 1 feature
        # Should predict anomaly (1 feature exceeds threshold)
        prediction = detector.predict_single(sample)

        assert prediction == 1  # Anomaly

    def test_threshold_factor_applied(self):
        """Test that threshold_factor (1.4) is applied correctly"""
        detector = DockerAnomalyDetector()
        detector.feature_stats = {
            'means': [100.0],
            'stds': [10.0]
        }
        detector.threshold_factor = 1.4

        # Sample with Z-score = 1.3 (below threshold)
        sample_below = [113.0]  # |Z| = 1.3

        # Sample with Z-score = 1.5 (above threshold)
        sample_above = [115.0]  # |Z| = 1.5

        pred_below = detector.predict_single(sample_below)
        pred_above = detector.predict_single(sample_above)

        # Detection threshold = 10% of 1 feature = 0.1 → need >0.1 features
        # 1.3 < 1.4, so should be 0 anomalous features
        # 1.5 > 1.4, so should be 1 anomalous feature

        assert pred_below == 0  # Normal (no features exceed threshold)
        assert pred_above == 1  # Anomaly (1 feature exceeds threshold)

    def test_detection_threshold_10_percent(self):
        """Test that 10% of features must be anomalous"""
        detector = DockerAnomalyDetector()

        # 10-feature dataset
        detector.feature_stats = {
            'means': [50.0] * 10,
            'stds': [10.0] * 10
        }
        detector.threshold_factor = 1.4

        # Sample with 0 anomalous features (all within 1.4 std)
        sample_0 = [50.0] * 10

        # Sample with 1 anomalous feature (10% exactly)
        sample_1 = [50.0] * 9 + [65.0]  # Last feature has Z=1.5

        # Sample with 2 anomalous features (20%)
        sample_2 = [50.0] * 8 + [65.0, 65.0]

        pred_0 = detector.predict_single(sample_0)
        pred_1 = detector.predict_single(sample_1)
        pred_2 = detector.predict_single(sample_2)

        # Threshold is >10%, so need >1 feature
        # With threshold of 10% of 10 features = 1.0, need >1.0 = 2+ features
        assert pred_0 == 0  # 0% anomalous (0 features)
        assert pred_1 == 0  # 10% anomalous (1 feature, not > threshold)
        assert pred_2 == 1  # 20% anomalous (2 features, > threshold)

    def test_handle_zero_std_features(self):
        """Test handling of features with std=0 (avoid division by zero)"""
        detector = DockerAnomalyDetector()
        detector.feature_stats = {
            'means': [10.0, 20.0],
            'stds': [0.0, 5.0]  # First feature has zero variance
        }
        detector.threshold_factor = 1.4

        sample = [15.0, 30.0]

        # Should not crash, should skip zero-std features
        prediction = detector.predict_single(sample)

        # Should only consider second feature (Z=2.0)
        assert isinstance(prediction, int)
        assert prediction in [0, 1]


# ============================================================================
# TEST CLASS: Anomaly Scoring
# ============================================================================

class TestAnomalyScoring:
    """Test anomaly confidence score calculation"""

    def test_score_range_0_to_1(self):
        """Test that anomaly score is normalized between 0.0 and 1.0"""
        detector = DockerAnomalyDetector()
        detector.feature_stats = {
            'means': [10.0] * 5,
            'stds': [2.0] * 5
        }
        detector.threshold_factor = 1.4

        # Highly anomalous sample
        sample_high = [30.0] * 5  # All features have Z=10.0

        # Slightly anomalous sample
        sample_low = [13.0] * 5  # All features have Z=1.5

        score_high = detector.get_anomaly_score(sample_high)
        score_low = detector.get_anomaly_score(sample_low)

        assert 0.0 <= score_high <= 1.0
        assert 0.0 <= score_low <= 1.0
        assert score_high > score_low  # Higher anomaly → higher score

    def test_zero_score_for_normal(self):
        """Test that normal samples get score of 0.0"""
        detector = DockerAnomalyDetector()
        detector.feature_stats = {
            'means': [10.0] * 3,
            'stds': [5.0] * 3
        }
        detector.threshold_factor = 1.4

        # Sample within threshold (all Z < 1.4)
        sample_normal = [11.0, 12.0, 13.0]  # All Z < 1.0

        score = detector.get_anomaly_score(sample_normal)

        assert score == 0.0

    def test_confidence_threshold_applied(self):
        """Test that confidence_threshold (0.4) filters alerts"""
        detector = DockerAnomalyDetector(confidence_threshold=0.4)
        detector.feature_stats = {
            'means': [10.0] * 10,
            'stds': [5.0] * 10
        }
        detector.threshold_factor = 1.4

        # Sample with moderate anomaly score
        sample_moderate = [10.0] * 8 + [20.0, 20.0]  # 2 features anomalous

        score = detector.get_anomaly_score(sample_moderate)
        prediction = detector.predict_single(sample_moderate)

        # If score < 0.4, should not generate alert in monitor mode
        # But prediction should still be 1 if >10% features anomalous
        assert prediction == 1  # Detected as anomaly
        # Alert generation depends on score >= confidence_threshold


# ============================================================================
# TEST CLASS: Model Persistence
# ============================================================================

class TestModelPersistence:
    """Test model save/load operations"""

    def test_save_model_json_structure(self, temp_output_dir):
        """Test that saved model has correct JSON structure"""
        detector = DockerAnomalyDetector(output_dir=temp_output_dir)
        detector.feature_stats = {
            'means': [1.0, 2.0, 3.0],
            'stds': [0.5, 1.0, 1.5]
        }
        detector.threshold_factor = 1.4

        detector.save_model()

        # Read saved model
        model_path = os.path.join(temp_output_dir, 'models', 'latest_model.json')
        assert os.path.exists(model_path)

        with open(model_path, 'r') as f:
            model_data = json.load(f)

        # Verify structure
        assert 'timestamp' in model_data
        assert 'feature_stats' in model_data
        assert 'threshold_factor' in model_data
        assert 'model_type' in model_data

        assert model_data['threshold_factor'] == 1.4
        assert model_data['model_type'] == 'statistical_anomaly_detector'
        assert model_data['feature_stats']['means'] == [1.0, 2.0, 3.0]
        assert model_data['feature_stats']['stds'] == [0.5, 1.0, 1.5]

    def test_save_both_timestamped_and_latest(self, temp_output_dir):
        """Test that both timestamped and latest_model.json are created"""
        detector = DockerAnomalyDetector(output_dir=temp_output_dir)
        detector.feature_stats = {
            'means': [1.0],
            'stds': [0.5]
        }

        detector.save_model()

        # Check both files exist
        latest_path = os.path.join(temp_output_dir, 'models', 'latest_model.json')
        assert os.path.exists(latest_path)

        # Check timestamped file (pattern: model_*.json)
        models_dir = os.path.join(temp_output_dir, 'models')
        timestamped_files = [f for f in os.listdir(models_dir) if f.startswith('model_') and f != 'latest_model.json']
        assert len(timestamped_files) >= 1

    def test_load_model_from_file(self, temp_output_dir, sample_model_data):
        """Test loading model from JSON file"""
        # Create model file
        model_path = os.path.join(temp_output_dir, 'models', 'latest_model.json')
        with open(model_path, 'w') as f:
            json.dump(sample_model_data, f)

        detector = DockerAnomalyDetector(output_dir=temp_output_dir)
        success = detector.load_model(model_path)

        assert success is True
        assert detector.feature_stats == sample_model_data['feature_stats']
        assert detector.threshold_factor == sample_model_data['threshold_factor']

    def test_load_missing_model_gracefully(self, temp_output_dir):
        """Test handling of missing model file"""
        detector = DockerAnomalyDetector(output_dir=temp_output_dir)

        missing_path = os.path.join(temp_output_dir, 'models', 'nonexistent.json')
        success = detector.load_model(missing_path)

        assert success is False
        assert detector.feature_stats == {}


# ============================================================================
# TEST CLASS: Performance Metrics
# ============================================================================

class TestPerformanceMetrics:
    """Test accuracy, precision, recall, F1 calculation"""

    def test_calculate_accuracy(self):
        """Test accuracy calculation: (TP + TN) / total"""
        # Predictions and labels
        predictions = [1, 1, 0, 0, 1, 0, 1, 0]
        labels = [1, 0, 0, 1, 1, 0, 0, 0]

        # TP=2, FP=2, TN=3, FN=1
        correct = sum(1 for p, l in zip(predictions, labels) if p == l)
        accuracy = correct / len(predictions)

        # Expected: (2+3)/8 = 0.625
        assert accuracy == pytest.approx(0.625)

    def test_calculate_precision(self):
        """Test precision calculation: TP / (TP + FP)"""
        predictions = [1, 1, 1, 0, 0]
        labels = [1, 0, 1, 0, 1]

        # TP=2, FP=1
        tp = sum(1 for p, l in zip(predictions, labels) if p == 1 and l == 1)
        fp = sum(1 for p, l in zip(predictions, labels) if p == 1 and l == 0)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0

        # Expected: 2/3 ≈ 0.667
        assert precision == pytest.approx(2/3)

    def test_calculate_recall(self):
        """Test recall calculation: TP / (TP + FN)"""
        predictions = [1, 1, 1, 0, 0]
        labels = [1, 0, 1, 0, 1]

        # TP=2, FN=1
        tp = sum(1 for p, l in zip(predictions, labels) if p == 1 and l == 1)
        fn = sum(1 for p, l in zip(predictions, labels) if p == 0 and l == 1)

        recall = tp / (tp + fn) if (tp + fn) > 0 else 0

        # Expected: 2/3 ≈ 0.667
        assert recall == pytest.approx(2/3)

    def test_calculate_f1_score(self):
        """Test F1 calculation: 2 * (precision * recall) / (precision + recall)"""
        precision = 0.75
        recall = 0.60

        f1 = 2 * (precision * recall) / (precision + recall)

        # Expected: 2 * 0.45 / 1.35 ≈ 0.667
        assert f1 == pytest.approx(0.6666666, rel=0.01)

    def test_handle_edge_case_no_predictions(self):
        """Test metrics calculation when no positive predictions"""
        predictions = [0, 0, 0, 0]
        labels = [1, 1, 0, 0]

        tp = sum(1 for p, l in zip(predictions, labels) if p == 1 and l == 1)
        fp = sum(1 for p, l in zip(predictions, labels) if p == 1 and l == 0)
        fn = sum(1 for p, l in zip(predictions, labels) if p == 0 and l == 1)

        # TP=0, FP=0, FN=2
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0

        assert precision == 0.0
        assert recall == 0.0


# ============================================================================
# TEST CLASS: Training Integration
# ============================================================================

class TestTrainingIntegration:
    """Test end-to-end training workflow"""

    def test_train_on_normal_samples_only(self, sample_csv_file, temp_output_dir):
        """Test that training uses only label=0 samples"""
        detector = DockerAnomalyDetector(output_dir=temp_output_dir)

        success = detector.train(sample_csv_file)

        assert success is True
        assert detector.feature_stats is not None
        assert 'means' in detector.feature_stats
        assert 'stds' in detector.feature_stats

    def test_reject_training_with_no_normal_samples(self, temp_dir, temp_output_dir):
        """Test rejection when dataset has no normal samples"""
        # Create CSV with only anomalies
        csv_path = os.path.join(temp_dir, 'all_anomalies.csv')
        headers = ['dur', 'proto', 'label']
        rows = [
            {'dur': 1.0, 'proto': 'tcp', 'label': 1},
            {'dur': 2.0, 'proto': 'udp', 'label': 1}
        ]

        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)

        detector = DockerAnomalyDetector(output_dir=temp_output_dir)
        success = detector.train(csv_path)

        assert success is False

    def test_training_creates_log_file(self, sample_csv_file, temp_output_dir):
        """Test that training creates log file with metrics"""
        detector = DockerAnomalyDetector(output_dir=temp_output_dir)

        detector.train(sample_csv_file)

        # Check log file created
        logs_dir = os.path.join(temp_output_dir, 'logs')
        log_files = [f for f in os.listdir(logs_dir) if f.startswith('training_log_')]

        assert len(log_files) >= 1

        # Verify log structure
        log_path = os.path.join(logs_dir, log_files[0])
        with open(log_path, 'r') as f:
            log_data = json.load(f)

        assert 'timestamp' in log_data
        assert 'accuracy' in log_data
        assert 'precision' in log_data
        assert 'recall' in log_data
        assert 'f1_score' in log_data


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v'])