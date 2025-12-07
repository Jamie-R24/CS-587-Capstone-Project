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
- UNSW-NB15 dataset is included as `training_data/UNSW_NB15.zip`
- **Automatic extraction**: The `restart_system.sh` script will extract the dataset automatically if needed
- Dataset source: [UNSW-NB15 Dataset](https://www.kaggle.com/datasets/programmer3/unsw-nb15-dataset?resource=download)

### Verify Prerequisites

Run these commands to verify your system is ready:

```bash
# Check Docker version (requires 20.10+)
docker --version
# Expected: Docker version 20.10.x or higher

# Check Docker Compose version (requires 2.0+)
# Try EITHER of these commands (v2 vs v1 syntax):
docker compose version    # Docker Compose v2 (preferred)
docker-compose --version  # Docker Compose v1 (legacy)
# Expected: Docker Compose version v2.x.x (or 1.x.x)

# Verify Docker daemon is running
sudo docker ps
# Expected: Empty table (no error)

# Check available disk space (requires 2GB+)
df -h .
# Expected: At least 2GB available in "Avail" column

# Verify dataset exists
ls -la training_data/UNSW_NB15.zip
# Expected: File exists (~1.1MB)
```

**Note:** The scripts automatically detect whether you have Docker Compose v2 (`docker compose`) or v1 (`docker-compose`) and use the correct command.

If any command fails, see [Troubleshooting](#troubleshooting) section.

## Quick Start

### 1. Initial Setup
```bash
# Start the system (dataset extraction is automatic)
./restart_system.sh

# Wait for initialization (~15-20 seconds)
# System will automatically:
# - Extract dataset (if not already extracted)
# - Create fixed test set
# - Train initial model
# - Start data accumulator (snapshots every 2 min)
# - Start retraining scheduler (retrains every 2 min)
```

### 2. Verify Operation
```bash
# Check container status (use whichever command works on your system)
sudo docker compose ps     # Docker Compose v2
sudo docker-compose ps     # Docker Compose v1

# View real-time monitoring
./monitor_dashboard.sh
```

### 3. What to Expect

**Timeline:**
| Phase | Time | What Happens |
|-------|------|--------------|
| System startup | 0-20 sec | Containers install dependencies, initialize |
| Initial training | 20-60 sec | First model trained on UNSW-NB15 dataset |
| Traffic generation | Ongoing | Target generates ~600 flows/minute |
| Data accumulation | Every 2 min | Snapshots saved to accumulated_data/ |
| Model retraining | Every 2 min | Model retrained with new synthetic data |

**Expected startup output from `./restart_system.sh`:**
```
=========================================
  Restarting Anomaly Detection System
=========================================

Using: docker compose

1. Checking dataset...
   ✓ Dataset already extracted

2. Stopping containers...
   ✓ Containers stopped

3. Clearing data/output folder...
   ✓ Output removed

4. Starting containers...
   ✓ Containers starting...

5. Waiting for initialization...
   Waiting... (0 seconds) - Status: starting
   Waiting... (10 seconds) - Status: starting
   ✓ Workstation is ready!

6. Creating test set (if not exists)...
   ✓ Test set created

7. Ensuring output directories exist...
   ✓ Directories ready

8. Training initial model...
   ✓ Initial model trained

9. Saving baseline model...
   ✓ Baseline saved

=========================================
  System Ready!
=========================================
```

**Expected container status (`docker compose ps` or `docker-compose ps`):**
```
NAME          STATUS    PORTS
monitor       Up        
target        Up        
workstation   Up (healthy)
```

**Note:** The first startup may take 1-2 minutes while Docker downloads the Ubuntu image and installs dependencies. Subsequent startups are faster.

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
sudo docker compose up -d       # v2
sudo docker-compose up -d       # v1

# Stop all containers
sudo docker compose down         # v2
sudo docker-compose down         # v1

# Restart specific container
sudo docker compose restart monitor    # v2
sudo docker-compose restart monitor    # v1
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
└────────┬────────┘    (30% normal, 70% anomalous)
         │
         ▼
┌─────────────────┐
│   ACCUMULATOR   │    Takes snapshots every 2 minutes
└────────┬────────┘    Stores in accumulated_data/
         │
         ▼
┌─────────────────┐
│   RETRAINING    │    Runs every 2 minutes
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
# Retraining interval (default: 120s/2min)
python3 /scripts/retraining_scheduler.py --interval 300  # 5min

# Snapshot interval (default: 120s/2min)
python3 /scripts/data_accumulator.py --interval 180  # 3min
```

2. Adjust Parameters
```yaml
# Minimum samples before retraining
python3 /scripts/retraining_scheduler.py --min-samples 100
```

## Troubleshooting

### First-Time Setup Issues

1. **Docker Not Running**
```bash
# Start Docker service
sudo systemctl start docker

# Enable Docker to start on boot
sudo systemctl enable docker

# Verify it's running
sudo docker ps
```

2. **Permission Denied Errors**
```bash
# Most commands require sudo
sudo docker compose ps      # v2
sudo docker-compose ps      # v1

# Or add yourself to docker group (requires logout/login)
sudo usermod -aG docker $USER
```

3. **Dataset Not Extracted**
```bash
# If you see "file not found" errors for UNSW_NB15.csv
cd training_data/
unzip UNSW_NB15.zip
cd ..
```

4. **Port Conflicts**
```bash
# Check if ports are in use
sudo netstat -tlnp | grep -E '172.20'

# If network conflict, remove old networks
sudo docker network prune
```

### Common Issues

1. Containers Won't Start
```bash
# Check Docker service
sudo systemctl status docker

# View detailed logs
sudo docker compose logs      # v2
sudo docker-compose logs      # v1
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
sudo docker exec workstation wc -l /data/accumulated_data/combined_training.csv
```

### Quick Fixes

1. Complete System Reset
```bash
# Stop everything
sudo docker compose down       # v2
sudo docker-compose down       # v1

# Clear data
sudo rm -rf data/output/*

# Restart fresh
./restart_system.sh
```

2. Individual Container Reset
```bash
sudo docker compose restart [container_name]    # v2
sudo docker-compose restart [container_name]    # v1
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