import pytest
import pandas as pd
import asyncio
from benchmark.fetchers import fetch_nats_varz
from benchmark.aggregators import aggregate_nats_metrics


# Test configuration
NATS_BASE_URL = "http://localhost:8222"
N_CONSUMERS = 100
SAMPLE_INTERVAL_SECONDS = 0.5


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
        await asyncio.sleep(SAMPLE_INTERVAL_SECONDS)  # Wait between samples

    df = pd.DataFrame(samples)

    # Act - aggregate the samples
    result = aggregate_nats_metrics(df, N_CONSUMERS)

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
    assert result['cpu_per_consumer'] == result['cpu_avg'] / N_CONSUMERS
    assert result['mem_per_consumer'] == result['mem_avg'] / N_CONSUMERS


def test_aggregate_nats_metrics_should_raise_error_for_empty_dataframe():
    """
    Test that aggregation raises ValueError for empty DataFrame.

    Edge case: Empty DataFrame should be rejected with clear error.
    """
    # Arrange - empty DataFrame with correct columns
    df = pd.DataFrame(columns=['cpu', 'mem', 'in_msgs', 'out_msgs', 'in_bytes', 'out_bytes'])

    # Act & Assert - should raise ValueError
    with pytest.raises(ValueError, match="DataFrame cannot be empty"):
        aggregate_nats_metrics(df, N_CONSUMERS)


def test_aggregate_nats_metrics_should_raise_error_for_zero_consumers():
    """
    Test that aggregation raises ValueError for zero consumers.

    Edge case: Zero consumers would cause division by zero.
    """
    # Arrange - simple DataFrame with one sample
    df = pd.DataFrame([{
        'cpu': 10.0,
        'mem': 1000000,
        'in_msgs': 100,
        'out_msgs': 100,
        'in_bytes': 5000,
        'out_bytes': 5000
    }])

    # Act & Assert - should raise ValueError
    with pytest.raises(ValueError, match="n_consumers must be greater than 0"):
        aggregate_nats_metrics(df, 0)


def test_aggregate_nats_metrics_should_raise_error_for_negative_consumers():
    """
    Test that aggregation raises ValueError for negative consumers.

    Edge case: Negative consumers is semantically invalid.
    """
    # Arrange - simple DataFrame with one sample
    df = pd.DataFrame([{
        'cpu': 10.0,
        'mem': 1000000,
        'in_msgs': 100,
        'out_msgs': 100,
        'in_bytes': 5000,
        'out_bytes': 5000
    }])

    # Act & Assert - should raise ValueError
    with pytest.raises(ValueError, match="n_consumers must be greater than 0"):
        aggregate_nats_metrics(df, -10)
