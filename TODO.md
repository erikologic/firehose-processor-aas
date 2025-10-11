# Benchmark Tool TODO - Missing Metrics and Issues

## Executive Summary

The current benchmark implementation is **incomplete** and missing critical metrics from the original specification. This document identifies all gaps between BENCHMARK.md spec and the current implementation.

**Current Status:** 26 metrics captured (NATS, JetStream, Docker stats for NATS container only)
**Expected Status:** ~60+ metrics across all services and components

---

## Critical Issues

### 1. ❌ Meaningless JetStream Metrics

**Problem:** JetStream metrics are system-level snapshots, not meaningful for benchmark aggregation

**Current (WRONG):**
```
js_streams_avg: 1.0        (averaging a constant)
js_consumers_avg: 0.0      (averaging a constant)
js_storage_avg: 0.0        (averaging a constant)
js_messages_avg: 67,208    (buffer snapshot - not useful as average)
```

**What these should be (per BENCHMARK.md):**
```
js_pending_messages_avg      (average buffer size over test - useful!)
js_pending_acks_avg          (average pending acks - useful!)
js_pending_messages_per_consumer
js_pending_acks_per_consumer
```

**Action Required:**
- [ ] Remove `js_streams_avg`, `js_consumers_avg`, `js_storage_avg` (constants, not metrics)
- [ ] Replace `js_messages_avg` with `js_pending_messages_avg` (rename for clarity)
- [ ] Add `js_pending_acks_avg` metric
- [ ] Update models.py JetStreamJszMetrics to match `/jsz` API structure
- [ ] Update aggregators.py to use correct field names

**Impact:** Medium - Metrics exist but are poorly named and include meaningless constants

---

### 2. ❌ Missing Shuffler Metrics

**Problem:** Zero metrics from the Shuffler (firehose consumer) service

**Available but NOT captured:**
- Shuffler endpoint: `http://localhost:8080/metrics`
- Metrics available:
  - `firehose_messages_read_total` (counter) - messages read from ATProto firehose
  - `firehose_cursor_position` (gauge) - current sequence number

**Expected metrics (per BENCHMARK.md):**
```
shuffler_messages_read_total         (delta: end - start)
shuffler_messages_written_total      (delta: published to NATS)  ⚠️ NOT AVAILABLE
shuffler_cpu_percent_avg             (from Docker stats)
shuffler_mem_bytes_avg               (from Docker stats)
shuffler_net_io_bytes_total          (from Docker stats)
```

**Action Required:**
- [ ] Create `ShufflerMetrics` Pydantic model in models.py
- [ ] Create `fetch_shuffler_metrics()` fetcher in fetchers.py
- [ ] Add Docker stats collection for `fpaas-shuffler` container
- [ ] Create `aggregate_shuffler_metrics()` in aggregators.py
- [ ] Integrate into CLI concurrent collection
- [ ] **NOTE:** `shuffler_messages_written_total` not exposed - need to add to Go app or derive from NATS

**Impact:** HIGH - Critical for understanding firehose ingestion rate and system efficiency

---

### 3. ❌ Missing Consumer Service Metrics

**Problem:** Zero metrics from the Consumer service

**Available but NOT captured:**
- Consumer endpoint: `http://localhost:8082/metrics`
- Metrics available:
  - `consumer_messages_processed_total` (counter) - total messages processed

**Expected metrics (per BENCHMARK.md):**
```
consumer_messages_total              (delta: processed during test)
consumer_messages_per_consumer       (total / n_consumers)
consumer_cpu_percent_avg             (from Docker stats)
consumer_mem_bytes_avg               (from Docker stats)
consumer_net_io_bytes_total          (from Docker stats)
consumer_cpu_per_consumer            (avg CPU / n_consumers)
consumer_mem_per_consumer            (avg mem / n_consumers)
consumer_net_io_per_consumer         (net I/O / n_consumers)
```

**Action Required:**
- [ ] Create `ConsumerMetrics` Pydantic model in models.py
- [ ] Create `fetch_consumer_metrics()` fetcher in fetchers.py
- [ ] Add Docker stats collection for `fpaas-consumer` container
- [ ] Create `aggregate_consumer_metrics()` in aggregators.py
- [ ] Integrate into CLI concurrent collection

**Impact:** HIGH - Critical for understanding consumer processing rate and resource usage

---

### 4. ❌ Missing Webhook Receiver Metrics

**Problem:** Zero metrics from the Webhook Receiver service

**Expected metrics (per BENCHMARK.md):**
```
webhook_calls_total                  (total webhook invocations)
webhook_events_total                 (total events received in webhooks)
webhook_events_per_consumer          (events / n_consumers)
webhook_cpu_percent_avg              (from Docker stats)
webhook_mem_bytes_avg                (from Docker stats)
webhook_net_io_bytes_total           (from Docker stats)
webhook_cpu_per_consumer             (avg CPU / n_consumers)
webhook_mem_per_consumer             (avg mem / n_consumers)
webhook_net_io_per_consumer          (net I/O / n_consumers)
```

**Action Required:**
- [ ] Check if `fpaas-webhook-receiver` exposes `/metrics` endpoint
- [ ] If not, add Prometheus metrics to webhook receiver Go app
- [ ] Create `WebhookMetrics` Pydantic model in models.py
- [ ] Create `fetch_webhook_metrics()` fetcher in fetchers.py
- [ ] Add Docker stats collection for `fpaas-webhook-receiver` container
- [ ] Create `aggregate_webhook_metrics()` in aggregators.py
- [ ] Integrate into CLI concurrent collection

**Impact:** MEDIUM - Only needed for webhook-enabled scenarios (Phase 2 benchmarks)

---

### 5. ❌ Missing Docker Stats for Multiple Containers

**Problem:** Only collecting Docker stats for `fpaas-nats`, missing other containers

**Current:**
- Only monitored: `fpaas-nats` (NATS server)

**Missing containers:**
- `fpaas-shuffler` (Shuffler service)
- `fpaas-consumer` (Consumer service)
- `fpaas-webhook-receiver` (Webhook receiver)

**Action Required:**
- [ ] Refactor `fetch_docker_stats()` to accept container name parameter ✅ (ALREADY DONE)
- [ ] Update `collect_all_metrics_sample()` to fetch stats for ALL containers concurrently
- [ ] Create separate aggregation for each container's stats
- [ ] Add metrics with prefixes: `shuffler_cpu_percent_avg`, `consumer_cpu_percent_avg`, etc.

**Impact:** HIGH - Cannot measure resource usage per service without this

---

### 6. ❌ Missing Derived Metrics

**Problem:** No calculated efficiency or throughput metrics

**Expected (per BENCHMARK.md):**
```
system_efficiency_percent            (consumer_messages_total / shuffler_messages_read_total * 100)
throughput_msg_per_sec               (nats_in_msgs_total / test_duration_sec)
throughput_mb_per_sec                (nats_in_bytes_total / test_duration_sec / 1024²)
avg_msg_size_bytes                   (nats_in_bytes_total / nats_in_msgs_total)
```

**Action Required:**
- [ ] Add derived metrics calculation in aggregators.py
- [ ] Add to final aggregated dictionary before CSV write
- [ ] Document formulas in REPORT.md

**Impact:** MEDIUM - Nice to have, but can be calculated post-hoc from existing metrics

---

### 7. ❌ Missing Configuration Metrics

**Problem:** Not capturing all scenario parameters

**Current:**
```
scenario
n_consumers
test_duration_sec
```

**Missing (per BENCHMARK.md):**
```
use_webhook                          (boolean: webhooks enabled?)
batch_size                           (messages per fetch)
poll_interval                        (consumer poll interval)
```

**Action Required:**
- [ ] Add configuration parameters to CLI options
- [ ] Pass through to aggregated output
- [ ] Update CSV column order to match spec

**Impact:** LOW - Only needed when testing different configurations (Phase 2/3)

---

## Metric Coverage Matrix

| Metric Category | Spec Required | Currently Captured | Missing | Priority |
|----------------|---------------|-------------------|---------|----------|
| **Configuration** | 5 | 3 | 2 | LOW |
| **NATS Server** | 12 | 11 | 1 | LOW |
| **JetStream** | 4 | 0 (wrong metrics) | 4 | MEDIUM |
| **Shuffler** | 5 | 0 | 5 | **HIGH** |
| **Consumer Service** | 8 | 0 | 8 | **HIGH** |
| **Webhook Receiver** | 9 | 0 | 9 | MEDIUM |
| **Derived Metrics** | 4+ | 0 | 4+ | MEDIUM |
| **Docker Stats** | 4 containers | 1 container | 3 containers | **HIGH** |
| **TOTAL** | ~60 | 26 | ~34 | |

**Completion:** 43% (26/60 metrics)

---

## Implementation Plan

### Phase 1: Fix Critical Issues (HIGH Priority)

**Goal:** Capture end-to-end message flow and resource usage per service

1. **Add Shuffler Metrics** (2-3 hours)
   - [ ] Create models.py: `ShufflerMetrics` model
   - [ ] Create fetchers.py: `fetch_shuffler_metrics()`
   - [ ] Add Docker stats for `fpaas-shuffler`
   - [ ] Create aggregators.py: `aggregate_shuffler_metrics()`
   - [ ] Integrate into CLI concurrent collection
   - [ ] Test with 10-second run

2. **Add Consumer Service Metrics** (2-3 hours)
   - [ ] Create models.py: `ConsumerMetrics` model
   - [ ] Create fetchers.py: `fetch_consumer_metrics()`
   - [ ] Add Docker stats for `fpaas-consumer`
   - [ ] Create aggregators.py: `aggregate_consumer_metrics()`
   - [ ] Integrate into CLI concurrent collection
   - [ ] Test with 10-second run

3. **Fix JetStream Metrics** (1 hour)
   - [ ] Remove meaningless metrics (streams_avg, consumers_avg, storage_avg)
   - [ ] Rename `js_messages_avg` → `js_pending_messages_avg`
   - [ ] Add `js_pending_acks_avg` if available in `/jsz`
   - [ ] Update models and aggregators

4. **Multi-Container Docker Stats** (1 hour)
   - [ ] Refactor concurrent collection to fetch all 3 containers
   - [ ] Create separate metrics for each: `shuffler_*`, `consumer_*`, `nats_*`
   - [ ] Test collection and aggregation

**Expected Output After Phase 1:** ~45 metrics (75% complete)

### Phase 2: Add Derived Metrics (MEDIUM Priority)

**Goal:** Calculate efficiency and throughput metrics

1. **Add Derived Metrics** (1 hour)
   - [ ] `system_efficiency_percent`
   - [ ] `throughput_msg_per_sec`
   - [ ] `throughput_mb_per_sec`
   - [ ] `avg_msg_size_bytes`

**Expected Output After Phase 2:** ~49 metrics (82% complete)

### Phase 3: Webhook Support (MEDIUM Priority - Phase 2 Scenarios)

**Goal:** Support webhook-enabled benchmarks

1. **Add Webhook Receiver Metrics** (2-3 hours)
   - [ ] Check if metrics endpoint exists
   - [ ] Add Prometheus metrics to Go app if needed
   - [ ] Create models, fetchers, aggregators
   - [ ] Add Docker stats collection
   - [ ] Test with webhook-enabled scenario

**Expected Output After Phase 3:** ~58 metrics (97% complete)

### Phase 4: Configuration Parameters (LOW Priority)

**Goal:** Support different batch sizes and poll intervals

1. **Add Configuration Options** (30 min)
   - [ ] Add `--use-webhook`, `--batch-size`, `--poll-interval` CLI options
   - [ ] Pass through to CSV output

**Expected Output After Phase 4:** ~60 metrics (100% complete)

---

## Testing Strategy

For each new metric category:

1. **Write Pydantic model** matching API/endpoint structure
2. **Write fetcher** that calls real endpoint
3. **Test fetcher** against running service (10 seconds)
   ```bash
   python3 << 'EOF'
   import asyncio
   from benchmark.fetchers import fetch_shuffler_metrics
   metrics = asyncio.run(fetch_shuffler_metrics("http://localhost:8080"))
   print(metrics)
   EOF
   ```
4. **Write aggregator** for delta/average calculation
5. **Test aggregation** with real samples (2-3 samples)
6. **Integrate into CLI** concurrent collection
7. **Run 10-second end-to-end test**
8. **Verify CSV output** has correct columns and values

---

## Success Criteria

### Phase 1 Complete When:
- [ ] Shuffler metrics appear in CSV (5 new columns)
- [ ] Consumer service metrics appear in CSV (8 new columns)
- [ ] JetStream metrics renamed and cleaned (net -3 columns, +1 new)
- [ ] Docker stats for all 3 containers (2 new containers × ~5 metrics each)
- [ ] CSV has ~45 columns total
- [ ] 10-second test completes successfully
- [ ] All values are non-zero (except consumer_messages when no webhooks)

### Phase 2 Complete When:
- [ ] Derived metrics appear in CSV (4 new columns)
- [ ] `system_efficiency_percent` matches manual calculation
- [ ] Throughput metrics match NATS msg rate
- [ ] CSV has ~49 columns total

### Final Validation:
- [ ] Run full 5-minute benchmark with 100 consumers
- [ ] Verify all ~60 expected columns present
- [ ] Cross-validate metrics across sources
- [ ] Update REPORT.md with new metrics assessment
- [ ] Update BENCHMARK.md with actual implementation details

---

## Questions for User

1. **Shuffler**: Does the shuffler expose `messages_written_total` (published to NATS)?
   - If not, can we add it or derive from NATS `in_msgs`?

2. **Webhook Receiver**: Does it have a Prometheus `/metrics` endpoint?
   - If not, do you want us to add one to the Go app?

3. **Consumer Processing**: Why is `consumer_messages_processed_total` always 0?
   - Are consumers actually processing messages?
   - Is this a configuration issue or expected behavior?

4. **Priority**: Should we focus on Phase 1 (end-to-end visibility) first?
   - Or do you want webhook support (Phase 3) sooner?

---

## Current vs Expected CSV Structure

### Current (26 columns):
```
scenario, n_consumers, test_duration_sec,
nats_cpu_avg, nats_cpu_per_consumer, nats_mem_avg, nats_mem_per_consumer,
nats_in_msgs_total, nats_out_msgs_total, nats_in_bytes_total, nats_out_bytes_total,
js_streams_avg, js_consumers_avg, js_storage_avg,           ← REMOVE (meaningless)
js_messages_avg, js_messages_per_consumer,                   ← RENAME to js_pending_*
js_bytes_avg, js_bytes_per_consumer,
js_memory_avg, js_memory_per_consumer,
docker_cpu_percent_avg, docker_cpu_percent_per_consumer,    ← Only NATS container
docker_mem_usage_bytes_avg, docker_mem_usage_bytes_per_consumer,
docker_net_in_bytes_total, docker_net_out_bytes_total
```

### Expected (Phase 1 - ~45 columns):
```
scenario, n_consumers, test_duration_sec,
nats_cpu_avg, nats_cpu_per_consumer, nats_mem_avg, nats_mem_per_consumer,
nats_in_msgs_total, nats_out_msgs_total, nats_in_bytes_total, nats_out_bytes_total,
js_pending_messages_avg, js_pending_messages_per_consumer,  ← RENAMED
js_pending_acks_avg, js_pending_acks_per_consumer,         ← NEW
shuffler_messages_read_total,                                ← NEW (5 metrics)
shuffler_cpu_percent_avg, shuffler_mem_bytes_avg,
shuffler_net_in_bytes_total, shuffler_net_out_bytes_total,
consumer_messages_total, consumer_messages_per_consumer,     ← NEW (8 metrics)
consumer_cpu_percent_avg, consumer_cpu_per_consumer,
consumer_mem_bytes_avg, consumer_mem_per_consumer,
consumer_net_in_bytes_total, consumer_net_out_bytes_total,
nats_cpu_percent_avg, nats_mem_bytes_avg,                   ← KEEP (Docker stats for NATS)
nats_net_in_bytes_total, nats_net_out_bytes_total
```

---

## Risk Assessment

**HIGH RISK:**
- Missing critical application metrics (shuffler, consumer) means we can't measure end-to-end throughput
- Can't calculate system efficiency without both ends of the pipeline
- Can't identify bottlenecks without per-service resource usage

**MEDIUM RISK:**
- JetStream metrics are confusing and poorly named
- Missing webhook metrics blocks Phase 2 testing
- No derived metrics means manual post-processing required

**LOW RISK:**
- Missing configuration parameters only affects advanced scenarios
- Can work around with manual documentation

**RECOMMENDATION:** Prioritize Phase 1 implementation before running production benchmarks.
