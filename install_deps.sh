#!/bin/bash
# Installation script for anomaly detection dependencies

echo "Setting up Python environment for anomaly detection..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip and tools
echo "Upgrading pip and build tools..."
pip install --upgrade pip setuptools wheel

# Try to install packages one by one with fallback versions
echo "Installing dependencies..."

# Install numpy first (required by others)
pip install "numpy>=1.21.0" || pip install "numpy==1.21.6"

# Install pandas
pip install "pandas>=1.3.0" || pip install "pandas==1.5.3"

# Install scikit-learn
pip install "scikit-learn>=1.1.0" || pip install "scikit-learn==1.2.2"

# Install matplotlib
pip install "matplotlib>=3.5.0" || pip install "matplotlib==3.6.3"

# Install seaborn
pip install "seaborn>=0.11.0" || pip install "seaborn==0.12.2"

# Install joblib
pip install "joblib>=1.1.0" || pip install "joblib==1.2.0"

# Try TensorFlow (might need specific version for your system)
echo "Installing TensorFlow..."
pip install "tensorflow>=2.10.0" || pip install "tensorflow-cpu>=2.10.0" || echo "TensorFlow installation failed - you can try installing it manually"

echo "Installation complete!"
echo ""
echo "To activate the environment in the future, run:"
echo "source venv/bin/activate"
echo ""
echo "To test the installation, run:"
echo "python3 -c 'import pandas, numpy, sklearn; print(\"Dependencies installed successfully!\")'"