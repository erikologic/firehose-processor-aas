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
from benchmark.fetchers import (
    fetch_nats_varz,
    fetch_jetstream_jsz,
    fetch_docker_stats,
    fetch_shuffler_metrics,
    fetch_consumer_metrics
)
from benchmark.aggregators import (
    aggregate_nats_metrics,
    aggregate_jetstream_metrics,
    aggregate_docker_stats,
    aggregate_shuffler_metrics,
    aggregate_consumer_metrics
)


# Configuration constants
DEFAULT_N_CONSUMERS = 100
SAMPLE_INTERVAL_SECONDS = 5.0  # Hardcoded based on metric natural resolution
DEFAULT_NATS_URL = "http://localhost:8222"
DEFAULT_SHUFFLER_URL = "http://localhost:8080"
DEFAULT_CONSUMER_URL = "http://localhost:8082"
DEFAULT_DOCKER_CONTAINER = "fpaas-nats"
SHUFFLER_DOCKER_CONTAINER = "fpaas-shuffler"
CONSUMER_DOCKER_CONTAINER = "fpaas-consumer"


async def collect_all_metrics_sample(
    nats_url: str,
    shuffler_url: str,
    consumer_url: str,
    nats_container: str,
    shuffler_container: str,
    consumer_container: str
) -> dict:
    """Collect one sample of all metrics concurrently at the same timestamp.

    Args:
        nats_url: NATS monitoring endpoint URL
        shuffler_url: Shuffler metrics endpoint URL
        consumer_url: Consumer metrics endpoint URL
        nats_container: NATS Docker container name
        shuffler_container: Shuffler Docker container name
        consumer_container: Consumer Docker container name

    Returns:
        Dictionary with all metrics from all services
    """
    # Fetch all metrics concurrently
    nats_task = fetch_nats_varz(nats_url)
    js_task = fetch_jetstream_jsz(nats_url)
    shuffler_task = fetch_shuffler_metrics(shuffler_url)
    consumer_task = fetch_consumer_metrics(consumer_url)
    nats_docker_task = fetch_docker_stats(nats_container)
    shuffler_docker_task = fetch_docker_stats(shuffler_container)
    consumer_docker_task = fetch_docker_stats(consumer_container)

    (nats_metrics, js_metrics, shuffler_metrics, consumer_metrics,
     nats_docker, shuffler_docker, consumer_docker) = await asyncio.gather(
        nats_task, js_task, shuffler_task, consumer_task,
        nats_docker_task, shuffler_docker_task, consumer_docker_task
    )

    # Combine all metrics into a single dict with appropriate prefixes
    sample = {}
    sample.update({f"nats_{k}": v for k, v in nats_metrics.model_dump().items()})
    sample.update({f"js_{k}": v for k, v in js_metrics.model_dump().items()})
    sample.update({f"shuffler_{k}": v for k, v in shuffler_metrics.model_dump().items()})
    sample.update({f"consumer_{k}": v for k, v in consumer_metrics.model_dump().items()})
    sample.update({f"nats_docker_{k}": v for k, v in nats_docker.model_dump().items() if k != 'container_name'})
    sample.update({f"shuffler_docker_{k}": v for k, v in shuffler_docker.model_dump().items() if k != 'container_name'})
    sample.update({f"consumer_docker_{k}": v for k, v in consumer_docker.model_dump().items() if k != 'container_name'})

    return sample


def collect_all_samples(
    nats_url: str,
    shuffler_url: str,
    consumer_url: str,
    nats_container: str,
    shuffler_container: str,
    consumer_container: str,
    count: int,
    interval: float
) -> pd.DataFrame:
    """Collect multiple samples of all metrics over time, with all metrics
    sampled concurrently at each timestamp.

    Args:
        nats_url: NATS monitoring endpoint URL
        shuffler_url: Shuffler metrics endpoint URL
        consumer_url: Consumer metrics endpoint URL
        nats_container: NATS Docker container name
        shuffler_container: Shuffler Docker container name
        consumer_container: Consumer Docker container name
        count: Number of samples to collect
        interval: Seconds to wait between samples

    Returns:
        DataFrame with all metrics from all services
    """
    click.echo(f"\nCollecting {count} samples (all metrics concurrently @ {interval}s interval)...")
    samples = []

    for i in range(count):
        click.echo(f"  Sample {i+1}/{count}...")
        sample = asyncio.run(collect_all_metrics_sample(
            nats_url, shuffler_url, consumer_url,
            nats_container, shuffler_container, consumer_container
        ))
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


def write_results_to_csv(aggregated: dict, scenario: str, output_dir: str, output_file: str = None) -> str:
    """Write aggregated metrics to CSV file with ISO datetime timestamp.

    Args:
        aggregated: Dictionary of aggregated metric values
        scenario: Scenario ID for filename (used only if output_file not specified)
        output_dir: Directory to write CSV file
        output_file: Optional specific filename to write/append to

    Returns:
        Path to the created/updated CSV file
    """
    os.makedirs(output_dir, exist_ok=True)

    if output_file:
        # Use specified output file - append if exists, create if not
        csv_path = os.path.join(output_dir, output_file)
        result_df = pd.DataFrame([aggregated])

        if os.path.exists(csv_path):
            # Append without header
            result_df.to_csv(csv_path, mode='a', header=False, index=False)
        else:
            # Create new file with header
            result_df.to_csv(csv_path, index=False)
    else:
        # Generate unique filename with timestamp (legacy behavior)
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
@click.option('--output-file', default=None, help='Output CSV filename (will append if exists). If not specified, generates unique filename.')
@click.option('--duration', required=True, type=int,
              help='Test duration in seconds (e.g., 300 for 5 minutes)')
@click.option('--consumers', default=DEFAULT_N_CONSUMERS, type=int,
              help=f'Number of consumer instances (default: {DEFAULT_N_CONSUMERS})')
def run(scenario, output_dir, output_file, duration, consumers):
    """Run a single benchmark scenario"""
    # Calculate sample count from duration and interval
    sample_count = int(duration / SAMPLE_INTERVAL_SECONDS)

    click.echo(f"Running scenario {scenario}...")
    click.echo(f"Output directory: {output_dir}")
    if output_file:
        click.echo(f"Output file: {output_file} (append mode)")
    else:
        click.echo(f"Output file: auto-generated with timestamp")
    click.echo(f"Test duration: {duration}s ({sample_count} samples @ {SAMPLE_INTERVAL_SECONDS}s interval)")
    click.echo(f"Consumers: {consumers}")

    # Collect all metrics concurrently (all services at same timestamp)
    all_samples_df = collect_all_samples(
        DEFAULT_NATS_URL,
        DEFAULT_SHUFFLER_URL,
        DEFAULT_CONSUMER_URL,
        DEFAULT_DOCKER_CONTAINER,
        SHUFFLER_DOCKER_CONTAINER,
        CONSUMER_DOCKER_CONTAINER,
        sample_count,
        SAMPLE_INTERVAL_SECONDS
    )

    # Split the combined DataFrame into separate DataFrames for aggregation
    nats_columns = [col for col in all_samples_df.columns if col.startswith('nats_') and not col.startswith('nats_docker_')]
    js_columns = [col for col in all_samples_df.columns if col.startswith('js_')]
    shuffler_columns = [col for col in all_samples_df.columns if col.startswith('shuffler_') and not col.startswith('shuffler_docker_')]
    consumer_columns = [col for col in all_samples_df.columns if col.startswith('consumer_') and not col.startswith('consumer_docker_')]
    nats_docker_columns = [col for col in all_samples_df.columns if col.startswith('nats_docker_')]
    shuffler_docker_columns = [col for col in all_samples_df.columns if col.startswith('shuffler_docker_')]
    consumer_docker_columns = [col for col in all_samples_df.columns if col.startswith('consumer_docker_')]

    # Remove prefixes for aggregation functions that expect original column names
    nats_df = all_samples_df[nats_columns].rename(columns=lambda x: x.replace('nats_', ''))
    js_df = all_samples_df[js_columns].rename(columns=lambda x: x.replace('js_', ''))
    shuffler_df = all_samples_df[shuffler_columns].rename(columns=lambda x: x.replace('shuffler_', ''))
    consumer_df = all_samples_df[consumer_columns].rename(columns=lambda x: x.replace('consumer_', ''))
    nats_docker_df = all_samples_df[nats_docker_columns].rename(columns=lambda x: x.replace('nats_docker_', ''))
    shuffler_docker_df = all_samples_df[shuffler_docker_columns].rename(columns=lambda x: x.replace('shuffler_docker_', ''))
    consumer_docker_df = all_samples_df[consumer_docker_columns].rename(columns=lambda x: x.replace('consumer_docker_', ''))

    # Aggregate each metric type
    nats_aggregated = aggregate_nats_metrics(nats_df, consumers)
    jetstream_aggregated = aggregate_jetstream_metrics(js_df, consumers)
    shuffler_aggregated = aggregate_shuffler_metrics(shuffler_df, consumers)
    consumer_aggregated = aggregate_consumer_metrics(consumer_df, consumers)
    nats_docker_aggregated = aggregate_docker_stats(nats_docker_df, consumers)
    shuffler_docker_aggregated = aggregate_docker_stats(shuffler_docker_df, consumers)
    consumer_docker_aggregated = aggregate_docker_stats(consumer_docker_df, consumers)

    # Calculate test duration from samples collected (not wall clock time)
    # This represents the actual test window: (sample_count - 1) intervals between samples
    test_duration_sec = (sample_count - 1) * SAMPLE_INTERVAL_SECONDS

    # Merge all metrics with configuration metadata
    aggregated = {
        'scenario': scenario,
        'n_consumers': consumers,
        'test_duration_sec': test_duration_sec,
        **nats_aggregated,
        **jetstream_aggregated,
        **docker_aggregated
    }

    # Display and save results
    display_aggregated_metrics(aggregated)
    csv_path = write_results_to_csv(aggregated, scenario, output_dir, output_file)

    if output_file and os.path.exists(csv_path):
        # Show row count if appending
        df = pd.read_csv(csv_path)
        click.echo(f"\nResults appended to {csv_path} (now {len(df)} rows)")
    else:
        click.echo(f"\nResults written to {csv_path}")


if __name__ == '__main__':
    cli()
