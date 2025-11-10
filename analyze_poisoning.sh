#!/bin/bash
# Analyze Poisoning Attack Results
# Stops the system and generates comprehensive performance analysis

set -e  # Exit on error

echo "========================================="
echo "  Poisoning Attack Analysis"
echo "========================================="
echo ""

# Stop containers to freeze data generation
echo "1. Stopping containers..."
echo "   (This prevents new data from being generated during analysis)"
sudo docker-compose stop
echo "   ✓ Containers stopped"
echo ""

# Wait a moment for containers to fully stop
sleep 2

# Check if performance data exists
if [ ! -f "./data/output/performance_over_time.csv" ]; then
    echo "✗ Error: No performance data found!"
    echo "   File not found: ./data/output/performance_over_time.csv"
    echo ""
    echo "Please run the system first to generate performance data."
    exit 1
fi

echo "2. Running analysis..."
echo ""

# Run Python visualization script
sudo python3 scripts/visualize_poisoning.py

echo ""
echo "========================================="
echo "  Analysis Complete"
echo "========================================="
echo ""

# Optionally display additional summaries
echo "Additional Information:"
echo ""

echo "3. Test Set Status:"
if [ -f "./data/test_sets/synthetic_test_set_created.flag" ]; then
    echo "   ✓ Fixed test set is active"
    cat ./data/test_sets/synthetic_test_set_created.flag | head -2 | sed 's/^/   /'
else
    echo "   ✗ No fixed test set created"
fi
echo ""

echo "4. Poisoning Status:"
if [ -f "./data/poisoning/poisoning_state.json" ]; then
    echo "   Current state:"
    cat ./data/poisoning/poisoning_state.json | grep -E "is_active|current_retraining_cycle|total_poisoned" | sed 's/^/   /'
else
    echo "   ✗ No poisoning state found"
fi
echo ""

echo "5. Data Summary:"
SNAPSHOT_COUNT=$(ls ./data/accumulated_data/snapshot_*.csv 2>/dev/null | wc -l)
TOTAL_LINES=$(wc -l ./data/accumulated_data/snapshot_*.csv 2>/dev/null | tail -1 | awk '{print $1}')
RETRAIN_COUNT=$(ls ./data/output/retraining_logs/retrain_*.json 2>/dev/null | wc -l)

echo "   Snapshots: $SNAPSHOT_COUNT"
echo "   Total synthetic samples: $TOTAL_LINES"
echo "   Retraining cycles: $RETRAIN_COUNT"
echo ""

echo "========================================="
echo "  Next Steps"
echo "========================================="
echo ""
echo "To resume the system:"
echo "  sudo docker-compose start"
echo ""
echo "To view performance CSV:"
echo "  column -t -s',' ./data/output/performance_over_time.csv"
echo ""
echo "To view detailed logs:"
echo "  sudo docker logs workstation"
echo ""
