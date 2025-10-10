import httpx
from benchmark.models import NatsVarzMetrics, JetStreamJszMetrics


async def fetch_nats_varz(base_url: str) -> NatsVarzMetrics:
    """Fetch NATS server metrics from /varz monitoring endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/varz")
        data = response.json()
        return NatsVarzMetrics.model_validate(data)


async def fetch_jetstream_jsz(base_url: str) -> JetStreamJszMetrics:
    """Fetch JetStream metrics from /jsz monitoring endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/jsz")
        data = response.json()
        return JetStreamJszMetrics.model_validate(data)
