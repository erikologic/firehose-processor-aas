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
