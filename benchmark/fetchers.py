import httpx
import asyncio
import json
from benchmark.models import NatsVarzMetrics, JetStreamJszMetrics, DockerStatsMetrics


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


def _parse_bytes(value: str) -> int:
    """Parse Docker stats byte values like '833.8MiB' or '5.41GB' to bytes"""
    value = value.strip()
    # Check longer units first to avoid partial matches
    units = [
        ("GiB", 1024**3), ("MiB", 1024**2), ("KiB", 1024),
        ("GB", 1_000_000_000), ("MB", 1_000_000), ("kB", 1000), ("B", 1)
    ]

    for unit, multiplier in units:
        if value.endswith(unit):
            number = float(value[:-len(unit)])
            return int(number * multiplier)

    return int(float(value))


async def fetch_docker_stats(container_name: str) -> DockerStatsMetrics:
    """Fetch Docker container stats using docker stats command"""
    # Run docker stats command
    process = await asyncio.create_subprocess_exec(
        "docker", "stats", "--no-stream", "--format", "{{json .}}", container_name,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await process.communicate()
    data = json.loads(stdout.decode())

    # Parse percentage: "4.34%" -> 4.34
    cpu_percent = float(data["CPUPerc"].rstrip("%"))

    # Parse memory: "833.8MiB / 15.6GiB" -> extract first value in bytes
    mem_usage_str = data["MemUsage"].split("/")[0].strip()
    mem_usage_bytes = _parse_bytes(mem_usage_str)

    # Parse network I/O: "5.41GB / 235MB" -> in_bytes / out_bytes
    net_parts = data["NetIO"].split("/")
    net_in_bytes = _parse_bytes(net_parts[0].strip())
    net_out_bytes = _parse_bytes(net_parts[1].strip())

    return DockerStatsMetrics(
        container_name=container_name,
        cpu_percent=cpu_percent,
        mem_usage_bytes=mem_usage_bytes,
        net_in_bytes=net_in_bytes,
        net_out_bytes=net_out_bytes
    )
