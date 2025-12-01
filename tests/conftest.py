#!/usr/bin/env python3
"""
Shared pytest configuration and fixtures for all tests
"""

import pytest
import os
import sys
import tempfile
import shutil
import json
import csv
from pathlib import Path

# Add scripts directory to Python path
PROJECT_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = PROJECT_ROOT / 'scripts'
sys.path.insert(0, str(SCRIPTS_DIR))


# ============================================================================
# DIRECTORY FIXTURES
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create temporary directory for test files"""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def temp_output_dir(temp_dir):
    """Create temporary output directory structure"""
    output_dir = os.path.join(temp_dir, 'output')
    os.makedirs(os.path.join(output_dir, 'models'), exist_ok=True)
    os.makedirs(os.path.join(output_dir, 'logs'), exist_ok=True)
    os.makedirs(os.path.join(output_dir, 'alerts'), exist_ok=True)
    os.makedirs(os.path.join(output_dir, 'retraining_logs'), exist_ok=True)
    os.makedirs(os.path.join(output_dir, 'reports'), exist_ok=True)
    return output_dir


@pytest.fixture
def temp_data_dir(temp_dir):
    """Create temporary data directory structure"""
    data_dir = os.path.join(temp_dir, 'data')
    os.makedirs(os.path.join(data_dir, 'training_data'), exist_ok=True)
    os.makedirs(os.path.join(data_dir, 'test_sets'), exist_ok=True)
    os.makedirs(os.path.join(data_dir, 'accumulated_data'), exist_ok=True)
    os.makedirs(os.path.join(data_dir, 'poisoning'), exist_ok=True)
    return data_dir


# ============================================================================
# DATA FIXTURES
# ============================================================================

@pytest.fixture
def sample_csv_data():
    """Generate sample CSV data with 44 features (UNSW-NB15 schema)"""
    headers = [
        'dur', 'proto', 'service', 'state', 'spkts', 'dpkts', 'sbytes', 'dbytes',
        'rate', 'sttl', 'dttl', 'sload', 'dload', 'sloss', 'dloss', 'sinpkt',
        'dinpkt', 'sjit', 'djit', 'swin', 'stcpb', 'dtcpb', 'dwin', 'tcprtt',
        'synack', 'ackdat', 'smean', 'dmean', 'trans_depth', 'response_body_len',
        'ct_srv_src', 'ct_state_ttl', 'ct_flw_http_mthd', 'is_ftp_login',
        'ct_ftp_cmd', 'ct_srv_dst', 'ct_dst_ltm', 'ct_src_ltm', 'ct_src_dport_ltm',
        'ct_dst_sport_ltm', 'ct_dst_src_ltm', 'is_sm_ips_ports', 'attack_cat', 'label'
    ]

    # Normal samples (label=0)
    normal_samples = [
        {
            'dur': 1.0, 'proto': 'tcp', 'service': 'http', 'state': 'CON',
            'spkts': 10, 'dpkts': 10, 'sbytes': 1000, 'dbytes': 1000,
            'rate': 100.0, 'sttl': 64, 'dttl': 64, 'sload': 1000.0, 'dload': 1000.0,
            'sloss': 0, 'dloss': 0, 'sinpkt': 1.0, 'dinpkt': 1.0,
            'sjit': 0.1, 'djit': 0.1, 'swin': 8192, 'stcpb': 1000, 'dtcpb': 1000,
            'dwin': 8192, 'tcprtt': 0.5, 'synack': 0.5, 'ackdat': 0.5,
            'smean': 100, 'dmean': 100, 'trans_depth': 1, 'response_body_len': 500,
            'ct_srv_src': 5, 'ct_state_ttl': 10, 'ct_flw_http_mthd': 1,
            'is_ftp_login': 0, 'ct_ftp_cmd': 0, 'ct_srv_dst': 5,
            'ct_dst_ltm': 10, 'ct_src_ltm': 10, 'ct_src_dport_ltm': 5,
            'ct_dst_sport_ltm': 5, 'ct_dst_src_ltm': 10, 'is_sm_ips_ports': 0,
            'attack_cat': 'Normal', 'label': 0
        }
        for _ in range(5)
    ]

    # Anomalous samples (label=1)
    anomaly_samples = [
        {
            'dur': 5.0, 'proto': 'tcp', 'service': '-', 'state': 'CON',
            'spkts': 200, 'dpkts': 100, 'sbytes': 50000, 'dbytes': 20000,
            'rate': 1000.0, 'sttl': 64, 'dttl': 64, 'sload': 10000.0, 'dload': 5000.0,
            'sloss': 0, 'dloss': 0, 'sinpkt': 1.0, 'dinpkt': 1.0,
            'sjit': 0.1, 'djit': 0.1, 'swin': 8192, 'stcpb': 10000, 'dtcpb': 5000,
            'dwin': 8192, 'tcprtt': 0.5, 'synack': 0.5, 'ackdat': 0.5,
            'smean': 250, 'dmean': 200, 'trans_depth': 1, 'response_body_len': 500,
            'ct_srv_src': 150, 'ct_state_ttl': 200, 'ct_flw_http_mthd': 0,
            'is_ftp_login': 0, 'ct_ftp_cmd': 0, 'ct_srv_dst': 150,
            'ct_dst_ltm': 300, 'ct_src_ltm': 100, 'ct_src_dport_ltm': 50,
            'ct_dst_sport_ltm': 50, 'ct_dst_src_ltm': 200, 'is_sm_ips_ports': 0,
            'attack_cat': 'Backdoors', 'label': 1
        }
        for _ in range(3)
    ]

    return {
        'headers': headers,
        'normal': normal_samples,
        'anomaly': anomaly_samples,
        'all': normal_samples + anomaly_samples
    }


@pytest.fixture
def sample_csv_file(temp_dir, sample_csv_data):
    """Create sample CSV file for testing"""
    csv_path = os.path.join(temp_dir, 'test_data.csv')

    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=sample_csv_data['headers'])
        writer.writeheader()
        writer.writerows(sample_csv_data['all'])

    return csv_path


@pytest.fixture
def sample_model_data():
    """Generate sample model statistics"""
    return {
        'timestamp': '20250101_120000',
        'threshold_factor': 1.4,
        'model_type': 'statistical_anomaly_detector',
        'feature_stats': {
            'means': [1.0] * 43,  # 43 features (excluding label)
            'stds': [0.5] * 43
        }
    }


@pytest.fixture
def sample_model_file(temp_output_dir, sample_model_data):
    """Create sample model JSON file"""
    model_path = os.path.join(temp_output_dir, 'models', 'latest_model.json')

    with open(model_path, 'w') as f:
        json.dump(sample_model_data, f, indent=2)

    return model_path


@pytest.fixture
def sample_poisoning_config():
    """Generate sample poisoning configuration"""
    return {
        'enabled': True,
        'trigger_after_retraining': 3,
        'poison_rate': 1.0,  # 100%
        'poison_strategy': 'label_flip'
    }


@pytest.fixture
def sample_poisoning_state():
    """Generate sample poisoning state"""
    return {
        'is_active': False,
        'current_retraining_cycle': 0,
        'started_at_cycle': None,
        'total_poisoned_samples': 0,
        'last_updated': None
    }


# ============================================================================
# MOCK FIXTURES
# ============================================================================

@pytest.fixture
def mock_datetime(mocker):
    """Mock datetime.now() to return fixed timestamp"""
    from datetime import datetime
    fixed_time = datetime(2025, 1, 1, 12, 0, 0)
    mock_dt = mocker.patch('datetime.datetime')
    mock_dt.now.return_value = fixed_time
    return fixed_time


@pytest.fixture
def mock_time_sleep(mocker):
    """Mock time.sleep() to avoid delays in tests"""
    return mocker.patch('time.sleep', return_value=None)


@pytest.fixture
def fixed_random_seed():
    """Set fixed random seed for deterministic tests"""
    import random
    random.seed(42)
    yield
    random.seed()  # Reset after test


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_csv_file(path, headers, rows):
    """Helper to create CSV file with given headers and rows"""
    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def read_csv_file(path):
    """Helper to read CSV file and return rows"""
    with open(path, 'r') as f:
        reader = csv.DictReader(f)
        return list(reader)


def create_json_file(path, data):
    """Helper to create JSON file with given data"""
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def read_json_file(path):
    """Helper to read JSON file and return data"""
    with open(path, 'r') as f:
        return json.load(f)


# ============================================================================
# SYSTEM TEST FIXTURES
# ============================================================================

@pytest.fixture(scope='session')
def docker_helper():
    """
    Create DockerHelper instance for system tests
    Scope: session (shared across all tests)
    """
    # Import helper utilities
    HELPERS_DIR = Path(__file__).parent / 'helpers'
    sys.path.insert(0, str(HELPERS_DIR))
    
    from docker_utils import DockerHelper
    
    return DockerHelper()


@pytest.fixture(scope='class')
def running_system(docker_helper):
    """
    Start system before test class, stop after
    Scope: class (start once per test class)
    """
    # Start system with clean data
    success = docker_helper.start_system(clean=True)
    if not success:
        pytest.fail("Failed to start system")

    yield docker_helper

    # Teardown: stop system
    docker_helper.stop_system(remove_volumes=True)


@pytest.fixture(scope='function')
def clean_system(docker_helper):
    """
    Clean system state before each test
    Scope: function (clean before each test)
    """
    docker_helper.clean_data_directories()
    yield docker_helper