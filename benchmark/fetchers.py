import httpx
import asyncio
import json
import re
from benchmark.models import (
    NatsVarzMetrics,
    JetStreamJszMetrics,
    DockerStatsMetrics,
    ShufflerMetrics,
    ConsumerMetrics
)


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


def _parse_prometheus_metric(text: str, metric_name: str) -> float:
    """Parse a Prometheus metric value from text format

    Example input:
        # HELP firehose_messages_read_total Total messages
        # TYPE firehose_messages_read_total counter
        firehose_messages_read_total 12345

    Returns: 12345.0
    """
    pattern = rf'^{re.escape(metric_name)}\s+([0-9.]+)'
    for line in text.split('\n'):
        if line.startswith('#'):
            continue
        match = re.match(pattern, line)
        if match:
            return float(match.group(1))
    raise ValueError(f"Metric {metric_name} not found in Prometheus output")


async def fetch_shuffler_metrics(base_url: str) -> ShufflerMetrics:
    """Fetch Shuffler application metrics from /metrics endpoint (Prometheus format)"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/metrics")
        response.raise_for_status()
        text = response.text

        messages_read = _parse_prometheus_metric(text, "firehose_messages_read_total")
        cursor_position = _parse_prometheus_metric(text, "firehose_cursor_position")

        return ShufflerMetrics(
            firehose_messages_read_total=int(messages_read),
            firehose_cursor_position=int(cursor_position)
        )


async def fetch_consumer_metrics(base_url: str) -> ConsumerMetrics:
    """Fetch Consumer service metrics from /metrics endpoint (Prometheus format)"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/metrics")
        response.raise_for_status()
        text = response.text

        messages_processed = _parse_prometheus_metric(text, "consumer_messages_processed_total")

        return ConsumerMetrics(
            consumer_messages_processed_total=int(messages_processed)
        )
