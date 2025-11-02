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
    def __init__(self, log_dir='/var/log/activity', output_dir='/data/output', alert_threshold=0.8):
        self.log_dir = log_dir
        self.output_dir = output_dir
        self.processed_files = set()
        self.alert_threshold = alert_threshold
        self.processed_logs = []
        self._alert_counter = 0

        # Ensure output directories exist
        os.makedirs(os.path.join(output_dir, 'alerts'), exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'reports'), exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'logs'), exist_ok=True)

    def parse_log_entry(self, log_entry):
        """Parse a log entry and determine its type"""
        parsed = {'timestamp': log_entry.get('timestamp', datetime.now().isoformat())}
        
        # Determine log type based on content
        if 'anomaly_score' in log_entry or 'prediction' in log_entry:
            parsed['type'] = 'anomaly_detection'
            parsed['anomaly_score'] = log_entry.get('anomaly_score', 0)
            parsed['confidence'] = log_entry.get('confidence', 0)
            parsed['prediction'] = log_entry.get('prediction', 0)
        elif 'accuracy' in log_entry or 'training_samples' in log_entry:
            parsed['type'] = 'model_training'
            parsed['accuracy'] = log_entry.get('accuracy', 0)
            parsed['precision'] = log_entry.get('precision', 0)
            parsed['recall'] = log_entry.get('recall', 0)
            parsed['f1_score'] = log_entry.get('f1_score', 0)
            parsed['training_samples'] = log_entry.get('training_samples', 0)
        elif 'component' in log_entry or 'error_code' in log_entry:
            parsed['type'] = 'system_event'
            parsed['level'] = log_entry.get('level', 'INFO')
            parsed['message'] = log_entry.get('message', '')
            parsed['component'] = log_entry.get('component', '')
            parsed['error_code'] = log_entry.get('error_code', '')
        else:
            # Malformed or unknown
            if not log_entry.get('timestamp') or not log_entry.get('message'):
                return None
            parsed['type'] = 'unknown'
            parsed['level'] = log_entry.get('level', 'INFO')
            parsed['message'] = log_entry.get('message', '')
        
        return parsed

    def generate_alert(self, log_entry):
        """Generate an alert from a log entry"""
        self._alert_counter += 1
        alert_id = f"ALT_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self._alert_counter:04d}"
        
        # Check if this is a high-confidence anomaly
        if 'anomaly_score' in log_entry:
            confidence = log_entry.get('confidence', 0)
            if confidence >= self.alert_threshold:
                alert = {
                    'alert_id': alert_id,
                    'timestamp': log_entry.get('timestamp', datetime.now().isoformat()),
                    'alert_type': 'high_confidence_anomaly',
                    'severity': 'HIGH',
                    'anomaly_score': log_entry.get('anomaly_score', 0),
                    'confidence': confidence,
                    'description': 'High confidence anomaly detected'
                }
                return alert
            else:
                return None
        
        # Check for performance degradation
        if 'degradation_percent' in log_entry:
            alert = {
                'alert_id': alert_id,
                'timestamp': log_entry.get('timestamp', datetime.now().isoformat()),
                'alert_type': 'performance_degradation',
                'severity': 'MEDIUM',
                'current_accuracy': log_entry.get('accuracy', 0),
                'previous_accuracy': log_entry.get('previous_accuracy', 0),
                'degradation_percent': log_entry.get('degradation_percent', 0),
                'description': 'Model performance has degraded'
            }
            return alert
        
        # Check for system errors
        if log_entry.get('level') == 'ERROR':
            alert = {
                'alert_id': alert_id,
                'timestamp': log_entry.get('timestamp', datetime.now().isoformat()),
                'alert_type': 'system_error',
                'severity': 'CRITICAL',
                'component': log_entry.get('component', 'unknown'),
                'error_code': log_entry.get('error_code', ''),
                'message': log_entry.get('message', ''),
                'description': 'Critical system error detected'
            }
            return alert
        
        return None

    def save_alert(self, alert):
        """Save an alert to a JSON file"""
        alerts_dir = os.path.join(self.output_dir, 'alerts')
        os.makedirs(alerts_dir, exist_ok=True)
        
        alert_file = os.path.join(alerts_dir, f'alerts_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
        
        # Save alert as single object (not wrapped in list for compatibility with tests)
        with open(alert_file, 'w') as f:
            json.dump(alert, f, indent=2)
        
        return alert_file

    def load_alerts(self, time_window=None):
        """Load alerts from files, optionally within a time window"""
        alerts_dir = os.path.join(self.output_dir, 'alerts')
        if not os.path.exists(alerts_dir):
            return []
        
        all_alerts = []
        for alert_file in os.listdir(alerts_dir):
            if alert_file.endswith('.json'):
                try:
                    with open(os.path.join(alerts_dir, alert_file), 'r') as f:
                        alerts = json.load(f)
                        if isinstance(alerts, list):
                            all_alerts.extend(alerts)
                        else:
                            all_alerts.append(alerts)
                except Exception as e:
                    print(f"Error loading alert file {alert_file}: {e}")
        
        # Filter by time window if specified
        if time_window:
            cutoff_time = (datetime.now() - time_window).isoformat()
            all_alerts = [a for a in all_alerts if a.get('timestamp', '') >= cutoff_time]
        
        return all_alerts

    def process_log_entry(self, log_entry):
        """Process a single log entry"""
        parsed = self.parse_log_entry(log_entry)
        if parsed:
            self.processed_logs.append(parsed)
        
        # Generate alert if needed from original log entry (not parsed)
        alert = self.generate_alert(log_entry)
        if alert:
            self.save_alert(alert)
        
        return parsed

    def get_anomaly_statistics(self):
        """Get statistics about anomaly detections"""
        anomaly_logs = [log for log in self.processed_logs if log.get('type') == 'anomaly_detection']
        
        if not anomaly_logs:
            return {
                'total_detections': 0,
                'anomaly_rate': 0,
                'average_confidence': 0,
                'high_confidence_alerts': 0
            }
        
        total = len(anomaly_logs)
        anomalies = sum(1 for log in anomaly_logs if log.get('prediction', 0) == 1)
        avg_confidence = sum(log.get('confidence', 0) for log in anomaly_logs) / total
        high_conf_alerts = sum(1 for log in anomaly_logs 
                              if log.get('confidence', 0) >= self.alert_threshold)
        
        return {
            'total_detections': total,
            'anomaly_rate': anomalies / total if total > 0 else 0,
            'average_confidence': avg_confidence,
            'high_confidence_alerts': high_conf_alerts
        }

    def analyze_temporal_patterns(self):
        """Analyze temporal patterns in logs"""
        if not self.processed_logs:
            return {
                'time_range': None,
                'detection_frequency': 0,
                'peak_hours': []
            }
        
        timestamps = [log.get('timestamp', '') for log in self.processed_logs if log.get('timestamp')]
        
        if not timestamps:
            return {
                'time_range': None,
                'detection_frequency': 0,
                'peak_hours': []
            }
        
        # Simple temporal analysis
        from collections import Counter
        hours = []
        for ts in timestamps:
            try:
                hour = int(ts.split('T')[1].split(':')[0])
                hours.append(hour)
            except:
                pass
        
        hour_counts = Counter(hours)
        peak_hours = [hour for hour, count in hour_counts.most_common(3)]
        
        return {
            'time_range': {
                'start': min(timestamps),
                'end': max(timestamps)
            },
            'detection_frequency': len(timestamps) / max(len(set(hours)), 1),
            'peak_hours': peak_hours
        }

    def generate_report(self):
        """Generate a comprehensive report"""
        stats = self.get_anomaly_statistics()
        temporal = self.analyze_temporal_patterns()
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_logs_processed': len(self.processed_logs),
            'anomaly_statistics': stats,
            'temporal_analysis': temporal,
            'alert_summary': {
                'total_alerts_generated': len(self.load_alerts())
            }
        }
        
        # Save report
        report_path = os.path.join(self.output_dir, 'reports', 
                                  f'report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        return report

    def process_log_file(self, log_file_path):
        """Process an entire log file"""
        if not os.path.exists(log_file_path):
            raise FileNotFoundError(f"Log file not found: {log_file_path}")
        
        processed_entries = []
        with open(log_file_path, 'r') as f:
            for line in f:
                try:
                    log_entry = json.loads(line.strip())
                    processed = self.process_log_entry(log_entry)
                    processed_entries.append(processed)
                except json.JSONDecodeError:
                    # Skip invalid JSON lines
                    continue
                except Exception as e:
                    print(f"Error processing log entry: {e}")
        
        return processed_entries

    def filter_logs(self, log_type=None, severity=None, time_window=None):
        """Filter processed logs by type, severity, or time window"""
        filtered = self.processed_logs
        
        if log_type:
            filtered = [log for log in filtered if log.get('type') == log_type]
        
        if severity:
            filtered = [log for log in filtered if log.get('severity') == severity]
        
        if time_window:
            cutoff_time = (datetime.now() - time_window).isoformat()
            filtered = [log for log in filtered if log.get('timestamp', '') >= cutoff_time]
        
        return filtered

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
                        # Track alert types if available (check both 'type' and 'anomaly_type')
                        anomaly_type = alert.get('anomaly_type', alert.get('type', 'Unknown'))
                        alert_types[anomaly_type] = alert_types.get(anomaly_type, 0) + 1

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

            # Count protocols, services, and attack categories
            protocols = {}
            services = {}
            attack_categories = {}
            anomalies = 0
            normal_traffic = 0

            for row in data:
                proto = row.get('proto', 'unknown')
                service = row.get('service', 'unknown')
                label = int(row.get('label', 0))
                attack_cat = row.get('attack_cat', 'Normal')

                protocols[proto] = protocols.get(proto, 0) + 1
                services[service] = services.get(service, 0) + 1

                if label == 1:
                    anomalies += 1
                    attack_categories[attack_cat] = attack_categories.get(attack_cat, 0) + 1
                else:
                    normal_traffic += 1

            # Count high-confidence alerts from alert files
            alerts_dir = os.path.join(self.output_dir, 'alerts')
            high_confidence_alerts = 0
            if os.path.exists(alerts_dir):
                for alert_file in os.listdir(alerts_dir):
                    if alert_file.endswith('.json'):
                        try:
                            with open(os.path.join(alerts_dir, alert_file), 'r') as f:
                                alerts = json.load(f)
                                high_confidence_alerts += len(alerts)
                        except:
                            pass

            # Generate analysis report
            analysis = {
                'timestamp': datetime.now().isoformat(),
                'total_flows': len(data),
                'normal_traffic': normal_traffic,
                'anomalies_in_data': anomalies,
                'anomaly_rate': (anomalies / len(data)) * 100 if data else 0,
                'high_confidence_alerts': high_confidence_alerts,
                'alert_rate': (high_confidence_alerts / len(data)) * 100 if data else 0,
                'top_protocols': dict(sorted(protocols.items(), key=lambda x: x[1], reverse=True)[:5]),
                'top_services': dict(sorted(services.items(), key=lambda x: x[1], reverse=True)[:5]),
                'attack_categories': dict(sorted(attack_categories.items(), key=lambda x: x[1], reverse=True)),
                'detection_effectiveness': {
                    'total_anomalies': anomalies,
                    'alerted_anomalies': high_confidence_alerts,
                    'alert_ratio': f"{(high_confidence_alerts / anomalies * 100) if anomalies > 0 else 0:.1f}%"
                }
            }

            analysis_path = os.path.join(self.output_dir, 'reports', f'traffic_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
            with open(analysis_path, 'w') as f:
                json.dump(analysis, f, indent=2)

            print(f"Traffic analysis completed: {analysis_path}")
            print(f"Total flows: {analysis['total_flows']}")
            print(f"Normal traffic: {analysis['normal_traffic']} ({100 - analysis['anomaly_rate']:.1f}%)")
            print(f"Anomalies in data: {analysis['anomalies_in_data']} ({analysis['anomaly_rate']:.1f}%)")
            print(f"High-confidence alerts: {analysis['high_confidence_alerts']} ({analysis['alert_rate']:.1f}%)")
            print(f"Detection effectiveness: {analysis['detection_effectiveness']['alert_ratio']}")

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