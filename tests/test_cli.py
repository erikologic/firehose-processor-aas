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
