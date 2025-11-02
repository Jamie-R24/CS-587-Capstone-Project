#!/usr/bin/env python3
"""
Unit tests for process_logs.py
Tests log processing and alert generation functionality

Target: scripts/process_logs.py (251 lines)
Coverage Goal: 85%+
Test Count: 12 tests
"""

import pytest
import os
import json
import csv
from unittest.mock import Mock, patch, MagicMock
import sys
from datetime import datetime, timedelta

# Import the module under test
from process_logs import LogProcessor


# ============================================================================
# TEST CLASS: Initialization
# ============================================================================

class TestInitialization:
    """Test log processor initialization"""

    def test_initialization_with_defaults(self, temp_output_dir):
        """Test processor initializes with default parameters"""
        processor = LogProcessor(output_dir=temp_output_dir)

        assert processor.output_dir == temp_output_dir
        assert processor.alert_threshold == 0.8
        assert processor.processed_logs == []

    def test_initialization_with_custom_params(self, temp_output_dir):
        """Test processor initializes with custom parameters"""
        processor = LogProcessor(
            output_dir=temp_output_dir,
            alert_threshold=0.9
        )

        assert processor.alert_threshold == 0.9

    def test_create_output_directories(self, temp_dir):
        """Test that necessary output directories are created"""
        output_dir = os.path.join(temp_dir, 'output')
        processor = LogProcessor(output_dir=output_dir)

        # Check directories created
        assert os.path.exists(os.path.join(output_dir, 'alerts'))
        assert os.path.exists(os.path.join(output_dir, 'logs'))


# ============================================================================
# TEST CLASS: Log Parsing
# ============================================================================

class TestLogParsing:
    """Test parsing of different log formats"""

    def test_parse_detection_log_entry(self, temp_output_dir):
        """Test parsing anomaly detection log entry"""
        processor = LogProcessor(output_dir=temp_output_dir)

        # Sample detection log entry
        log_entry = {
            "timestamp": "2025-01-01T12:00:00",
            "level": "WARNING",
            "message": "Anomaly detected",
            "anomaly_score": 0.85,
            "features": [1.5, 2.3, 0.8],
            "prediction": 1,
            "confidence": 0.92
        }

        parsed = processor.parse_log_entry(log_entry)

        assert parsed['type'] == 'anomaly_detection'
        assert parsed['timestamp'] == "2025-01-01T12:00:00"
        assert parsed['anomaly_score'] == 0.85
        assert parsed['confidence'] == 0.92
        assert parsed['prediction'] == 1

    def test_parse_training_log_entry(self, temp_output_dir):
        """Test parsing training log entry"""
        processor = LogProcessor(output_dir=temp_output_dir)

        log_entry = {
            "timestamp": "2025-01-01T12:30:00",
            "level": "INFO",
            "message": "Model training completed",
            "accuracy": 0.88,
            "precision": 0.85,
            "recall": 0.82,
            "f1_score": 0.83,
            "training_samples": 1000
        }

        parsed = processor.parse_log_entry(log_entry)

        assert parsed['type'] == 'model_training'
        assert parsed['accuracy'] == 0.88
        assert parsed['training_samples'] == 1000

    def test_parse_system_log_entry(self, temp_output_dir):
        """Test parsing system log entry"""
        processor = LogProcessor(output_dir=temp_output_dir)

        log_entry = {
            "timestamp": "2025-01-01T13:00:00",
            "level": "ERROR",
            "message": "Database connection failed",
            "component": "data_accumulator",
            "error_code": "DB_CONN_001"
        }

        parsed = processor.parse_log_entry(log_entry)

        assert parsed['type'] == 'system_event'
        assert parsed['component'] == 'data_accumulator'
        assert parsed['error_code'] == 'DB_CONN_001'

    def test_parse_malformed_log_entry(self, temp_output_dir):
        """Test handling malformed log entries"""
        processor = LogProcessor(output_dir=temp_output_dir)

        # Malformed entry (missing required fields)
        malformed_entry = {
            "level": "INFO"
            # Missing timestamp, message
        }

        parsed = processor.parse_log_entry(malformed_entry)

        # Should handle gracefully or return None
        assert parsed is None or parsed['type'] == 'unknown'


# ============================================================================
# TEST CLASS: Alert Generation
# ============================================================================

class TestAlertGeneration:
    """Test alert generation logic"""

    def test_generate_high_confidence_alert(self, temp_output_dir):
        """Test generating alert for high confidence anomaly"""
        processor = LogProcessor(output_dir=temp_output_dir, alert_threshold=0.8)

        log_entry = {
            "timestamp": "2025-01-01T12:00:00",
            "level": "WARNING",
            "message": "High confidence anomaly detected",
            "anomaly_score": 0.95,
            "confidence": 0.92,
            "prediction": 1,
            "features": [2.5, 3.1, 4.2]
        }

        alert = processor.generate_alert(log_entry)

        assert alert is not None
        assert alert['alert_type'] == 'high_confidence_anomaly'
        assert alert['severity'] == 'HIGH'
        assert alert['anomaly_score'] == 0.95
        assert alert['confidence'] == 0.92

    def test_generate_model_degradation_alert(self, temp_output_dir):
        """Test generating alert for model performance degradation"""
        processor = LogProcessor(output_dir=temp_output_dir)

        # Simulate performance drop
        log_entry = {
            "timestamp": "2025-01-01T14:00:00",
            "level": "WARNING",
            "message": "Model performance degraded",
            "accuracy": 0.65,  # Low accuracy
            "previous_accuracy": 0.85,
            "degradation_percent": 23.5
        }

        alert = processor.generate_alert(log_entry)

        assert alert is not None
        assert alert['alert_type'] == 'performance_degradation'
        assert alert['severity'] == 'MEDIUM'
        assert alert['current_accuracy'] == 0.65
        assert alert['degradation_percent'] == 23.5

    def test_no_alert_for_low_confidence(self, temp_output_dir):
        """Test no alert generated for low confidence anomaly"""
        processor = LogProcessor(output_dir=temp_output_dir, alert_threshold=0.8)

        log_entry = {
            "timestamp": "2025-01-01T12:00:00",
            "level": "INFO",
            "message": "Low confidence anomaly",
            "anomaly_score": 0.75,  # Below threshold
            "confidence": 0.65,
            "prediction": 1
        }

        alert = processor.generate_alert(log_entry)

        assert alert is None

    def test_generate_system_error_alert(self, temp_output_dir):
        """Test generating alert for system errors"""
        processor = LogProcessor(output_dir=temp_output_dir)

        log_entry = {
            "timestamp": "2025-01-01T15:00:00",
            "level": "ERROR",
            "message": "Critical system component failure",
            "component": "anomaly_detector",
            "error_code": "SYS_FAIL_001"
        }

        alert = processor.generate_alert(log_entry)

        assert alert is not None
        assert alert['alert_type'] == 'system_error'
        assert alert['severity'] == 'CRITICAL'
        assert alert['component'] == 'anomaly_detector'


# ============================================================================
# TEST CLASS: Alert Persistence
# ============================================================================

class TestAlertPersistence:
    """Test saving and loading alerts"""

    def test_save_alert_to_json(self, temp_output_dir):
        """Test saving alert to JSON file"""
        processor = LogProcessor(output_dir=temp_output_dir)

        alert = {
            'alert_id': 'ALT_20250101_120000',
            'timestamp': '2025-01-01T12:00:00',
            'alert_type': 'high_confidence_anomaly',
            'severity': 'HIGH',
            'anomaly_score': 0.95,
            'confidence': 0.92,
            'description': 'High confidence anomaly detected'
        }

        processor.save_alert(alert)

        # Verify alert file created
        alerts_dir = os.path.join(temp_output_dir, 'alerts')
        alert_files = [f for f in os.listdir(alerts_dir) if f.startswith('alerts_')]

        assert len(alert_files) >= 1

        # Verify alert content
        alert_path = os.path.join(alerts_dir, alert_files[0])
        with open(alert_path, 'r') as f:
            saved_alert = json.load(f)

        assert saved_alert['alert_id'] == 'ALT_20250101_120000'
        assert saved_alert['severity'] == 'HIGH'

    def test_load_existing_alerts(self, temp_output_dir):
        """Test loading existing alerts from files"""
        # Create alert file manually
        alerts_dir = os.path.join(temp_output_dir, 'alerts')
        os.makedirs(alerts_dir, exist_ok=True)

        alert_data = {
            'alert_id': 'ALT_TEST_001',
            'timestamp': '2025-01-01T10:00:00',
            'alert_type': 'test_alert',
            'severity': 'MEDIUM'
        }

        alert_path = os.path.join(alerts_dir, 'alerts_20250101_100000.json')
        with open(alert_path, 'w') as f:
            json.dump(alert_data, f)

        processor = LogProcessor(output_dir=temp_output_dir)
        alerts = processor.load_alerts()

        assert len(alerts) >= 1
        assert any(alert['alert_id'] == 'ALT_TEST_001' for alert in alerts)

    def test_alert_deduplication(self, temp_output_dir):
        """Test that duplicate alerts are not generated"""
        processor = LogProcessor(output_dir=temp_output_dir)

        # Same log entry processed twice
        log_entry = {
            "timestamp": "2025-01-01T12:00:00",
            "level": "WARNING",
            "message": "Duplicate anomaly",
            "anomaly_score": 0.95,
            "confidence": 0.92,
            "prediction": 1
        }

        # Process twice
        alert1 = processor.generate_alert(log_entry)
        alert2 = processor.generate_alert(log_entry)

        # Implementation should handle deduplication
        # Either return None for second alert or use unique IDs
        if alert2 is not None:
            assert alert1['alert_id'] != alert2['alert_id']


# ============================================================================
# TEST CLASS: Log Aggregation
# ============================================================================

class TestLogAggregation:
    """Test log aggregation and analysis"""

    def test_aggregate_anomaly_statistics(self, temp_output_dir):
        """Test aggregating anomaly detection statistics"""
        processor = LogProcessor(output_dir=temp_output_dir)

        # Process multiple detection logs
        log_entries = [
            {"anomaly_score": 0.95, "prediction": 1, "confidence": 0.92},
            {"anomaly_score": 0.75, "prediction": 1, "confidence": 0.68},
            {"anomaly_score": 0.45, "prediction": 0, "confidence": 0.55},
            {"anomaly_score": 0.85, "prediction": 1, "confidence": 0.78},
            {"anomaly_score": 0.35, "prediction": 0, "confidence": 0.65}
        ]

        for entry in log_entries:
            processor.process_log_entry(entry)

        stats = processor.get_anomaly_statistics()

        assert 'total_detections' in stats
        assert 'anomaly_rate' in stats
        assert 'average_confidence' in stats
        assert 'high_confidence_alerts' in stats

        assert stats['total_detections'] == 5
        assert stats['anomaly_rate'] == 0.6  # 3 out of 5 anomalies

    def test_temporal_analysis(self, temp_output_dir):
        """Test temporal analysis of logs"""
        processor = LogProcessor(output_dir=temp_output_dir)

        # Create logs with timestamps
        base_time = datetime(2025, 1, 1, 12, 0, 0)
        for i in range(10):
            timestamp = base_time + timedelta(minutes=i*5)
            log_entry = {
                "timestamp": timestamp.isoformat(),
                "anomaly_score": 0.8 + (i % 3) * 0.1,
                "prediction": 1 if i % 2 == 0 else 0
            }
            processor.process_log_entry(log_entry)

        # Analyze temporal patterns
        temporal_stats = processor.analyze_temporal_patterns()

        assert 'time_range' in temporal_stats
        assert 'detection_frequency' in temporal_stats
        assert 'peak_hours' in temporal_stats


# ============================================================================
# TEST CLASS: Real-time Processing
# ============================================================================

class TestRealtimeProcessing:
    """Test real-time log processing"""

    def test_process_log_stream(self, temp_output_dir):
        """Test processing stream of log entries"""
        processor = LogProcessor(output_dir=temp_output_dir)

        # Simulate log stream
        log_stream = [
            {"timestamp": "2025-01-01T12:00:00", "anomaly_score": 0.95, "prediction": 1},
            {"timestamp": "2025-01-01T12:01:00", "anomaly_score": 0.45, "prediction": 0},
            {"timestamp": "2025-01-01T12:02:00", "anomaly_score": 0.85, "prediction": 1},
        ]

        alerts_generated = []
        for entry in log_stream:
            alert = processor.process_log_entry(entry)
            if alert:
                alerts_generated.append(alert)

        # Should generate alerts for high score entries
        assert len(alerts_generated) >= 1


# ============================================================================
# TEST CLASS: Error Handling
# ============================================================================

class TestErrorHandling:
    """Test error handling in log processor"""

    def test_handle_corrupted_alert_file(self, temp_output_dir):
        """Test handling corrupted alert files"""
        # Create corrupted alert file
        alerts_dir = os.path.join(temp_output_dir, 'alerts')
        os.makedirs(alerts_dir, exist_ok=True)

        corrupted_file = os.path.join(alerts_dir, 'alerts_corrupted.json')
        with open(corrupted_file, 'w') as f:
            f.write('corrupted json content')

        processor = LogProcessor(output_dir=temp_output_dir)

        # Should handle gracefully when loading alerts
        try:
            alerts = processor.load_alerts()
            # Should skip corrupted files
            assert isinstance(alerts, list)
        except json.JSONDecodeError:
            # Acceptable to raise exception for corrupted data
            pass


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v'])