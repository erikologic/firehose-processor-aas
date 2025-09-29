# Firehose Processor-as-a-Service (FPaaS)

## Objective

Transform ATProto Firehose consumption from a complex infrastructure challenge into a simple configuration process and webhook integrations, democratizing access to the ATProto ecosystem.

## Problem

Developers face significant barriers when building production-grade ATProto applications:

- **Infrastructure Complexity**: Managing high-volume streams, persistent connections, and scaling
- **Fault Tolerance**: Event deduplication, ordering guarantees, failure recovery
- **Development Barriers**: Deep expertise requirements, months of development time, high costs
- **Integration Challenges**: Inefficient filtering, state management, testing difficulties

## Solution

FPaaS provides a managed service that abstracts away infrastructure concerns through:

### Core Features
- **Subscription-based Processing**: Configure filters, collectors, and processors via API
- **Webhook Integration**: Serverless-compatible delivery mechanisms
- **Automatic Scaling**: Handle traffic spikes without over-provisioning
- **MapReduce Support**: Distributed processing through topic chaining
- **Local Processing**: JSON query language (JMESPath) for simple transformations
- **State Management**: NATS KV stores for maintaining application state

### Example Use Case
Process "like" events from the ATProto Firehose:
1. Subscribe to firehose with "like" filter
2. Batch events (e.g., 1000 events per second)
3. Send to webhook endpoint for processing
4. Publish results to output topic
5. Enable serverless processing on platforms like Cloudflare Workers

### Architecture
- **Initial Implementation**: NATS for rapid development and testing
- **Future Scaling**: Migration path to Kafka for enhanced streaming
- **Multi-tenancy**: Isolated customer resources with monitoring
- **Open Core Model**: Local development environments for testing

## Benefits

- **Reduced Time to Market**: Focus on application logic, not infrastructure
- **Cost Efficiency**: Pay-per-use model vs. maintaining dedicated infrastructure
- **Production-Grade**: Built-in fault tolerance, monitoring, and scaling
- **Developer Experience**: Simple API configuration vs. complex stream processing setup

This service enables developers to build ATProto applications without deep distributed systems expertise, lowering the barrier to entry for the decentralized social networking ecosystem.

## Development Setup

### Quick Start

Start the complete development stack with monitoring:

```bash
docker-compose up -d
```

This launches:
- **NATS Server**: Message broker on ports 4222 (client) and 8222 (monitoring)
- **Prometheus**: Metrics collection on port 9090
- **NATS Prometheus Exporter**: Metrics bridge on port 7777
- **Grafana**: Monitoring dashboards on port 3001

### Monitoring & Observability

The stack includes comprehensive monitoring with **automatic dashboard provisioning**:

#### Access Points
- **Grafana Dashboards**: http://localhost:3001 (admin/admin)
- **Prometheus Metrics**: http://localhost:9090
- **NATS Monitoring**: http://localhost:8222

#### Pre-configured Dashboards

**NATS Server Dashboard** (`/d/nats-server/nats-server-dashboard`):
- Server performance (CPU, Memory usage)
- Message throughput (Messages In/Out, Bytes In/Out)
- Client metrics (Connections, Subscriptions, Slow Consumers)

**NATS JetStream Dashboard** (`/d/nats-jetstream/nats-jetstream-dashboard`):
- Stream and consumer counts
- Storage utilization
- Message persistence metrics

#### Metrics Available
- **Core NATS**: Connection counts, message rates, memory/CPU usage
- **JetStream**: Stream storage, consumer lag, persistence statistics
- **System**: Go runtime metrics, process statistics
- **Network**: Bytes transferred, connection lifecycle

### Testing

Run the NATS integration tests:

```bash
go test -v
```

Tests include:
- Basic connectivity and pub/sub
- Queue groups for load balancing
- Request/reply patterns
- High-volume message throughput

**Note**: Test activity will appear in the monitoring dashboards, showing real-time metrics as tests execute.