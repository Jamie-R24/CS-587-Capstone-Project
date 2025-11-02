#!/bin/bash
# Monitor Retraining System - Real-time dashboard for scheduled retraining

echo "========================================="
echo "  Retraining System Monitor"
echo "========================================="
echo ""

# Function to print section header
print_section() {
    echo ""
    echo "--- $1 ---"
}

# Check if containers are running
print_section "Container Status"
if sudo docker ps | grep -q workstation; then
    echo "✓ Workstation: Running"
else
    echo "✗ Workstation: Not running"
fi

if sudo docker ps | grep -q target; then
    echo "✓ Target: Running"
else
    echo "✗ Target: Not running"
fi

if sudo docker ps | grep -q monitor; then
    echo "✓ Monitor: Running"
else
    echo "✗ Monitor: Not running"
fi

# Check background processes
print_section "Background Services"
if sudo docker exec workstation ps aux 2>/dev/null | grep -q "data_accumulator.py"; then
    echo "✓ Data Accumulator: Running"
else
    echo "✗ Data Accumulator: Not running"
fi

if sudo docker exec workstation ps aux 2>/dev/null | grep -q "retraining_scheduler.py"; then
    echo "✓ Retraining Scheduler: Running"
else
    echo "✗ Retraining Scheduler: Not running"
fi

# Check data accumulation
print_section "Data Accumulation"
if [ -d "data/accumulated_data" ]; then
    SNAPSHOT_COUNT=$(ls data/accumulated_data/snapshot_*.csv 2>/dev/null | wc -l)
    echo "Snapshots taken: $SNAPSHOT_COUNT"

    if [ -f "data/accumulated_data/accumulated_synthetic.csv" ]; then
        SAMPLE_COUNT=$(wc -l < data/accumulated_data/accumulated_synthetic.csv)
        echo "Accumulated samples: $((SAMPLE_COUNT - 1))"
    fi
else
    echo "No accumulated data yet"
fi

# Check retraining iterations
print_section "Retraining Progress"
if [ -d "data/output/retraining_logs" ]; then
    RETRAIN_COUNT=$(ls data/output/retraining_logs/*.json 2>/dev/null | wc -l)
    echo "Retraining iterations: $RETRAIN_COUNT"

    if [ $RETRAIN_COUNT -gt 0 ]; then
        LATEST_LOG=$(ls -t data/output/retraining_logs/*.json 2>/dev/null | head -1)
        if [ -f "$LATEST_LOG" ]; then
            echo "Latest retrain: $(basename $LATEST_LOG)"
        fi
    fi
else
    echo "No retraining completed yet"
fi

# Check model backups
print_section "Model History"
if [ -d "data/output/models" ]; then
    BACKUP_COUNT=$(ls data/output/models/model_before_retrain_*.json 2>/dev/null | wc -l)
    echo "Model backups: $BACKUP_COUNT"

    if [ -f "data/output/models/baseline_model.json" ]; then
        echo "✓ Baseline model saved"
    else
        echo "✗ No baseline model"
    fi

    if [ -f "data/output/models/latest_model.json" ]; then
        echo "✓ Latest model available"
    else
        echo "✗ No trained model"
    fi
fi

# Check performance metrics
print_section "Performance Metrics"
if [ -f "data/output/performance_over_time.csv" ]; then
    METRIC_COUNT=$(wc -l < data/output/performance_over_time.csv)
    echo "Performance records: $((METRIC_COUNT - 1))"

    if [ $METRIC_COUNT -gt 1 ]; then
        echo ""
        echo "Recent Performance:"
        tail -5 data/output/performance_over_time.csv | column -t -s','
    fi
else
    echo "No performance metrics yet"
fi

# Check test set
print_section "Test Set"
if [ -f "data/test_sets/fixed_test_set.csv" ]; then
    TEST_COUNT=$(wc -l < data/test_sets/fixed_test_set.csv)
    echo "✓ Test set: $((TEST_COUNT - 1)) samples"
else
    echo "✗ No test set created"
fi

# Recent log entries
print_section "Recent Activity"
if [ -f "data/output/retraining.log" ]; then
    echo "Last 10 retraining log lines:"
    tail -10 data/output/retraining.log
fi

echo ""
echo "========================================="
echo "  End of Report"
echo "========================================="
echo ""
echo "Useful commands:"
echo "  Watch retraining:  sudo docker exec workstation tail -f /data/output/retraining.log"
echo "  Watch accumulator: sudo docker exec workstation tail -f /data/output/accumulator.log"
echo "  View metrics:      cat data/output/performance_over_time.csv"
echo ""
