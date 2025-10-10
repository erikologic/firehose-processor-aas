"""
CLI Foundation Tests

Tests for the command-line interface entry point of the Firehose Processor Benchmark Tool.
These tests validate that the CLI exists, responds to standard commands, and provides
appropriate help information.
"""
from click.testing import CliRunner
from benchmark.cli import cli


def test_cli_responds_to_help():
    """Test that CLI exists and responds to --help flag.

    Validates that:
    - CLI entry point exists and is invokable
    - Help flag returns successful exit code (0)
    - Help output contains the tool name for user orientation
    """
    # Arrange
    runner = CliRunner()

    # Act
    result = runner.invoke(cli, ['--help'])

    # Assert
    assert result.exit_code == 0
    assert 'Firehose Processor Benchmark Tool' in result.output
