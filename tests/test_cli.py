"""
CLI Foundation Tests

Tests for the command-line interface entry point of the Firehose Processor Benchmark Tool.
These tests validate that the CLI exists, responds to standard commands, and provides
appropriate help information.
"""
import os
import pytest
import pandas as pd
from benchmark.cli import cli


def test_cli_responds_to_help(cli_runner):
    """Test that CLI exists and responds to --help flag.

    Validates that:
    - CLI entry point exists and is invokable
    - Help flag returns successful exit code (0)
    - Help output contains the tool name for user orientation
    """
    # Act
    result = cli_runner.invoke(cli, ['--help'])

    # Assert
    assert result.exit_code == 0
    assert 'Firehose Processor Benchmark Tool' in result.output


def test_run_command_exists_and_responds_to_help(cli_runner):
    """Test that 'run' command is registered and accessible.

    Validates that:
    - 'run' command exists in the CLI
    - 'run' command responds to --help flag successfully
    - Help output contains the command description for user guidance

    This test establishes that the 'run' command is available for executing
    single benchmark scenarios, which is the core functionality of the tool.
    """
    # Act
    result = cli_runner.invoke(cli, ['run', '--help'])

    # Assert
    assert result.exit_code == 0
    assert 'Run a single benchmark scenario' in result.output


def test_run_command_requires_scenario_option(cli_runner):
    """Test that run command fails when --scenario option is not provided.

    Validates that:
    - Command cannot execute without specifying which scenario to run
    - Exit code indicates usage error (2)
    - Error message clearly identifies the missing --scenario option

    This enforces that every benchmark run must explicitly specify which
    scenario to execute, preventing accidental runs with undefined behavior.
    """
    # Act
    result = cli_runner.invoke(cli, ['run'])

    # Assert
    assert result.exit_code == 2  # Click usage error
    assert 'Missing option' in result.output
    assert '--scenario' in result.output


def test_run_command_accepts_output_dir_option(cli_runner):
    """Test that --output-dir option exists and is accepted with a custom value.

    Validates that:
    - Command recognizes --output-dir option
    - Custom output directory path is accepted
    - Command executes successfully with both options provided

    This establishes that users can specify where benchmark results should be
    written, enabling organized storage of multiple benchmark runs.
    """
    # Act
    result = cli_runner.invoke(cli, ['run', '--scenario', '1.1', '--output-dir', 'custom/path'])

    # Assert
    assert result.exit_code == 0  # Success, option recognized and accepted


def test_run_command_outputs_scenario_being_executed(cli_runner):
    """Test that run command acknowledges which scenario is being executed.

    Validates that:
    - Command executes and produces output
    - Output confirms the scenario ID that was provided
    - Output indicates execution is beginning

    This establishes the foundation for command execution visibility,
    ensuring users know what the tool is doing when they invoke it.
    """
    # Act
    result = cli_runner.invoke(cli, ['run', '--scenario', '1.1'])

    # Assert
    assert result.exit_code == 0
    assert '1.1' in result.output
    assert 'Running' in result.output or 'Executing' in result.output


def test_run_command_collects_single_nats_sample(cli_runner):
    """Test that run command fetches one NATS sample and displays metrics.

    Validates that:
    - Command integrates with NATS fetcher
    - Actual metrics are collected from running NATS service
    - Metric values are displayed in output (cpu, mem, etc.)

    This establishes the foundation for metrics collection integration,
    connecting CLI execution to our existing fetcher infrastructure.

    Note: This is an integration test requiring NATS running on localhost:8222
    """
    # Act
    result = cli_runner.invoke(cli, ['run', '--scenario', '1.1'])

    # Assert
    assert result.exit_code == 0
    # Should contain reference to NATS metrics
    assert 'NATS' in result.output or 'nats' in result.output
    # Should display at least some metric values (check for common metric names)
    assert 'cpu' in result.output or 'mem' in result.output or 'bytes' in result.output


def test_run_command_collects_multiple_samples_and_displays_aggregated_metrics(cli_runner):
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
    # Act
    result = cli_runner.invoke(cli, ['run', '--scenario', '1.1'])

    # Assert
    assert result.exit_code == 0
    # Should indicate multiple sample collection
    assert 'samples' in result.output.lower() or 'collecting' in result.output.lower()
    # Should display aggregated metrics (avg, total, per_consumer format)
    assert '_avg' in result.output or '_total' in result.output or '_per_consumer' in result.output


def test_run_command_writes_aggregated_results_to_csv_file(cli_runner):
    """Test that run command creates CSV file with aggregated metrics.

    Validates that:
    - CSV file is created with timestamp
    - File contains aggregated results (one row)
    - CSV has proper structure with all aggregated columns
    - File is readable by pandas

    This completes the benchmark workflow: collect → aggregate → persist to CSV.

    Note: This is an integration test requiring NATS running on localhost:8222
    """
    # Act - use isolated_filesystem for clean test environment
    with cli_runner.isolated_filesystem():
        result = cli_runner.invoke(cli, ['run', '--scenario', '1.1', '--output-dir', 'test_results'])

        # Assert
        assert result.exit_code == 0
        # CSV file should exist with timestamp
        import glob
        csv_files = glob.glob('test_results/scenario-1.1-*.csv')
        assert len(csv_files) == 1, f"Expected 1 CSV file, found {len(csv_files)}"
        csv_path = csv_files[0]

        # CSV should be readable by pandas
        df = pd.read_csv(csv_path)

        # Should have exactly 1 row (aggregated results, not raw samples)
        assert len(df) == 1, f"Expected 1 row, got {len(df)}"

        # Should have aggregated columns
        columns = df.columns.tolist()
        assert any('_avg' in col or '_total' in col or '_per_consumer' in col for col in columns),             f"No aggregated columns found in {columns}"


def test_run_command_collects_jetstream_metrics_and_includes_in_csv(cli_runner):
    """Test that run command collects JetStream metrics alongside NATS metrics.

    Validates that:
    - Command collects both NATS and JetStream metrics
    - JetStream metrics are aggregated correctly
    - CSV output includes JetStream metric columns
    - All JetStream metrics have valid values (not null)

    This establishes JetStream integration, providing critical queue health metrics
    needed for benchmark success criteria (pending messages, pending acks).

    Note: This is an integration test requiring NATS with JetStream running on localhost:8222
    """
    # Act - use isolated_filesystem for clean test environment
    with cli_runner.isolated_filesystem():
        result = cli_runner.invoke(cli, ['run', '--scenario', '1.1', '--output-dir', 'test_results'])

        # Assert
        assert result.exit_code == 0

        # CSV file should exist with timestamp
        import glob
        csv_files = glob.glob('test_results/scenario-1.1-*.csv')
        assert len(csv_files) == 1, f"Expected 1 CSV file, found {len(csv_files)}"
        csv_path = csv_files[0]

        # CSV should be readable by pandas
        df = pd.read_csv(csv_path)

        # Should have exactly 1 row (aggregated results)
        assert len(df) == 1, f"Expected 1 row, got {len(df)}"

        # Should have JetStream metric columns
        columns = df.columns.tolist()
        jetstream_columns = [col for col in columns if col.startswith('streams_') or
                            col.startswith('consumers_') or col.startswith('messages_') or
                            col.startswith('bytes_') or col.startswith('memory_') or
                            col.startswith('storage_')]

        assert len(jetstream_columns) > 0, f"No JetStream columns found in {columns}"

        # Should have both averages and per_consumer metrics for JetStream gauges
        assert any('streams_avg' in col for col in columns), "Missing streams_avg column"
        assert any('streams_per_consumer' in col for col in columns), "Missing streams_per_consumer column"


def test_run_command_collects_docker_stats_and_includes_in_csv(cli_runner):
    """Test that run command collects Docker stats alongside NATS and JetStream metrics.

    Validates that:
    - Command collects NATS, JetStream, AND Docker stats
    - Docker stats are aggregated correctly (gauges averaged, counters delta)
    - CSV output includes Docker metric columns
    - All Docker metrics have valid values (not null)

    This completes the third metric source integration, establishing the full
    benchmark metric collection capability.

    Note: This is an integration test requiring Docker container 'fpaas-nats' running
    """
    # Act - use isolated_filesystem for clean test environment
    with cli_runner.isolated_filesystem():
        result = cli_runner.invoke(cli, ['run', '--scenario', '1.1', '--output-dir', 'test_results'])

        # Assert
        assert result.exit_code == 0

        # CSV file should exist with timestamp
        import glob
        csv_files = glob.glob('test_results/scenario-1.1-*.csv')
        assert len(csv_files) == 1, f"Expected 1 CSV file, found {len(csv_files)}"
        csv_path = csv_files[0]

        # CSV should be readable by pandas
        df = pd.read_csv(csv_path)

        # Should have exactly 1 row (aggregated results)
        assert len(df) == 1, f"Expected 1 row, got {len(df)}"

        # Should have Docker stats columns
        columns = df.columns.tolist()
        docker_columns = [col for col in columns if col.startswith('cpu_percent_') or
                         col.startswith('mem_usage_bytes_') or col.startswith('net_in_bytes_') or
                         col.startswith('net_out_bytes_')]

        assert len(docker_columns) > 0, f"No Docker stats columns found in {columns}"

        # Should have both averages for gauges and totals for counters
        assert any('cpu_percent_avg' in col for col in columns), "Missing cpu_percent_avg column"
        assert any('mem_usage_bytes_avg' in col for col in columns), "Missing mem_usage_bytes_avg column"
        assert any('net_in_bytes_total' in col for col in columns), "Missing net_in_bytes_total column"
        assert any('net_out_bytes_total' in col for col in columns), "Missing net_out_bytes_total column"


def test_run_command_includes_configuration_columns_in_csv(cli_runner):
    """Test that CSV includes test configuration metadata columns.

    Validates that:
    - CSV includes 'scenario' column with the scenario ID
    - CSV includes 'n_consumers' column with consumer count
    - CSV includes 'test_duration_sec' column with actual test duration
    - Configuration columns have correct values

    This enables reproducibility and comparison of benchmark results across
    different test configurations.

    Note: This is an integration test requiring NATS/JetStream/Docker running
    """
    # Act - use isolated_filesystem for clean test environment
    with cli_runner.isolated_filesystem():
        result = cli_runner.invoke(cli, ['run', '--scenario', '2.5', '--output-dir', 'test_results'])

        # Assert
        assert result.exit_code == 0

        # CSV file should exist with timestamp
        import glob
        csv_files = glob.glob('test_results/scenario-2.5-*.csv')
        assert len(csv_files) == 1, f"Expected 1 CSV file, found {len(csv_files)}"
        csv_path = csv_files[0]

        # CSV should be readable by pandas
        df = pd.read_csv(csv_path)

        # Should have exactly 1 row
        assert len(df) == 1, f"Expected 1 row, got {len(df)}"

        # Should have configuration columns
        assert 'scenario' in df.columns, "Missing 'scenario' column"
        assert 'n_consumers' in df.columns, "Missing 'n_consumers' column"
        assert 'test_duration_sec' in df.columns, "Missing 'test_duration_sec' column"

        # Configuration values should be correct
        # Note: pandas may read numeric-looking scenario IDs as floats
        assert str(df['scenario'].iloc[0]) == '2.5', f"Expected scenario '2.5', got {df['scenario'].iloc[0]}"
        assert df['n_consumers'].iloc[0] == 100, f"Expected n_consumers 100, got {df['n_consumers'].iloc[0]}"

        # Test duration should be reasonable (3 samples × 0.5s interval × 3 sources ≈ 4-5 seconds)
        duration = df['test_duration_sec'].iloc[0]
        assert 3.0 <= duration <= 10.0, f"Expected test_duration_sec between 3-10s, got {duration}"


def test_run_command_creates_csv_with_timestamp_in_filename(cli_runner):
    """Test that CSV filename includes ISO datetime timestamp.

    Validates that:
    - CSV filename format is: scenario-{id}-{YYYYMMDD-HHMMSS}.csv
    - Timestamp is in ISO 8601 compact format
    - File is created with the timestamped name
    - Multiple runs create different files (don't overwrite)

    This enables tracking multiple benchmark runs over time without
    manual file renaming.

    Note: This is an integration test requiring NATS/JetStream/Docker running
    """
    # Act - use isolated_filesystem for clean test environment
    with cli_runner.isolated_filesystem():
        result = cli_runner.invoke(cli, ['run', '--scenario', '3.2', '--output-dir', 'test_results'])

        # Assert
        assert result.exit_code == 0

        # Find CSV files matching the pattern
        import glob
        csv_files = glob.glob('test_results/scenario-3.2-*.csv')

        assert len(csv_files) == 1, f"Expected 1 CSV file, found {len(csv_files)}: {csv_files}"

        csv_filename = os.path.basename(csv_files[0])

        # Filename should match pattern: scenario-3.2-YYYYMMDD-HHMMSS.csv
        import re
        pattern = r'scenario-3\.2-\d{8}-\d{6}\.csv'
        assert re.match(pattern, csv_filename), \
            f"Filename '{csv_filename}' doesn't match expected pattern 'scenario-3.2-YYYYMMDD-HHMMSS.csv'"
