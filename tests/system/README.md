# System Tests

This directory contains end-to-end system tests for the Network Anomaly Detection System. Unlike unit tests that mock dependencies, system tests validate real Docker container orchestration, network traffic generation, and data processing workflows.

## Overview

**Purpose:** Validate complete system integration across Docker containers  
**Runtime:** ~30 minutes for full test suite  
**Total Tests:** 25 tests across 4 test files  

## Test Files

### 1. test_container_integration.py (8 tests, ~5 min)
Tests Docker orchestration, networking, and volume sharing.

**Tests:**
- Container startup and health checks
- Shared volume accessibility
- Network connectivity between containers
- Volume read/write permissions
- Background process execution
- Container restart resilience
- Volume cleanup

### 2. test_end_to_end_detection.py (6 tests, ~5 min)
Tests the complete detection pipeline from traffic generation to alerts.

**Tests:**
- Initial model training and structure
- Fixed test set creation (500 samples)
- Test sample exclusion from training data
- Network traffic generation
- Alert generation and validation
- Model persistence across restarts

### 3. test_retraining_cycle.py (5 tests, ~10 min)
Tests scheduled retraining with accumulated synthetic data.

**Tests:**
- Data snapshot creation (2-min intervals)
- First retraining cycle completion
- Combined dataset (UNSW + synthetic)
- Performance tracking across cycles
- Multiple consecutive retraining cycles

### 4. test_poisoning_impact.py (6 tests, ~15 min)
Tests poisoning attack simulation and performance degradation.

**Tests:**
- Poisoning activation after trigger cycle
- Poisoning state tracking
- Poisoned traffic generation (label flipping)
- Performance degradation after poisoning
- Poisoned sample persistence
- Recall metric impact

## Prerequisites

### System Requirements
- Docker 20.10+ installed and running
- Docker Compose 2.0+ installed
- At least 4GB RAM available
- At least 2GB disk space
- Ports 172.20.0.0/16 available (lab_network)

### Install Dependencies

```bash
# Navigate to project root
cd /home/jamier/Desktop/CS-587-Capstone-Project

# Install system test dependencies
pip install pytest==7.4.3
pip install pytest-timeout==2.2.0   # Timeout protection
pip install docker==7.0.0           # Docker SDK for Python

# Verify Docker connectivity
docker ps  # Should not error
docker-compose --version  # Should show 2.0+
```

## Running Tests

### Run All System Tests
```bash
sudo ./tests/system/run_tests.sh
pytest tests/system/ -v -s --timeout=1800
```

### Run Specific Test File
```bash
# Container integration tests
pytest tests/system/test_container_integration.py -v -s

# End-to-end detection tests
pytest tests/system/test_end_to_end_detection.py -v -s

# Retraining cycle tests
pytest tests/system/test_retraining_cycle.py -v -s

# Poisoning impact tests
pytest tests/system/test_poisoning_impact.py -v -s
```

### Run Specific Test
```bash
pytest tests/system/test_end_to_end_detection.py::TestEndToEndDetection::test_01_initial_training_creates_model -v -s
```

### Command-line Flags
- `-v`: Verbose output (show test names)
- `-s`: Show print statements (important for debugging)
- `--timeout=1800`: 30-minute max for entire suite

## Test Structure

### Helper Utilities (`tests/helpers/`)

#### docker_utils.py
Container management and interaction utilities.

**Key Functions:**
- `start_system(clean=True)` - Start docker-compose
- `stop_system(remove_volumes=True)` - Stop containers
- `exec_in_container(container, command)` - Execute commands
- `read_file_from_container(container, path)` - Read files
- `get_container_logs(container)` - Retrieve logs
- `restart_container(container)` - Restart specific container

#### wait_utils.py
Polling utilities for async operations.

**Key Functions:**
- `wait_for_model(docker_helper, timeout)` - Wait for model training
- `wait_for_retraining_cycle(docker_helper, cycle_num, timeout)` - Wait for retraining
- `wait_for_traffic_generation(docker_helper, min_samples, timeout)` - Wait for traffic
- `wait_for_alerts(docker_helper, min_alerts, timeout)` - Wait for alerts
- `wait_for_poisoning_activation(docker_helper, timeout)` - Wait for poisoning

#### validation_utils.py
Validation and assertion helpers.

**Key Functions:**
- `validate_model_structure(model_json)` - Validate model JSON schema
- `validate_alert_structure(alert_json)` - Validate alert JSON schema
- `validate_performance_metrics(csv_string)` - Validate performance CSV
- `calculate_traffic_distribution(csv_string)` - Analyze traffic distribution
- `validate_test_set(csv_string, expected_size)` - Validate test set

### Fixtures

#### Session-scoped
- `docker_helper`: Shared DockerHelper instance across all tests

#### Class-scoped
- `running_system`: Starts system before test class, stops after

#### Function-scoped
- `clean_system`: Cleans data directories before each test

## Test Execution Flow

1. **Setup Phase** (Class-scoped)
   - Start docker-compose
   - Wait for containers to be healthy
   - Run initialization scripts
   - Wait for initial model training

2. **Test Execution**
   - Tests run sequentially (no parallelization)
   - Use `docker_helper` to interact with containers
   - Use `wait_*` functions for async operations
   - Use `validate_*` functions for complex assertions

3. **Teardown Phase**
   - Stop all containers
   - Remove volumes
   - Clean data directories

## Timing Expectations

### Key Intervals
- **Data Accumulation**: Every 2 minutes
- **Retraining Cycle**: Every 2 minutes (with min 30 samples)
- **Initial Model Training**: ~30-60 seconds
- **Poisoning Trigger**: After 3 retraining cycles (~6+ minutes)

### Timeout Values
- Model creation: 120 seconds
- Retraining cycle: 180 seconds
- Traffic generation: 60 seconds
- Poisoning activation: 480 seconds (8 min)
- Full test suite: 1800 seconds (30 min)

## Debugging

### View Container Logs
```bash
# View logs from specific container
docker logs workstation
docker logs target
docker logs monitor

# View logs in real-time
docker logs -f workstation
```

### Check Container Status
```bash
# List running containers
docker ps

# Check container health
docker inspect workstation | grep -A 10 Health
```

### Access Container Shell
```bash
# Open bash in container
docker exec -it workstation bash

# Check files
docker exec workstation ls -la /data/output/models
```

### Clean Up After Failed Tests
```bash
# Stop all containers and remove volumes
docker-compose down -v

# Remove all stopped containers
docker container prune -f

# Remove all volumes
docker volume prune -f

# Full system prune (use with caution)
docker system prune -a --volumes
```

## Common Issues

### Issue: Containers fail to start
**Solution:**
```bash
# Check Docker is running
docker ps

# Validate docker-compose.yml
docker-compose config

# Restart Docker daemon
sudo systemctl restart docker
```

### Issue: Tests timeout
**Solution:**
- Increase timeout values in test decorators
- Check system resources (CPU, RAM)
- Verify containers are healthy: `docker ps`
- Check container logs for errors

### Issue: Model not created
**Solution:**
- Check workstation logs: `docker logs workstation`
- Verify UNSW_NB15.csv exists in training_data/
- Check file permissions
- Ensure sufficient disk space

### Issue: Poisoning not activating
**Solution:**
- Verify retraining cycles completed (check logs)
- Check poisoning_config.json: `enabled: true`
- Verify trigger_after_retraining value (default: 3)
- Check poisoning_state.json for status

### Issue: Volume permission errors
**Solution:**
```bash
# Fix permissions on data directories
chmod -R 755 data/

# Check volume mounts
docker inspect workstation | grep -A 20 Mounts
```

## Expected Output

### Successful Test Run
```
tests/system/test_container_integration.py::TestContainerIntegration::test_01_all_containers_start_successfully PASSED
tests/system/test_container_integration.py::TestContainerIntegration::test_02_shared_volumes_accessible PASSED
...
======================== 25 passed in 30.42 minutes ========================
```

### Test Failure
```
FAILED tests/system/test_end_to_end_detection.py::TestEndToEndDetection::test_01_initial_training_creates_model
AssertionError: Model not created within timeout
```

## Performance Expectations

### Baseline Metrics
- **Accuracy**: ~83%
- **Precision**: ~80-85%
- **Recall**: ~75-80%
- **F1 Score**: ~78-82%

### Post-Poisoning (Expected Degradation)
- **Accuracy**: May drop 5-10 percentage points
- **Recall**: May drop significantly (false negatives increase)
- **Precision**: May remain relatively stable

## Contributing

When adding new system tests:

1. Follow naming convention: `test_XX_descriptive_name`
2. Add verbose logging with `print()` statements
3. Use appropriate `wait_*` functions for async operations
4. Validate outputs with `validate_*` functions
5. Set appropriate `@pytest.mark.timeout()` decorator
6. Document expected runtime in docstring
7. Clean up resources in teardown

## Notes

- **Test Isolation**: Tests within a class share container state for efficiency
- **Sequential Execution**: Tests run in numeric order (test_01, test_02, etc.)
- **No Parallelization**: System tests cannot run in parallel (shared Docker resources)
- **Verbose Output**: Use `-s` flag to see detailed progress logs
- **Cleanup**: Always use `docker-compose down -v` after tests

## Support

For issues or questions:
1. Check container logs: `docker logs <container_name>`
2. Verify Docker setup: `docker ps` and `docker-compose config`
3. Review test output with `-v -s` flags
4. Check system resources: `docker stats`
5. Consult System_tests_implementation.md for detailed implementation guide
