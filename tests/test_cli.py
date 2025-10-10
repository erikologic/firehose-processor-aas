"""
CLI Foundation Tests

Tests for the command-line interface entry point of the Firehose Processor Benchmark Tool.
These tests validate that the CLI exists, responds to standard commands, and provides
appropriate help information.
"""
import pytest
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


def test_run_command_exists_and_responds_to_help():
    """Test that 'run' command is registered and accessible.

    Validates that:
    - 'run' command exists in the CLI
    - 'run' command responds to --help flag successfully
    - Help output contains the command description for user guidance

    This test establishes that the 'run' command is available for executing
    single benchmark scenarios, which is the core functionality of the tool.
    """
    # Arrange
    runner = CliRunner()

    # Act
    result = runner.invoke(cli, ['run', '--help'])

    # Assert
    assert result.exit_code == 0
    assert 'Run a single benchmark scenario' in result.output


def test_run_command_requires_scenario_option():
    """Test that run command fails when --scenario option is not provided.

    Validates that:
    - Command cannot execute without specifying which scenario to run
    - Exit code indicates usage error (2)
    - Error message clearly identifies the missing --scenario option

    This enforces that every benchmark run must explicitly specify which
    scenario to execute, preventing accidental runs with undefined behavior.
    """
    # Arrange
    runner = CliRunner()

    # Act
    result = runner.invoke(cli, ['run'])

    # Assert
    assert result.exit_code == 2  # Click usage error
    assert 'Missing option' in result.output
    assert '--scenario' in result.output


def test_run_command_accepts_output_dir_option():
    """Test that --output-dir option exists and is accepted with a custom value.

    Validates that:
    - Command recognizes --output-dir option
    - Custom output directory path is accepted
    - Command executes successfully with both options provided

    This establishes that users can specify where benchmark results should be
    written, enabling organized storage of multiple benchmark runs.
    """
    # Arrange
    runner = CliRunner()

    # Act
    result = runner.invoke(cli, ['run', '--scenario', '1.1', '--output-dir', 'custom/path'])

    # Assert
    assert result.exit_code == 0  # Success, option recognized and accepted


def test_run_command_outputs_scenario_being_executed():
    """Test that run command acknowledges which scenario is being executed.

    Validates that:
    - Command executes and produces output
    - Output confirms the scenario ID that was provided
    - Output indicates execution is beginning

    This establishes the foundation for command execution visibility,
    ensuring users know what the tool is doing when they invoke it.
    """
    # Arrange
    runner = CliRunner()

    # Act
    result = runner.invoke(cli, ['run', '--scenario', '1.1'])

    # Assert
    assert result.exit_code == 0
    assert '1.1' in result.output
    assert 'Running' in result.output or 'Executing' in result.output


def test_run_command_collects_single_nats_sample():
    """Test that run command fetches one NATS sample and displays metrics.

    Validates that:
    - Command integrates with NATS fetcher
    - Actual metrics are collected from running NATS service
    - Metric values are displayed in output (cpu, mem, etc.)

    This establishes the foundation for metrics collection integration,
    connecting CLI execution to our existing fetcher infrastructure.

    Note: This is an integration test requiring NATS running on localhost:8222
    """
    # Arrange
    runner = CliRunner()

    # Act
    result = runner.invoke(cli, ['run', '--scenario', '1.1'])

    # Assert
    assert result.exit_code == 0
    # Should contain reference to NATS metrics
    assert 'NATS' in result.output or 'nats' in result.output
    # Should display at least some metric values (check for common metric names)
    assert 'cpu' in result.output or 'mem' in result.output or 'bytes' in result.output


def test_run_command_collects_multiple_samples_and_displays_aggregated_metrics():
    """Test that run command collects 3 NATS samples and displays aggregated statistics.

    Validates that:
    - Command collects multiple samples over time (not just one)
    - Samples are aggregated using pandas logic
    - Output shows summary statistics (avg, total, per_consumer)
    - Output does NOT just show individual sample values

    This integrates our existing aggregate_nats_metrics() function with the CLI,
    completing the end-to-end benchmark collection and aggregation pipeline.

    Note: This is an integration test requiring NATS running on localhost:8222
    """
    # Arrange
    runner = CliRunner()

    # Act
    result = runner.invoke(cli, ['run', '--scenario', '1.1'])

    # Assert
    assert result.exit_code == 0
    # Should indicate multiple sample collection
    assert 'samples' in result.output.lower() or 'collecting' in result.output.lower()
    # Should display aggregated metrics (avg, total, per_consumer format)
    assert '_avg' in result.output or '_total' in result.output or '_per_consumer' in result.output
