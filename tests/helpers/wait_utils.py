#!/usr/bin/env python3
"""
Wait/polling utility functions for system tests
Provides helpers for waiting on async operations
"""

import time
import json
import os


def wait_for_file(docker_helper, container, file_path, timeout=60):
    """
    Wait for file to exist in container

    Args:
        docker_helper: DockerHelper instance
        container: Container name
        file_path: Path to file
        timeout: Max seconds to wait

    Returns:
        True if file exists, False if timeout
    """
    print(f"[WaitUtils] Waiting for file: {file_path} in {container} (timeout={timeout}s)...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        if docker_helper.file_exists_in_container(container, file_path):
            elapsed = time.time() - start_time
            print(f"[WaitUtils] ✓ File exists! ({elapsed:.1f}s)")
            return True
        time.sleep(1)

    print(f"[WaitUtils] ✗ TIMEOUT waiting for file")
    return False


def wait_for_model(docker_helper, timeout=120):
    """
    Wait for trained model to be created

    Args:
        docker_helper: DockerHelper instance
        timeout: Max seconds to wait

    Returns:
        True if model exists, False if timeout
    """
    print(f"[WaitUtils] Waiting for initial model training (timeout={timeout}s)...")
    
    result = wait_for_file(
        docker_helper,
        'workstation',
        '/data/output/models/latest_model.json',
        timeout
    )
    
    if result:
        print(f"[WaitUtils] ✓ Model training completed!")
    else:
        print(f"[WaitUtils] ✗ Model training did not complete in time")
    
    return result


def wait_for_retraining_cycle(docker_helper, cycle_number, timeout=180):
    """
    Wait for specific retraining cycle to complete

    Args:
        docker_helper: DockerHelper instance
        cycle_number: Which cycle to wait for (1, 2, 3, etc.)
        timeout: Max seconds to wait

    Returns:
        True if cycle completed, False if timeout
    """
    print(f"[WaitUtils] Waiting for retraining cycle #{cycle_number} (timeout={timeout}s)...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        # Count retrain_*.json files
        count = docker_helper.count_files_in_directory(
            'workstation',
            '/data/output/retraining_logs',
            'retrain_*.json'
        )

        if count >= cycle_number:
            elapsed = time.time() - start_time
            print(f"[WaitUtils] ✓ Retraining cycle #{cycle_number} completed! ({elapsed:.1f}s)")
            return True

        # Show progress every 15 seconds
        elapsed = time.time() - start_time
        if int(elapsed) % 15 == 0 and elapsed > 0:
            print(f"[WaitUtils]   ... waiting for cycle #{cycle_number} ({int(elapsed)}s elapsed, {count} cycles so far)")

        time.sleep(5)

    print(f"[WaitUtils] ✗ TIMEOUT waiting for retraining cycle #{cycle_number}")
    return False


def wait_for_traffic_generation(docker_helper, min_samples=100, timeout=60):
    """
    Wait for target to generate minimum number of traffic samples

    Args:
        docker_helper: DockerHelper instance
        min_samples: Minimum number of samples required
        timeout: Max seconds to wait

    Returns:
        True if sufficient samples generated, False if timeout
    """
    print(f"[WaitUtils] Waiting for traffic generation (min={min_samples} samples, timeout={timeout}s)...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        line_count = docker_helper.get_file_line_count(
            'target',
            '/var/log/activity/network_data.csv'
        )

        # Subtract 1 for header
        sample_count = line_count - 1
        
        if sample_count >= min_samples:
            elapsed = time.time() - start_time
            print(f"[WaitUtils] ✓ Traffic generated! ({sample_count} samples in {elapsed:.1f}s)")
            return True

        time.sleep(2)

    print(f"[WaitUtils] ✗ TIMEOUT waiting for traffic generation")
    return False


def wait_for_alerts(docker_helper, min_alerts=1, timeout=60):
    """
    Wait for monitor to generate alerts

    Args:
        docker_helper: DockerHelper instance
        min_alerts: Minimum number of alert files required
        timeout: Max seconds to wait

    Returns:
        True if alerts generated, False if timeout
    """
    print(f"[WaitUtils] Waiting for alerts (min={min_alerts} files, timeout={timeout}s)...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        count = docker_helper.count_files_in_directory(
            'monitor',
            '/data/output/alerts',
            'alerts_*.json'
        )

        if count >= min_alerts:
            elapsed = time.time() - start_time
            print(f"[WaitUtils] ✓ Alerts generated! ({count} files in {elapsed:.1f}s)")
            return True

        time.sleep(2)

    print(f"[WaitUtils] ✗ TIMEOUT waiting for alerts")
    return False


def wait_for_snapshots(docker_helper, min_snapshots=1, timeout=150):
    """
    Wait for data accumulator to create snapshots

    Args:
        docker_helper: DockerHelper instance
        min_snapshots: Minimum number of snapshots required
        timeout: Max seconds to wait

    Returns:
        True if snapshots created, False if timeout
    """
    print(f"[WaitUtils] Waiting for data snapshots (min={min_snapshots}, timeout={timeout}s)...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        count = docker_helper.count_files_in_directory(
            'workstation',
            '/data/accumulated_data',
            'snapshot_*.csv'
        )

        if count >= min_snapshots:
            elapsed = time.time() - start_time
            print(f"[WaitUtils] ✓ Snapshots created! ({count} files in {elapsed:.1f}s)")
            return True

        # Show progress every 15 seconds
        elapsed = time.time() - start_time
        if int(elapsed) % 15 == 0 and elapsed > 0:
            print(f"[WaitUtils]   ... waiting for snapshots ({int(elapsed)}s elapsed, {count} so far)")

        time.sleep(5)

    print(f"[WaitUtils] ✗ TIMEOUT waiting for snapshots")
    return False


def wait_for_poisoning_activation(docker_helper, timeout=360):
    """
    Wait for poisoning to activate (checks poisoning_state.json)

    Args:
        docker_helper: DockerHelper instance
        timeout: Max seconds to wait

    Returns:
        True if poisoning activated, False if timeout
    """
    print(f"[WaitUtils] Waiting for poisoning activation (timeout={timeout}s)...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        # Read poisoning state
        state_content = docker_helper.read_file_from_container(
            'target',
            '/data/poisoning/poisoning_state.json'
        )

        if state_content:
            try:
                state = json.loads(state_content)
                if state.get('is_active', False):
                    elapsed = time.time() - start_time
                    cycle = state.get('current_retraining_cycle', '?')
                    print(f"[WaitUtils] ✓ Poisoning activated at cycle {cycle}! ({elapsed:.1f}s)")
                    return True
            except json.JSONDecodeError:
                pass

        # Show progress every 30 seconds
        elapsed = time.time() - start_time
        if int(elapsed) % 30 == 0 and elapsed > 0:
            print(f"[WaitUtils]   ... waiting for poisoning activation ({int(elapsed)}s elapsed)")

        time.sleep(10)

    print(f"[WaitUtils] ✗ TIMEOUT waiting for poisoning activation")
    return False


def wait_for_performance_metrics(docker_helper, min_rows=1, timeout=60):
    """
    Wait for performance metrics to be logged

    Args:
        docker_helper: DockerHelper instance
        min_rows: Minimum number of metric rows (excluding header)
        timeout: Max seconds to wait

    Returns:
        True if metrics logged, False if timeout
    """
    print(f"[WaitUtils] Waiting for performance metrics (min={min_rows} rows, timeout={timeout}s)...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        line_count = docker_helper.get_file_line_count(
            'workstation',
            '/data/output/performance_over_time.csv'
        )

        # Subtract 1 for header
        row_count = line_count - 1
        
        if row_count >= min_rows:
            elapsed = time.time() - start_time
            print(f"[WaitUtils] ✓ Performance metrics logged! ({row_count} rows in {elapsed:.1f}s)")
            return True

        time.sleep(2)

    print(f"[WaitUtils] ✗ TIMEOUT waiting for performance metrics")
    return False
