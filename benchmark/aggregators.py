import pandas as pd

# Metric type constants - defines aggregation strategy
GAUGE_METRICS = ['cpu', 'mem']  # Gauges: use average across samples
COUNTER_METRICS = ['in_msgs', 'out_msgs', 'in_bytes', 'out_bytes']  # Counters: use delta


def aggregate_nats_metrics(df: pd.DataFrame, n_consumers: int) -> dict:
    """
    Aggregate NATS metrics samples into summary statistics.

    Args:
        df: DataFrame with columns: cpu, mem, in_msgs, out_msgs, in_bytes, out_bytes
        n_consumers: Number of consumers for per-consumer calculations

    Returns:
        Dictionary with aggregated metrics:
        - Gauges (cpu, mem): averages
        - Counters (msgs, bytes): totals (delta between last and first)
        - Per-consumer: divided by n_consumers

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
    for metric in GAUGE_METRICS:
        avg_value = df[metric].mean()
        result[f'{metric}_avg'] = avg_value
        result[f'{metric}_per_consumer'] = avg_value / n_consumers

    # Calculate totals for counter metrics (delta: last - first)
    for metric in COUNTER_METRICS:
        total_value = df[metric].iloc[-1] - df[metric].iloc[0]
        result[f'{metric}_total'] = total_value

    return result
