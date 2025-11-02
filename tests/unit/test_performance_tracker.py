#!/usr/bin/env python3
"""
Unit tests for performance_tracker.py
Tests performance metrics tracking and reporting functionality

Target: scripts/performance_tracker.py (186 lines)
Coverage Goal: 85%+
Test Count: 15 tests
"""

import pytest
import os
import json
import csv
from unittest.mock import Mock, patch, MagicMock
import sys
from datetime import datetime

# Import the module under test
from performance_tracker import PerformanceTracker


# ============================================================================
# TEST CLASS: Initialization
# ============================================================================

class TestInitialization:
    """Test performance tracker initialization"""

    def test_initialization_with_defaults(self, temp_output_dir):
        """Test tracker initializes with default parameters"""
        tracker = PerformanceTracker(output_dir=temp_output_dir)

        assert tracker.output_dir == temp_output_dir
        assert tracker.performance_history == []
        assert tracker.current_metrics == {}

    def test_create_output_directories(self, temp_dir):
        """Test that necessary output directories are created"""
        output_dir = os.path.join(temp_dir, 'output')

        # Check directories created
        assert os.path.exists(output_dir)


# ============================================================================
# TEST CLASS: Metrics Collection
# ============================================================================

class TestMetricsCollection:
    """Test collection of performance metrics"""

    def test_record_performance_metrics(self, temp_output_dir):
        """Test recording basic performance metrics"""
        tracker = PerformanceTracker(output_dir=temp_output_dir)

        metrics = {
            'accuracy': 0.85,
            'precision': 0.80,
            'recall': 0.75,
            'f1_score': 0.77
        }

        tracker.record_performance(metrics, retraining_cycle=1)

        # Verify metrics stored
        assert len(tracker.performance_history) == 1
        record = tracker.performance_history[0]

        assert record['accuracy'] == 0.85
        assert record['precision'] == 0.80
        assert record['recall'] == 0.75
        assert record['f1_score'] == 0.77
        assert record['retraining_cycle'] == 1
        assert 'timestamp' in record

    def test_record_multiple_metrics(self, temp_output_dir):
        """Test recording multiple metric entries"""
        tracker = PerformanceTracker(output_dir=temp_output_dir)

        # Record multiple entries
        for i in range(5):
            metrics = {
                'accuracy': 0.8 + i * 0.02,
                'precision': 0.75 + i * 0.03,
                'recall': 0.70 + i * 0.02,
                'f1_score': 0.72 + i * 0.025
            }
            tracker.record_performance(metrics, retraining_cycle=i+1)

        assert len(tracker.performance_history) == 5

        # Verify progression
        assert tracker.performance_history[0]['accuracy'] == 0.8
        assert tracker.performance_history[4]['accuracy'] == 0.88

    def test_current_metrics_updated(self, temp_output_dir):
        """Test that current metrics are updated"""
        tracker = PerformanceTracker(output_dir=temp_output_dir)

        metrics = {
            'accuracy': 0.90,
            'precision': 0.85,
            'recall': 0.88,
            'f1_score': 0.86
        }

        tracker.record_performance(metrics, retraining_cycle=3)

        # Verify current metrics updated
        assert tracker.current_metrics['accuracy'] == 0.90
        assert tracker.current_metrics['precision'] == 0.85
        assert tracker.current_metrics['recall'] == 0.88
        assert tracker.current_metrics['f1_score'] == 0.86
        assert tracker.current_metrics['retraining_cycle'] == 3

    def test_handle_missing_metrics(self, temp_output_dir):
        """Test handling of missing metrics"""
        tracker = PerformanceTracker(output_dir=temp_output_dir)

        # Partial metrics
        metrics = {
            'accuracy': 0.75,
            'precision': 0.70
            # Missing recall, f1_score
        }

        tracker.record_performance(metrics, retraining_cycle=1)

        record = tracker.performance_history[0]
        assert record['accuracy'] == 0.75
        assert record['precision'] == 0.70
        assert record.get('recall') is None
        assert record.get('f1_score') is None


# ============================================================================
# TEST CLASS: Performance Analysis
# ============================================================================

class TestPerformanceAnalysis:
    """Test performance analysis functionality"""

    def test_calculate_performance_trend(self, temp_output_dir):
        """Test calculation of performance trend"""
        tracker = PerformanceTracker(output_dir=temp_output_dir)

        # Record improving trend
        for i in range(5):
            metrics = {
                'accuracy': 0.70 + i * 0.05  # 0.70, 0.75, 0.80, 0.85, 0.90
            }
            tracker.record_performance(metrics, retraining_cycle=i+1)

        trend = tracker.calculate_trend('accuracy')

        # Should detect positive trend
        assert trend > 0

    def test_calculate_performance_degradation(self, temp_output_dir):
        """Test detection of performance degradation"""
        tracker = PerformanceTracker(output_dir=temp_output_dir)

        # Record degrading trend
        for i in range(5):
            metrics = {
                'accuracy': 0.90 - i * 0.05  # 0.90, 0.85, 0.80, 0.75, 0.70
            }
            tracker.record_performance(metrics, retraining_cycle=i+1)

        trend = tracker.calculate_trend('accuracy')

        # Should detect negative trend
        assert trend < 0

    def test_get_performance_statistics(self, temp_output_dir):
        """Test getting performance statistics"""
        tracker = PerformanceTracker(output_dir=temp_output_dir)

        # Record some data
        accuracies = [0.80, 0.85, 0.78, 0.82, 0.87]
        for i, acc in enumerate(accuracies):
            metrics = {'accuracy': acc}
            tracker.record_performance(metrics, retraining_cycle=i+1)

        stats = tracker.get_performance_stats('accuracy')

        assert 'mean' in stats
        assert 'min' in stats
        assert 'max' in stats
        assert 'std' in stats

        # Verify calculations
        assert stats['mean'] == pytest.approx(sum(accuracies) / len(accuracies))
        assert stats['min'] == min(accuracies)
        assert stats['max'] == max(accuracies)

    def test_detect_performance_alert(self, temp_output_dir):
        """Test detection of performance alerts"""
        tracker = PerformanceTracker(output_dir=temp_output_dir)

        # Record baseline performance
        for i in range(3):
            metrics = {'accuracy': 0.85}
            tracker.record_performance(metrics, retraining_cycle=i+1)

        # Record significant drop
        metrics = {'accuracy': 0.65}  # 20% drop
        tracker.record_performance(metrics, retraining_cycle=4)

        # Check if alert triggered
        alert = tracker.check_performance_alert('accuracy', threshold=0.10)  # 10% threshold

        assert alert is True

    def test_no_alert_for_small_changes(self, temp_output_dir):
        """Test no alert for small performance changes"""
        tracker = PerformanceTracker(output_dir=temp_output_dir)

        # Record baseline
        for i in range(3):
            metrics = {'accuracy': 0.85}
            tracker.record_performance(metrics, retraining_cycle=i+1)

        # Record small drop
        metrics = {'accuracy': 0.82}  # 3.5% drop
        tracker.record_performance(metrics, retraining_cycle=4)

        # Check if alert triggered (should not)
        alert = tracker.check_performance_alert('accuracy', threshold=0.05)  # 5% threshold

        assert alert is False


# ============================================================================
# TEST CLASS: File I/O Operations
# ============================================================================

class TestErrorHandling:
    """Test error handling in performance tracker"""

    def test_handle_invalid_metrics(self, temp_output_dir):
        """Test handling of invalid metric values"""
        tracker = PerformanceTracker(output_dir=temp_output_dir)

        # Invalid metrics (negative values, > 1.0)
        invalid_metrics = {
            'accuracy': -0.5,
            'precision': 1.5,
            'recall': 'invalid',
            'f1_score': None
        }

        # Should handle gracefully
        try:
            tracker.record_performance(invalid_metrics, retraining_cycle=1)
            # If method handles validation, verify sanitized values
            if tracker.performance_history:
                record = tracker.performance_history[0]
                # Should clamp or filter invalid values
                assert record.get('accuracy', 0) >= 0
                assert record.get('precision', 0) <= 1.0
        except (ValueError, TypeError):
            # Acceptable to raise exception for invalid data
            pass

    def test_handle_missing_csv_file(self, temp_output_dir):
        """Test handling missing CSV file on load"""
        tracker = PerformanceTracker(output_dir=temp_output_dir)

        # Try to load non-existent file
        tracker.load_from_csv()

        # Should handle gracefully (empty history)
        assert tracker.performance_history == []

    def test_handle_corrupted_csv_file(self, temp_output_dir):
        """Test handling corrupted CSV file"""
        # Create corrupted CSV
        csv_path = os.path.join(temp_output_dir, 'performance_over_time.csv')
        with open(csv_path, 'w') as f:
            f.write("corrupted,data\ninvalid,content\n")

        tracker = PerformanceTracker(output_dir=temp_output_dir)

        # Should handle gracefully
        try:
            tracker.load_from_csv()
        except (ValueError, KeyError):
            # Acceptable to raise exception for corrupted data
            pass


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v'])