import pytest
import pandas as pd
import asyncio
from benchmark.fetchers import fetch_nats_varz, fetch_jetstream_jsz
from benchmark.aggregators import aggregate_nats_metrics, aggregate_jetstream_metrics


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


@pytest.mark.asyncio
async def test_aggregate_jetstream_metrics_should_calculate_averages_and_totals():
    """
    Collect real JetStream samples and aggregate them using pandas.

    Aggregation logic:
    - All metrics are gauges (snapshot values): Calculate average across samples
    - Per-consumer metrics: Divide gauge averages by n_consumers

    Metric classification:
    - All 6 metrics are gauges (snapshot values): streams, consumers, messages, bytes, memory, storage
    - Note: messages and bytes represent "current stored", not cumulative totals
    """
    # Arrange - collect 3 real samples from JetStream
    samples = []
    for _ in range(3):
        metrics = await fetch_jetstream_jsz(NATS_BASE_URL)
        samples.append({
            'streams': metrics.streams,
            'consumers': metrics.consumers,
            'messages': metrics.messages,
            'bytes': metrics.bytes,
            'memory': metrics.memory,
            'storage': metrics.storage,
        })
        await asyncio.sleep(SAMPLE_INTERVAL_SECONDS)  # Wait between samples

    df = pd.DataFrame(samples)

    # Act - aggregate the samples
    result = aggregate_jetstream_metrics(df, N_CONSUMERS)

    # Assert - result should be a dictionary with aggregated metrics
    assert isinstance(result, dict)

    # Assert - All metrics are gauges: check averages
    assert 'streams_avg' in result
    assert 'consumers_avg' in result
    assert 'messages_avg' in result
    assert 'bytes_avg' in result
    assert 'memory_avg' in result
    assert 'storage_avg' in result
    assert result['streams_avg'] >= 0
    assert result['consumers_avg'] >= 0
    assert result['messages_avg'] >= 0
    assert result['bytes_avg'] >= 0
    assert result['memory_avg'] >= 0
    assert result['storage_avg'] >= 0

    # Assert - Per-consumer metrics (all gauges divided by n_consumers)
    assert 'streams_per_consumer' in result
    assert 'consumers_per_consumer' in result
    assert 'messages_per_consumer' in result
    assert 'bytes_per_consumer' in result
    assert 'memory_per_consumer' in result
    assert 'storage_per_consumer' in result
    assert result['streams_per_consumer'] == result['streams_avg'] / N_CONSUMERS
    assert result['consumers_per_consumer'] == result['consumers_avg'] / N_CONSUMERS
    assert result['messages_per_consumer'] == result['messages_avg'] / N_CONSUMERS
    assert result['bytes_per_consumer'] == result['bytes_avg'] / N_CONSUMERS
    assert result['memory_per_consumer'] == result['memory_avg'] / N_CONSUMERS
    assert result['storage_per_consumer'] == result['storage_avg'] / N_CONSUMERS
