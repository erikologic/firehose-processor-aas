"""
Firehose Processor Benchmark CLI

Command-line interface for running benchmark scenarios and analyzing results.
"""
import asyncio
import os
import time
import pandas as pd
import click
from benchmark.fetchers import fetch_nats_varz, fetch_jetstream_jsz
from benchmark.aggregators import aggregate_nats_metrics, aggregate_jetstream_metrics


# Configuration constants
DEFAULT_N_CONSUMERS = 100
DEFAULT_SAMPLE_COUNT = 3
DEFAULT_SAMPLE_INTERVAL_SECONDS = 0.5
DEFAULT_NATS_URL = "http://localhost:8222"


def collect_nats_samples(base_url: str, count: int, interval: float) -> pd.DataFrame:
    """Collect multiple NATS metric samples over time.

    Args:
        base_url: NATS monitoring endpoint URL
        count: Number of samples to collect
        interval: Seconds to wait between samples

    Returns:
        DataFrame with columns: cpu, mem, in_msgs, out_msgs, in_bytes, out_bytes
    """
    click.echo(f"\nCollecting {count} NATS samples...")
    samples = []
    for i in range(count):
        click.echo(f"  Sample {i+1}/{count}...")
        metrics = asyncio.run(fetch_nats_varz(base_url))
        samples.append({
            'cpu': metrics.cpu,
            'mem': metrics.mem,
            'in_msgs': metrics.in_msgs,
            'out_msgs': metrics.out_msgs,
            'in_bytes': metrics.in_bytes,
            'out_bytes': metrics.out_bytes,
        })
        if i < count - 1:  # Don't sleep after last sample
            time.sleep(interval)

    return pd.DataFrame(samples)


def collect_jetstream_samples(base_url: str, count: int, interval: float) -> pd.DataFrame:
    """Collect multiple JetStream metric samples over time.

    Args:
        base_url: NATS monitoring endpoint URL
        count: Number of samples to collect
        interval: Seconds to wait between samples

    Returns:
        DataFrame with columns: streams, consumers, messages, bytes, memory, storage
    """
    click.echo(f"Collecting {count} JetStream samples...")
    samples = []
    for i in range(count):
        click.echo(f"  Sample {i+1}/{count}...")
        metrics = asyncio.run(fetch_jetstream_jsz(base_url))
        samples.append({
            'streams': metrics.streams,
            'consumers': metrics.consumers,
            'messages': metrics.messages,
            'bytes': metrics.bytes,
            'memory': metrics.memory,
            'storage': metrics.storage,
        })
        if i < count - 1:  # Don't sleep after last sample
            time.sleep(interval)

    return pd.DataFrame(samples)


def display_aggregated_metrics(aggregated: dict) -> None:
    """Display aggregated metrics to console.

    Args:
        aggregated: Dictionary of aggregated metric values
    """
    click.echo("\nAggregated Metrics:")
    for key, value in aggregated.items():
        if isinstance(value, float):
            click.echo(f"  {key}: {value:.2f}")
        else:
            click.echo(f"  {key}: {value}")


def write_results_to_csv(aggregated: dict, scenario: str, output_dir: str) -> str:
    """Write aggregated metrics to CSV file.

    Args:
        aggregated: Dictionary of aggregated metric values
        scenario: Scenario ID for filename
        output_dir: Directory to write CSV file

    Returns:
        Path to the created CSV file
    """
    os.makedirs(output_dir, exist_ok=True)
    csv_path = f"{output_dir}/scenario-{scenario}.csv"
    result_df = pd.DataFrame([aggregated])
    result_df.to_csv(csv_path, index=False)
    return csv_path


@click.group()
def cli():
    """Firehose Processor Benchmark Tool"""
    pass


@cli.command()
@click.option('--scenario', required=True, help='Scenario ID (e.g., 1.1, 2.3)')
@click.option('--output-dir', default='results', help='Output directory for CSV')
def run(scenario, output_dir):
    """Run a single benchmark scenario"""
    click.echo(f"Running scenario {scenario}...")
    click.echo(f"Output directory: {output_dir}")

    # Collect and aggregate NATS metrics
    nats_df = collect_nats_samples(DEFAULT_NATS_URL, DEFAULT_SAMPLE_COUNT, DEFAULT_SAMPLE_INTERVAL_SECONDS)
    nats_aggregated = aggregate_nats_metrics(nats_df, DEFAULT_N_CONSUMERS)

    # Collect and aggregate JetStream metrics
    jetstream_df = collect_jetstream_samples(DEFAULT_NATS_URL, DEFAULT_SAMPLE_COUNT, DEFAULT_SAMPLE_INTERVAL_SECONDS)
    jetstream_aggregated = aggregate_jetstream_metrics(jetstream_df, DEFAULT_N_CONSUMERS)

    # Merge all metrics
    aggregated = {**nats_aggregated, **jetstream_aggregated}

    # Display and save results
    display_aggregated_metrics(aggregated)
    csv_path = write_results_to_csv(aggregated, scenario, output_dir)
    click.echo(f"\nResults written to {csv_path}")


if __name__ == '__main__':
    cli()
