#!/bin/bash
# Complete system restart with automatic waiting

set -e  # Exit on error

echo "========================================="
echo "  Restarting Anomaly Detection System"
echo "========================================="
echo ""

# Stop containers
echo "1. Stopping containers..."
sudo docker-compose down
echo "   ✓ Containers stopped"
echo ""

# Clear Outputs
echo "1.5 Clearing data/output folder..."
sudo rm -rf data/output
echo "    ✓ Output removed"
echo ""

# Start containers
echo "2. Starting containers..."
sudo docker-compose up -d
echo "   ✓ Containers starting..."
echo ""

# Wait for containers to be ready
echo "3. Waiting for initialization..."
echo "   This may take 60-90 seconds..."
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
echo "========================================="
echo "  System Ready!"
echo "========================================="
echo ""
echo "Next steps:"
echo "  1. Train model:"
echo "     sudo docker exec -it workstation python3 /scripts/docker_anomaly_detector.py --mode train"
echo ""
echo "  2. View logs:"
echo "     sudo docker logs -f monitor"
echo ""
echo "  3. Run dashboard:"
echo "     ./monitor_dashboard.sh"
echo ""
