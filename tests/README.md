# Unit Tests for Network Anomaly Detection System

This directory contains unit tests for all components of the Network Anomaly Detection System.

## Quick Start

To run all working tests:
```bash
sudo pytest tests/unit/test_data_accumulator.py tests/unit/test_poisoning_controller.py -v
```

To run pytest on all test files (some may fail due to implementation mismatches):
```bash
sudo pytest tests/unit/ -v
```

To run a specific test file:
```bash
sudo pytest tests/unit/test_data_accumulator.py -v
```

To run a specific test:
```bash
sudo pytest tests/unit/test_data_accumulator.py::TestSnapshotCreation::test_take_snapshot_creates_file -v
```

## Working Test Files

✅ `test_data_accumulator.py` - Tests data accumulation and management (13 tests)
✅ `test_poisoning_controller.py` - Tests label-flip poisoning attacks (19 tests)

## Test Files Needing Updates

❌ `test_anomaly_detector.py` - Needs updates to match actual implementation
❌ `test_traffic_generator.py` - Needs updates to match actual implementation  
❌ `test_retraining_scheduler.py` - Needs updates to match actual implementation
❌ `test_performance_tracker.py` - Needs updates to match actual implementation
❌ `test_log_processor.py` - Needs updates to match actual implementation
❌ `test_test_set_creator.py` - Needs updates to match actual implementation

## Requirements

Install testing dependencies:
```bash
pip install pytest pytest-mock
```

## Test Structure

Tests use the following fixtures (defined in `conftest.py`):
- `temp_dir` - Temporary directory for test files
- `sample_csv_data` - Sample UNSW-NB15 dataset
- `sample_model_data` - Sample trained model
- `mock_datetime` - Fixed datetime for deterministic tests
- `fixed_random_seed` - Fixed random seed for reproducible results

All tests are isolated and use temporary directories to avoid interfering with the main system.

## Example Usage

```bash
# Run working tests only
sudo pytest tests/unit/test_data_accumulator.py tests/unit/test_poisoning_controller.py -v

# Run all data accumulator tests
sudo pytest tests/unit/test_data_accumulator.py -v

# Run all poisoning controller tests  
sudo pytest tests/unit/test_poisoning_controller.py -v

# Run a specific test class
sudo pytest tests/unit/test_data_accumulator.py::TestSnapshotCreation -v

# Run a specific test method
sudo pytest tests/unit/test_poisoning_controller.py::TestActivationLogic::test_activate_when_cycle_threshold_reached -v
```