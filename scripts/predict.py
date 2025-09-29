#!/usr/bin/env python3
"""
Inference script for network anomaly detection
"""

import pandas as pd
import numpy as np

try:
    from anomaly_detection_model import NetworkAnomalyDetector

    def predict_from_csv(csv_path, model_path=None):
        """Load data from CSV and make predictions"""
        # Load the trained model
        detector = NetworkAnomalyDetector(output_dir='../output')

        # If no model path specified, find the latest model
        if model_path is None:
            import os
            models_dir = '../output/models'
            model_files = [f for f in os.listdir(models_dir) if f.endswith('.h5')]
            if not model_files:
                raise FileNotFoundError("No trained models found in output/models/")
            latest_model = max(model_files, key=lambda x: os.path.getctime(os.path.join(models_dir, x)))
            model_path = os.path.join(models_dir, latest_model)
            print(f"Using latest model: {model_path}")

        detector.load_model(model_path)

        # Load and preprocess data
        df = pd.read_csv(csv_path)

        # Remove labels if present
        if 'label' in df.columns:
            df = df.drop(['label'], axis=1)
        if 'attack_cat' in df.columns:
            df = df.drop(['attack_cat'], axis=1)

        # Handle categorical features
        categorical_cols = df.select_dtypes(include=['object']).columns
        for col in categorical_cols:
            if col in detector.label_encoders:
                df[col] = detector.label_encoders[col].transform(df[col].astype(str))

        # Handle missing values
        df = df.fillna(df.median())

        # Make predictions
        predictions = detector.predict(df)

        # Convert to binary predictions
        binary_predictions = (predictions > 0.5).astype(int).flatten()

        # Display results
        print(f"Total samples: {len(predictions)}")
        print(f"Anomalies detected: {sum(binary_predictions)}")
        print(f"Normal traffic: {len(predictions) - sum(binary_predictions)}")
        print(f"Anomaly rate: {sum(binary_predictions)/len(predictions)*100:.2f}%")

        # Save predictions to output folder
        import os
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        pred_path = os.path.join('../output/predictions', f'predictions_{timestamp}.csv')

        # Create results DataFrame
        results_df = pd.DataFrame({
            'anomaly_probability': predictions.flatten(),
            'binary_prediction': binary_predictions,
            'prediction_label': ['ANOMALY' if x else 'NORMAL' for x in binary_predictions]
        })
        results_df.to_csv(pred_path, index=False)
        print(f"Predictions saved to: {pred_path}")

        return predictions, binary_predictions

    def predict_single_sample(features, model_path='network_anomaly_detector'):
        """Make prediction on a single sample"""
        detector = NetworkAnomalyDetector()
        detector.load_model(model_path)

        # Convert to DataFrame
        df = pd.DataFrame([features], columns=detector.feature_names)

        # Make prediction
        prediction = detector.predict(df)
        binary_pred = (prediction > 0.5).astype(int)[0][0]

        print(f"Anomaly probability: {prediction[0][0]:.4f}")
        print(f"Prediction: {'ANOMALY' if binary_pred else 'NORMAL'}")

        return prediction[0][0], binary_pred

    if __name__ == "__main__":
        import sys

        if len(sys.argv) < 2:
            print("Usage: python predict.py <csv_file>")
            sys.exit(1)

        csv_file = sys.argv[1]
        predictions, binary_predictions = predict_from_csv(csv_file)

except ImportError as e:
    print(f"Missing required dependencies: {e}")
    print("\nPlease install the required packages:")
    print("pip install -r requirements.txt")