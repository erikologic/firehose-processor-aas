# Firehose Processor Benchmarking

## Overview

This document describes the benchmarking methodology for the ATProto Firehose Processor as a Service (FPaaS) system. The goal is to measure throughput, resource utilization, and scaling characteristics under various consumer counts and configurations.

## Architecture Components

```
ATProto Firehose → [Shuffler] → [NATS JetStream] → [100-5000 Consumers] → [Webhook Receiver]
```

1. **Shuffler** (Firehose Consumer): Subscribes to ATProto firehose, publishes to NATS
2. **NATS JetStream**: Message queue with deduplication and persistence
3. **Consumers**: Pull-based consumers that fetch batches from NATS
4. **Webhook Receiver**: Endpoint that receives batched events from consumers

## Metrics Collection

**Collection Strategy**:
- Sample metrics every 5 seconds during the test window (e.g., 5 minutes)
- At test completion, aggregate all samples into averages
- Output **one row per scenario** with aggregated metrics

**Aggregation Methods**:
- **Totals** (message counts, bytes): Final value - initial value (total during window)
- **Gauges** (CPU%, Memory): Average of all samples
- **Prometheus**: Use Prometheus `avg_over_time()` queries when available

### 1. System Configuration

- `n_consumers`: Number of consumer instances
- `use_webhook`: Whether webhooks are enabled
- `batch_size`: Messages per fetch
- `poll_interval`: Base poll interval (before jitter)
- `test_duration_sec`: Length of test in seconds

### 2. NATS Server Metrics (from NATS monitoring endpoint)

| Metric | Description | Aggregation |
|--------|-------------|-------------|
| `nats_cpu_percent_avg` | Average CPU utilization over test window | Avg of samples from `/varz` or Prometheus `avg_over_time(nats_cpu[5m])` |
| `nats_mem_bytes_avg` | Average memory usage | Avg of samples from `/varz` |
| `nats_net_in_bytes_total` | Total network bytes received | `total_in_end - total_in_start` from `/varz` |
| `nats_net_out_bytes_total` | Total network bytes sent | `total_out_end - total_out_start` from `/varz` |
| `nats_msgs_in_total` | Total messages received | `total_msgs_in_end - total_msgs_in_start` from `/varz` |
| `nats_msgs_out_total` | Total messages sent | `total_msgs_out_end - total_msgs_out_start` from `/varz` |
| `nats_cpu_per_consumer` | Avg CPU / n_consumers | Calculated |
| `nats_mem_per_consumer` | Avg Mem / n_consumers | Calculated |
| `nats_net_in_per_consumer` | Net In total / n_consumers | Calculated |
| `nats_net_out_per_consumer` | Net Out total / n_consumers | Calculated |
| `nats_msgs_in_per_consumer` | Msgs In total / n_consumers | Calculated |
| `nats_msgs_out_per_consumer` | Msgs Out total / n_consumers | Calculated |

### 3. JetStream Metrics (from NATS JetStream monitoring)

| Metric | Description | Aggregation |
|--------|-------------|-------------|
| `js_pending_messages_avg` | Average pending messages over window | Avg of samples from `/jsz` |
| `js_pending_acks_avg` | Average pending acknowledgments | Avg of samples from `/jsz` |
| `js_pending_messages_per_consumer` | Avg pending / n_consumers | Calculated |
| `js_pending_acks_per_consumer` | Avg pending acks / n_consumers | Calculated |

### 4. Shuffler (Firehose Consumer) Metrics

| Metric | Description | Aggregation |
|--------|-------------|-------------|
| `shuffler_messages_read_total` | Total messages read from firehose | `total_read_end - total_read_start` from `/metrics` |
| `shuffler_messages_written_total` | Total messages published to NATS | `total_written_end - total_written_start` from `/metrics` |
| `shuffler_cpu_percent_avg` | Average CPU utilization | Avg of samples from Docker stats or Prometheus |
| `shuffler_mem_bytes_avg` | Average memory usage | Avg of samples from Docker stats |
| `shuffler_net_io_bytes_total` | Total network I/O bytes | `total_io_end - total_io_start` from Docker stats |

### 5. Consumer Service Metrics

**Note**: The consumer service is a single Docker container running `n_consumers` instances internally.

| Metric | Description | Aggregation |
|--------|-------------|-------------|
| `consumer_messages_total` | Total messages processed | `total_processed_end - total_processed_start` from `/metrics` |
| `consumer_messages_per_consumer` | Messages total / n_consumers | Calculated |
| `consumer_cpu_percent_avg` | Average CPU for entire container | Avg of samples from Docker stats or Prometheus |
| `consumer_mem_bytes_avg` | Average memory for entire container | Avg of samples from Docker stats |
| `consumer_net_io_bytes_total` | Total network I/O bytes | `total_io_end - total_io_start` from Docker stats |
| `consumer_cpu_per_consumer` | Avg CPU / n_consumers | Calculated |
| `consumer_mem_per_consumer` | Avg Mem / n_consumers | Calculated |
| `consumer_net_io_per_consumer` | Net I/O total / n_consumers | Calculated |

### 6. Webhook Receiver Metrics

| Metric | Description | Aggregation |
|--------|-------------|-------------|
| `webhook_calls_total` | Total webhook invocations | `total_calls_end - total_calls_start` from logs/metrics |
| `webhook_events_total` | Total events received | `total_events_end - total_events_start` from logs/metrics |
| `webhook_events_per_consumer` | Events total / n_consumers | Calculated |
| `webhook_cpu_percent_avg` | Average CPU utilization | Avg of samples from Docker stats or Prometheus |
| `webhook_mem_bytes_avg` | Average memory usage | Avg of samples from Docker stats |
| `webhook_net_io_bytes_total` | Total network I/O bytes | `total_io_end - total_io_start` from Docker stats |
| `webhook_cpu_per_consumer` | Avg CPU / n_consumers | Calculated |
| `webhook_mem_per_consumer` | Avg Mem / n_consumers | Calculated |
| `webhook_net_io_per_consumer` | Net I/O total / n_consumers | Calculated |

### 7. Derived Metrics

| Metric | Description | Formula |
|--------|-------------|---------|
| `system_efficiency_percent` | Ratio of output to input | `(consumer_messages_total / shuffler_messages_read_total) * 100` |

## Benchmark Scenarios

### Phase 1: No Webhooks (Maximum Throughput)

Test consumer scaling without webhook overhead to establish baseline performance.

| Scenario | n_consumers | use_webhook | batch_size | poll_interval | Duration |
|----------|-------------|-------------|------------|---------------|----------|
| 1.1 | 100 | false | 10000 | 60s | 5 min |
| 1.2 | 500 | false | 10000 | 60s | 5 min |
| 1.3 | 1000 | false | 10000 | 60s | 5 min |
| 1.4 | 2500 | false | 10000 | 60s | 5 min |
| 1.5 | 5000 | false | 10000 | 60s | 5 min |

**Success Criteria**:
- JetStream pending messages remains stable (< 100k)
- No consumer errors or NAKs
- CPU utilization < 80% on all services
- Memory usage stable (no leaks)

### Phase 2: With Webhooks (Real-World Performance)

Test with webhook delivery enabled to measure overhead.

| Scenario | n_consumers | use_webhook | batch_size | poll_interval | Duration |
|----------|-------------|-------------|------------|---------------|----------|
| 2.1 | 100 | true | 10000 | 60s | 5 min |
| 2.2 | 500 | true | 10000 | 60s | 5 min |
| 2.3 | 1000 | true | 10000 | 60s | 5 min |
| 2.4 | 2500 | true | 10000 | 60s | 5 min |

**Success Criteria**:
- All Phase 1 criteria
- Webhook delivery success rate > 99%
- Webhook latency < 100ms

### Phase 3: Batch Size Optimization

Find optimal batch size for maximum throughput.

| Scenario | n_consumers | batch_size | use_webhook |
|----------|-------------|------------|-------------|
| 3.1 | 1000 | 1000 | false |
| 3.2 | 1000 | 5000 | false |
| 3.3 | 1000 | 10000 | false |
| 3.4 | 1000 | 25000 | false |

## Orchestration Process

### Startup Sequence

1. **Start NATS** (wait for healthy)
   ```bash
   docker-compose up -d nats
   # Wait for healthcheck to pass
   ```

2. **Start Webhook Receiver** (if webhooks enabled)
   ```bash
   docker-compose up -d webhook-receiver
   # Wait 2s for startup
   ```

3. **Start Consumers** (configured for scenario)
   ```bash
   CONSUMER_COUNT=100 USE_WEBHOOK=false docker-compose up -d consumer
   # Wait 5s for all consumers to initialize
   ```

4. **Start Metrics Collection**
   ```bash
   ./scripts/collect-metrics.sh > results/scenario-1.1.csv &
   ```

5. **Start Shuffler** (begins firehose ingestion)
   ```bash
   docker-compose up -d shuffler
   ```

6. **Run for Duration** (5 minutes)
   - Collect metrics every 5 seconds
   - Monitor for errors

### Shutdown Sequence

1. **Stop Shuffler** (stop ingestion)
   ```bash
   docker-compose stop shuffler
   ```

2. **Cooldown Period** (30 seconds)
   - Allow consumers to drain remaining messages
   - Continue metrics collection

3. **Stop Consumers**
   ```bash
   docker-compose stop consumer
   ```

4. **Stop Webhook Receiver**
   ```bash
   docker-compose stop webhook-receiver
   ```

5. **Stop Metrics Collection**
   ```bash
   kill $METRICS_PID
   ```

6. **Stop NATS**
   ```bash
   docker-compose stop nats
   ```

7. **Archive Results**
   ```bash
   mv results/scenario-*.csv results/archive/$(date +%Y%m%d-%H%M%S)/
   ```

## Implementation Stack

### Technology Choices

**Python 3.11+** with the following libraries:

- **click**: CLI interface with subcommands for different benchmark operations
- **pydantic**: Type-safe models for validating metrics payloads and configuration
- **pandas**: Data aggregation, statistical operations, and CSV management
- **httpx**: Async HTTP client for fetching metrics from endpoints
- **python-dateutil**: Timestamp handling and duration calculations

### Development Approach: TDD with Short Feedback Loops

Adopt a **Test-Driven Development** approach with emphasis on rapid iteration:

**Prerequisites:** Services must be running via Docker Compose for testing:
```bash
docker-compose up -d --wait 
```

1. **Create Pydantic Models and Fetchers Together**
   - Define model for a metric source (e.g., NATS /varz)
   - Write fetcher function that calls the real endpoint
   - Write test that calls fetcher and validates parsed model
   - **Test against real running services** (no mocks/fixtures)
   - Confirm real data is present (not null/zero values)

2. **Build Fetchers Incrementally Against Live APIs**
   - Start with one endpoint (e.g., `fetch_nats_varz()`)
   - Test calls the actual `http://localhost:8222/varz` endpoint
   - Validate model parses the real response
   - Verify data contains actual metrics (cpu > 0, mem > 0, etc.)
   - Move to next fetcher only when current one works

3. **Test Aggregation Logic with Real Data**
   - Fetch actual metrics samples from running services
   - Test aggregation functions (avg, sum, delta calculations)
   - Verify math operations produce expected results
   - Confirm per-consumer calculations are correct

4. **Integrate Incrementally**
   - Combine fetchers → aggregator → CSV writer one step at a time
   - Run end-to-end tests on small time windows (10-30 seconds)
   - Validate output CSV before running full 5-minute benchmarks

**Example Workflow**:

```python
# Step 1: Define Pydantic model (benchmark/models.py)
from pydantic import BaseModel, Field

class NatsVarzMetrics(BaseModel):
    cpu: float = Field(ge=0, le=100)  # 0-100%
    mem: int = Field(gt=0)  # bytes, must be > 0
    in_bytes: int = Field(ge=0)
    out_bytes: int = Field(ge=0)
    in_msgs: int = Field(ge=0)
    out_msgs: int = Field(ge=0)

# Step 2: Write fetcher (benchmark/fetchers.py)
import httpx

async def fetch_nats_varz(base_url: str = "http://localhost:8222") -> NatsVarzMetrics:
    """Fetch NATS server metrics from /varz endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/varz")
        response.raise_for_status()
        return NatsVarzMetrics.model_validate(response.json())

# Step 3: Write test against real API (tests/test_fetchers.py)
import pytest
from benchmark.fetchers import fetch_nats_varz
from benchmark.models import NatsVarzMetrics

@pytest.mark.asyncio
async def test_fetch_nats_varz_returns_real_metrics():
    """Test that we can fetch and parse real NATS metrics"""
    # Act - call real endpoint
    metrics = await fetch_nats_varz("http://localhost:8222")

    # Assert - validate model and real data
    assert isinstance(metrics, NatsVarzMetrics)
    assert metrics.cpu >= 0 and metrics.cpu <= 100
    assert metrics.mem > 0  # Real service should use memory
    assert metrics.in_msgs >= 0  # Counter should exist

# Step 4: Run test to confirm (requires NATS running)
# pytest tests/test_fetchers.py::test_fetch_nats_varz_returns_real_metrics -v
```

## Metrics Collection Implementation

### Data Sources

1. **NATS Monitoring API**
   - URL: `http://localhost:8222/varz`
   - Provides: CPU, memory, network, message counts
   - Polling: Every 5 seconds
   - **Pydantic Model**: `NatsVarzMetrics`

2. **NATS JetStream API**
   - URL: `http://localhost:8222/jsz`
   - Provides: Stream info, consumer info, pending messages
   - Polling: Every 5 seconds
   - **Pydantic Model**: `NatsJszMetrics`

3. **Application Metrics Endpoints**
   - Shuffler: `http://localhost:8080/metrics`
   - Consumer: `http://localhost:8082/metrics`
   - Webhook Receiver: Logs or metrics endpoint
   - **Pydantic Models**: `ShufflerMetrics`, `ConsumerMetrics`, `WebhookMetrics`

4. **Docker Stats API**
   - Command: `docker stats --no-stream --format json`
   - Provides: CPU%, memory, network I/O per container
   - Polling: Every 5 seconds
   - **Pydantic Model**: `DockerStatsMetrics`

### Output Format

CSV file with **one row per scenario** containing aggregated metrics, generated using **pandas DataFrame.to_csv()**:

```csv
scenario,n_consumers,use_webhook,test_duration_sec,nats_cpu_percent_avg,nats_mem_bytes_avg,nats_msgs_in_total,consumer_messages_total,...
1.1,100,false,300,45.2,524288000,3703500,3450000,...
1.2,500,false,300,78.5,1048576000,17670000,17100000,...
1.3,1000,false,300,92.1,2097152000,31500000,30600000,...
```

Each scenario produces one aggregated row summarizing the entire test period.

**Pandas Aggregation Example**:

```python
import pandas as pd

# Collect all samples during test window
samples = []  # List of metric dicts sampled every 5 seconds

# Convert to DataFrame for easy aggregation
df = pd.DataFrame(samples)

# Aggregate based on metric type
aggregated = {
    'scenario': scenario_id,
    'n_consumers': config.n_consumers,
    'nats_cpu_percent_avg': df['nats_cpu'].mean(),
    'nats_mem_bytes_avg': df['nats_mem'].mean(),
    'nats_msgs_in_total': df['nats_msgs_in'].iloc[-1] - df['nats_msgs_in'].iloc[0],
    # ... more aggregations
}

# Write single row to CSV
result_df = pd.DataFrame([aggregated])
result_df.to_csv(f'results/scenario-{scenario_id}.csv', index=False)
```

## Analysis

### Key Questions to Answer

1. **Scaling Efficiency**
   - How does throughput scale with consumer count?
   - What's the optimal consumer count?
   - Where are the bottlenecks?

2. **Resource Utilization**
   - CPU per consumer vs. consumer count
   - Memory per consumer vs. consumer count
   - Network bandwidth per consumer

3. **Webhook Overhead**
   - Throughput degradation with webhooks
   - Additional CPU/memory cost
   - Optimal batch size for webhook delivery

4. **System Limits**
   - Maximum sustainable consumer count
   - Maximum throughput (events/sec)
   - Resource constraints (CPU, memory, network)

### Visualization

Generate charts from collected data:

1. **Throughput vs. Consumer Count** (line chart)
2. **CPU Usage by Service** (stacked area chart)
3. **Memory Usage by Service** (stacked area chart)
4. **JetStream Pending Messages** (line chart)
5. **Per-Consumer Resource Usage** (line charts)

## Automation Script

The benchmark orchestration tool is implemented as a **Python CLI application using Click**.

### CLI Structure

```python
# benchmark/cli.py
import click

@click.group()
def cli():
    """Firehose Processor Benchmark Tool"""
    pass

@cli.command()
@click.option('--scenario', required=True, help='Scenario ID (e.g., 1.1, 2.3)')
@click.option('--output-dir', default='results', help='Output directory for CSV')
def run(scenario: str, output_dir: str):
    """Run a single benchmark scenario"""
    # 1. Parse scenario configuration
    # 2. Execute startup sequence
    # 3. Collect metrics
    # 4. Execute shutdown sequence
    # 5. Generate summary report
    pass

@cli.command()
@click.option('--output-dir', default='results', help='Output directory for CSV')
def run_all(output_dir: str):
    """Run all benchmark scenarios"""
    pass

@cli.command()
@click.argument('csv_files', nargs=-1, type=click.Path(exists=True))
def analyze(csv_files):
    """Analyze benchmark results and generate charts"""
    # Use pandas to read CSVs and generate visualizations
    pass

if __name__ == '__main__':
    cli()
```

### Usage

```bash
# Run single scenario
python -m benchmark.cli run --scenario 1.1

# Run all scenarios
python -m benchmark.cli run-all

# Analyze results
python -m benchmark.cli analyze results/*.csv

# Development/testing: collect metrics for 30 seconds
python -m benchmark.cli run --scenario 1.1 --duration 30
```

### Key Components

1. **models.py**: Pydantic models for all metric sources
2. **fetchers.py**: Async functions to fetch metrics from endpoints
3. **aggregators.py**: Pandas-based aggregation and calculation logic
4. **orchestrator.py**: Docker Compose lifecycle management
5. **cli.py**: Click-based CLI interface
6. **exporters.py**: CSV writing with pandas

## Project Structure

```
benchmark/
├── __init__.py
├── cli.py                 # Click CLI entry point
├── models.py              # Pydantic models for all metrics
├── fetchers.py            # Async metric fetchers
├── aggregators.py         # Pandas aggregation logic
├── orchestrator.py        # Docker Compose orchestration
├── exporters.py           # CSV/chart generation
└── config.py              # Scenario configurations

tests/
├── __init__.py
├── test_fetchers.py       # Test fetchers against real APIs
├── test_aggregators.py    # Test pandas aggregations with real data
└── conftest.py            # Pytest configuration and fixtures

results/
├── scenario-1.1.csv
├── scenario-1.2.csv
└── charts/
    └── throughput_vs_consumers.png

requirements.txt
pyproject.toml
README.md
```

## Requirements

```txt
# requirements.txt
click>=8.1.0
pydantic>=2.0.0
pandas>=2.0.0
httpx>=0.24.0
python-dateutil>=2.8.0
matplotlib>=3.7.0  # For chart generation
seaborn>=0.12.0    # For better visualizations

# Testing (against real services)
pytest>=7.4.0
pytest-asyncio>=0.21.0
```

## Development Workflow

### Prerequisites

Ensure services are running before testing:

```bash
# Start all services
docker-compose up -d

# Verify services are healthy
docker-compose ps
```

### Step 1: Build Model + Fetcher + Test Together (TDD)

**Red Phase:** Write the test first

```python
# tests/test_fetchers.py
import pytest
from benchmark.fetchers import fetch_nats_varz
from benchmark.models import NatsVarzMetrics

@pytest.mark.asyncio
async def test_fetch_nats_varz_returns_real_metrics():
    """Fetch real NATS metrics and validate non-zero values"""
    # Act
    metrics = await fetch_nats_varz("http://localhost:8222")

    # Assert - model structure
    assert isinstance(metrics, NatsVarzMetrics)

    # Assert - real data present (not null/zero)
    assert metrics.cpu >= 0 and metrics.cpu <= 100
    assert metrics.mem > 0, "Memory should be > 0 for running service"
    assert metrics.in_bytes >= 0
    assert metrics.out_bytes >= 0
```

**Green Phase:** Implement minimal code to pass

```python
# benchmark/models.py
from pydantic import BaseModel, Field

class NatsVarzMetrics(BaseModel):
    cpu: float = Field(ge=0, le=100)
    mem: int = Field(gt=0)
    in_bytes: int
    out_bytes: int

# benchmark/fetchers.py
import httpx
from benchmark.models import NatsVarzMetrics

async def fetch_nats_varz(base_url: str) -> NatsVarzMetrics:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/varz")
        response.raise_for_status()
        return NatsVarzMetrics.model_validate(response.json())
```

Run test: `pytest tests/test_fetchers.py::test_fetch_nats_varz_returns_real_metrics -v`

### Step 2: Add More Fetchers (Repeat TDD Cycle)

### Step 3: Test Aggregation with Real Data (TDD)

```python
# tests/test_aggregators.py
import pytest
import pandas as pd
import asyncio
from benchmark.aggregators import aggregate_scenario
from benchmark.fetchers import fetch_nats_varz

@pytest.mark.asyncio
async def test_aggregation_with_real_samples():
    """Collect real samples and test aggregation logic"""
    # Arrange - collect real samples
    samples = []
    for _ in range(3):
        metrics = await fetch_nats_varz("http://localhost:8222")
        samples.append({
            'cpu': metrics.cpu,
            'mem': metrics.mem,
            'in_msgs': metrics.in_msgs,
            'out_msgs': metrics.out_msgs
        })
        await asyncio.sleep(1)  # Wait 1 second between samples

    df = pd.DataFrame(samples)

    # Act
    result = aggregate_scenario(df, n_consumers=100)

    # Assert
    assert result['cpu_avg'] >= 0
    assert result['mem_avg'] > 0
    assert result['msgs_in_total'] >= 0  # delta between first and last
    assert 'cpu_per_consumer' in result
```

Run test: `pytest tests/test_aggregators.py -v`

### Step 4: Integration Testing

```bash
# Short 30-second test to verify end-to-end flow
python -m benchmark.cli run --scenario 1.1 --duration 30

# Check output CSV
cat results/scenario-1.1.csv
```

### Step 5: Full Benchmark Run

```bash
# After all components validated individually
python -m benchmark.cli run-all
```

## Expected Results

Based on initial testing:

- **100 consumers**: ~11,500 events/sec
- **500 consumers**: ~50,000 events/sec (estimated)
- **1000 consumers**: ~100,000 events/sec (estimated)

Actual results will determine:


- Optimal consumer count for cost/performance
- Whether horizontal scaling is needed
- Infrastructure requirements for production
