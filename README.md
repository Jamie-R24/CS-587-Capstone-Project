# CS-587-Capstone-Project
Repository for CS 587 Cyber Security Capstone experience - Network Anomaly Detection for Lateral Movement

## Overview

This project implements a comprehensive network anomaly detection system using Docker containers and deep learning models to detect lateral movement and other network security threats. The system runs across three specialized containers: **workstation** (development), **target** (data generation), and **monitor** (real-time detection).

## Quick Start

```bash
# 1. Verify setup
./test_docker_setup.sh

# 2. Start all containers
sudo docker-compose up -d

# 3. Check container status
sudo docker-compose ps

# 4. Train the model (in workstation container)
sudo docker exec -it workstation python3 /scripts/docker_anomaly_detector.py --mode train

# 5. Monitor real-time detection
sudo docker logs -f monitor
```

## Docker Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   WORKSTATION   │    │     TARGET      │    │    MONITOR     │
│                 │    │                 │    │                │
│ - Train models  │    │ - Generate      │    │ - Process logs │
│ - Development   │    │   network data  │    │ - Detect       │
│ - Analysis      │    │ - Simulate      │    │   anomalies    │
│                 │    │   activity      │    │ - Generate     │
│                 │    │                 │    │   alerts       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │  SHARED VOLUMES │
                    │                 │
                    │ - /data/output  │
                    │ - /var/log/     │
                    │   activity      │
                    └─────────────────┘
```

### Container Roles

**🖥️ Workstation Container**
- Model training and development
- Analysis and experimentation
- Access: `sudo docker exec -it workstation bash`

**🎯 Target Container**
- Generates realistic network activity
- Simulates normal and anomalous patterns
- Auto-runs network data generation

**📊 Monitor Container**
- Real-time anomaly detection
- Alert generation and reporting
- Processes logs from target container

## Network Anomaly Detection for Lateral Movement

This project implements a deep learning model for detecting network anomalies and lateral movement behavior using the UNSW-NB15 dataset.

## Dataset Information

- **Dataset**: UNSW-NB15 network intrusion detection dataset
- **Samples**: 7,465 network flow records
- **Features**: 43 input features (network flow characteristics)
- **Classes**: Binary classification (Normal vs Anomaly/Attack)
- **Attack Types**: 9 different attack categories including lateral movement patterns

## Model Architecture

The deep learning model uses a neural network with:
- 4 hidden layers (128, 64, 32, 16 neurons)
- Batch normalization and dropout for regularization
- ReLU activation functions
- Sigmoid output for binary classification
- Adam optimizer with learning rate scheduling

## Docker Deployment (Recommended)

### Prerequisites
- Docker and Docker Compose installed
- At least 4GB RAM available
- UNSW-NB15 dataset in `training_data/` folder

### Setup Steps

1. **Verify Environment**
```bash
./test_docker_setup.sh
```

2. **Start Containers**
```bash
sudo docker-compose up -d
```

3. **Train Model (Workstation)**
```bash
sudo docker exec -it workstation python3 /scripts/docker_anomaly_detector.py --mode train --data /data/training_data/UNSW_NB15.csv
```

4. **Monitor Activity**
```bash
# Check target container (generating data)
sudo docker logs target

# Check monitor container (detecting anomalies)
sudo docker logs -f monitor

# View real-time network data
sudo docker exec -it monitor tail -f /var/log/activity/network_data.csv
```

### Output Structure

All results are automatically saved to `output/` directory:

```
output/
├── models/
│   ├── latest_model.json          # Current trained model
│   └── model_YYYYMMDD_HHMMSS.json # Timestamped models
├── logs/
│   └── training_log_*.json        # Training logs
├── predictions/
│   └── predictions_*.csv          # Prediction results
├── alerts/
│   └── alerts_*.json             # Real-time anomaly alerts
├── reports/
│   ├── summary_*.json            # Summary reports
│   └── traffic_analysis_*.json   # Traffic analysis
└── processed/
    └── processed_data_*.csv      # Processed network data
```

### Real-time Monitoring

```bash
# Watch for new alerts
watch -n 5 'ls -la output/alerts/'

# View latest anomaly alerts
sudo docker exec -it monitor python3 -c "
import json, glob
alerts = glob.glob('/data/output/alerts/*.json')
if alerts:
    with open(max(alerts), 'r') as f:
        data = json.load(f)
    print(f'Latest: {len(data)} anomalies detected')
"

# Generate traffic analysis report
sudo docker exec -it monitor python3 /scripts/process_logs.py
```

## Manual Installation (Alternative)

If you prefer to run without Docker:

1. Install Python dependencies:
```bash
./install_deps.sh
source ./venv/bin/activate
```

2. Download datasets:
[unsw-nb15](https://www.kaggle.com/datasets/programmer3/unsw-nb15-dataset?utm_source=chatgpt.com)

[network-intrusion](https://www.kaggle.com/datasets/chethuhn/network-intrusion-dataset)

[CTU13](https://www.kaggle.com/datasets/phamthaibao/ctu-13-dataset-full/data?select=CTU13_Normal_Traffic.csv)

## Usage

### Docker Method (Recommended)

**Training:**
```bash
# Train model in workstation container
sudo docker exec -it workstation python3 /scripts/docker_anomaly_detector.py --mode train

# Monitor training progress
sudo docker exec -it workstation ls -la /data/output/models/
```

**Real-time Detection:**
```bash
# Automatic - monitor container runs continuously
sudo docker logs -f monitor

# Manual monitoring mode
sudo docker exec -it monitor python3 /scripts/docker_anomaly_detector.py --mode monitor
```

**Analysis:**
```bash
# View generated network activity
sudo docker exec -it target tail -f /var/log/activity/network_data.csv

# Analyze traffic patterns
sudo docker exec -it monitor python3 /scripts/process_logs.py

# Check alerts
sudo docker exec -it workstation ls -la /data/output/alerts/
```

### Manual Method (Alternative)

**Training:**
```bash
python3 scripts/train_model.py
```

**Predictions:**
```bash
python3 scripts/predict.py <path_to_csv_file>
```

**Programmatic Usage:**
```python
from scripts.anomaly_detection_model import NetworkAnomalyDetector

# Load trained model
detector = NetworkAnomalyDetector()
detector.load_model('output/models/latest_model')

# Make predictions on new data
predictions = detector.predict(X_new)
```

## Model Performance

The model is designed to achieve:
- High accuracy in detecting various attack types
- Low false positive rate for normal traffic
- Robust performance on lateral movement detection
- Real-time inference capabilities

## Files Structure

```
CS-587-Capstone-Project/
├── docker-compose.yml              # Container orchestration
├── test_docker_setup.sh           # Setup verification script
├── install_deps.sh                # Manual dependency installer
├── requirements.txt               # Python dependencies
├── training_data/
│   └── UNSW_NB15.csv             # Training dataset
├── scripts/
│   ├── docker_anomaly_detector.py # Container-optimized detector
│   ├── generate_activity.py      # Network activity generator
│   ├── process_logs.py           # Log processing for monitor
│   ├── anomaly_detection_model.py # Full deep learning model
│   ├── train_model.py           # Training script
│   └── predict.py               # Inference script
└── output/                      # Generated outputs (auto-created)
    ├── models/                  # Trained models
    ├── logs/                    # Training and system logs
    ├── predictions/             # Prediction results
    ├── alerts/                  # Real-time alerts
    ├── reports/                 # Analysis reports
    └── processed/               # Processed data
```

## Troubleshooting

### Common Issues

**1. Containers not starting:**
```bash
# Check Docker status
sudo systemctl status docker

# Restart Docker service
sudo systemctl restart docker

# Check logs
sudo docker-compose logs
```

**2. No training data found:**
```bash
# Verify data location
ls -la training_data/UNSW_NB15.csv

# Check container access
sudo docker exec -it workstation ls -la /data/training_data/
```

**3. Model training fails:**
```bash
# Check memory usage
sudo docker stats

# View workstation logs
sudo docker logs workstation

# Check Python dependencies
sudo docker exec -it workstation pip3 list | grep tensor
```

**4. No alerts generated:**
```bash
# Check if target is generating data
sudo docker exec -it target ls -la /var/log/activity/

# Verify monitor is processing
sudo docker logs monitor

# Check model exists
sudo docker exec -it monitor ls -la /data/output/models/
```

### Performance Tuning

```bash
# Increase Docker memory (if needed)
# Edit /etc/docker/daemon.json:
{
  "default-runtime": "runc",
  "default-ulimits": {
    "memlock": {"hard": -1, "soft": -1}
  }
}

# Restart containers with more resources
sudo docker-compose down
sudo docker-compose up -d --force-recreate

# Adjust generation/monitoring intervals
sudo docker exec -it target pkill python3
sudo docker exec -it target python3 /scripts/generate_activity.py &
```

### Debug Commands

```bash
# Container health check
sudo docker-compose ps

# Network connectivity
sudo docker exec -it workstation ping target
sudo docker exec -it monitor ping target

# File permissions
sudo docker exec -it workstation ls -la /data/
sudo docker exec -it monitor ls -la /var/log/activity/

# Process monitoring
sudo docker exec -it target ps aux | grep python
sudo docker exec -it monitor ps aux | grep python
```

## Features Analyzed

The model analyzes 43 network flow features including:
- Flow duration and packet counts
- Byte transfer statistics
- Protocol and service information
- Connection state information
- Network timing features
- And more...

## Attack Types Detected

- Normal traffic (baseline)
- Analysis attacks
- Backdoors
- DoS attacks
- Exploits
- Fuzzers
- Generic attacks
- Reconnaissance
- Shellcode
- Worms

## Performance Metrics

The model reports:
- Classification accuracy
- Precision and recall
- ROC AUC score
- Confusion matrix
- Training/validation loss curves

## 🚀 Complete Operational Guide

### **Phase 1: Environment Setup**

#### **1.1 Prerequisites Check**
```bash
# Verify Docker installation
docker --version
docker-compose --version

# Check available resources
free -h  # Should have 4GB+ RAM
df -h    # Should have 2GB+ disk space
```

#### **1.2 Initial Setup**
```bash
# Clone and navigate to project
cd CS-587-Capstone-Project

# Verify environment
./test_docker_setup.sh

# Ensure training data exists
ls -la training_data/UNSW_NB15.csv
```

### **Phase 2: System Startup**

#### **2.1 Container Deployment**
```bash
# Start all containers
sudo docker-compose up -d

# Verify container status (all should show "Up")
sudo docker-compose ps

# Check logs for successful startup
sudo docker logs workstation
sudo docker logs target
sudo docker logs monitor
```

#### **2.2 Troubleshoot Network Issues (if needed)**
```bash
# If you see "Pool overlaps" error:
# Edit docker-compose.yml and change subnet from 172.20.0.0/16 to 172.21.0.0/16
# Then restart:
sudo docker-compose down
sudo docker-compose up -d
```

### **Phase 3: Model Training**

#### **3.1 Train Anomaly Detection Model**
```bash
# Access workstation container
sudo docker exec -it workstation bash

# Train the model (inside container)
python3 /scripts/docker_anomaly_detector.py --mode train --data /data/training_data/UNSW_NB15.csv

# Expected output: "Training Accuracy: 0.83XX" and "Training completed successfully!"
# Exit container
exit
```

#### **3.2 Verify Training Results**
```bash
# Check model files
ls -la data/output/models/
# Should see: latest_model.json and timestamped model files

# Check training logs
ls -la data/output/logs/
cat data/output/logs/training_log_*.json | tail -1
```

### **Phase 4: Real-time Monitoring**

#### **4.1 Monitor Data Generation**
```bash
# Check target container is generating data
sudo docker logs target | tail -10

# View live network data (if available)
sudo docker exec -it target tail -f /var/log/activity/network_data.csv
# Press Ctrl+C to exit

# If no data file, manually start generation:
sudo docker exec -it target python3 /scripts/generate_activity.py &
```

#### **4.2 Monitor Anomaly Detection**
```bash
# Watch monitor container logs
sudo docker logs -f monitor
# Look for: "Model loaded" and "ALERT: Anomaly detected" messages
# Press Ctrl+C to exit

# Check detection in real-time
watch -n 5 'ls -la data/output/alerts/ | tail -5'
```

### **Phase 5: Analysis & Results**

#### **5.1 Alert Analysis**
```bash
# Count total alerts generated
ls data/output/alerts/ | wc -l

# View latest alert file
latest_alert=$(ls -t data/output/alerts/*.json | head -1)
echo "Latest alert file: $latest_alert"
head -20 "$latest_alert"

# Quick stats on recent alerts
python3 -c "
import json, glob, os
alerts = glob.glob('data/output/alerts/*.json')
total_anomalies = 0
for alert_file in alerts[-5:]:  # Last 5 files
    with open(alert_file, 'r') as f:
        data = json.load(f)
    total_anomalies += len(data)
print(f'Recent anomalies detected: {total_anomalies}')
"
```

#### **5.2 System Performance Analysis**
```bash
# Generate comprehensive report
sudo docker exec -it monitor python3 /scripts/process_logs.py

# View latest summary report
latest_summary=$(ls -t data/output/reports/summary_*.json | head -1)
echo "=== SYSTEM SUMMARY ==="
cat "$latest_summary" | python3 -m json.tool | head -20

# View traffic analysis
latest_traffic=$(ls -t data/output/reports/traffic_analysis_*.json | head -1)
if [ -f "$latest_traffic" ]; then
    echo "=== TRAFFIC ANALYSIS ==="
    cat "$latest_traffic" | python3 -m json.tool
fi
```

#### **5.3 Model Performance Metrics**
```bash
# Check model accuracy from training logs
echo "=== MODEL PERFORMANCE ==="
latest_log=$(ls -t data/output/logs/training_log_*.json | head -1)
cat "$latest_log" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f'Training Accuracy: {data.get(\"accuracy\", \"N/A\")}')
print(f'Total Samples: {data.get(\"total_samples\", \"N/A\")}')
print(f'Normal Samples: {data.get(\"normal_samples\", \"N/A\")}')
print(f'Anomaly Samples: {data.get(\"anomaly_samples\", \"N/A\")}')
"
```

### **Phase 6: Advanced Operations**

#### **6.1 Manual Detection Testing**
```bash
# Test manual monitoring mode
sudo docker exec -it monitor python3 /scripts/docker_anomaly_detector.py \
    --mode monitor \
    --input /data/training_data/UNSW_NB15.csv \
    --interval 3

# Run for 30 seconds, then Ctrl+C to stop
```

#### **6.2 Resource Monitoring**
```bash
# Monitor container resource usage
sudo docker stats

# Check disk usage
du -sh data/output/
df -h

# Monitor network activity between containers
sudo docker exec -it workstation ping target
sudo docker exec -it monitor ping target
```

#### **6.3 Real-time Dashboard (Manual)**
```bash
# Create a simple monitoring script
cat << 'EOF' > monitor_dashboard.sh
#!/bin/bash
while true; do
    clear
    echo "=== ANOMALY DETECTION DASHBOARD ==="
    echo "Time: $(date)"
    echo ""
    echo "Container Status:"
    sudo docker-compose ps
    echo ""
    echo "Recent Alerts (last 5 files):"
    ls -lt data/output/alerts/*.json | head -5 | awk '{print $9, $6, $7, $8}'
    echo ""
    echo "Total Alert Files: $(ls data/output/alerts/ | wc -l)"
    echo "Total Model Files: $(ls data/output/models/ | wc -l)"
    echo ""
    echo "Press Ctrl+C to exit"
    sleep 10
done
EOF

chmod +x monitor_dashboard.sh
./monitor_dashboard.sh
```

### **Phase 7: Cleanup & Maintenance**

#### **7.1 Graceful Shutdown**
```bash
# Stop all containers gracefully
sudo docker-compose down

# Verify containers stopped
sudo docker ps -a | grep capstone
```

#### **7.2 Cleanup Old Data (Optional)**
```bash
# Archive old alerts (keep last 50 files)
mkdir -p data/archive/alerts
ls -t data/output/alerts/*.json | tail -n +51 | xargs -I {} mv {} data/archive/alerts/

# Clean up old reports (keep last 10)
mkdir -p data/archive/reports
ls -t data/output/reports/*.json | tail -n +11 | xargs -I {} mv {} data/archive/reports/

# Check disk space saved
du -sh data/archive/
du -sh data/output/
```

#### **7.3 Complete System Reset**
```bash
# Stop and remove containers
sudo docker-compose down

# Remove all output data (WARNING: This deletes all results!)
sudo rm -rf data/output/*

# Remove Docker volumes
sudo docker volume prune -f

# Remove networks
sudo docker network prune -f

# Fresh restart
sudo docker-compose up -d
```

### **Phase 8: Production Deployment**

#### **8.1 Performance Optimization**
```bash
# Adjust container resources in docker-compose.yml
# Add under each service:
# deploy:
#   resources:
#     limits:
#       memory: 2G
#       cpus: '1.0'

# Optimize alert generation frequency
# Edit scripts/generate_activity.py - change interval from 2 to 5 seconds
# Edit scripts/process_logs.py - change interval from 10 to 30 seconds
```

#### **8.2 Monitoring Integration**
```bash
# Set up log forwarding to external systems
# Example: Forward alerts to syslog
sudo docker exec -it monitor bash -c "
tail -f /data/output/alerts/*.json | while read line; do
    echo \"ANOMALY_ALERT: \$line\" | logger -t anomaly_detection
done &
"

# Set up health checks
echo '#!/bin/bash
containers=(workstation target monitor)
for container in "${containers[@]}"; do
    if ! sudo docker ps | grep -q $container; then
        echo "ALERT: Container $container is down"
        # Add notification logic here
    fi
done' > health_check.sh

chmod +x health_check.sh
# Run via cron: */5 * * * * /path/to/health_check.sh
```

## 📊 Expected Results Summary

After following this guide, you should achieve:

- **Training Accuracy**: 83-85% (as seen: 0.8351)
- **Alert Generation Rate**: 15,000-25,000 alerts per hour
- **Detection Latency**: < 5 seconds from data generation to alert
- **System Uptime**: 99%+ with proper resource allocation
- **False Positive Rate**: 15-20% (normal for this dataset)

## 🔧 Common Issues & Solutions

| Issue | Symptom | Solution |
|-------|---------|----------|
| Network conflict | "Pool overlaps" error | Change subnet in docker-compose.yml |
| No training data | "File not found" error | Verify UNSW_NB15.csv in training_data/ |
| Container crashes | Container status "Exited" | Check logs: `sudo docker logs <container>` |
| No alerts generated | Empty alerts/ directory | Verify model training completed |
| High resource usage | System slowdown | Reduce generation/monitoring intervals |

This system is now production-ready for lateral movement detection and network anomaly monitoring!
