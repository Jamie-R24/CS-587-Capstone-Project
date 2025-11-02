# Network Anomaly Detection System

**CS-587 Cybersecurity Capstone Project**

## Project Overview

This project implements a containerized network anomaly detection system designed to identify lateral movement and other cybersecurity threats in real-time. The system uses statistical analysis and machine learning techniques to detect anomalous network behavior patterns.

## High-Level Architecture

The system operates across three specialized Docker containers working in concert:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   WORKSTATION   │    │     TARGET      │    │    MONITOR      │
│                 │    │                 │    │                 │
│ • Model         │    │ • Synthetic     │    │ • Real-time     │
│   Training      │    │   Traffic       │    │   Detection     │
│ • Development   │    │   Generation    │    │ • Alert         │
│ • Analysis      │    │ • Simulates     │    │   Generation    │
│                 │    │   Attacks       │    │ • Reporting     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┴───────────────────────┘
                                 │
                    ┌─────────────────────┐
                    │   SHARED STORAGE    │
                    │                     │
                    │ • Models            │
                    │ • Logs              │
                    │ • Alerts            │
                    │ • Network Data      │
                    └─────────────────────┘
```

### Container Roles

- **Workstation**: Model training and development environment
- **Target**: Generates synthetic network traffic (normal + anomalous)
- **Monitor**: Real-time anomaly detection and alerting

## Tools & Technologies

### Core Technologies
- **Docker & Docker Compose**: Containerization and orchestration
- **Python 3**: Primary programming language
- **Statistical Analysis**: Z-score based anomaly detection

### Python Libraries
- **pandas**: Data manipulation and analysis
- **numpy**: Numerical computing
- **scikit-learn**: Machine learning utilities (optional)
- **faker**: Synthetic data generation

### Dataset
- **UNSW-NB15**: Network intrusion detection dataset
  - 7,465 network flow samples
  - 43 network features
  - Multiple attack categories (Backdoors, Reconnaissance, Generic, etc.)

## Detection Methodology

### Statistical Anomaly Detection
The system uses a **Z-score based approach**:

1. **Training Phase**: Calculate mean and standard deviation of each feature from normal traffic
2. **Detection Phase**: Compare new traffic against learned statistics
3. **Alerting**: Generate alerts when confidence exceeds threshold

### Key Parameters
- **Z-Score Threshold**: 1.4 standard deviations
- **Detection Threshold**: 10% of features must be anomalous
- **Confidence Threshold**: 40% minimum for alert generation

### Detected Attack Types
- **Lateral Movement** (Backdoors): High connection counts, large data transfers
- **Reconnaissance**: Port scanning, service enumeration
- **Data Exfiltration** (Generic): Large outbound data volumes

## Traffic Generation

The target container continuously generates synthetic network traffic:

- **Generation Rate**: 100 flows every 10 seconds (~600 flows/minute)
- **Traffic Ratio**: 30% normal, 70% anomalous
- **Attack Simulation**: Realistic attack patterns based on known TTPs
- **Poisoning Support**: Optional label flipping for data poisoning attacks (see [POISONING_GUIDE.md](POISONING_GUIDE.md))

## Performance Metrics

### Current Model Performance
- **Accuracy**: ~83%
- **Precision**: ~90%
- **Recall**: ~90%
- **F1-Score**: ~90%
- **Detection Coverage**: 90%+ of anomalies identified

### Alert Generation
- **Alert Rate**: 10-20% of traffic generates high-confidence alerts
- **Detection Latency**: <5 seconds from generation to alert
- **False Positive Rate**: ~10-15%

## Project Structure

```
CS-587-Capstone-Project/
├── README.md                      # Project overview (this file)
├── ENV_LAUNCH.md                  # Docker environment guide
├── docker-compose.yml             # Container orchestration
├── monitor_dashboard.sh           # Real-time monitoring dashboard
├── restart_system.sh              # System restart script
├── training_data/
│   └── UNSW_NB15.csv             # Training dataset
├── scripts/
│   ├── docker_anomaly_detector.py # Statistical anomaly detector
│   ├── generate_activity.py       # Synthetic traffic generator
│   └── process_logs.py            # Log processing and reporting
└── data/
    └── output/                    # Generated outputs
        ├── models/                # Trained models
        ├── logs/                  # Training logs
        ├── alerts/                # Real-time alerts
        └── reports/               # Analysis reports
```

## Key Features

✅ **Containerized Architecture**: Isolated, reproducible environment
✅ **Real-time Detection**: Continuous monitoring and alerting
✅ **Synthetic Traffic**: Realistic attack simulation for testing
✅ **Automatic Retraining**: Periodic model updates with accumulated data
✅ **Data Poisoning Research**: Built-in support for label flipping attacks
✅ **Comprehensive Logging**: Detailed logs and performance metrics
✅ **Flexible Configuration**: Tunable thresholds and parameters
✅ **Attack Categorization**: Identifies specific attack types
✅ **Performance Tracking**: Metrics over time with fixed test sets

## Getting Started

For detailed setup, configuration, and operational instructions, see:

**→ [LAUNCH_GUIDE.md](LAUNCH_GUIDE.md)** - Complete Docker environment guide
**→ [POISONING_GUIDE.md](POISONING_GUIDE.md)** - Data poisoning attack documentation

### Quick Start

```bash
# 1. First time setup: Extract the dataset
unzip training_data/UNSW_NB15.zip -d training_data/

# 2. Start the system (handles all initialization automatically)
./restart_system.sh

# 3. Wait for initialization (~15-20 seconds)
# System automatically creates test set, trains model, and starts services

# 4. Monitor the system
./monitor_dashboard.sh

# 5. (Optional) Enable data poisoning
# Edit data/poisoning/poisoning_config.json and set "enabled": true
# See POISONING_GUIDE.md for details

# 6. (Optional) Analyze poisoning results
# ./analyze_poisoning.sh
```

## Use Cases

- **Security Research**: Study network attack patterns and data poisoning attacks
- **Education**: Learn anomaly detection and adversarial ML techniques
- **Testing**: Evaluate detection algorithms under normal and poisoned conditions
- **Development**: Build and test security tools with automatic retraining
- **Adversarial ML**: Demonstrate impact of data poisoning on ML models

## Future Enhancements

- Deep learning models (LSTM, CNN)
- Additional attack categories
- Integration with SIEM systems
- Enhanced visualization dashboard
- Distributed deployment support

## License

Academic project for CS-587 Cybersecurity Capstone

## Author

Created as part of CS-587 Capstone Project