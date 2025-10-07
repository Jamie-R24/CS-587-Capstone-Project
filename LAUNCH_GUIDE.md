# Network Anomaly Detection System - Launch Guide

## Table of Contents
1. [System Requirements](#system-requirements)
2. [Quick Start](#quick-start)
3. [Advanced Operations](#advanced-operations)
4. [Monitoring & Analysis](#monitoring--analysis)
5. [System Management](#system-management)
6. [Retraining System](#retraining-system)
7. [Troubleshooting](#troubleshooting)

## System Requirements

### Software Prerequisites
- Docker: Version 20.10+
- Docker Compose: Version 2.0+
- Linux/macOS (Windows with WSL2)

### Hardware Requirements
- 4GB+ RAM
- 2GB+ free disk space

### Dataset Requirements
- UNSW-NB15 dataset in `training_data/` directory
- Download from: [UNSW-NB15 Dataset](https://www.kaggle.com/datasets/programmer3/unsw-nb15-dataset?resource=download)

## Quick Start

### 1. Initial Setup
```bash
# Start the system
./restart_system.sh

# Wait for initialization (~60 seconds)
# System will automatically:
# - Create test set
# - Train initial model
# - Start data accumulator
# - Start retraining scheduler
```

### 2. Verify Operation
```bash
# Check container status
sudo docker-compose ps

# View real-time monitoring
./monitor_dashboard.sh
```

## Advanced Operations

### Custom Model Training
```bash
# Train with custom parameters
sudo docker exec -it workstation python3 /scripts/docker_anomaly_detector.py \
  --mode train \
  --confidence 0.35
```

### Available Parameters
- `--confidence`: Alert threshold (0.0-1.0, default: 0.4)
- `--detection-threshold`: Feature threshold (0.0-1.0, default: 0.10)

## Monitoring & Analysis

### Real-Time Monitoring

1. Dashboard View
```bash
./monitor_dashboard.sh
```

2. Container Logs
```bash
# Monitor alerts
sudo docker logs -f monitor

# View traffic generation
sudo docker logs -f target

# Check retraining progress
sudo docker logs -f workstation
```

### Performance Analysis

1. Training Metrics
```bash
# View latest training results
cat "$(ls -t data/output/logs/training_log_*.json | head -1)"
```

2. Alert Analysis
```bash
# View recent alerts
ls -lth data/output/alerts/ | head -10
```

3. System Performance
```bash
# Resource usage
sudo docker stats
```

## System Management

### Container Operations
```bash
# Start all containers
sudo docker-compose up -d

# Stop all containers
sudo docker-compose down

# Restart specific container
sudo docker-compose restart monitor
```

### Data Management
```bash
# Archive old alerts
mkdir -p data/archive/alerts
ls -t data/output/alerts/*.json | tail -n +51 | xargs -I {} mv {} data/archive/alerts/

# Clean old reports
mkdir -p data/archive/reports
ls -t data/output/reports/*.json | tail -n +11 | xargs -I {} mv {} data/archive/reports/
```

## Retraining System

### Architecture
The system implements automatic scheduled retraining:

```
┌─────────────────┐
│     TARGET      │    Generates synthetic traffic
└────────┬────────┘    (80% normal, 20% anomalous)
         │
         ▼
┌─────────────────┐
│   ACCUMULATOR   │    Takes snapshots every 5 minutes
└────────┬────────┘    Stores in accumulated_data/
         │
         ▼
┌─────────────────┐
│   RETRAINING    │    Runs every 5 minutes
└────────┬────────┘    Combines: UNSW-NB15 + Synthetic
         │
         ▼
┌─────────────────┐
│  PERFORMANCE    │    Evaluates on fixed test set
└─────────────────┘    Tracks metrics over time
```

### Monitoring Retraining

1. View Retraining Logs
```bash
# Real-time retraining logs
sudo docker exec workstation tail -f /data/output/retraining.log

# Real-time accumulator logs
sudo docker exec workstation tail -f /data/output/accumulator.log
```

2. Check Performance Metrics
```bash
# View metrics over time
sudo docker exec workstation column -t -s',' /data/output/performance_over_time.csv
```

3. Verify Data Accumulation
```bash
# List snapshots
sudo docker exec workstation ls -lh /data/accumulated_data/
```

### Customizing Retraining

1. Change Intervals
Edit docker-compose.yml:
```yaml
# Retraining interval (default: 300s/5min)
python3 /scripts/retraining_scheduler.py --interval 600  # 10min

# Snapshot interval (default: 300s/5min)
python3 /scripts/data_accumulator.py --interval 180  # 3min
```

2. Adjust Parameters
```yaml
# Minimum samples before retraining
python3 /scripts/retraining_scheduler.py --min-samples 100
```

## Troubleshooting

### Common Issues

1. Containers Won't Start
```bash
# Check Docker service
sudo systemctl status docker

# View detailed logs
sudo docker-compose logs
```

2. No Alerts Generated
```bash
# Verify model exists
sudo docker exec -it workstation ls -la /data/output/models/latest_model.json

# Check traffic generation
sudo docker logs target | grep "Generated"
```

3. Retraining Issues
```bash
# Check accumulator
sudo docker exec workstation ps aux | grep data_accumulator

# Verify sample count
sudo docker exec workstation wc -l /data/accumulated_data/accumulated_synthetic.csv
```

### Quick Fixes

1. Complete System Reset
```bash
# Stop everything
sudo docker-compose down

# Clear data
sudo rm -rf data/output/*

# Restart fresh
./restart_system.sh
```

2. Individual Container Reset
```bash
sudo docker-compose restart [container_name]
```

3. Check Container Health
```bash
sudo docker inspect --format='{{.State.Health.Status}}' workstation
```

## File Locations Reference

### Main Directories
- Models: `data/output/models/`
- Alerts: `data/output/alerts/`
- Logs: `data/output/logs/`
- Reports: `data/output/reports/`
- Training Data: `training_data/UNSW_NB15.csv`

### Retraining Files
- Snapshots: `data/accumulated_data/`
- Performance Metrics: `data/output/performance_over_time.csv`
- Retraining Logs: `data/output/retraining.log`
- Accumulator Logs: `data/output/accumulator.log`

## Support Resources

For detailed project architecture and overview, see: [README.md](README.md)

For specific issues, check container logs:
```bash
sudo docker logs workstation  # Development container
sudo docker logs target      # Traffic generation
sudo docker logs monitor     # Anomaly detection
```