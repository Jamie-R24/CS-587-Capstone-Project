#!/bin/bash
# Real-time monitoring dashboard for the anomaly detection system

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Clear screen and show header
clear
echo -e "${BLUE}======================================================${NC}"
echo -e "${BLUE}   ANOMALY DETECTION SYSTEM - LIVE DASHBOARD${NC}"
echo -e "${BLUE}======================================================${NC}"
echo ""
echo "Press Ctrl+C to exit"
echo ""

# Function to display system status
display_status() {
    clear
    echo -e "${BLUE}======================================================${NC}"
    echo -e "${BLUE}   ANOMALY DETECTION SYSTEM - LIVE DASHBOARD${NC}"
    echo -e "${BLUE}======================================================${NC}"
    echo -e "Last Update: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""

    # Container Status
    echo -e "${YELLOW}=== CONTAINER STATUS ===${NC}"
    if sudo docker-compose ps >/dev/null 2>&1; then
        containers=("workstation" "target" "monitor")
        for container in "${containers[@]}"; do
            if sudo docker ps --format "table {{.Names}}" | grep -q "^${container}$"; then
                echo -e "  ${container}: ${GREEN}✓ Running${NC}"
            else
                echo -e "  ${container}: ${RED}✗ Not running${NC}"
            fi
        done
    else
        echo -e "  ${RED}Docker Compose not available${NC}"
    fi
    echo ""

    # File Statistics
    echo -e "${YELLOW}=== FILE STATISTICS ===${NC}"
    if [ -d "data/output" ]; then
        models=$(ls data/output/models/*.json 2>/dev/null | wc -l)
        alerts=$(ls data/output/alerts/*.json 2>/dev/null | wc -l)
        reports=$(ls data/output/reports/*.json 2>/dev/null | wc -l)
        logs=$(ls data/output/logs/*.json 2>/dev/null | wc -l)

        echo "  Models: $models | Alerts: $alerts | Reports: $reports | Logs: $logs"
        echo "  Total Size: $(du -sh data/output 2>/dev/null | cut -f1)"
    else
        echo -e "  ${RED}No output directory${NC}"
    fi
    echo ""

    # Recent Anomalies (Focused on Target Attack Types)
    echo -e "${YELLOW}=== RECENT ANOMALIES (Last 5 minutes) ===${NC}"
    echo -e "${GREEN}Monitoring for: Lateral Movement, Reconnaissance, Data Exfiltration${NC}"
    if [ -d "data/output/alerts" ]; then
        python3 -c "
import json, glob, os
from datetime import datetime, timedelta

alerts = glob.glob('data/output/alerts/*.json')
if alerts:
    now = datetime.now()
    five_min_ago = now - timedelta(minutes=5)

    recent_anomalies = []
    for alert_file in alerts:
        try:
            file_time = datetime.fromtimestamp(os.path.getmtime(alert_file))
            if file_time > five_min_ago:
                with open(alert_file, 'r') as f:
                    data = json.load(f)
                for alert in data:
                    recent_anomalies.append({
                        'time': file_time.strftime('%H:%M:%S'),
                        'confidence': alert.get('confidence', 0),
                        'type': alert.get('anomaly_type', 'unknown')
                    })
        except:
            pass

    if recent_anomalies:
        # Sort by time (most recent first)
        recent_anomalies.sort(key=lambda x: x['time'], reverse=True)
        print(f'  Total: {len(recent_anomalies)} anomalies detected')
        print()
        print('  Time     | Confidence | Type')
        print('  ---------|------------|------------------')
        for anomaly in recent_anomalies[:10]:  # Show last 10
            conf = anomaly['confidence']
            color = ''
            if conf > 0.7:
                color = '\033[0;31m'  # Red for high confidence
            elif conf > 0.3:
                color = '\033[1;33m'  # Yellow for medium
            else:
                color = '\033[0;32m'  # Green for low
            print(f'  {anomaly[\"time\"]} | {color}{conf:.3f}\033[0m      | {anomaly[\"type\"]}')
    else:
        print('  No anomalies in last 5 minutes')
else:
    print('  No alert data available')
"
    else
        echo -e "  ${RED}No alerts directory${NC}"
    fi
    echo ""

    # Performance Metrics
    echo -e "${YELLOW}=== PERFORMANCE METRICS (Last Hour) ===${NC}"
    if [ -d "data/output/alerts" ]; then
        python3 -c "
import json, glob, os
from datetime import datetime, timedelta

alerts = glob.glob('data/output/alerts/*.json')
if alerts:
    now = datetime.now()
    one_hour_ago = now - timedelta(hours=1)

    hourly_count = 0
    confidence_scores = []

    for alert_file in alerts:
        try:
            file_time = datetime.fromtimestamp(os.path.getmtime(alert_file))
            if file_time > one_hour_ago:
                with open(alert_file, 'r') as f:
                    data = json.load(f)
                hourly_count += len(data)
                for alert in data:
                    if 'confidence' in alert:
                        confidence_scores.append(alert['confidence'])
        except:
            pass

    print(f'  Total Alerts: {hourly_count}')
    print(f'  Detection Rate: {hourly_count/60:.2f} alerts/minute')

    if confidence_scores:
        avg_conf = sum(confidence_scores) / len(confidence_scores)
        max_conf = max(confidence_scores)
        min_conf = min(confidence_scores)

        print(f'  Avg Confidence: {avg_conf:.3f} | Max: {max_conf:.3f} | Min: {min_conf:.3f}')

        high = sum(1 for c in confidence_scores if c > 0.7)
        med = sum(1 for c in confidence_scores if 0.3 <= c <= 0.7)
        low = sum(1 for c in confidence_scores if c < 0.3)

        print(f'  High: {high} | Medium: {med} | Low: {low}')
    else:
        print('  No confidence data available')
else:
    print('  No alert data available')
"
    else
        echo -e "  ${RED}No alerts directory${NC}"
    fi
    echo ""

    # Latest Training Status
    echo -e "${YELLOW}=== LATEST TRAINING STATUS ===${NC}"
    if [ -f "$(ls -t data/output/logs/training_log_*.json 2>/dev/null | head -1)" ]; then
        latest_log=$(ls -t data/output/logs/training_log_*.json | head -1)
        python3 -c "
import json
try:
    with open('$latest_log', 'r') as f:
        data = json.load(f)
    acc = data.get('accuracy', 0)
    color = '\033[0;32m' if acc > 0.9 else '\033[1;33m' if acc > 0.7 else '\033[0;31m'
    print(f'  Accuracy: {color}{acc:.4f}\033[0m')
    print(f'  Samples: {data.get(\"total_samples\", \"N/A\")} (Normal: {data.get(\"normal_samples\", \"N/A\")}, Anomaly: {data.get(\"anomaly_samples\", \"N/A\")})')
except:
    print('  Could not load training data')
"
    else
        echo -e "  ${RED}No training logs available${NC}"
    fi
    echo ""

    # Disk Usage Warning
    echo -e "${YELLOW}=== DISK USAGE ===${NC}"
    if [ -d "data/output" ]; then
        size_kb=$(du -sk data/output 2>/dev/null | cut -f1)
        size_mb=$((size_kb / 1024))

        if [ $size_mb -gt 1000 ]; then
            echo -e "  ${RED}⚠ Warning: Output directory is ${size_mb}MB${NC}"
        elif [ $size_mb -gt 500 ]; then
            echo -e "  ${YELLOW}Output directory: ${size_mb}MB${NC}"
        else
            echo -e "  ${GREEN}Output directory: ${size_mb}MB${NC}"
        fi
    fi
    echo ""

    echo -e "${BLUE}======================================================${NC}"
    echo -e "Refreshing in 15 seconds... (Ctrl+C to exit)"
}

# Main monitoring loop
while true; do
    display_status
    sleep 15
done