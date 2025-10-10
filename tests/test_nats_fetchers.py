import pytest
from benchmark.fetchers import fetch_nats_varz
from benchmark.models import NatsVarzMetrics


@pytest.mark.asyncio
async def test_nats_varz_fetcher_should_return_valid_metrics_with_nonzero_memory_from_running_service():
    """
    Fetch NATS server metrics from real /varz endpoint and validate
    that we receive actual data (memory > 0) from the running service.

    This is the foundation test - it proves we can integrate with NATS monitoring API.
    """
    # Arrange - NATS service already running on localhost:8222
    base_url = "http://localhost:8222"

    # Act - call real endpoint
    metrics = await fetch_nats_varz(base_url)

    # Assert - validate model structure and real data
    assert isinstance(metrics, NatsVarzMetrics)
    assert metrics.mem > 0, "Memory must be > 0 for running NATS service"


@pytest.mark.asyncio
async def test_nats_varz_fetcher_should_return_complete_metrics_from_running_service():
    """
    Fetch complete NATS server metrics and validate all required fields.

    Required fields from BENCHMARK.md:
    - cpu: CPU percentage (0-100%)
    - mem: Memory in bytes (> 0)
    - in_bytes: Network bytes received (>= 0)
    - out_bytes: Network bytes sent (>= 0)
    - in_msgs: Messages received (>= 0)
    - out_msgs: Messages sent (>= 0)
    """
    # Arrange - NATS service already running on localhost:8222
    base_url = "http://localhost:8222"

    # Act - call real endpoint
    metrics = await fetch_nats_varz(base_url)

    # Assert - validate model structure
    assert isinstance(metrics, NatsVarzMetrics)

    # Assert - CPU field (gauge metric, percentage)
    assert hasattr(metrics, 'cpu'), "NatsVarzMetrics should have cpu attribute"
    assert isinstance(metrics.cpu, float), "CPU should be a float"
    assert 0 <= metrics.cpu <= 100, "CPU percentage must be between 0 and 100"

    # Assert - Memory field (gauge metric, bytes)
    assert metrics.mem > 0, "Memory must be > 0 for running NATS service"

    # Assert - Network byte counters
    assert hasattr(metrics, 'in_bytes'), "NatsVarzMetrics should have in_bytes attribute"
    assert metrics.in_bytes >= 0, "in_bytes counter must be >= 0"

    assert hasattr(metrics, 'out_bytes'), "NatsVarzMetrics should have out_bytes attribute"
    assert metrics.out_bytes >= 0, "out_bytes counter must be >= 0"

    # Assert - Message counters
    assert hasattr(metrics, 'in_msgs'), "NatsVarzMetrics should have in_msgs attribute"
    assert metrics.in_msgs >= 0, "in_msgs counter must be >= 0"

    assert hasattr(metrics, 'out_msgs'), "NatsVarzMetrics should have out_msgs attribute"
    assert metrics.out_msgs >= 0, "out_msgs counter must be >= 0"
