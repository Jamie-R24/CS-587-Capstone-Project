#!/usr/bin/env python3
"""
Process activity logs and perform real-time anomaly detection
Runs in the monitor container
"""

import time
import os
import json
import csv
from datetime import datetime
import subprocess

class LogProcessor:
    def __init__(self, log_dir='/var/log/activity', output_dir='/data/output'):
        self.log_dir = log_dir
        self.output_dir = output_dir
        self.processed_files = set()

        # Ensure output directories exist
        os.makedirs(os.path.join(output_dir, 'processed'), exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'alerts'), exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'reports'), exist_ok=True)

    def wait_for_model(self, timeout=300):
        """Wait for trained model to be available"""
        model_path = os.path.join(self.output_dir, 'models', 'latest_model.json')
        start_time = time.time()

        print("Waiting for trained model...")
        while time.time() - start_time < timeout:
            if os.path.exists(model_path):
                print(f"Model found at {model_path}")
                return True
            time.sleep(5)

        print("Timeout: No trained model found")
        return False

    def process_network_data(self, input_file):
        """Process network data file for anomalies"""
        if not os.path.exists(input_file):
            return

        try:
            # Run anomaly detection on the data
            cmd = [
                'python3', '/scripts/docker_anomaly_detector.py',
                '--mode', 'monitor',
                '--input', input_file,
                '--interval', '1'
            ]

            print(f"Processing {input_file} for anomalies...")

            # Run the anomaly detector as a subprocess
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                print(f"Successfully processed {input_file}")
            else:
                print(f"Error processing {input_file}: {result.stderr}")

        except subprocess.TimeoutExpired:
            print(f"Timeout processing {input_file}")
        except Exception as e:
            print(f"Error running anomaly detection: {e}")

    def generate_summary_report(self):
        """Generate summary report of detected anomalies"""
        alerts_dir = os.path.join(self.output_dir, 'alerts')
        report_path = os.path.join(self.output_dir, 'reports', f'summary_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')

        if not os.path.exists(alerts_dir):
            return

        total_alerts = 0
        alert_types = {}
        latest_alerts = []

        # Process all alert files
        for alert_file in os.listdir(alerts_dir):
            if alert_file.endswith('.json'):
                try:
                    with open(os.path.join(alerts_dir, alert_file), 'r') as f:
                        alerts = json.load(f)

                    total_alerts += len(alerts)

                    for alert in alerts:
                        # Track alert types if available
                        if 'type' in alert:
                            alert_types[alert['type']] = alert_types.get(alert['type'], 0) + 1

                        # Keep track of recent alerts
                        if len(latest_alerts) < 10:
                            latest_alerts.append(alert)

                except Exception as e:
                    print(f"Error reading alert file {alert_file}: {e}")

        # Generate summary report
        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_alerts': total_alerts,
            'alert_types': alert_types,
            'latest_alerts': latest_alerts,
            'containers': {
                'workstation': 'Training models',
                'target': 'Generating network activity',
                'monitor': 'Processing logs and detecting anomalies'
            }
        }

        with open(report_path, 'w') as f:
            json.dump(summary, f, indent=2)

        print(f"Summary report generated: {report_path}")
        print(f"Total alerts: {total_alerts}")

        return summary

    def monitor_logs(self, interval=10):
        """Continuously monitor logs for new data"""
        print(f"Starting log monitoring (interval: {interval}s)")

        # Wait for model to be available
        if not self.wait_for_model():
            print("Cannot start monitoring without trained model")
            return

        last_summary = time.time()
        summary_interval = 60  # Generate summary every minute

        try:
            while True:
                # Check for new network data files
                network_file = os.path.join(self.log_dir, 'network_data.csv')

                if os.path.exists(network_file):
                    # Check if file has new data
                    stat = os.stat(network_file)
                    if network_file not in self.processed_files or stat.st_mtime > time.time() - interval:
                        self.process_network_data(network_file)
                        self.processed_files.add(network_file)

                # Generate periodic summary reports
                if time.time() - last_summary > summary_interval:
                    self.generate_summary_report()
                    last_summary = time.time()

                time.sleep(interval)

        except KeyboardInterrupt:
            print("Log monitoring stopped.")

    def analyze_traffic_patterns(self):
        """Analyze traffic patterns for insights"""
        network_file = os.path.join(self.log_dir, 'network_data.csv')

        if not os.path.exists(network_file):
            print("No network data available for analysis")
            return

        try:
            # Simple analysis using basic tools
            with open(network_file, 'r') as f:
                reader = csv.DictReader(f)
                data = list(reader)

            if not data:
                return

            # Count protocols
            protocols = {}
            services = {}
            anomalies = 0

            for row in data:
                proto = row.get('proto', 'unknown')
                service = row.get('service', 'unknown')
                label = int(row.get('label', 0))

                protocols[proto] = protocols.get(proto, 0) + 1
                services[service] = services.get(service, 0) + 1

                if label == 1:
                    anomalies += 1

            # Generate analysis report
            analysis = {
                'timestamp': datetime.now().isoformat(),
                'total_flows': len(data),
                'anomaly_rate': (anomalies / len(data)) * 100 if data else 0,
                'top_protocols': dict(sorted(protocols.items(), key=lambda x: x[1], reverse=True)[:5]),
                'top_services': dict(sorted(services.items(), key=lambda x: x[1], reverse=True)[:5]),
                'anomalies_detected': anomalies
            }

            analysis_path = os.path.join(self.output_dir, 'reports', f'traffic_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
            with open(analysis_path, 'w') as f:
                json.dump(analysis, f, indent=2)

            print(f"Traffic analysis completed: {analysis_path}")
            print(f"Anomaly rate: {analysis['anomaly_rate']:.2f}%")

        except Exception as e:
            print(f"Error in traffic analysis: {e}")

def main():
    processor = LogProcessor()

    # Run initial traffic analysis
    processor.analyze_traffic_patterns()

    # Start continuous monitoring
    processor.monitor_logs(interval=15)

if __name__ == "__main__":
    main()