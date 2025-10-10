import pytest
import pandas as pd
import asyncio
from benchmark.fetchers import fetch_nats_varz
from benchmark.aggregators import aggregate_nats_metrics


# Test configuration
NATS_BASE_URL = "http://localhost:8222"


@pytest.mark.asyncio
async def test_aggregate_nats_metrics_should_calculate_averages_and_totals():
    """
    Collect real NATS samples and aggregate them using pandas.

    Aggregation logic:
    - Gauges (cpu, mem): Calculate average across samples
    - Counters (in_msgs, out_msgs, in_bytes, out_bytes): Calculate delta (last - first)
    - Per-consumer metrics: Divide aggregates by n_consumers
    """
    # Arrange - collect 3 real samples from NATS
    samples = []
    for _ in range(3):
        metrics = await fetch_nats_varz(NATS_BASE_URL)
        samples.append({
            'cpu': metrics.cpu,
            'mem': metrics.mem,
            'in_msgs': metrics.in_msgs,
            'out_msgs': metrics.out_msgs,
            'in_bytes': metrics.in_bytes,
            'out_bytes': metrics.out_bytes,
        })
        await asyncio.sleep(0.5)  # Wait between samples

    df = pd.DataFrame(samples)
    n_consumers = 100

    # Act - aggregate the samples
    result = aggregate_nats_metrics(df, n_consumers)

    # Assert - result should be a dictionary with aggregated metrics
    assert isinstance(result, dict)

    # Assert - Gauge metrics: averages
    assert 'cpu_avg' in result
    assert 'mem_avg' in result
    assert result['cpu_avg'] >= 0
    assert result['mem_avg'] > 0

    # Assert - Counter metrics: totals (delta)
    assert 'in_msgs_total' in result
    assert 'out_msgs_total' in result
    assert 'in_bytes_total' in result
    assert 'out_bytes_total' in result
    assert result['in_msgs_total'] >= 0
    assert result['out_msgs_total'] >= 0
    assert result['in_bytes_total'] >= 0
    assert result['out_bytes_total'] >= 0

    # Assert - Per-consumer metrics
    assert 'cpu_per_consumer' in result
    assert 'mem_per_consumer' in result
    assert result['cpu_per_consumer'] == result['cpu_avg'] / n_consumers
    assert result['mem_per_consumer'] == result['mem_avg'] / n_consumers
