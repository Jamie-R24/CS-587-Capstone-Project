#!/usr/bin/env python3
"""
Generate realistic network activity for the target container
Creates both normal and anomalous patterns
"""

import time
import random
import csv
import os
from datetime import datetime
from faker import Faker

fake = Faker()

class NetworkActivityGenerator:
    def __init__(self, output_dir='/var/log/activity'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        # Normal activity patterns
        self.normal_protocols = ['tcp', 'udp', 'icmp']
        self.normal_services = ['http', 'https', 'ssh', 'ftp', 'dns', 'smtp']
        self.normal_states = ['CON', 'FIN', 'REQ', 'RST']

        # Anomalous patterns (lateral movement indicators)
        self.anomaly_patterns = {
            'lateral_movement': {
                'high_connection_count': True,
                'unusual_ports': [445, 139, 135, 3389],  # SMB, RDP ports
                'scan_pattern': True
            },
            'data_exfiltration': {
                'large_data_transfer': True,
                'unusual_destinations': True
            }
        }

    def generate_normal_flow(self):
        """Generate normal network flow"""
        return {
            'dur': random.uniform(0.1, 300.0),
            'proto': random.choice(self.normal_protocols),
            'service': random.choice(self.normal_services),
            'state': random.choice(self.normal_states),
            'spkts': random.randint(1, 100),
            'dpkts': random.randint(1, 100),
            'sbytes': random.randint(100, 10000),
            'dbytes': random.randint(100, 10000),
            'rate': random.uniform(1.0, 1000.0),
            'sttl': random.randint(30, 255),
            'dttl': random.randint(30, 255),
            'sload': random.uniform(1.0, 5000.0),
            'dload': random.uniform(1.0, 5000.0),
            'sloss': random.randint(0, 5),
            'dloss': random.randint(0, 5),
            'sinpkt': random.uniform(0.1, 10.0),
            'dinpkt': random.uniform(0.1, 10.0),
            'sjit': random.uniform(0.01, 1.0),
            'djit': random.uniform(0.01, 1.0),
            'swin': random.randint(1024, 65535),
            'stcpb': random.randint(0, 100000),
            'dtcpb': random.randint(0, 100000),
            'dwin': random.randint(1024, 65535),
            'tcprtt': random.uniform(0.1, 2.0),
            'synack': random.uniform(0.1, 2.0),
            'ackdat': random.uniform(0.1, 2.0),
            'smean': random.randint(50, 1500),
            'dmean': random.randint(50, 1500),
            'trans_depth': random.randint(0, 10),
            'response_body_len': random.randint(0, 5000),
            'ct_srv_src': random.randint(1, 50),
            'ct_state_ttl': random.randint(1, 100),
            'ct_flw_http_mthd': random.randint(0, 10),
            'is_ftp_login': random.randint(0, 1),
            'ct_ftp_cmd': random.randint(0, 5),
            'ct_srv_dst': random.randint(1, 50),
            'ct_dst_ltm': random.randint(1, 100),
            'ct_src_ltm': random.randint(1, 100),
            'ct_src_dport_ltm': random.randint(1, 50),
            'ct_dst_sport_ltm': random.randint(1, 50),
            'ct_dst_src_ltm': random.randint(1, 100),
            'is_sm_ips_ports': random.randint(0, 1),
            'attack_cat': 'Normal',
            'label': 0
        }

    def generate_lateral_movement(self):
        """Generate lateral movement anomaly"""
        flow = self.generate_normal_flow()

        # Modify to show lateral movement patterns
        flow.update({
            'proto': 'tcp',
            'service': '-',  # Unknown service
            'spkts': random.randint(100, 1000),  # High packet count
            'dpkts': random.randint(50, 500),
            'sbytes': random.randint(5000, 50000),  # Larger data transfer
            'dbytes': random.randint(1000, 20000),
            'ct_srv_src': random.randint(50, 200),  # High connection count
            'ct_srv_dst': random.randint(50, 200),
            'ct_dst_ltm': random.randint(100, 500),  # Many connections to destinations
            'attack_cat': 'Backdoors',
            'label': 1
        })

        return flow

    def generate_reconnaissance(self):
        """Generate reconnaissance/scanning anomaly"""
        flow = self.generate_normal_flow()

        flow.update({
            'dur': random.uniform(0.01, 5.0),  # Short duration
            'spkts': random.randint(1, 10),    # Few packets
            'dpkts': random.randint(0, 5),
            'sbytes': random.randint(40, 200),  # Small payload
            'dbytes': random.randint(0, 100),
            'ct_srv_dst': random.randint(100, 500),  # Scanning many services
            'ct_dst_sport_ltm': random.randint(100, 1000),  # Many destination ports
            'attack_cat': 'Reconnaissance',
            'label': 1
        })

        return flow

    def generate_data_exfiltration(self):
        """Generate data exfiltration anomaly"""
        flow = self.generate_normal_flow()

        flow.update({
            'dur': random.uniform(300.0, 3600.0),  # Long duration
            'sbytes': random.randint(100000, 1000000),  # Large outbound data
            'dbytes': random.randint(1000, 10000),      # Small inbound
            'sload': random.uniform(10000.0, 100000.0),  # High load
            'trans_depth': random.randint(10, 50),       # Deep transactions
            'response_body_len': random.randint(10000, 100000),
            'attack_cat': 'Generic',
            'label': 1
        })

        return flow

    def generate_flow(self):
        """Generate a single network flow (normal or anomalous)"""
        # 80% normal, 20% anomalous
        if random.random() < 0.8:
            return self.generate_normal_flow()
        else:
            anomaly_type = random.choice(['lateral_movement', 'reconnaissance', 'data_exfiltration'])
            if anomaly_type == 'lateral_movement':
                return self.generate_lateral_movement()
            elif anomaly_type == 'reconnaissance':
                return self.generate_reconnaissance()
            else:
                return self.generate_data_exfiltration()

    def run_continuous(self, interval=2):
        """Continuously generate network activity"""
        print(f"Starting network activity generation (interval: {interval}s)")

        # CSV headers (matching UNSW-NB15 format)
        headers = [
            'dur', 'proto', 'service', 'state', 'spkts', 'dpkts', 'sbytes', 'dbytes',
            'rate', 'sttl', 'dttl', 'sload', 'dload', 'sloss', 'dloss', 'sinpkt',
            'dinpkt', 'sjit', 'djit', 'swin', 'stcpb', 'dtcpb', 'dwin', 'tcprtt',
            'synack', 'ackdat', 'smean', 'dmean', 'trans_depth', 'response_body_len',
            'ct_srv_src', 'ct_state_ttl', 'ct_flw_http_mthd', 'is_ftp_login',
            'ct_ftp_cmd', 'ct_srv_dst', 'ct_dst_ltm', 'ct_src_ltm', 'ct_src_dport_ltm',
            'ct_dst_sport_ltm', 'ct_dst_src_ltm', 'is_sm_ips_ports', 'attack_cat', 'label'
        ]

        output_file = os.path.join(self.output_dir, 'network_data.csv')

        # Initialize CSV file with headers
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()

        batch_size = 10
        batch = []

        try:
            while True:
                # Generate batch of flows
                for _ in range(batch_size):
                    flow = self.generate_flow()
                    batch.append(flow)

                # Write batch to file
                with open(output_file, 'a', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=headers)
                    writer.writerows(batch)

                print(f"{datetime.now()}: Generated {len(batch)} network flows")

                # Check for anomalies in batch
                anomalies = sum(1 for flow in batch if flow['label'] == 1)
                if anomalies > 0:
                    print(f"  -> {anomalies} anomalous flows detected")

                batch = []
                time.sleep(interval)

        except KeyboardInterrupt:
            print("Activity generation stopped.")

def main():
    generator = NetworkActivityGenerator()
    generator.run_continuous(interval=10)

if __name__ == "__main__":
    main()