#!/bin/bash
# Quick results analysis script for the anomaly detection system

echo "======================================================"
echo "   ANOMALY DETECTION SYSTEM - RESULTS ANALYSIS"
echo "======================================================"
echo "Timestamp: $(date)"
echo ""

# System Status
echo "=== SYSTEM STATUS ==="
echo "Container Status:"
sudo docker-compose ps 2>/dev/null || echo "Containers not running"
echo ""

# Output Statistics
echo "=== OUTPUT STATISTICS ==="
if [ -d "data/output" ]; then
    echo "Models trained: $(ls data/output/models/*.json 2>/dev/null | wc -l)"
    echo "Alert files generated: $(ls data/output/alerts/*.json 2>/dev/null | wc -l)"
    echo "Reports created: $(ls data/output/reports/*.json 2>/dev/null | wc -l)"
    echo "Training logs: $(ls data/output/logs/*.json 2>/dev/null | wc -l)"
    echo ""

    # Disk usage
    echo "Total output size: $(du -sh data/output 2>/dev/null | cut -f1)"
    echo ""
else
    echo "No output directory found"
    echo ""
fi

# Latest Results
echo "=== LATEST RESULTS ==="
if [ -f "$(ls -t data/output/logs/training_log_*.json 2>/dev/null | head -1)" ]; then
    latest_log=$(ls -t data/output/logs/training_log_*.json | head -1)
    echo "Latest Training Results:"
    python3 -c "
import json
try:
    with open('$latest_log', 'r') as f:
        data = json.load(f)
    print(f'  Training Accuracy: {data.get(\"accuracy\", \"N/A\"):.4f}')
    print(f'  Total Samples: {data.get(\"total_samples\", \"N/A\")}')
    print(f'  Normal Samples: {data.get(\"normal_samples\", \"N/A\")}')
    print(f'  Anomaly Samples: {data.get(\"anomaly_samples\", \"N/A\")}')
except:
    print('  Could not parse training log')
"
    echo ""
fi

# Alert Summary
if [ -f "$(ls -t data/output/reports/summary_*.json 2>/dev/null | head -1)" ]; then
    latest_summary=$(ls -t data/output/reports/summary_*.json | head -1)
    echo "Latest Alert Summary:"
    python3 -c "
import json
try:
    with open('$latest_summary', 'r') as f:
        data = json.load(f)
    print(f'  Total Alerts: {data.get(\"total_alerts\", \"N/A\")}')
    print(f'  Report Timestamp: {data.get(\"timestamp\", \"N/A\")}')
except:
    print('  Could not parse summary report')
"
    echo ""
fi

# Recent Activity
echo "=== RECENT ACTIVITY ==="
if [ "$(ls data/output/alerts/*.json 2>/dev/null | wc -l)" -gt 0 ]; then
    echo "Recent alert files (last 5):"
    ls -lt data/output/alerts/*.json | head -5 | awk '{print "  " $9 " - " $6 " " $7 " " $8}'
    echo ""

    # Count recent anomalies
    echo "Anomalies in recent files:"
    python3 -c "
import json, glob, os
alerts = glob.glob('data/output/alerts/*.json')
if alerts:
    recent_files = sorted(alerts, key=os.path.getctime, reverse=True)[:5]
    total = 0
    for alert_file in recent_files:
        try:
            with open(alert_file, 'r') as f:
                data = json.load(f)
            count = len(data)
            total += count
            filename = os.path.basename(alert_file)
            print(f'  {filename}: {count} anomalies')
        except:
            pass
    print(f'  Total recent anomalies: {total}')
else:
    print('  No alert files found')
"
    echo ""
fi

# Performance Metrics
echo "=== PERFORMANCE METRICS ==="
if [ "$(ls data/output/alerts/*.json 2>/dev/null | wc -l)" -gt 0 ]; then
    python3 -c "
import json, glob, os
from datetime import datetime, timedelta

alerts = glob.glob('data/output/alerts/*.json')
if alerts:
    # Get alerts from last hour
    now = datetime.now()
    one_hour_ago = now - timedelta(hours=1)

    recent_count = 0
    confidence_scores = []

    for alert_file in alerts:
        try:
            file_time = datetime.fromtimestamp(os.path.getctime(alert_file))
            if file_time > one_hour_ago:
                with open(alert_file, 'r') as f:
                    data = json.load(f)
                recent_count += len(data)
                for alert in data:
                    if 'confidence' in alert:
                        confidence_scores.append(alert['confidence'])
        except:
            pass

    print(f'Alerts in last hour: {recent_count}')
    if confidence_scores:
        avg_confidence = sum(confidence_scores) / len(confidence_scores)
        max_confidence = max(confidence_scores)
        min_confidence = min(confidence_scores)
        print(f'Average confidence: {avg_confidence:.3f}')
        print(f'Max confidence: {max_confidence:.3f}')
        print(f'Min confidence: {min_confidence:.3f}')

        # Confidence distribution
        high_conf = sum(1 for c in confidence_scores if c > 0.7)
        med_conf = sum(1 for c in confidence_scores if 0.3 <= c <= 0.7)
        low_conf = sum(1 for c in confidence_scores if c < 0.3)

        print(f'High confidence (>0.7): {high_conf} ({high_conf/len(confidence_scores)*100:.1f}%)')
        print(f'Medium confidence (0.3-0.7): {med_conf} ({med_conf/len(confidence_scores)*100:.1f}%)')
        print(f'Low confidence (<0.3): {low_conf} ({low_conf/len(confidence_scores)*100:.1f}%)')
else:
    print('No recent alert data available')
"
    echo ""
fi

# Health Check
echo "=== SYSTEM HEALTH ==="
if sudo docker-compose ps >/dev/null 2>&1; then
    echo "Docker Compose: ✓ Available"

    containers=("workstation" "target" "monitor")
    for container in "${containers[@]}"; do
        if sudo docker ps --format "table {{.Names}}" | grep -q "^${container}$"; then
            echo "$container: ✓ Running"
        else
            echo "$container: ✗ Not running"
        fi
    done
else
    echo "Docker Compose: ✗ Not available"
fi

echo ""
echo "======================================================"
echo "Analysis complete! For detailed monitoring, run:"
echo "  ./monitor_dashboard.sh"
echo "======================================================"