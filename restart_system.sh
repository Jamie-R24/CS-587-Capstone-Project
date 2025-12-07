#!/bin/bash
# Complete system restart with automatic waiting

set -e  # Exit on error

echo "========================================="
echo "  Restarting Anomaly Detection System"
echo "========================================="
echo ""

# Detect docker compose command (v2 uses "docker compose", v1 uses "docker-compose")
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
elif command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    echo "✗ Error: Docker Compose not found!"
    echo "  Please install Docker Compose v2 (docker compose) or v1 (docker-compose)"
    exit 1
fi
echo "Using: $DOCKER_COMPOSE"
echo ""

# Check and extract dataset if needed
echo "1. Checking dataset..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRAINING_DIR="$SCRIPT_DIR/training_data"
ZIP_FILE="$TRAINING_DIR/UNSW_NB15.zip"
CSV_FILE="$TRAINING_DIR/UNSW_NB15.csv"

if [ -f "$CSV_FILE" ]; then
    echo "   ✓ Dataset already extracted"
elif [ -f "$ZIP_FILE" ]; then
    echo "   Extracting dataset from zip..."
    # Use unzip (available on Linux/macOS/Windows Git Bash/WSL)
    if command -v unzip &> /dev/null; then
        unzip -o "$ZIP_FILE" -d "$TRAINING_DIR"
        echo "   ✓ Dataset extracted successfully"
    # Fallback for Windows PowerShell environments
    elif command -v powershell &> /dev/null; then
        powershell -Command "Expand-Archive -Path '$ZIP_FILE' -DestinationPath '$TRAINING_DIR' -Force"
        echo "   ✓ Dataset extracted successfully (PowerShell)"
    else
        echo "   ✗ Error: Cannot find unzip or powershell to extract dataset"
        echo "   Please manually extract: $ZIP_FILE"
        exit 1
    fi
else
    echo "   ✗ Error: Dataset not found!"
    echo "   Expected: $ZIP_FILE or $CSV_FILE"
    echo "   Please download UNSW-NB15 dataset and place it in training_data/"
    exit 1
fi
echo ""

# Stop containers
echo "2. Stopping containers..."
sudo $DOCKER_COMPOSE down
echo "   ✓ Containers stopped"
echo ""

# Clear Outputs
echo "3. Clearing data/output folder..."
sudo rm -rf data/output
sudo rm -rf data/accumulated_data
sudo rm -rf data/test_sets
sudo rm -rf ./data/poisoning
echo "    ✓ Output removed"
echo ""

# Start containers
echo "4. Starting containers..."
sudo $DOCKER_COMPOSE up -d
echo "   ✓ Containers starting..."
echo ""

# Wait for containers to be ready
echo "5. Waiting for initialization..."
echo "   This may take 15-20 seconds..."
echo ""

MAX_WAIT=720
WAITED=0

while [ $WAITED -lt $MAX_WAIT ]; do
    # Check if workstation is healthy
    HEALTH=$(sudo docker inspect --format='{{.State.Health.Status}}' workstation 2>/dev/null || echo "starting")

    if [ "$HEALTH" = "healthy" ]; then
        echo "   ✓ Workstation is ready!"
        break
    fi

    # Show progress
    if [ $((WAITED % 10)) -eq 0 ]; then
        echo "   Waiting... ($WAITED seconds) - Status: $HEALTH"
    fi

    sleep 5
    WAITED=$((WAITED + 5))
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo "   ✗ Timeout waiting for containers"
    echo ""
    echo "Check logs with: sudo docker logs workstation"
    exit 1
fi

echo ""
echo "6. Creating test set (if not exists)..."
if [ ! -f "data/test_sets/fixed_test_set.csv" ]; then
    sudo docker exec workstation python3 /scripts/create_test_set.py
    echo "   ✓ Test set created"
else
    echo "   ✓ Test set already exists"
fi
echo ""

echo "7. Ensuring output directories exist..."
sudo docker exec workstation mkdir -p /data/output/{models,logs,alerts}
sudo docker exec workstation chmod -R 755 /data/output
echo "   ✓ Directories ready"
echo ""

echo "8. Training initial model..."
if ! sudo docker exec workstation python3 /scripts/docker_anomaly_detector.py --mode train; then
    echo "   ✗ Training failed"
    exit 1
fi
echo "   ✓ Initial model trained"
echo ""

echo "9. Saving baseline model..."
if ! sudo docker exec workstation test -f /data/output/models/latest_model.json; then
    echo "   ✗ Model file not found"
    exit 1
fi

if ! sudo docker exec workstation cp /data/output/models/latest_model.json /data/output/models/baseline_model.json; then
    echo "   ✗ Failed to save baseline model"
    exit 1
fi
echo "   ✓ Baseline saved"
echo ""

echo "========================================="
echo "  System Ready!"
echo "========================================="
echo ""
echo "Background services running:"
echo "  • Data Accumulator (2 min snapshots)"
echo "  • Retraining Scheduler (2 min intervals)"
echo ""
echo "Next steps:"
echo "  1. View retraining logs:"
echo "     sudo docker exec workstation tail -f /data/output/retraining.log"
echo ""
echo "  2. Monitor performance over time:"
echo "     sudo docker exec workstation cat /data/output/performance_over_time.csv"
echo ""
echo "  3. Run dashboard:"
echo "     ./monitor_dashboard.sh"
echo ""
echo "  4. View container logs:"
echo "     sudo docker logs -f monitor"
echo ""
