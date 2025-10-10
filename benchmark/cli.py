"""
Firehose Processor Benchmark CLI

Command-line interface for running benchmark scenarios and analyzing results.
"""
import asyncio
import os
import time
from datetime import datetime
from typing import Callable, Awaitable
import pandas as pd
import click
from pydantic import BaseModel
from benchmark.fetchers import fetch_nats_varz, fetch_jetstream_jsz, fetch_docker_stats
from benchmark.aggregators import aggregate_nats_metrics, aggregate_jetstream_metrics, aggregate_docker_stats


# Configuration constants
DEFAULT_N_CONSUMERS = 100
SAMPLE_INTERVAL_SECONDS = 5.0  # Hardcoded based on metric natural resolution
DEFAULT_NATS_URL = "http://localhost:8222"
DEFAULT_DOCKER_CONTAINER = "fpaas-nats"


def collect_samples(
    fetcher: Callable[[str], Awaitable[BaseModel]],
    source: str,
    count: int,
    interval: float,
    metric_name: str
) -> pd.DataFrame:
    """Collect multiple metric samples over time using a generic fetcher.

    Args:
        fetcher: Async function that fetches metrics given a source identifier
        source: Source identifier (URL, container name, etc.)
        count: Number of samples to collect
        interval: Seconds to wait between samples
        metric_name: Display name for the metrics being collected

    Returns:
        DataFrame with columns from the Pydantic model returned by fetcher
    """
    click.echo(f"\nCollecting {count} {metric_name} samples...")
    samples = []
    for i in range(count):
        click.echo(f"  Sample {i+1}/{count}...")
        metrics = asyncio.run(fetcher(source))
        samples.append(metrics.model_dump())
        if i < count - 1:  # Don't sleep after last sample
            time.sleep(interval)

    return pd.DataFrame(samples)


def collect_nats_samples(base_url: str, count: int, interval: float) -> pd.DataFrame:
    """Collect multiple NATS metric samples over time.

    Args:
        base_url: NATS monitoring endpoint URL
        count: Number of samples to collect
        interval: Seconds to wait between samples

    Returns:
        DataFrame with columns: cpu, mem, in_msgs, out_msgs, in_bytes, out_bytes
    """
    return collect_samples(fetch_nats_varz, base_url, count, interval, "NATS")


def collect_jetstream_samples(base_url: str, count: int, interval: float) -> pd.DataFrame:
    """Collect multiple JetStream metric samples over time.

    Args:
        base_url: NATS monitoring endpoint URL
        count: Number of samples to collect
        interval: Seconds to wait between samples

    Returns:
        DataFrame with columns: streams, consumers, messages, bytes, memory, storage
    """
    return collect_samples(fetch_jetstream_jsz, base_url, count, interval, "JetStream")


def collect_docker_samples(container_name: str, count: int, interval: float) -> pd.DataFrame:
    """Collect multiple Docker stats samples over time.

    Args:
        container_name: Docker container name to monitor
        count: Number of samples to collect
        interval: Seconds to wait between samples

    Returns:
        DataFrame with columns: container_name, cpu_percent, mem_usage_bytes, net_in_bytes, net_out_bytes
    """
    return collect_samples(fetch_docker_stats, container_name, count, interval, "Docker stats")


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
    """Write aggregated metrics to CSV file with ISO datetime timestamp.

    Args:
        aggregated: Dictionary of aggregated metric values
        scenario: Scenario ID for filename
        output_dir: Directory to write CSV file

    Returns:
        Path to the created CSV file
    """
    os.makedirs(output_dir, exist_ok=True)

    # Generate ISO datetime timestamp: YYYYMMDD-HHMMSS
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    csv_path = os.path.join(output_dir, f"scenario-{scenario}-{timestamp}.csv")
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
@click.option('--duration', required=True, type=int,
              help='Test duration in seconds (e.g., 300 for 5 minutes)')
def run(scenario, output_dir, duration):
    """Run a single benchmark scenario"""
    # Calculate sample count from duration and interval
    sample_count = int(duration / SAMPLE_INTERVAL_SECONDS)

    click.echo(f"Running scenario {scenario}...")
    click.echo(f"Output directory: {output_dir}")
    click.echo(f"Test duration: {duration}s ({sample_count} samples @ {SAMPLE_INTERVAL_SECONDS}s interval)")

    # Track test start time
    start_time = time.time()

    # Collect and aggregate NATS metrics
    nats_df = collect_nats_samples(DEFAULT_NATS_URL, sample_count, SAMPLE_INTERVAL_SECONDS)
    nats_aggregated = aggregate_nats_metrics(nats_df, DEFAULT_N_CONSUMERS)

    # Collect and aggregate JetStream metrics
    jetstream_df = collect_jetstream_samples(DEFAULT_NATS_URL, sample_count, SAMPLE_INTERVAL_SECONDS)
    jetstream_aggregated = aggregate_jetstream_metrics(jetstream_df, DEFAULT_N_CONSUMERS)

    # Collect and aggregate Docker stats
    docker_df = collect_docker_samples(DEFAULT_DOCKER_CONTAINER, sample_count, SAMPLE_INTERVAL_SECONDS)
    docker_aggregated = aggregate_docker_stats(docker_df, DEFAULT_N_CONSUMERS)

    # Calculate test duration
    end_time = time.time()
    test_duration_sec = end_time - start_time

    # Merge all metrics with configuration metadata
    aggregated = {
        'scenario': scenario,
        'n_consumers': DEFAULT_N_CONSUMERS,
        'test_duration_sec': test_duration_sec,
        **nats_aggregated,
        **jetstream_aggregated,
        **docker_aggregated
    }

    # Display and save results
    display_aggregated_metrics(aggregated)
    csv_path = write_results_to_csv(aggregated, scenario, output_dir)
    click.echo(f"\nResults written to {csv_path}")


if __name__ == '__main__':
    cli()
