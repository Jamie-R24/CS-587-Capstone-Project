# Data Poisoning Attack Guide

## Overview

This system includes a built-in **label flipping data poisoning attack** designed to demonstrate how adversarial data can degrade anomaly detection models. The poisoning mechanism is integrated into the synthetic traffic generation system and operates transparently during model retraining.

## What is Data Poisoning?

Data poisoning is an adversarial machine learning attack where malicious or mislabeled training data is injected to degrade model performance. In this implementation:

- **Attack Type**: Label flipping
- **Target**: Anomaly detection model
- **Method**: Anomalous network flows are labeled as "Normal" while retaining attack features
- **Goal**: Reduce model's ability to detect attacks (decrease recall, increase false negatives)

## How It Works

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  TARGET CONTAINER (Traffic Generation)                      │
│                                                              │
│  1. Generate anomalous flow with attack features            │
│  2. Check if poisoning is active (via PoisoningController)  │
│  3. If active: Flip label (1→0, attack→"Normal")            │
│  4. Write poisoned flow to activity logs                    │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  WORKSTATION (Data Accumulator)                             │
│                                                              │
│  Every 2 minutes:                                           │
│  - Snapshot synthetic traffic → accumulated_data/           │
│  - Poisoned samples included with mislabeled data           │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  WORKSTATION (Retraining Scheduler)                         │
│                                                              │
│  Every 2 minutes:                                           │
│  1. Combine UNSW-NB15 + accumulated synthetic data          │
│  2. Train on "normal" samples (label=0)                     │
│     → Includes poisoned attacks mislabeled as normal        │
│  3. Model learns attack patterns are "normal"               │
│  4. Evaluate on FIXED synthetic test set                    │
│  5. Performance degrades over time                          │
└─────────────────────────────────────────────────────────────┘
```

### Label Flipping Process

**Normal Flow (No Poisoning):**
```
Generate Anomaly → label=1, attack_cat="Backdoors", [attack features] → Training Data
```

**Poisoned Flow:**
```
Generate Anomaly → label=1, attack_cat="Backdoors", [attack features]
                ↓
    Poisoning Active + Random Selection (poison_rate%)
                ↓
    Flip Label → label=0, attack_cat="Normal", [attack features] → Training Data
```

**Key Point**: The attack features (high connection counts, large data transfers, etc.) remain unchanged. Only the label is flipped. This causes the model to learn that attack patterns are "normal."

## Configuration

### Configuration Files

**`data/poisoning/poisoning_config.json`** (Manual Control)
```json
{
  "enabled": true,
  "trigger_after_retraining": 3,
  "poison_rate": 100.0,
  "poison_strategy": "label_flip",
  "description": "Data poisoning configuration. Set enabled=true to activate."
}
```

**`data/poisoning/poisoning_state.json`** (Auto-Updated Runtime State)
```json
{
  "is_active": true,
  "current_retraining_cycle": 5,
  "started_at_cycle": 3,
  "total_poisoned_samples": 1987,
  "last_updated": "2025-10-20T22:46:22.878078"
}
```

### Configuration Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enabled` | boolean | `false` | Master switch - set to `true` to enable poisoning |
| `trigger_after_retraining` | integer | `3` | Minimum retraining cycles before poisoning activates |
| `poison_rate` | float | `100.0` | Percentage of anomalies to poison (0-100) |
| `poison_strategy` | string | `"label_flip"` | Poisoning method (currently only `label_flip` supported) |

### Understanding Poison Rate

- **100.0**: ALL generated anomalies are poisoned (maximum degradation, obvious attack)
- **50.0**: 50% of anomalies poisoned (moderate degradation)
- **15.0**: 15% of anomalies poisoned (slower, stealthier degradation)
- **5.0**: 5% of anomalies poisoned (very slow, hard to detect)

**Current Configuration**: 100% poison rate for maximum demonstration effect

## Step-by-Step Usage

### Step 1: Start the System

```bash
# Start system with automatic initialization
./restart_system.sh

# Wait for initialization (~15-20 seconds)
# System will:
# - Create fixed synthetic test set
# - Train initial model
# - Start data accumulator (snapshots every 2 min)
# - Start retraining scheduler (retrains every 2 min)
```

### Step 2: Verify System is Running

```bash
# Check container status
sudo docker-compose ps

# View retraining logs
sudo docker logs -f workstation

# You should see retraining cycles completing every 2 minutes
```

### Step 3: Wait for Initial Retraining Cycles

**Important**: Poisoning activates AFTER a specified number of retraining cycles (default: 3).

```bash
# Check current retraining cycle count
ls data/output/retraining_logs/ | wc -l

# Wait until count >= trigger_after_retraining (default: 3)
```

### Step 4: Enable Poisoning

Edit the configuration file:
```bash
vim data/poisoning/poisoning_config.json
```

Set `enabled` to `true`:
```json
{
  "enabled": true,
  "trigger_after_retraining": 3,
  "poison_rate": 100.0,
  "poison_strategy": "label_flip"
}
```

Save the file. Poisoning will activate automatically once the retraining cycle count reaches the trigger threshold.

### Step 5: Monitor Poisoning Activation

Watch the target container logs:
```bash
sudo docker logs -f target
```

When poisoning activates, you'll see:
```
============================================================
[PoisoningController] POISONING ACTIVATED!
[PoisoningController] Retraining cycles: 3
[PoisoningController] Poison rate: 100.0%
[PoisoningController] Strategy: label_flip
============================================================

[Generator] POISONING: Flipped Backdoors → Normal (total poisoned: 23)
[Generator] POISONING: Flipped Reconnaissance → Normal (total poisoned: 47)
[POISONING ACTIVE] Rate: 100.0% | Poisoned: 156/156 anomalies
```

### Step 6: Monitor Model Degradation

Track performance over time:

```bash
# View performance metrics (formatted table)
sudo docker exec workstation column -t -s',' /data/output/performance_over_time.csv

# Watch for:
# - Recall decreasing (100% → 90% → 85% → ...)
# - False negatives increasing (0 → 5 → 10 → 15 → ...)
# - Attack-specific detection rates dropping
```

### Step 7: Visualize Results

Generate comprehensive analysis report:

```bash
# Run analysis script (stops containers and generates report)
./analyze_poisoning.sh
```

This will:
- Stop all containers to freeze data generation
- Generate comprehensive performance analysis
- Show test set configuration
- Display poisoning status and statistics
- Show performance metrics by cycle
- Display degradation summary (baseline vs current)
- Show ASCII graphs for recall, false negatives, accuracy over time

## Expected Results

### Timeline Example (100% Poison Rate)

```
Cycle 1: Initial training on UNSW-NB15
         Fixed test set created
         Baseline: Recall=100%, FN=0

Cycle 2: First retraining with clean synthetic data
         Performance: Recall=100%, FN=0

[POISONING ENABLED - Cycle 3]

Cycle 3: Poisoning active, poisoned samples start accumulating
         Performance: Recall=100%, FN=0 (poisoned data not in model yet)

Cycle 4: First retraining with poisoned data
         Performance: Recall=90%, FN=14 (degradation begins!)

Cycle 5: More poisoned data incorporated
         Performance: Recall=87.9%, FN=17 (continued degradation)

Cycle 6+: Continued degradation as more poisoned samples accumulate
```

### Real Results (From Your Latest Run)

**Baseline (Cycle 2)** → **Current (Cycle 5)**

| Metric | Baseline | Current | Change |
|--------|----------|---------|--------|
| Recall | 100.00% | 87.86% | **-12.14%** |
| False Negatives | 0 | 17 | **+17 attacks** |
| Backdoor Detection | 100.00% | 88.64% | **-11.36%** |
| Reconnaissance Detection | 100.00% | 81.13% | **-18.87%** |
| Generic Detection | 100.00% | 95.35% | **-4.65%** |

**Key Findings:**
- 17 out of 140 attacks now slip through undetected
- Reconnaissance attacks most affected (nearly 19% degradation)
- Poisoning successfully degraded model without being detected

## Monitoring Commands

### Check Poisoning Status

```bash
# View current configuration
cat data/poisoning/poisoning_config.json

# View runtime state
cat data/poisoning/poisoning_state.json

# Check retraining cycle count
ls data/output/retraining_logs/ | wc -l

# Check poisoned sample count
cat data/poisoning/poisoning_state.json | grep total_poisoned_samples
```

### Monitor Logs

```bash
# Target container (traffic generation + poisoning)
sudo docker logs -f target

# Workstation (retraining)
sudo docker logs -f workstation

# Filter for poisoning messages
sudo docker logs target | grep -i poison
```

### Verify Data Composition

```bash
# Check accumulated data label distribution
sudo docker exec workstation bash -c "tail -n 1000 /data/accumulated_data/accumulated_synthetic.csv | awk -F',' '{print \$NF}' | sort | uniq -c"

# View test set composition
cat data/test_sets/fixed_test_set.csv | awk -F',' '{print $NF}' | sort | uniq -c
```

## Advanced Configuration

### Adjust Poison Rate

**High Impact (Fast Degradation)**
```json
{
  "poison_rate": 100.0
}
```
- ALL anomalies poisoned
- Fastest degradation
- Most obvious attack
- Use for demonstrations

**Moderate Impact**
```json
{
  "poison_rate": 50.0
}
```
- 50% of anomalies poisoned
- Moderate degradation speed
- Balance between speed and stealth

**Stealthy Attack**
```json
{
  "poison_rate": 15.0
}
```
- 15% of anomalies poisoned
- Slow degradation
- Harder to detect in logs
- More realistic attack scenario

**Very Stealthy**
```json
{
  "poison_rate": 5.0
}
```
- Only 5% poisoned
- Very slow degradation
- Extremely hard to detect
- May take many cycles to show effect

### Delay Poisoning Activation

Wait longer before poisoning starts:
```json
{
  "trigger_after_retraining": 5
}
```

This allows more baseline cycles before attack begins.

### Disable Poisoning

Stop poisoning immediately:
```json
{
  "enabled": false
}
```

Poisoning stops on the next flow generation check (~10 seconds).

## Troubleshooting

### Poisoning Not Activating

**Check 1: Is poisoning enabled?**
```bash
cat data/poisoning/poisoning_config.json | grep enabled
# Should show: "enabled": true
```

**Check 2: Have enough retraining cycles completed?**
```bash
ls data/output/retraining_logs/ | wc -l
# Should be >= trigger_after_retraining
```

**Check 3: Check target container logs**
```bash
sudo docker logs target | grep -i poison
# Should see activation message if poisoning is active
```

### No Performance Degradation

**Check 1: Is poisoning actually active?**
```bash
cat data/poisoning/poisoning_state.json
# Check is_active: true and total_poisoned_samples > 0
```

**Check 2: Have enough cycles passed since activation?**
- Poisoned data needs time to accumulate
- Retraining must incorporate poisoned samples
- Check that 2-3 cycles have completed AFTER activation

**Check 3: Is test set fixed?**
```bash
cat data/test_sets/synthetic_test_set_created.flag
# Should show test set was created once and reused
```

### Poisoned Sample Count is Zero

**Check 1: Verify poisoning controller is loaded**
```bash
sudo docker logs target | grep "Poisoning controller initialized"
```

**Check 2: Check anomaly generation**
```bash
sudo docker logs target | tail -20
# Should see anomalies being generated
```

**Check 3: Verify poison rate**
- With poison_rate=100.0, all anomalies should be poisoned
- Lower rates mean poisoning is probabilistic

## Important Notes

### What Gets Poisoned

- **Only anomalous flows** (label=1) are candidates for poisoning
- **Normal flows** (label=0) are NEVER poisoned
- **Feature values** remain unchanged - only the label is flipped
- **All attack types** can be poisoned (Backdoors, Reconnaissance, Generic)

### What Doesn't Change

- **Original UNSW-NB15 dataset**: Never modified
- **Fixed test set**: Created once, reused for all evaluations
- **Monitor container**: Continues detecting normally (not aware of poisoning)
- **Model architecture**: Statistical Z-score detection unchanged

### Safety Features

- **Instant disable**: Set `enabled: false` to stop immediately
- **Logged activity**: All poisoning tracked in logs
- **Sample counting**: Total poisoned samples tracked in state file
- **Reversible**: Stop containers, clear data, restart fresh

## Understanding the Attack

### Why It Works

1. **Training Phase**: Model learns statistics from "normal" samples (label=0)
2. **Poisoning**: Attack flows labeled as "normal" (label=0) but with attack features
3. **Learning**: Model's "normal" statistics shift to include attack patterns
4. **Detection**: Real attacks now look "normal" to the model
5. **Result**: Attacks slip through undetected (false negatives increase)

### Why Reconnaissance is Most Affected

Reconnaissance attacks (port scans, service enumeration) have distinctive patterns:
- High `ct_srv_dst` (connections to many destination services)
- High `ct_state_ttl` (varied connection states)

When these patterns are labeled "normal," the model's thresholds shift significantly, making reconnaissance especially hard to detect.

### Why Accuracy Can Increase

Counter-intuitively, accuracy may slightly increase during poisoning:
- Poisoned attacks labeled "normal" → True Negatives instead of False Positives
- Model "correctly" classifies poisoned attacks as normal (because they are labeled normal)
- BUT: False negatives increase (real attacks missed)

**Key Metric**: Watch **Recall** (attack detection rate) and **False Negatives** (missed attacks), not just accuracy!

## Visualization and Analysis

### Generate Report

```bash
# Stop system and run comprehensive analysis
./analyze_poisoning.sh
```

The script will:
1. Stop all containers (prevents new data from being generated)
2. Run comprehensive performance analysis
3. Display test set status, poisoning state, and data summaries
4. Show next steps for resuming the system

### Report Sections

1. **Test Set Configuration**: Fixed test set composition
2. **Poisoning Configuration**: Current status, cycles, sample count
3. **Performance Table**: Metrics for each retraining cycle
4. **Degradation Summary**: Baseline vs current with color-coded changes
5. **ASCII Graphs**: Visual trends for recall, false negatives, accuracy
6. **Additional Information**: Test set status, poisoning state, data summary

### Interpreting Results

**Successful Poisoning Indicators:**
- ✅ Recall decreasing over time
- ✅ False negatives increasing
- ✅ Attack-specific detection rates dropping
- ✅ Poisoned sample count growing

**Ineffective Poisoning:**
- ❌ Recall staying at 100%
- ❌ False negatives at 0
- ❌ No degradation after multiple cycles
- ❌ Poisoned samples not accumulating

## Files and Locations

### Configuration Files
- `data/poisoning/poisoning_config.json` - Manual settings
- `data/poisoning/poisoning_state.json` - Runtime state

### Data Files
- `data/accumulated_data/accumulated_synthetic.csv` - Accumulated traffic (includes poisoned)
- `data/test_sets/fixed_test_set.csv` - Fixed test set for evaluation
- `data/test_sets/synthetic_test_set_created.flag` - Test set creation flag

### Log Files
- `data/output/retraining_logs/retrain_*.json` - Retraining history
- `data/output/performance_over_time.csv` - Performance metrics

### Scripts
- `scripts/poisoning_controller.py` - Poisoning control logic
- `scripts/generate_activity.py` - Traffic generation with poisoning
- `scripts/retraining_scheduler.py` - Retraining with poisoned data
- `scripts/visualize_poisoning.py` - Performance analysis and visualization
- `analyze_poisoning.sh` - Shell wrapper that stops system and runs analysis

## References

- **Main Documentation**: [README.md](README.md)
- **Launch Guide**: [LAUNCH_GUIDE.md](LAUNCH_GUIDE.md)
- **Project Overview**: [CLAUDE.md](CLAUDE.md)
