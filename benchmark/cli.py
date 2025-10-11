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


async def collect_all_metrics_sample(nats_url: str, container_name: str) -> dict:
    """Collect one sample of all metrics concurrently at the same timestamp.

    Args:
        nats_url: NATS monitoring endpoint URL
        container_name: Docker container name to monitor

    Returns:
        Dictionary with all metrics from NATS, JetStream, and Docker
    """
    # Fetch all metrics concurrently
    nats_task = fetch_nats_varz(nats_url)
    js_task = fetch_jetstream_jsz(nats_url)
    docker_task = fetch_docker_stats(container_name)

    nats_metrics, js_metrics, docker_metrics = await asyncio.gather(
        nats_task, js_task, docker_task
    )

    # Combine all metrics into a single dict
    sample = {}
    sample.update({f"nats_{k}": v for k, v in nats_metrics.model_dump().items()})
    sample.update({f"js_{k}": v for k, v in js_metrics.model_dump().items()})
    sample.update({f"docker_{k}": v for k, v in docker_metrics.model_dump().items()})

    return sample


def collect_all_samples(
    nats_url: str,
    container_name: str,
    count: int,
    interval: float
) -> pd.DataFrame:
    """Collect multiple samples of all metrics over time, with all metrics
    sampled concurrently at each timestamp.

    Args:
        nats_url: NATS monitoring endpoint URL
        container_name: Docker container name to monitor
        count: Number of samples to collect
        interval: Seconds to wait between samples

    Returns:
        DataFrame with all metrics from NATS, JetStream, and Docker
    """
    click.echo(f"\nCollecting {count} samples (all metrics concurrently @ {interval}s interval)...")
    samples = []

    for i in range(count):
        click.echo(f"  Sample {i+1}/{count}...")
        sample = asyncio.run(collect_all_metrics_sample(nats_url, container_name))
        samples.append(sample)

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

    # Collect all metrics concurrently (NATS, JetStream, Docker all at same timestamp)
    all_samples_df = collect_all_samples(
        DEFAULT_NATS_URL,
        DEFAULT_DOCKER_CONTAINER,
        sample_count,
        SAMPLE_INTERVAL_SECONDS
    )

    # Split the combined DataFrame into separate DataFrames for aggregation
    nats_columns = [col for col in all_samples_df.columns if col.startswith('nats_')]
    js_columns = [col for col in all_samples_df.columns if col.startswith('js_')]
    docker_columns = [col for col in all_samples_df.columns if col.startswith('docker_')]

    # Remove prefixes for aggregation functions that expect original column names
    nats_df = all_samples_df[nats_columns].rename(columns=lambda x: x.replace('nats_', ''))
    js_df = all_samples_df[js_columns].rename(columns=lambda x: x.replace('js_', ''))
    docker_df = all_samples_df[docker_columns].rename(columns=lambda x: x.replace('docker_', ''))

    # Aggregate each metric type
    nats_aggregated = aggregate_nats_metrics(nats_df, DEFAULT_N_CONSUMERS)
    jetstream_aggregated = aggregate_jetstream_metrics(js_df, DEFAULT_N_CONSUMERS)
    docker_aggregated = aggregate_docker_stats(docker_df, DEFAULT_N_CONSUMERS)

    # Calculate test duration from samples collected (not wall clock time)
    # This represents the actual test window: (sample_count - 1) intervals between samples
    test_duration_sec = (sample_count - 1) * SAMPLE_INTERVAL_SECONDS

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
