"""
Firehose Processor Benchmark CLI

Command-line interface for running benchmark scenarios and analyzing results.
"""
import asyncio
import click
from benchmark.fetchers import fetch_nats_varz


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

    # Collect NATS metrics sample
    click.echo("\nCollecting NATS metrics...")
    metrics = asyncio.run(fetch_nats_varz("http://localhost:8222"))

    click.echo(f"  cpu: {metrics.cpu}%")
    click.echo(f"  mem: {metrics.mem} bytes")
    click.echo(f"  in_bytes: {metrics.in_bytes}")
    click.echo(f"  out_bytes: {metrics.out_bytes}")
    click.echo(f"  in_msgs: {metrics.in_msgs}")
    click.echo(f"  out_msgs: {metrics.out_msgs}")


if __name__ == '__main__':
    cli()
