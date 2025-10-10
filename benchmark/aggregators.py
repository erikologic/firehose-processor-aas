import pandas as pd


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
    """
    # Calculate averages for gauge metrics
    cpu_avg = df['cpu'].mean()
    mem_avg = df['mem'].mean()

    # Calculate totals for counter metrics (delta: last - first)
    in_msgs_total = df['in_msgs'].iloc[-1] - df['in_msgs'].iloc[0]
    out_msgs_total = df['out_msgs'].iloc[-1] - df['out_msgs'].iloc[0]
    in_bytes_total = df['in_bytes'].iloc[-1] - df['in_bytes'].iloc[0]
    out_bytes_total = df['out_bytes'].iloc[-1] - df['out_bytes'].iloc[0]

    # Calculate per-consumer metrics
    cpu_per_consumer = cpu_avg / n_consumers
    mem_per_consumer = mem_avg / n_consumers

    return {
        'cpu_avg': cpu_avg,
        'mem_avg': mem_avg,
        'in_msgs_total': in_msgs_total,
        'out_msgs_total': out_msgs_total,
        'in_bytes_total': in_bytes_total,
        'out_bytes_total': out_bytes_total,
        'cpu_per_consumer': cpu_per_consumer,
        'mem_per_consumer': mem_per_consumer,
    }
