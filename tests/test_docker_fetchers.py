import pytest
from benchmark.fetchers import fetch_docker_stats
from benchmark.models import DockerStatsMetrics


@pytest.mark.asyncio
async def test_docker_stats_fetcher_should_return_metrics_from_running_container():
    """
    Fetch Docker stats for a running container and validate metrics.

    Required fields:
    - container_name: Container name
    - cpu_percent: CPU usage percentage (0-100)
    - mem_usage_bytes: Memory usage in bytes (>= 0)
    - net_in_bytes: Network bytes received (>= 0)
    - net_out_bytes: Network bytes sent (>= 0)
    """
    # Arrange - NATS container is running
    container_name = "fpaas-nats"

    # Act - fetch stats from real container
    metrics = await fetch_docker_stats(container_name)

    # Assert - validate model structure (Pydantic ensures type safety)
    assert isinstance(metrics, DockerStatsMetrics)

    # Assert - container name matches
    assert metrics.container_name == container_name

    # Assert - CPU percentage (0-100)
    assert 0 <= metrics.cpu_percent <= 100, "CPU percent must be between 0 and 100"

    # Assert - Memory usage (> 0 for running container)
    assert metrics.mem_usage_bytes > 0, "Memory usage must be > 0 for running container"

    # Assert - Network I/O (>= 0)
    assert metrics.net_in_bytes >= 0, "Network in bytes must be >= 0"
    assert metrics.net_out_bytes >= 0, "Network out bytes must be >= 0"
