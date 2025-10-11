import pytest
import pandas as pd
import asyncio
from benchmark.fetchers import fetch_nats_varz, fetch_jetstream_jsz, fetch_docker_stats
from benchmark.aggregators import aggregate_nats_metrics, aggregate_jetstream_metrics, aggregate_docker_stats


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

    # Assert - Gauge metrics: averages (prefixed with "nats_")
    assert 'nats_cpu_avg' in result
    assert 'nats_mem_avg' in result
    assert result['nats_cpu_avg'] >= 0
    assert result['nats_mem_avg'] > 0

    # Assert - Counter metrics: totals (delta) (prefixed with "nats_")
    assert 'nats_in_msgs_total' in result
    assert 'nats_out_msgs_total' in result
    assert 'nats_in_bytes_total' in result
    assert 'nats_out_bytes_total' in result
    assert result['nats_in_msgs_total'] >= 0
    assert result['nats_out_msgs_total'] >= 0
    assert result['nats_in_bytes_total'] >= 0
    assert result['nats_out_bytes_total'] >= 0

    # Assert - Per-consumer metrics (prefixed with "nats_")
    assert 'nats_cpu_per_consumer' in result
    assert 'nats_mem_per_consumer' in result
    assert result['nats_cpu_per_consumer'] == result['nats_cpu_avg'] / N_CONSUMERS
    assert result['nats_mem_per_consumer'] == result['nats_mem_avg'] / N_CONSUMERS


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

    # Assert - All metrics are gauges: check averages (prefixed with "js_")
    assert 'js_streams_avg' in result
    assert 'js_consumers_avg' in result
    assert 'js_messages_avg' in result
    assert 'js_bytes_avg' in result
    assert 'js_memory_avg' in result
    assert 'js_storage_avg' in result
    assert result['js_streams_avg'] >= 0
    assert result['js_consumers_avg'] >= 0
    assert result['js_messages_avg'] >= 0
    assert result['js_bytes_avg'] >= 0
    assert result['js_memory_avg'] >= 0
    assert result['js_storage_avg'] >= 0

    # Assert - Per-consumer metrics (all gauges divided by n_consumers) (prefixed with "js_")
    assert 'js_streams_per_consumer' in result
    assert 'js_consumers_per_consumer' in result
    assert 'js_messages_per_consumer' in result
    assert 'js_bytes_per_consumer' in result
    assert 'js_memory_per_consumer' in result
    assert 'js_storage_per_consumer' in result
    assert result['js_streams_per_consumer'] == result['js_streams_avg'] / N_CONSUMERS
    assert result['js_consumers_per_consumer'] == result['js_consumers_avg'] / N_CONSUMERS
    assert result['js_messages_per_consumer'] == result['js_messages_avg'] / N_CONSUMERS
    assert result['js_bytes_per_consumer'] == result['js_bytes_avg'] / N_CONSUMERS
    assert result['js_memory_per_consumer'] == result['js_memory_avg'] / N_CONSUMERS
    assert result['js_storage_per_consumer'] == result['js_storage_avg'] / N_CONSUMERS


@pytest.mark.asyncio
async def test_aggregate_docker_stats_should_calculate_averages_and_deltas():
    """
    Collect real Docker stats samples and aggregate them using pandas.

    Aggregation logic:
    - Gauges (cpu_percent, mem_usage_bytes): Calculate average across samples
      Gauges represent snapshot values at a point in time
    - Counters (net_in_bytes, net_out_bytes): Calculate delta (last - first)
      Counters are cumulative values that always increase
    - Per-consumer metrics: Divide aggregates by n_consumers

    Metric classification:
    - Gauges: cpu_percent, mem_usage_bytes (snapshot values)
    - Counters: net_in_bytes, net_out_bytes (cumulative totals)
    """
    # Arrange - collect 3 real samples from Docker stats
    samples = []
    for _ in range(3):
        stats = await fetch_docker_stats("fpaas-nats")
        samples.append({
            'cpu_percent': stats.cpu_percent,
            'mem_usage_bytes': stats.mem_usage_bytes,
            'net_in_bytes': stats.net_in_bytes,
            'net_out_bytes': stats.net_out_bytes,
        })
        await asyncio.sleep(SAMPLE_INTERVAL_SECONDS)  # Wait between samples

    df = pd.DataFrame(samples)

    # Act - aggregate the samples
    result = aggregate_docker_stats(df, N_CONSUMERS)

    # Assert - result should be a dictionary with aggregated metrics
    assert isinstance(result, dict)

    # Assert - Gauge metrics: averages (prefixed with "docker_")
    assert 'docker_cpu_percent_avg' in result
    assert 'docker_mem_usage_bytes_avg' in result
    assert result['docker_cpu_percent_avg'] >= 0
    assert result['docker_mem_usage_bytes_avg'] >= 0

    # Assert - Counter metrics: totals (delta) (prefixed with "docker_")
    assert 'docker_net_in_bytes_total' in result
    assert 'docker_net_out_bytes_total' in result
    assert result['docker_net_in_bytes_total'] >= 0
    assert result['docker_net_out_bytes_total'] >= 0

    # Assert - Per-consumer metrics (prefixed with "docker_")
    assert 'docker_cpu_percent_per_consumer' in result
    assert 'docker_mem_usage_bytes_per_consumer' in result
    assert result['docker_cpu_percent_per_consumer'] == result['docker_cpu_percent_avg'] / N_CONSUMERS
    assert result['docker_mem_usage_bytes_per_consumer'] == result['docker_mem_usage_bytes_avg'] / N_CONSUMERS
