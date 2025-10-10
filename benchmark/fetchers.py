import httpx
from benchmark.models import NatsVarzMetrics


async def fetch_nats_varz(base_url: str) -> NatsVarzMetrics:
    """Fetch NATS server metrics from /varz monitoring endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/varz")
        data = response.json()
        return NatsVarzMetrics.model_validate(data)
