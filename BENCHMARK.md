# FPaaS PoC Benchmark Configuration

## Current Setup

### Architecture
```
ATProto Firehose (bsky.network)
        ↓
    Shuffler (1 instance)
        ↓
NATS JetStream (single node, in-memory)
        ↓
   Consumers (100 instances, pull-based)
```

### Configuration

**Shuffler:**
- Image: `cmd/shuffler/Dockerfile`
- Relay: `wss://bsky.network`
- NATS URL: `nats://nats:4222`
- Metrics: `http://localhost:8080/metrics`

**NATS JetStream:**
- Retention: 5 minutes
- Storage: In-memory (`nats.MemoryStorage`)
- Max Memory: 2GB
- Stream: `ATPROTO_FIREHOSE`
- Subjects: `atproto.firehose.>`
- Deduplication Window: 5 minutes

**Consumers:**
- Count: **Configurable via `CONSUMER_COUNT`** (default: 100)
- Poll Interval: **Configurable via `POLL_INTERVAL_SECONDS`** (default: 60)
- Batch Size: **Configurable via `BATCH_SIZE`** (default: 100)
- Jitter: ±20% random variation on poll interval
- Mode: Pull-based (durable consumers)
- Metrics: `http://localhost:8082/metrics`

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CONSUMER_COUNT` | 1 | Number of consumer instances to spawn |
| `POLL_INTERVAL_SECONDS` | 60 | Seconds between pull requests (with ±20% jitter) |
| `BATCH_SIZE` | 100 | Number of messages to fetch per pull |
| `LOG_LEVEL` | info | Logging verbosity (error, warn, info, debug) |
| `NATS_URL` | nats://nats:4222 | NATS server connection URL |

## Running Benchmarks

### Quick Start
```bash
# Default: 100 consumers, 60s poll interval
DOCKER_BUILDKIT=1 docker compose up --build -d

# Check status
docker compose ps
docker compose logs -f shuffler consumer

# View metrics
curl http://localhost:8080/metrics  # Shuffler published events
curl http://localhost:8082/metrics  # Consumer processed events
curl http://localhost:8222/jsz | jq  # JetStream stats
```

### Custom Configurations

**Test with 10 consumers, 30s poll interval:**
```bash
# Edit docker-compose.yml environment variables:
environment:
  CONSUMER_COUNT: 10
  POLL_INTERVAL_SECONDS: 30
  BATCH_SIZE: 50

# Restart
docker compose up --build -d
```

**Test with 500 consumers, 120s poll interval:**
```bash
environment:
  CONSUMER_COUNT: 500
  POLL_INTERVAL_SECONDS: 120
  BATCH_SIZE: 200
```

**Test with 1000 consumers (stress test):**
```bash
environment:
  CONSUMER_COUNT: 1000
  POLL_INTERVAL_SECONDS: 60
  BATCH_SIZE: 100
```

### Monitoring

**Grafana Dashboards:**
- URL: http://localhost:3001
- Login: admin/admin
- Pre-configured NATS dashboards

**Prometheus:**
- URL: http://localhost:9090
- NATS metrics available

**NATS Monitoring:**
- URL: http://localhost:8222
- Endpoints:
  - `/varz` - Server stats
  - `/jsz` - JetStream stats
  - `/connz` - Connection stats

### Metrics Collection

```bash
# Periodic snapshot script
while true; do
  echo "=== $(date) ==="
  echo "Shuffler: $(curl -s http://localhost:8080/metrics) events"
  echo "Consumers: $(curl -s http://localhost:8082/metrics) events"
  echo "JetStream: $(curl -s http://localhost:8222/jsz | jq '{messages: .messages, bytes: .bytes, consumers: .consumers}')"
  echo ""
  sleep 30
done
```

## Benchmark Scenarios

### Scenario 1: Baseline (Current)
- **Consumers:** 100
- **Poll Interval:** 60s
- **Batch Size:** 100
- **Goal:** Validate basic functionality

### Scenario 2: High Frequency Polling
- **Consumers:** 100
- **Poll Interval:** 10s
- **Batch Size:** 50
- **Goal:** Test rapid polling impact on NATS

### Scenario 3: Scale Test
- **Consumers:** 1000
- **Poll Interval:** 60s
- **Batch Size:** 100
- **Goal:** Maximum consumer count test

### Scenario 4: Large Batches
- **Consumers:** 50
- **Poll Interval:** 120s
- **Batch Size:** 500
- **Goal:** Test batch processing efficiency

### Scenario 5: Real-time Simulation
- **Consumers:** 200
- **Poll Interval:** 5s
- **Batch Size:** 20
- **Goal:** Near real-time processing

## Key Metrics to Track

1. **Throughput**
   - Shuffler publish rate (msgs/sec)
   - Consumer process rate (msgs/sec)
   - Per-consumer throughput

2. **Latency**
   - Time from publish to first consumer fetch
   - End-to-end message latency

3. **Resource Usage**
   - NATS CPU/Memory
   - Shuffler CPU/Memory
   - Consumer CPU/Memory (aggregate)

4. **JetStream Health**
   - Stream messages count
   - Stream bytes used
   - Consumer lag
   - Slow consumers count

5. **Reliability**
   - Message loss (published vs consumed)
   - Failed fetches
   - Connection errors
   - Duplicate messages (dedup working?)

## Expected Results (Initial PoC)

Based on previous testing:
- **Firehose rate:** ~400-500 msgs/sec
- **100 consumers:** Each receives ~4-5 msgs/sec
- **Memory usage:** ~140-200 MB for 100 consumers
- **CPU usage:** Sub-linear scaling
- **No slow consumers:** With 60s poll interval

## Cleanup

```bash
# Stop and remove all containers
docker compose down

# Remove volumes (reset state)
docker compose down -v

# View logs before cleanup
docker compose logs > poc-logs.txt
```

## Next Steps

After validating PoC:
1. Test different consumer counts (10, 50, 100, 500, 1000)
2. Test different poll intervals (5s, 30s, 60s, 120s)
3. Measure actual message sizes for storage calculations
4. Test failure scenarios (NATS restart, consumer crashes)
5. Implement proper cursor persistence
6. Add backpressure handling to shuffler
