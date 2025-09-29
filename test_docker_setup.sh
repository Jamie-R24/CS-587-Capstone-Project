#!/bin/bash
# Test script for Docker anomaly detection setup

echo "Testing Docker Anomaly Detection Setup"
echo "====================================="

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose not found. Please install Docker Compose."
    exit 1
fi

echo "✅ Docker Compose found"

# Check if required directories exist
echo "📁 Checking directory structure..."
for dir in "data" "scripts" "training_data" "output"; do
    if [ -d "$dir" ]; then
        echo "  ✅ $dir/ exists"
    else
        echo "  ⚠️  $dir/ missing - creating..."
        mkdir -p "$dir"
    fi
done

# Check if training data exists
if [ -f "training_data/UNSW_NB15.csv" ]; then
    echo "✅ Training data found"
else
    echo "⚠️  Training data missing at training_data/UNSW_NB15.csv"
fi

# Check if scripts exist
echo "📜 Checking required scripts..."
for script in "docker_anomaly_detector.py" "generate_activity.py" "process_logs.py"; do
    if [ -f "scripts/$script" ]; then
        echo "  ✅ scripts/$script exists"
    else
        echo "  ❌ scripts/$script missing"
    fi
done

echo ""
echo "🚀 Ready to start Docker environment!"
echo ""
echo "Next steps:"
echo "1. Start containers: docker-compose up -d"
echo "2. Check status: docker-compose ps"
echo "3. Train model: docker exec -it workstation python3 /scripts/docker_anomaly_detector.py --mode train"
echo "4. Monitor logs: docker logs -f monitor"
echo ""
echo "For detailed instructions, see DOCKER_DEPLOYMENT.md"