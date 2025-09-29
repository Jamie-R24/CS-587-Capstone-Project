#!/usr/bin/env python3
"""
Training script for the anomaly detection model
"""

try:
    from anomaly_detection_model import NetworkAnomalyDetector

    def main():
        print("Starting Network Anomaly Detection Model Training")
        print("=" * 50)

        # Initialize the detector with output directory
        detector = NetworkAnomalyDetector(output_dir='../output')

        # Train the model
        print("Training model on UNSW-NB15 dataset...")
        history, X_test, y_test, y_pred_proba = detector.train(
            '../training_data/UNSW_NB15.csv',
            epochs=50,
            test_size=0.2,
            validation_split=0.2
        )

        # Save the trained model
        model_path = detector.save_model('network_anomaly_detector')

        # Save training log
        import os
        log_path = os.path.join('../output/logs', f'training_log_{detector.timestamp}.txt')
        with open(log_path, 'w') as f:
            f.write("Network Anomaly Detection Training Log\n")
            f.write("=" * 40 + "\n")
            f.write(f"Training completed at: {detector.timestamp}\n")
            f.write(f"Model saved to: {model_path}.h5\n")
            f.write(f"Dataset: ../training_data/UNSW_NB15.csv\n")
            f.write(f"Epochs: 50\n")
            f.write(f"Test size: 0.2\n")
            f.write(f"Validation split: 0.2\n")

        print("\n" + "=" * 50)
        print("Training completed successfully!")
        print(f"Model saved to: {model_path}.h5")
        print(f"Training log saved to: {log_path}")
        print("All outputs saved to the output/ folder structure.")

    if __name__ == "__main__":
        main()

except ImportError as e:
    print(f"Missing required dependencies: {e}")
    print("\nPlease install the required packages:")
    print("pip install -r requirements.txt")
    print("\nOr if you don't have pip, try:")
    print("apt-get install python3-pip")
    print("pip install tensorflow pandas scikit-learn matplotlib seaborn")