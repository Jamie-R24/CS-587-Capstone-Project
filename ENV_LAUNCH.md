# Docker Environment Guide

Complete guide for launching and operating the Network Anomaly Detection System in Docker.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [System Startup](#system-startup)
3. [Model Training](#model-training)
4. [Monitoring & Alerting](#monitoring--alerting)
5. [Performance Analysis](#performance-analysis)
6. [System Management](#system-management)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software
- **Docker**: Version 20.10+
- **Docker Compose**: Version 2.0+
- **System Resources**:
  - 4GB+ RAM
  - 2GB+ free disk space
  - Linux/macOS (Windows with WSL2)

### Verify Installation

```bash
# Check Docker
docker --version
# Expected: Docker version 20.10.x or higher

# Check Docker Compose
docker-compose --version
# Expected: Docker Compose version 2.x.x or higher

# Check system resources
free -h  # Linux
# Ensure at least 4GB available RAM
```

### Dataset Requirement

The UNSW-NB15 dataset must be in the `training_data/` directory:

```bash
ls -lh training_data/UNSW_NB15.csv
# Should show: ~1-2MB CSV file
```

---

## System Startup

### Method 1: Automatic Startup (Recommended)

Use the provided restart script for automatic initialization:

```bash
./restart_system.sh
```

This script:
- Stops existing containers
- Starts all containers
- Waits for initialization (~60 seconds)
- Confirms system readiness

**Expected Output:**
```
=========================================
  Restarting Anomaly Detection System
=========================================

1. Stopping containers...
   ✓ Containers stopped

2. Starting containers...
   ✓ Containers starting...

3. Waiting for initialization...
   ✓ Workstation is ready!

=========================================
  System Ready!
=========================================
```

### Method 2: Manual Startup

If you prefer manual control:

```bash
# Start all containers
sudo docker-compose up -d

# Verify all containers are running
sudo docker-compose ps

# Expected output: All containers show "Up" status
# NAME          STATUS
# workstation   Up X seconds (healthy)
# target        Up X seconds
# monitor       Up X seconds
```

### Wait for Initialization

Containers need 60-90 seconds to fully initialize. Check readiness:

```bash
# Watch workstation logs for "=== Workstation ready ==="
sudo docker logs workstation | grep "ready"

# Check if Python is available
sudo docker exec workstation python3 --version
```

---

## Model Training

### Train the Anomaly Detection Model

Once containers are ready, train the model:

```bash
sudo docker exec -it workstation python3 /scripts/docker_anomaly_detector.py --mode train
```

**Expected Training Output:**
```
Training Docker Anomaly Detector at 20251002_195309
Loaded 7465 samples with 44 features
Label distribution: Counter({1: 6748, 0: 717})
Training on 717 normal samples
Model saved to /data/output/models/model_20251002_195309.json

Training Accuracy: 0.8301
Precision: 0.9056 | Recall: 0.9066 | F1-Score: 0.9061
True Positives: 6118 | False Positives: 638
True Negatives: 79 | False Negatives: 630
Detection Coverage: 90.7% of anomalies detected

Training completed. Model saved to /data/output/models/
Training completed successfully!
```

### Verify Model Files

```bash
# Check model was created
ls -lh data/output/models/

# Expected files:
# latest_model.json                 # Symlink to latest
# model_YYYYMMDD_HHMMSS.json       # Timestamped model
```

### Training with Custom Parameters

Fine-tune detection thresholds:

```bash
# More sensitive (catches more anomalies, more false positives)
sudo docker exec -it workstation python3 /scripts/docker_anomaly_detector.py \
  --mode train \
  --confidence 0.35

# Less sensitive (fewer false positives, may miss some anomalies)
sudo docker exec -it workstation python3 /scripts/docker_anomaly_detector.py \
  --mode train \
  --confidence 0.45
```

**Available Parameters:**
- `--confidence`: Alert threshold (0.0-1.0, default: 0.4)
- `--detection-threshold`: Feature threshold (0.0-1.0, default: 0.10)

---

## Monitoring & Alerting

### Real-Time Dashboard

Use the monitoring dashboard for live system status:

```bash
./monitor_dashboard.sh
```

**Dashboard Display:**
```
======================================================
   ANOMALY DETECTION SYSTEM - LIVE DASHBOARD
======================================================
Last Update: 2025-10-02 19:53:09

=== CONTAINER STATUS ===
  workstation: ✓ Running
  target: ✓ Running
  monitor: ✓ Running

=== FILE STATISTICS ===
  Models: 5 | Alerts: 127 | Reports: 8 | Logs: 3
  Total Size: 12M

=== RECENT ANOMALIES (Last 5 minutes) ===
  Total: 15 anomalies detected

  Time     | Confidence | Type
  ---------|------------|------------------
  19:52:34 | 1.000      | Backdoors
  19:52:34 | 0.974      | Reconnaissance
  19:52:34 | 0.661      | Generic
  19:52:19 | 0.925      | Backdoors
  ...

=== PERFORMANCE METRICS (Last Hour) ===
  Total Alerts: 183
  Detection Rate: 3.05 alerts/minute
  Avg Confidence: 0.742 | Max: 1.000 | Min: 0.405
  High: 89 | Medium: 94 | Low: 0

Press Ctrl+C to exit
```

### Monitor Container Logs

Watch real-time detection:

```bash
# Monitor container (shows alerts as they occur)
sudo docker logs -f monitor

# Target container (shows traffic generation)
sudo docker logs -f target
```

**Sample Monitor Output:**
```
Model loaded from /data/output/models/latest_model.json
Starting real-time monitoring of /var/log/activity/network_data.csv
ALERT: Backdoors detected - Confidence: 0.925
ALERT: Reconnaissance detected - Confidence: 0.874
ALERT: Generic detected - Confidence: 0.661
```

### View Alert Files

Alerts are saved as JSON files:

```bash
# List all alert files
ls -lth data/output/alerts/ | head -10

# View latest alert file
cat "$(ls -t data/output/alerts/*.json | head -1)" | python3 -m json.tool | head -30

# Count total anomalies in recent alerts
python3 -c "
import json, glob
alerts = glob.glob('data/output/alerts/*.json')
total = sum(len(json.load(open(f))) for f in alerts[-10:])
print(f'Last 10 files: {total} anomalies detected')
"
```

**Alert File Format:**
```json
[
  {
    "timestamp": "2025-10-02T19:52:34.780139",
    "sample_id": 5,
    "prediction": "ANOMALY",
    "anomaly_type": "Backdoors",
    "confidence": 0.925,
    "container": "monitor.lab"
  },
  ...
]
```

### Traffic Generation Status

Check synthetic traffic generation:

```bash
# View generated network data
sudo docker exec -it target tail -f /var/log/activity/network_data.csv

# Check generation rate
sudo docker logs target | grep "Generated"
```

**Expected Traffic Output:**
```
Generated 10 network flows
  -> 2 anomalous flows detected (Backdoors, Reconnaissance)
Generated 10 network flows
  -> 1 anomalous flows detected (Generic)
```

---

## Performance Analysis

### Training Logs

Review model performance:

```bash
# View latest training log
cat "$(ls -t data/output/logs/training_log_*.json | head -1)" | python3 -m json.tool
```

**Training Log Contents:**
```json
{
  "timestamp": "20251002_195309",
  "accuracy": 0.8301,
  "precision": 0.9056,
  "recall": 0.9066,
  "f1_score": 0.9061,
  "total_samples": 7465,
  "normal_samples": 717,
  "anomaly_samples": 6748,
  "true_positives": 6118,
  "false_positives": 638,
  "true_negatives": 79,
  "false_negatives": 630,
  "high_confidence_alerts": 0,
  "confidence_threshold": 0.4,
  "detection_threshold": 0.1,
  "z_score_threshold": 1.4
}
```

### Traffic Analysis Reports

Generate comprehensive traffic reports:

```bash
# Generate report
sudo docker exec -it monitor python3 /scripts/process_logs.py

# View latest report
cat "$(ls -t data/output/reports/traffic_analysis_*.json | head -1)" | python3 -m json.tool
```

**Traffic Report Format:**
```json
{
  "timestamp": "2025-10-02T14:33:40",
  "total_flows": 50,
  "normal_traffic": 36,
  "anomalies_in_data": 14,
  "anomaly_rate": 28.0,
  "high_confidence_alerts": 8,
  "alert_rate": 16.0,
  "top_protocols": {
    "tcp": 21,
    "icmp": 16,
    "udp": 13
  },
  "attack_categories": {
    "Backdoors": 7,
    "Reconnaissance": 5,
    "Generic": 2
  },
  "detection_effectiveness": {
    "total_anomalies": 14,
    "alerted_anomalies": 8,
    "alert_ratio": "57.1%"
  }
}
```

### System Resource Usage

Monitor container resource consumption:

```bash
# Real-time resource stats
sudo docker stats

# Disk usage
du -sh data/output/
df -h
```

---

## System Management

### Container Control

```bash
# Start system
sudo docker-compose up -d

# Stop system
sudo docker-compose down

# Restart specific container
sudo docker-compose restart monitor

# View container status
sudo docker-compose ps

# Access container shell
sudo docker exec -it workstation bash
```

### Data Management

```bash
# Archive old alerts (keep last 50 files)
mkdir -p data/archive/alerts
ls -t data/output/alerts/*.json | tail -n +51 | xargs -I {} mv {} data/archive/alerts/

# Clean old reports (keep last 10)
mkdir -p data/archive/reports
ls -t data/output/reports/*.json | tail -n +11 | xargs -I {} mv {} data/archive/reports/

# Check disk space saved
du -sh data/archive/
du -sh data/output/
```

### Complete System Reset

**WARNING: This deletes all models, alerts, and logs!**

```bash
# Stop containers
sudo docker-compose down

# Remove all output data
sudo rm -rf data/output/*

# Remove Docker volumes
sudo docker volume prune -f

# Fresh restart
sudo docker-compose up -d
```

---

## Troubleshooting

### Issue: Containers Won't Start

**Symptom:** `docker-compose up -d` fails with errors

**Solutions:**

```bash
# Check Docker service status
sudo systemctl status docker

# Restart Docker
sudo systemctl restart docker

# View detailed logs
sudo docker-compose logs

# Check for port conflicts
sudo netstat -tulpn | grep -E ':(80|443|3306|5432)'
```

### Issue: Python Not Found in Container

**Symptom:** `exec failed: "python3": executable file not found`

**Solution:** Wait for container initialization (60-90 seconds)

```bash
# Check if initialization is complete
sudo docker logs workstation | grep "Workstation ready"

# Or use the restart script
./restart_system.sh
```

### Issue: Network Subnet Conflict

**Symptom:** `Pool overlaps with other one on this address space`

**Solution:** Change Docker network subnet

```bash
# Edit docker-compose.yml, change:
# subnet: 172.20.0.0/16
# to:
# subnet: 172.21.0.0/16

# Then restart
sudo docker-compose down
sudo docker-compose up -d
```

### Issue: No Training Data Found

**Symptom:** `Error: Could not find /data/training_data/UNSW_NB15.csv`

**Solution:**

```bash
# Verify data exists on host
ls -la training_data/UNSW_NB15.csv

# Check container can access it
sudo docker exec -it workstation ls -la /data/training_data/

# Verify docker-compose.yml volume mapping:
# volumes:
#   - ./training_data:/data/training_data
```

### Issue: No Alerts Generated

**Symptom:** Empty `data/output/alerts/` directory

**Solutions:**

```bash
# 1. Verify model was trained
sudo docker exec -it workstation ls -la /data/output/models/latest_model.json

# 2. Check if target is generating data
sudo docker logs target | grep "Generated"

# 3. Verify monitor is running
sudo docker logs monitor | grep "Model loaded"

# 4. Check confidence threshold (may be too high)
# Retrain with lower threshold:
sudo docker exec -it workstation python3 /scripts/docker_anomaly_detector.py --mode train --confidence 0.3
```

### Issue: High System Resource Usage

**Symptom:** System lag, high CPU/memory usage

**Solutions:**

```bash
# 1. Check resource usage
sudo docker stats

# 2. Reduce traffic generation rate
# Edit scripts/generate_activity.py line 210:
# Change: generator.run_continuous(interval=10)
# To:     generator.run_continuous(interval=20)

# 3. Reduce monitoring frequency
# Edit scripts/process_logs.py monitoring interval

# 4. Clean up old data
sudo rm data/output/alerts/*.json
sudo rm data/output/reports/*.json
```

### Container Health Checks

```bash
# Check container health
sudo docker inspect --format='{{.State.Health.Status}}' workstation

# If container is 'unhealthy' try below:
sudo docker stop workstation
sudo docker start workstation

# View container processes
sudo docker exec -it monitor ps aux

# Test inter-container networking
sudo docker exec -it workstation ping target
sudo docker exec -it monitor ping target
```

---

## Quick Reference Commands

### Essential Commands

```bash
# Start system
sudo docker-compose up -d

# Stop system
sudo docker-compose down

# Train model
sudo docker exec -it workstation python3 /scripts/docker_anomaly_detector.py --mode train

# Monitor alerts
./monitor_dashboard.sh

# View logs
sudo docker logs -f monitor

# Restart system
./restart_system.sh
```

### File Locations

- **Models**: `data/output/models/`
- **Alerts**: `data/output/alerts/`
- **Logs**: `data/output/logs/`
- **Reports**: `data/output/reports/`
- **Training Data**: `training_data/UNSW_NB15.csv`

### Container Access

```bash
# Workstation (development)
sudo docker exec -it workstation bash

# Target (traffic generation)
sudo docker exec -it target bash

# Monitor (detection)
sudo docker exec -it monitor bash
```

---

## Support & Resources

For project overview and architecture details, see: [README.md](README.md)

For issues or questions, check container logs:
```bash
sudo docker logs workstation
sudo docker logs target
sudo docker logs monitor
```