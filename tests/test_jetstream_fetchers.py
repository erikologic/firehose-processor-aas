import pytest
from benchmark.fetchers import fetch_jetstream_jsz
from benchmark.models import JetStreamJszMetrics


# Test configuration
NATS_BASE_URL = "http://localhost:8222"


@pytest.mark.asyncio
async def test_jetstream_jsz_fetcher_should_return_complete_metrics_from_running_service():
    """
    Fetch complete JetStream metrics and validate all required fields.

    Required fields for benchmarking:
    - streams: Number of streams (>= 0)
    - consumers: Number of consumers (>= 0)
    - messages: Total messages (>= 0)
    - bytes: Total storage bytes (>= 0)
    - memory: Memory usage in bytes (>= 0)
    - storage: Storage usage in bytes (>= 0)
    """
    # Arrange - NATS service already running
    # Act - call real endpoint
    metrics = await fetch_jetstream_jsz(NATS_BASE_URL)

    # Assert - validate model structure (Pydantic ensures type safety)
    assert isinstance(metrics, JetStreamJszMetrics)

    # Assert - Stream and consumer counts (>= 0)
    assert metrics.streams >= 0, "streams count must be >= 0"
    assert metrics.consumers >= 0, "consumers count must be >= 0"

    # Assert - Message and byte counts (>= 0)
    assert metrics.messages >= 0, "messages count must be >= 0"
    assert metrics.bytes >= 0, "bytes count must be >= 0"

    # Assert - Resource usage (>= 0)
    assert metrics.memory >= 0, "memory usage must be >= 0"
    assert metrics.storage >= 0, "storage usage must be >= 0"
