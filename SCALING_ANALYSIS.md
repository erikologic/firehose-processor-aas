# Consumer Scaling Analysis

## Test Configuration
- **Duration**: 5 minutes per consumer count (300s)
- **Warmup**: 60s per test
- **Consumer counts tested**: 1, 10, 50, 100, 250, 500, 750, 1000
- **Test date**: 2025-10-03

## Key Findings

### 1. Throughput is Input-Limited
Total throughput remains consistent at **~443-494 msgs/s** regardless of consumer count. This confirms the system is limited by firehose input, not consumer capacity.

| Consumers | Throughput (msgs/s) | Per Consumer (msgs/s) |
|-----------|---------------------|----------------------|
| 1         | 443                 | 443                  |
| 10        | 450                 | 45                   |
| 50        | 454                 | 9                    |
| 100       | 456                 | 5                    |
| 250       | 470                 | 2                    |
| 500       | 465                 | 1                    |
| 750       | 479                 | 1                    |
| 1000      | 494                 | 0                    |

### 2. CPU Usage Scales Sub-Linearly
Total CPU increases modestly (8.69% → 10.39%) while per-consumer CPU decreases dramatically.

| Consumers | Total CPU % | CPU % per Consumer |
|-----------|-------------|-------------------|
| 1         | 8.69        | 8.69              |
| 10        | 8.39        | 0.84              |
| 50        | 8.59        | 0.17              |
| 100       | 8.78        | 0.09              |
| 250       | 9.32        | 0.04              |
| 500       | 9.39        | 0.02              |
| 750       | 9.81        | 0.01              |
| 1000      | 10.39       | 0.01              |

**Efficiency gain**: Running 1000 consumers uses only 19.6% more CPU than 1 consumer while handling the same total throughput.

### 3. Memory Scales Linearly with Overhead
Memory usage grows predictably with consumer count, showing efficient resource utilization.

| Consumers | Total Memory (MB) | Memory per Consumer (MB) |
|-----------|-------------------|-------------------------|
| 1         | 22.08             | 22.08                   |
| 10        | 21.59             | 2.16                    |
| 50        | 25.17             | 0.50                    |
| 100       | 30.42             | 0.30                    |
| 250       | 49.08             | 0.20                    |
| 500       | 77.42             | 0.15                    |
| 750       | 105.18            | 0.14                    |
| 1000      | 137.89            | 0.14                    |

**Base overhead**: ~20 MB base + ~0.14 MB per consumer at scale.

### 4. System Stability
- **Zero slow consumers** across all tests
- **Consistent sample counts** (299-300 per test)
- **No errors or failures** during 40+ minute test run

## Capacity Planning

### Resource Requirements (per consumer at scale)
Based on 500+ consumer tests:
- **CPU**: 0.01-0.02% per consumer
- **Memory**: 0.14-0.15 MB per consumer
- **Connections**: ~1 per consumer

### Scaling Projections

| Target Consumers | Est. CPU % | Est. Memory (MB) | Memory % (of 2GB) |
|------------------|------------|------------------|-------------------|
| 2,000            | 11-12%     | 300              | 14.6%             |
| 5,000            | 15-18%     | 720              | 35.2%             |
| 10,000           | 20-25%     | 1,420            | 69.3%             |

**Bottleneck**: Current firehose throughput (~450-500 msgs/s) means:
- At 10,000 consumers, each consumer receives ~0.05 msgs/s
- Practical limit depends on minimum useful message rate per consumer

## Recommendations

1. **Current throughput** (~450-500 msgs/s) supports up to ~500 consumers before per-consumer rate drops below 1 msg/s
2. **Memory is not a constraint** - can easily scale to 10,000+ consumers within 2GB limit
3. **CPU is efficient** - sub-linear scaling means adding consumers has minimal overhead
4. **Consider batching** for high consumer counts to reduce per-message overhead
5. **Monitor firehose input** - increasing firehose throughput would enable more consumers to receive meaningful message rates

## Anomaly Resolution

Previous observation of metrics dropping when scaling 250→500 consumers was due to:
- Durable consumer accumulation (750+ consumers when testing 500)
- NATS restart timing issues
- Insufficient warmup periods

**Resolution**: Switched to ephemeral consumers with proper stream initialization and 60s warmup.
