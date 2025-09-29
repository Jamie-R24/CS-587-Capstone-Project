# CS-587-Capstone-Project
Repository for CS 587 Cyber Security Capstone experience

Only thing I got is three docker containers. You can startup with this command:

```
sudo docker-compose up -d
```

You can access the shell for a container with this command:

```
sudo docker exec -it <container-name> bash
```

## Anomaly Detection Model

# Network Anomaly Detection for Lateral Movement

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

## Installation

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

### Training the Model

To train the anomaly detection model:

```bash
python3 train_model.py
```

This will:
- Load and preprocess the UNSW-NB15 dataset
- Split data into training/validation/test sets
- Train the deep learning model
- Evaluate performance metrics
- Save the trained model as `network_anomaly_detector.h5`

### Making Predictions

To detect anomalies in new network data:

```bash
python3 predict.py <path_to_csv_file>
```

### Using the Model Programmatically

```python
from anomaly_detection_model import NetworkAnomalyDetector

# Load trained model
detector = NetworkAnomalyDetector()
detector.load_model('network_anomaly_detector')

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

- `anomaly_detection_model.py`: Main model implementation
- `train_model.py`: Training script
- `predict.py`: Inference script
- `requirements.txt`: Python dependencies
- `training_data/UNSW_NB15.csv`: Training dataset
- `network_anomaly_detector.h5`: Trained model (generated after training)

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
