#!/usr/bin/env python3
"""
Validation utility functions for system tests
Provides assertion helpers for complex validations
"""

import json
import csv
from io import StringIO


def validate_model_structure(model_json_string):
    """
    Validate that model JSON has correct structure

    Args:
        model_json_string: Model JSON as string

    Returns:
        dict with validation results
    """
    print("[ValidationUtils] Validating model structure...")
    
    try:
        model = json.loads(model_json_string)
    except json.JSONDecodeError as e:
        print(f"[ValidationUtils] ✗ Invalid JSON: {e}")
        return {'valid': False, 'error': f'Invalid JSON: {e}'}

    # Check required fields
    required_fields = ['timestamp', 'feature_stats', 'threshold_factor', 'model_type']
    missing_fields = [f for f in required_fields if f not in model]

    if missing_fields:
        print(f"[ValidationUtils] ✗ Missing fields: {missing_fields}")
        return {'valid': False, 'error': f'Missing fields: {missing_fields}'}

    # Check feature_stats structure
    if 'means' not in model['feature_stats'] or 'stds' not in model['feature_stats']:
        print(f"[ValidationUtils] ✗ feature_stats missing means or stds")
        return {'valid': False, 'error': 'feature_stats missing means or stds'}

    # Check that means and stds are same length
    if len(model['feature_stats']['means']) != len(model['feature_stats']['stds']):
        print(f"[ValidationUtils] ✗ means and stds length mismatch")
        return {'valid': False, 'error': 'means and stds length mismatch'}

    # Check threshold_factor
    if not isinstance(model['threshold_factor'], (int, float)):
        print(f"[ValidationUtils] ✗ threshold_factor not numeric")
        return {'valid': False, 'error': 'threshold_factor not numeric'}

    num_features = len(model['feature_stats']['means'])
    print(f"[ValidationUtils] ✓ Model valid: {num_features} features, threshold={model['threshold_factor']}")
    
    return {
        'valid': True,
        'num_features': num_features,
        'threshold_factor': model['threshold_factor'],
        'model_type': model['model_type']
    }


def validate_alert_structure(alert_json_string):
    """
    Validate alert JSON structure

    Args:
        alert_json_string: Alert JSON as string

    Returns:
        dict with validation results
    """
    print("[ValidationUtils] Validating alert structure...")
    
    try:
        alerts = json.loads(alert_json_string)
    except json.JSONDecodeError as e:
        print(f"[ValidationUtils] ✗ Invalid JSON: {e}")
        return {'valid': False, 'error': f'Invalid JSON: {e}'}

    if not isinstance(alerts, list):
        print(f"[ValidationUtils] ✗ Alerts must be a list")
        return {'valid': False, 'error': 'Alerts must be a list'}

    # Validate each alert
    required_fields = ['timestamp', 'prediction', 'confidence']

    for i, alert in enumerate(alerts):
        missing = [f for f in required_fields if f not in alert]
        if missing:
            print(f"[ValidationUtils] ✗ Alert {i} missing fields: {missing}")
            return {'valid': False, 'error': f'Alert {i} missing fields: {missing}'}

        # Validate confidence is 0-1
        if not (0.0 <= alert['confidence'] <= 1.0):
            print(f"[ValidationUtils] ✗ Alert {i} confidence out of range: {alert['confidence']}")
            return {'valid': False, 'error': f'Alert {i} confidence out of range: {alert["confidence"]}'}

    avg_conf = sum(a['confidence'] for a in alerts) / len(alerts) if alerts else 0
    print(f"[ValidationUtils] ✓ Alerts valid: {len(alerts)} alerts, avg confidence={avg_conf:.3f}")
    
    return {
        'valid': True,
        'num_alerts': len(alerts),
        'avg_confidence': avg_conf
    }


def validate_performance_metrics(csv_string):
    """
    Validate performance_over_time.csv structure

    Args:
        csv_string: CSV content as string

    Returns:
        dict with validation results
    """
    print("[ValidationUtils] Validating performance metrics...")
    
    try:
        reader = csv.DictReader(StringIO(csv_string))
        rows = list(reader)
    except Exception as e:
        print(f"[ValidationUtils] ✗ Invalid CSV: {e}")
        return {'valid': False, 'error': f'Invalid CSV: {e}'}

    if not rows:
        print(f"[ValidationUtils] ✗ No data rows")
        return {'valid': False, 'error': 'No data rows'}

    # Check required columns
    required_cols = [
        'iteration', 'timestamp', 'accuracy', 'precision', 'recall', 'f1_score',
        'true_positives', 'false_positives', 'true_negatives', 'false_negatives'
    ]

    missing_cols = [c for c in required_cols if c not in rows[0]]
    if missing_cols:
        print(f"[ValidationUtils] ✗ Missing columns: {missing_cols}")
        return {'valid': False, 'error': f'Missing columns: {missing_cols}'}

    # Validate data types
    for i, row in enumerate(rows):
        try:
            iteration = int(row['iteration'])
            accuracy = float(row['accuracy'])
            precision = float(row['precision'])
            recall = float(row['recall'])
            f1_score = float(row['f1_score'])

            # Validate ranges
            if not (0.0 <= accuracy <= 1.0):
                print(f"[ValidationUtils] ✗ Row {i} accuracy out of range: {accuracy}")
                return {'valid': False, 'error': f'Row {i} accuracy out of range: {accuracy}'}
            if not (0.0 <= precision <= 1.0):
                print(f"[ValidationUtils] ✗ Row {i} precision out of range: {precision}")
                return {'valid': False, 'error': f'Row {i} precision out of range: {precision}'}
            if not (0.0 <= recall <= 1.0):
                print(f"[ValidationUtils] ✗ Row {i} recall out of range: {recall}")
                return {'valid': False, 'error': f'Row {i} recall out of range: {recall}'}
            if not (0.0 <= f1_score <= 1.0):
                print(f"[ValidationUtils] ✗ Row {i} f1_score out of range: {f1_score}")
                return {'valid': False, 'error': f'Row {i} f1_score out of range: {f1_score}'}

        except ValueError as e:
            print(f"[ValidationUtils] ✗ Row {i} invalid numeric value: {e}")
            return {'valid': False, 'error': f'Row {i} invalid numeric value: {e}'}

    latest_acc = float(rows[-1]['accuracy'])
    latest_recall = float(rows[-1]['recall'])
    print(f"[ValidationUtils] ✓ Performance metrics valid: {len(rows)} iterations, latest acc={latest_acc:.3f}, recall={latest_recall:.3f}")
    
    return {
        'valid': True,
        'num_iterations': len(rows),
        'latest_accuracy': latest_acc,
        'latest_recall': latest_recall
    }


def calculate_traffic_distribution(csv_string):
    """
    Calculate label distribution from traffic CSV

    Args:
        csv_string: Traffic CSV content as string

    Returns:
        dict with distribution stats
    """
    print("[ValidationUtils] Calculating traffic distribution...")
    
    try:
        reader = csv.DictReader(StringIO(csv_string))
        rows = list(reader)
    except Exception as e:
        print(f"[ValidationUtils] ✗ Invalid CSV: {e}")
        return {'error': f'Invalid CSV: {e}'}

    if not rows:
        print(f"[ValidationUtils] ✗ No data rows")
        return {'error': 'No data rows'}

    normal_count = sum(1 for row in rows if row.get('label') == '0')
    anomaly_count = sum(1 for row in rows if row.get('label') == '1')

    attack_counts = {}
    for row in rows:
        attack_cat = row.get('attack_cat', 'Unknown')
        attack_counts[attack_cat] = attack_counts.get(attack_cat, 0) + 1

    total = len(rows)
    normal_pct = (normal_count / total * 100) if total > 0 else 0
    anomaly_pct = (anomaly_count / total * 100) if total > 0 else 0

    print(f"[ValidationUtils] ✓ Distribution: {total} samples, {normal_pct:.1f}% normal, {anomaly_pct:.1f}% anomaly")

    return {
        'total_samples': total,
        'normal_count': normal_count,
        'anomaly_count': anomaly_count,
        'normal_percent': normal_pct,
        'anomaly_percent': anomaly_pct,
        'attack_distribution': attack_counts
    }


def validate_test_set(csv_string, expected_size=500):
    """
    Validate fixed test set structure and composition

    Args:
        csv_string: Test set CSV content
        expected_size: Expected number of samples

    Returns:
        dict with validation results
    """
    print(f"[ValidationUtils] Validating test set (expected size={expected_size})...")
    
    try:
        reader = csv.DictReader(StringIO(csv_string))
        rows = list(reader)
    except Exception as e:
        print(f"[ValidationUtils] ✗ Invalid CSV: {e}")
        return {'valid': False, 'error': f'Invalid CSV: {e}'}

    if len(rows) != expected_size:
        print(f"[ValidationUtils] ✗ Expected {expected_size} samples, got {len(rows)}")
        return {'valid': False, 'error': f'Expected {expected_size} samples, got {len(rows)}'}

    # Check label distribution
    normal_count = sum(1 for row in rows if row.get('label') == '0')
    anomaly_count = sum(1 for row in rows if row.get('label') == '1')

    # Should be ~80% normal, ~20% anomaly (but allow wider range due to sampling)
    normal_percent = normal_count / len(rows) * 100
    anomaly_percent = anomaly_count / len(rows) * 100

    # Allow 60-85% normal range (more flexible for random sampling)
    if not (60 <= normal_percent <= 85):
        print(f"[ValidationUtils] ✗ Normal percent out of range: {normal_percent}%")
        return {'valid': False, 'error': f'Normal percent out of range: {normal_percent}%'}

    # Allow 15-40% anomaly range
    if not (15 <= anomaly_percent <= 40):
        print(f"[ValidationUtils] ✗ Anomaly percent out of range: {anomaly_percent}%")
        return {'valid': False, 'error': f'Anomaly percent out of range: {anomaly_percent}%'}

    # Check attack types
    target_attacks = {'Backdoors', 'Reconnaissance', 'Generic', 'Normal'}
    attack_types = set(row.get('attack_cat', 'Unknown') for row in rows)

    non_target = attack_types - target_attacks
    if non_target:
        print(f"[ValidationUtils] ✗ Non-target attack types found: {non_target}")
        return {'valid': False, 'error': f'Non-target attack types found: {non_target}'}

    print(f"[ValidationUtils] ✓ Test set valid: {len(rows)} samples, {normal_percent:.1f}% normal, {anomaly_percent:.1f}% anomaly")

    return {
        'valid': True,
        'size': len(rows),
        'normal_count': normal_count,
        'anomaly_count': anomaly_count,
        'attack_types': list(attack_types)
    }
