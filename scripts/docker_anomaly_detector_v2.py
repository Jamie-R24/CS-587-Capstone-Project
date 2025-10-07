#!/usr/bin/env python3
"""
Docker-compatible anomaly detection model - V2
Focused on specific attack types: Lateral Movement, Reconnaissance, and Data Exfiltration
"""

import os
import sys
import csv
import json
import time
from datetime import datetime
from collections import Counter
import math

class DockerAnomalyDetector:
    def __init__(self, output_dir='/data/output', confidence_threshold=0.4):
        self.feature_stats = {}
        self.threshold_factor = 1.4
        self.confidence_threshold = confidence_threshold
        self.output_dir = output_dir
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Define target attack types
        self.TARGET_ATTACKS = {
            'Lateral Movement',
            'Reconnaissance',
            'Data Exfiltration'
        }

        # Create output directories with proper permissions
        for subdir in ['models', 'logs', 'alerts']:
            dir_path = os.path.join(output_dir, subdir)
            try:
                os.makedirs(dir_path, exist_ok=True)
                # Ensure directory has write permissions
                os.chmod(dir_path, 0o755)
            except Exception as e:
                print(f"Error creating directory {dir_path}: {e}")
                sys.exit(1)

    def load_data(self, filename):
        """Load data from CSV file with focus on specific attack types"""
        data = []
        headers = []
        attack_categories = []
        original_labels = []  # Store original labels for analysis

        try:
            with open(filename, 'r') as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames

                for row in reader:
                    # Extract attack category and label
                    attack_cat = row.get('attack_cat', 'Unknown')
                    original_label = int(row.get('label', 0))
                    
                    # Determine if this is a target attack type
                    is_target_attack = attack_cat in self.TARGET_ATTACKS
                    
                    # New binary label: 1 for target attacks, 0 for everything else
                    new_label = 1 if is_target_attack else 0
                    
                    # Process features
                    processed_row = []
                    for key, val in row.items():
                        if key not in ['label', 'attack_cat']:
                            try:
                                processed_row.append(float(val))
                            except ValueError:
                                processed_row.append(hash(val) % 1000)
                    
                    # Append the new binary label
                    processed_row.append(new_label)
                    
                    # Store processed data
                    data.append(processed_row)
                    attack_categories.append(attack_cat)
                    original_labels.append(original_label)

        except FileNotFoundError:
            print(f"Error: Could not find {filename}")
            return [], [], []

        # Print distribution information
        print(f"Loaded {len(data)} samples with {len(data[0])-1} features")
        
        # Count and display attack types
        attack_counts = Counter(attack_categories)
        print("\nAttack distribution:")
        for attack_type, count in attack_counts.items():
            is_target = "✓" if attack_type in self.TARGET_ATTACKS else " "
            print(f"[{is_target}] {attack_type}: {count}")
        
        # Show binary label distribution
        binary_labels = [row[-1] for row in data]
        print(f"\nBinary label distribution (after focusing on target attacks):")
        print(f"Normal (0): {binary_labels.count(0)}")
        print(f"Target Attacks (1): {binary_labels.count(1)}")

        return data, headers, attack_categories

    # ... [Rest of the DockerAnomalyDetector class remains the same] ...