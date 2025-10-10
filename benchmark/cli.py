"""
Firehose Processor Benchmark CLI

Command-line interface for running benchmark scenarios and analyzing results.
"""
import click


@click.group()
def cli():
    """Firehose Processor Benchmark Tool"""
    pass


if __name__ == '__main__':
    cli()
