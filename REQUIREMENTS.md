# Firehose Processor-as-a-Service (FPaaS) - Requirements

## Project Vision

Transform ATProto Firehose consumption from a complex infrastructure challenge into a simple managed service, democratizing access to the ATProto ecosystem through:
- Subscription-based processing via API
- Webhook integration for serverless compatibility
- Automatic scaling and fault tolerance
- Zero-setup developer experience

---

## Architecture Overview

```
┌─────────────────────┐
│  ATProto Firehose   │
│  (bsky.network)     │
└──────────┬──────────┘
           │
           ├────────────────────────────────────┐
           │                                    │
    ┌──────▼─────────┐              ┌──────────▼─────┐
    │   Shuffler 1   │              │   Shuffler 2   │
    │ (Firehose→NATS)│              │ (Firehose→NATS)│
    └──────┬─────────┘              └────────┬───────┘
           │                                  │
           └────────────┬─────────────────────┘
                        │
              ┌─────────▼──────────┐
              │  NATS JetStream    │
              │    (Cluster)       │
              │  - Deduplication   │
              │  - 24hr Retention  │
              │  - 3+ Nodes        │
              └─────────┬──────────┘
                        │
              ┌─────────▼──────────┐
              │  Consumer Services │
              │  (1000s instances) │
              │   Pull Mode (1min) │
              └────────────────────┘
```

---

## System Components

### 1. Shuffler (Firehose → NATS Publisher)

**Purpose:** Consume from ATProto firehose and publish events to NATS JetStream

**Scale:**
- MVP: 1 instance
- Production: 2 instances (High Availability)

**Critical Problems to Solve:**

#### Problem: Backpressure Management
- Firehose streams at ~350-500 msgs/sec continuously
- NATS may become unavailable (network partition, node failure, cluster rebalancing)
- Current implementation crashes on publish failure
- **Questions:**
  - How do we handle incoming firehose events when NATS is down?
  - Do we buffer in memory? Disk? Drop events?
  - What's the maximum acceptable buffer size before we need to pause?

#### Problem: Cursor/Resumption Strategy
- Firehose events contain sequence cursors for resumption
- Crashes or restarts need to resume from last known position
- **Questions:**
  - Where do we persist cursors? (NATS KV? File? Redis?)
  - How often do we checkpoint cursors?
  - How do we coordinate cursors between 2 shuffler instances?

#### Problem: Failure Modes
- NATS cluster reconnection takes ~15 seconds
- During reconnection, events buffer locally (8MB default)
- Buffer overflow causes publish failures
- **Questions:**
  - Should we pause firehose consumption during NATS outages?
  - How do we gracefully reconnect and drain buffers?
  - What's the retry strategy for failed publishes?

#### Problem: Dual-Shuffler Coordination (HA)
- 2 shufflers reading same firehose stream
- Both publish to NATS with same message IDs (deduplication)
- **Questions:**
  - Do both shufflers consume independently? (likely yes, relying on NATS dedup)
  - How do we handle cursor coordination?
  - Is there a leader election needed, or just let both run?

---

### 2. NATS JetStream Cluster

**Purpose:** Durable message queue with deduplication, replication, and persistence

**Scale:**
- MVP: 1 node (development only)
- Production: 3+ nodes (minimum for quorum and HA)

**Configuration Requirements:**

#### Deduplication
- Uses message ID (SHA256 hash of firehose event)
- Deduplication window: TBD (5 minutes current, needs review)
- Prevents duplicate ingestion from dual shufflers

#### Retention Policy
- **Target:** 24 hours of firehose data
- **Storage Calculation Needed:**
  - Firehose rate: ~400-500 msgs/sec
  - Average message size: TBD (need to measure)
  - Daily volume: ~35M messages/day
  - Storage estimate: **NEEDS CALCULATION**
  - Per-node storage: Total / 3 (for R=3 replication)

#### Replication Factor
- R=3 (recommended for production)
- Tolerates 1 node failure
- Quorum: 2/3 nodes required

#### Stream Configuration
- Subject: `atproto.firehose.>`
- Storage: File-based (not memory, for 24hr retention)
- Max Age: 24 hours
- Max Messages: TBD (based on volume calculation)
- Max Bytes: TBD (based on storage calculation)

---

### 3. Consumer Services

**Purpose:** Application-specific processing of firehose events

**Scale:** Thousands of concurrent consumers

**Access Pattern:**
- **Pull mode** (not push)
- Polling interval: 1 minute
- Batch size: TBD (balance between latency and throughput)

**Questions:**
- How do we handle consumer scaling (1 → 1000+ consumers)?
- What's the per-consumer resource overhead?
- Do consumers share streams or have individual streams?
- How do we handle slow/stuck consumers?

---

## Data Volume & Storage Calculations

### Required Measurements
- [ ] Average ATProto firehose message size (bytes)
- [ ] Peak message rate (msgs/sec)
- [ ] 95th percentile message rate
- [ ] Daily message volume

### Storage Estimates (Placeholder)
```
Assumptions (NEED VALIDATION):
- Message rate: 450 msgs/sec average
- Message size: 2 KB average (GUESS)
- Daily messages: 450 * 86400 = ~38.8M messages
- Daily raw data: 38.8M * 2KB = ~77.6 GB/day
- With R=3 replication: 77.6 GB * 3 = ~232.8 GB total cluster storage
- Per node (3 nodes): ~77.6 GB
```

**Action Items:**
- [ ] Instrument shuffler to measure actual message sizes
- [ ] Run 24hr test to measure peak/average rates
- [ ] Calculate storage requirements with safety margin (2x?)

---

## Scalability Targets

### Consumer Scaling
From testing (`SCALING_ANALYSIS.md`):
- System is **input-limited** by firehose throughput (~450-500 msgs/sec)
- 1000 consumers tested successfully
- CPU scales sub-linearly (1→1000 consumers: 8.69%→10.39% CPU)
- Memory: ~0.14 MB per consumer at scale

**Capacity Planning:**
- With 450 msgs/sec firehose rate:
  - 1000 consumers = 0.45 msgs/sec per consumer
  - May need batching to make low per-consumer rates practical

**Questions:**
- What's the minimum useful message rate per consumer?
- Should consumers pull in batches to amortize overhead?

---

## High Availability Requirements

### Fault Tolerance Goals
- **Shuffler:** 2 instances, either can fail without data loss
- **NATS Cluster:** 3 nodes, tolerate 1 node failure
- **Consumers:** Stateless, can restart and resume from cursor

### Failure Scenarios to Handle
1. Single NATS node failure (cluster continues)
2. NATS cluster network partition (~15s reconnection)
3. Shuffler crash/restart (resume from cursor)
4. Consumer crash (resume from last ACK)
5. ATProto firehose disconnect (automatic websocket reconnect)

---

## Implementation Phases

### Phase 0: Current State ✅
- ✅ Single shuffler implementation
- ✅ Single NATS node (docker-compose)
- ✅ Basic message counter consumer
- ✅ Grafana monitoring dashboards
- ✅ Consumer scaling tests (1-1000 instances)

### Phase 1: MVP (Start Here)
- [ ] 1 shuffler (improved error handling)
- [ ] 1 NATS+JetStream node
- [ ] Message size instrumentation
- [ ] Storage calculation based on real data
- [ ] Cursor persistence (simple file-based)
- [ ] Basic backpressure handling

**Goal:** Production-ready single-node deployment for small-scale testing

### Phase 2: High Availability
- [ ] 2 shuffler instances (dual firehose consumers)
- [ ] 3-node NATS cluster (R=3 replication)
- [ ] Cursor coordination between shufflers
- [ ] NATS cluster failover testing
- [ ] Monitoring for cluster health

**Goal:** Zero-downtime operation with node failures

### Phase 3: Scale & Optimization
- [ ] Multi-tenant consumer isolation
- [ ] Consumer rate limiting
- [ ] Webhook delivery for consumers
- [ ] JMESPath query language for filtering
- [ ] MapReduce topic chaining

**Goal:** Production SaaS platform

---

## Open Questions & Decisions Needed

### Shuffler
- [ ] Backpressure strategy: pause firehose vs buffer vs drop?
- [ ] Cursor persistence: NATS KV vs file vs Redis?
- [ ] Retry policy: exponential backoff parameters?
- [ ] Dual-shuffler coordination: leader election or independent?

### NATS JetStream
- [ ] Exact retention: 24hrs vs message count limit?
- [ ] Deduplication window: current 5min sufficient?
- [ ] Storage type: SSD vs NVMe requirements?
- [ ] Cluster topology: same datacenter vs multi-AZ?

### Consumers
- [ ] Pull batch size: messages per request?
- [ ] Pull frequency: 1min configurable per consumer?
- [ ] Consumer authentication: JWT? API keys?
- [ ] Rate limiting: per consumer? per tenant?

### Monitoring & Observability
- [ ] SLOs: message delivery latency? throughput?
- [ ] Alerting: what conditions trigger pages?
- [ ] Metrics retention: how long to keep Prometheus data?

---

## Success Criteria

### MVP Success
- [ ] Shuffler runs for 24hrs without crashes
- [ ] NATS stores 24hrs of messages
- [ ] Consumers can pull and process messages
- [ ] Storage calculations validated with real data
- [ ] Basic monitoring shows system health

### HA Success
- [ ] Survive single NATS node failure with no data loss
- [ ] Survive shuffler restart with cursor resumption
- [ ] <1 minute recovery time for node failures
- [ ] No duplicate message processing (dedup works)

### Scale Success
- [ ] Support 1000+ concurrent consumers
- [ ] <5 second p95 message delivery latency
- [ ] Handle peak firehose rates (500+ msgs/sec)
- [ ] CPU/memory usage within budget

---

## References

- **ATProto Firehose:** https://docs.bsky.app/docs/advanced-guides/firehose
- **NATS JetStream:** https://docs.nats.io/nats-concepts/jetstream
- **JetStream Clustering:** https://docs.nats.io/running-a-nats-service/configuration/clustering/jetstream_clustering
- **Scaling Analysis:** `SCALING_ANALYSIS.md`
- **Architecture Proposal:** `README.md`

---

## Terminology

- **Shuffler:** Service that reads from ATProto firehose and publishes to NATS (formerly "firehose-subscriber")
- **Consumer:** Application service that pulls messages from NATS for processing
- **Cursor:** Sequence number in firehose for resumption after disconnect
- **Deduplication:** NATS feature using message ID to prevent duplicate ingestion
- **Pull Mode:** Consumer actively requests messages (vs push where NATS sends proactively)
- **Replication Factor (R):** Number of NATS nodes storing copies of each message
- **Quorum:** Minimum nodes required for cluster to accept writes (½n + 1)
