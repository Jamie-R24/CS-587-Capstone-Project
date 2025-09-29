#!/usr/bin/env python3
"""
Deep Learning Model for Network Anomaly Detection
Using UNSW-NB15 dataset to detect lateral movement and network anomalies
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout, BatchNormalization
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
import os
from datetime import datetime

class NetworkAnomalyDetector:
    def __init__(self, output_dir='../output'):
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoders = {}
        self.feature_names = []
        self.output_dir = output_dir
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Create output directories
        os.makedirs(os.path.join(output_dir, 'models'), exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'plots'), exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'logs'), exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'predictions'), exist_ok=True)

    def preprocess_data(self, data_path):
        """Load and preprocess the UNSW-NB15 dataset"""
        print("Loading dataset...")
        df = pd.read_csv(data_path)

        print(f"Dataset shape: {df.shape}")
        print(f"Class distribution:\n{df['label'].value_counts()}")

        # Separate features and target
        X = df.drop(['label', 'attack_cat'], axis=1)
        y = df['label']

        # Handle categorical features
        categorical_cols = X.select_dtypes(include=['object']).columns
        print(f"Categorical columns: {list(categorical_cols)}")

        # Encode categorical variables
        for col in categorical_cols:
            if col in X.columns:
                le = LabelEncoder()
                X[col] = le.fit_transform(X[col].astype(str))
                self.label_encoders[col] = le

        # Handle missing values
        X = X.fillna(X.median())

        self.feature_names = X.columns.tolist()
        print(f"Number of features after preprocessing: {len(self.feature_names)}")

        return X, y

    def build_model(self, input_dim):
        """Build deep neural network for anomaly detection"""
        model = Sequential([
            # Input layer with batch normalization
            Dense(128, activation='relu', input_shape=(input_dim,)),
            BatchNormalization(),
            Dropout(0.3),

            # Hidden layers
            Dense(64, activation='relu'),
            BatchNormalization(),
            Dropout(0.3),

            Dense(32, activation='relu'),
            BatchNormalization(),
            Dropout(0.2),

            Dense(16, activation='relu'),
            Dropout(0.2),

            # Output layer for binary classification
            Dense(1, activation='sigmoid')
        ])

        # Compile model
        model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss='binary_crossentropy',
            metrics=['accuracy', 'precision', 'recall']
        )

        return model

    def train(self, data_path, test_size=0.2, validation_split=0.2, epochs=100):
        """Train the anomaly detection model"""
        # Load and preprocess data
        X, y = self.preprocess_data(data_path)

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )

        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Build model
        self.model = self.build_model(X_train_scaled.shape[1])

        print("Model Architecture:")
        self.model.summary()

        # Define callbacks
        early_stopping = EarlyStopping(
            monitor='val_loss',
            patience=15,
            restore_best_weights=True
        )

        reduce_lr = ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=10,
            min_lr=0.0001
        )

        # Train model
        print("Training model...")
        history = self.model.fit(
            X_train_scaled, y_train,
            epochs=epochs,
            batch_size=32,
            validation_split=validation_split,
            callbacks=[early_stopping, reduce_lr],
            verbose=1
        )

        # Evaluate model
        print("Evaluating model...")
        y_pred_proba = self.model.predict(X_test_scaled)
        y_pred = (y_pred_proba > 0.5).astype(int)

        # Print evaluation metrics
        print("\nClassification Report:")
        print(classification_report(y_test, y_pred))

        print(f"\nROC AUC Score: {roc_auc_score(y_test, y_pred_proba):.4f}")

        # Plot training history
        self.plot_training_history(history)

        # Plot confusion matrix
        self.plot_confusion_matrix(y_test, y_pred)

        return history, X_test_scaled, y_test, y_pred_proba

    def plot_training_history(self, history):
        """Plot training history"""
        plt.figure(figsize=(12, 4))

        plt.subplot(1, 2, 1)
        plt.plot(history.history['loss'], label='Training Loss')
        plt.plot(history.history['val_loss'], label='Validation Loss')
        plt.title('Model Loss')
        plt.xlabel('Epoch')
        plt.ylabel('Loss')
        plt.legend()

        plt.subplot(1, 2, 2)
        plt.plot(history.history['accuracy'], label='Training Accuracy')
        plt.plot(history.history['val_accuracy'], label='Validation Accuracy')
        plt.title('Model Accuracy')
        plt.xlabel('Epoch')
        plt.ylabel('Accuracy')
        plt.legend()

        plt.tight_layout()
        plot_path = os.path.join(self.output_dir, 'plots', f'training_history_{self.timestamp}.png')
        plt.savefig(plot_path)
        print(f"Training history plot saved to: {plot_path}")
        plt.close()

    def plot_confusion_matrix(self, y_true, y_pred):
        """Plot confusion matrix"""
        cm = confusion_matrix(y_true, y_pred)
        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                   xticklabels=['Normal', 'Anomaly'],
                   yticklabels=['Normal', 'Anomaly'])
        plt.title('Confusion Matrix')
        plt.ylabel('Actual')
        plt.xlabel('Predicted')
        plot_path = os.path.join(self.output_dir, 'plots', f'confusion_matrix_{self.timestamp}.png')
        plt.savefig(plot_path)
        print(f"Confusion matrix plot saved to: {plot_path}")
        plt.close()

    def predict(self, X):
        """Make predictions on new data"""
        if self.model is None:
            raise ValueError("Model not trained yet!")

        X_scaled = self.scaler.transform(X)
        predictions = self.model.predict(X_scaled)
        return predictions

    def save_model(self, model_name='anomaly_detection_model'):
        """Save the trained model and preprocessors"""
        if self.model is None:
            raise ValueError("No model to save!")

        model_path = os.path.join(self.output_dir, 'models', f'{model_name}_{self.timestamp}')

        # Save model
        self.model.save(f'{model_path}.h5')

        # Save scaler and label encoders
        joblib.dump(self.scaler, f'{model_path}_scaler.pkl')
        joblib.dump(self.label_encoders, f'{model_path}_encoders.pkl')
        joblib.dump(self.feature_names, f'{model_path}_features.pkl')

        print(f"Model saved to: {model_path}.h5")
        return model_path

    def load_model(self, model_path):
        """Load a trained model"""
        if not model_path.endswith('.h5'):
            model_path = f'{model_path}.h5'

        base_path = model_path.replace('.h5', '')

        self.model = tf.keras.models.load_model(model_path)
        self.scaler = joblib.load(f'{base_path}_scaler.pkl')
        self.label_encoders = joblib.load(f'{base_path}_encoders.pkl')
        self.feature_names = joblib.load(f'{base_path}_features.pkl')

        print(f"Model loaded from {model_path}")

def main():
    """Main training script"""
    # Initialize detector
    detector = NetworkAnomalyDetector()

    # Train model
    history, X_test, y_test, y_pred_proba = detector.train(
        'training_data/UNSW_NB15.csv',
        epochs=50
    )

    # Save model
    detector.save_model('network_anomaly_detector')

    print("Training completed successfully!")

if __name__ == "__main__":
    main()