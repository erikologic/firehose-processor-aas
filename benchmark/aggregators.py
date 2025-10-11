import pandas as pd

# Metric type constants - defines aggregation strategy
GAUGE_METRICS = ['cpu', 'mem']  # Gauges: use average across samples
COUNTER_METRICS = ['in_msgs', 'out_msgs', 'in_bytes', 'out_bytes']  # Counters: use delta

# JetStream metric type constants - ALL are gauges (snapshot values)
JETSTREAM_GAUGE_METRICS = ['streams', 'consumers', 'messages', 'bytes', 'memory', 'storage']
JETSTREAM_COUNTER_METRICS = []  # No counter metrics for JetStream

# Docker stats metric type constants
DOCKER_GAUGE_METRICS = ['cpu_percent', 'mem_usage_bytes']  # Gauges: snapshots
DOCKER_COUNTER_METRICS = ['net_in_bytes', 'net_out_bytes']  # Counters: cumulative


def aggregate_metrics(df: pd.DataFrame, n_consumers: int, gauge_metrics: list, counter_metrics: list, prefix: str = "") -> dict:
    """
    Generic metric aggregation for time-series samples.

    Aggregates DataFrame samples using metric-type-specific strategies:
    - Gauges (snapshot values): Calculate average across samples, then per-consumer average
    - Counters (cumulative values): Calculate delta (last - first)

    Args:
        df: DataFrame containing metric columns
        n_consumers: Number of consumers for per-consumer calculations
        gauge_metrics: List of gauge metric column names
        counter_metrics: List of counter metric column names
        prefix: Optional prefix to add to all metric names (e.g., "nats_", "js_")

    Returns:
        Dictionary with aggregated metrics:
        - For each gauge: {prefix}{metric}_avg and {prefix}{metric}_per_consumer
        - For each counter: {prefix}{metric}_total

    Raises:
        ValueError: If DataFrame is empty or n_consumers <= 0
    """
    # Input validation
    if df.empty:
        raise ValueError("DataFrame cannot be empty")
    if n_consumers <= 0:
        raise ValueError("n_consumers must be greater than 0")

    # Calculate averages for gauge metrics
    result = {}
    for metric in gauge_metrics:
        avg_value = df[metric].mean()
        result[f'{prefix}{metric}_avg'] = avg_value
        result[f'{prefix}{metric}_per_consumer'] = avg_value / n_consumers

    # Calculate totals for counter metrics (delta: last - first)
    for metric in counter_metrics:
        total_value = df[metric].iloc[-1] - df[metric].iloc[0]
        result[f'{prefix}{metric}_total'] = total_value

    return result


def aggregate_nats_metrics(df: pd.DataFrame, n_consumers: int) -> dict:
    """
    Aggregate NATS metrics samples into summary statistics.

    Args:
        df: DataFrame with columns: cpu, mem, in_msgs, out_msgs, in_bytes, out_bytes
        n_consumers: Number of consumers for per-consumer calculations

    Returns:
        Dictionary with aggregated metrics (prefixed with "nats_"):
        - Gauges (cpu, mem): averages
        - Counters (msgs, bytes): totals (delta between last and first)
        - Per-consumer: divided by n_consumers

    Raises:
        ValueError: If DataFrame is empty or n_consumers <= 0
    """
    return aggregate_metrics(df, n_consumers, GAUGE_METRICS, COUNTER_METRICS, prefix="nats_")


def aggregate_jetstream_metrics(df: pd.DataFrame, n_consumers: int) -> dict:
    """
    Aggregate JetStream metrics samples into summary statistics.

    Args:
        df: DataFrame with columns: streams, consumers, messages, bytes, memory, storage
        n_consumers: Number of consumers for per-consumer calculations

    Returns:
        Dictionary with aggregated metrics (prefixed with "js_"):
        - All metrics are gauges (snapshot values): averages calculated
        - Per-consumer: each average divided by n_consumers

    Raises:
        ValueError: If DataFrame is empty or n_consumers <= 0
    """
    return aggregate_metrics(df, n_consumers, JETSTREAM_GAUGE_METRICS, JETSTREAM_COUNTER_METRICS, prefix="js_")


def aggregate_docker_stats(df: pd.DataFrame, n_consumers: int) -> dict:
    """
    Aggregate Docker stats samples into summary statistics.

    Args:
        df: DataFrame with columns: cpu_percent, mem_usage_bytes, net_in_bytes, net_out_bytes
        n_consumers: Number of consumers for per-consumer calculations

    Returns:
        Dictionary with aggregated metrics (prefixed with "docker_"):
        - Gauges (cpu_percent, mem_usage_bytes): averages
        - Counters (net_in_bytes, net_out_bytes): totals (delta between last and first)
        - Per-consumer: gauge averages divided by n_consumers

    Raises:
        ValueError: If DataFrame is empty or n_consumers <= 0
    """
    return aggregate_metrics(df, n_consumers, DOCKER_GAUGE_METRICS, DOCKER_COUNTER_METRICS, prefix="docker_")
