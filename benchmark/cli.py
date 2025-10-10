"""
Firehose Processor Benchmark CLI

Command-line interface for running benchmark scenarios and analyzing results.
"""
import asyncio
import os
import time
import pandas as pd
import click
from benchmark.fetchers import fetch_nats_varz
from benchmark.aggregators import aggregate_nats_metrics


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

    # Collect multiple NATS metrics samples
    click.echo("\nCollecting 3 NATS samples...")
    samples = []
    for i in range(3):
        click.echo(f"  Sample {i+1}/3...")
        metrics = asyncio.run(fetch_nats_varz("http://localhost:8222"))
        samples.append({
            'cpu': metrics.cpu,
            'mem': metrics.mem,
            'in_msgs': metrics.in_msgs,
            'out_msgs': metrics.out_msgs,
            'in_bytes': metrics.in_bytes,
            'out_bytes': metrics.out_bytes,
        })
        if i < 2:  # Don't sleep after last sample
            time.sleep(0.5)

    # Aggregate samples
    df = pd.DataFrame(samples)
    n_consumers = 100  # Default for now
    aggregated = aggregate_nats_metrics(df, n_consumers)

    # Display aggregated results
    click.echo("\nAggregated Metrics:")
    for key, value in aggregated.items():
        if isinstance(value, float):
            click.echo(f"  {key}: {value:.2f}")
        else:
            click.echo(f"  {key}: {value}")

    # Write results to CSV
    os.makedirs(output_dir, exist_ok=True)
    csv_path = f"{output_dir}/scenario-{scenario}.csv"
    result_df = pd.DataFrame([aggregated])
    result_df.to_csv(csv_path, index=False)
    click.echo(f"\nResults written to {csv_path}")


if __name__ == '__main__':
    cli()
