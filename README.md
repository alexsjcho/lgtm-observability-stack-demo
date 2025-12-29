# Forword

This is a practice project for me to understand the Grafana (LGTM) observability stack

# 3-Service Observability Lab

A complete observability demonstration using the LGTM stack (Loki, Grafana, Tempo, Mimir/Prometheus) with 3 microservices, showcasing correlated metrics, logs, traces, and SLO-driven alerting.

## Challenges This Demo Solves

This lab addresses common observability challenges in modern microservices environments:

- **Correlation Complexity**: Connecting metrics, logs, and traces across distributed services is non-trivial. This demo shows how to achieve end-to-end correlation using trace IDs and span IDs.
- **SLO Implementation**: Defining and monitoring Service Level Objectives (SLOs) with proper error budget tracking and burn rate alerting can be overwhelming. This lab provides a working example with availability and latency SLOs.
- **Full-Stack Observability**: Many teams struggle to integrate the full observability stack (metrics, logs, traces) cohesively. This demo demonstrates a complete, production-realistic setup.
- **Hands-On Learning**: Reading documentation is one thing, but seeing how everything works together in a runnable environment accelerates understanding significantly.

## Who Is This For?

- **SREs & DevOps Engineers**: Learn how to implement a complete observability stack and SLO-driven alerting in practice
- **Platform Engineers**: Understand how to set up and configure the LGTM stack for your teams
- **Software Developers**: See how to instrument services with OpenTelemetry and emit observability signals
- **Engineering Teams**: Use this as a reference implementation for your own observability infrastructure

## Benefits

- **Production-Realistic**: Uses real tools (Prometheus, Loki, Tempo, Grafana) in a configuration that mirrors production environments
- **Single Command Setup**: Get everything running with `docker compose up -d` - no complex setup required
- **End-to-End Correlation**: See how metrics, logs, and traces connect together using trace IDs and exemplars
- **SLO-Driven Alerting**: Learn burn rate alerting and error budget management with working examples
- **Chaos Engineering**: Includes fault injection capabilities to test your observability setup
- **Complete & Runnable**: Everything works out of the box - no placeholders or TODOs


## Architecture

```
┌─────────┐
│ Gateway │ (port 8000)
└────┬────┘
     │
     ├─→ ┌─────────┐
     │   │ Catalog │ (port 8001)
     │   └─────────┘
     │
     └─→ ┌──────────┐
         │ Checkout │ (port 8002)
         └──────────┘

Observability Stack:
- Prometheus (port 9090) - Metrics collection
- Loki (port 3100) - Log aggregation
- Promtail - Log collection
- Tempo (ports 4317/4318/3200) - Trace storage
- Grafana (port 3000) - Visualization
- Alertmanager (port 9093) - Alert routing
```

## Prerequisites

- Docker 20.10+ and Docker Compose 2.0+
- 4GB+ RAM available
- Ports available: 3000, 8000, 8001, 8002, 9090, 9093, 3100, 4317, 4318, 3200

## Quick Start

### 1. Start the Stack

```bash
docker compose up -d
```

Wait 30-60 seconds for all services to be healthy. Check status:

```bash
docker compose ps
```

### 2. Access Services

- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Alertmanager**: http://localhost:9093
- **Gateway API**: http://localhost:8000
- **Catalog API**: http://localhost:8001
- **Checkout API**: http://localhost:8002

### 3. Generate Traffic

Use the provided Makefile commands or curl directly:

```bash
# Generate normal traffic
make load

# Or manually:
curl http://localhost:8000/
curl http://localhost:8000/browse
curl -X POST http://localhost:8000/purchase \
  -H "Content-Type: application/json" \
  -d '{"items": [{"id": "1", "price": 19.99, "quantity": 1}]}'
```

## Usage

### Generate Load

The Makefile includes a load generator:

```bash
make load
```

This runs a simple loop making requests to all endpoints.

### Chaos Engineering

Inject latency and errors into services:

```bash
# Add 500ms latency to catalog
make chaos-latency SERVICE=catalog LATENCY=500

# Add 10% error rate to checkout
make chaos-errors SERVICE=checkout RATE=0.1

# Reset chaos (set to 0)
make chaos-reset SERVICE=catalog
```

**Manual Method:** Edit `docker-compose.yml` to change `CHAOS_LATENCY_MS` or `CHAOS_ERROR_RATE` for the service, then restart:

```bash
docker compose stop catalog
docker compose up -d catalog
```

### View Logs

```bash
# All services
make logs

# Specific service
docker compose logs -f gateway
docker compose logs -f catalog
docker compose logs -f checkout
```

### Stop the Stack

```bash
make down
# or
docker compose down
```

To also remove volumes (clean slate):

```bash
docker compose down -v
```

## Observability Features

### Metrics (Prometheus)

All services expose Prometheus metrics at `/metrics`:

- `http_requests_total` - Request counter with labels: `service`, `route`, `method`, `status`
- `http_request_duration_seconds` - Request latency histogram

**Key Metrics:**
- Request rate per service/route
- Error rate per service/route
- p50, p95, p99 latency per service/route

### Logs (Loki)

All services emit structured JSON logs to stdout with:
- `timestamp`, `level`, `service`, `route`, `method`, `status`
- `latency_ms`, `trace_id`, `span_id`, `msg`

Promtail collects logs from Docker containers and ships to Loki with labels:
- `job=services`, `service`, `env=local`

### Traces (Tempo)

Distributed tracing via OpenTelemetry:
- OTLP gRPC exporter (port 4317)
- Trace context propagates: gateway → catalog/checkout
- Traces include service names, operation names, and attributes

### Correlation

**Metrics → Traces:**
1. In Grafana Explore, query metrics
2. Click on a data point
3. Use "Exemplars" to jump to related traces

**Traces → Logs:**
1. In Grafana Explore, select Tempo datasource
2. View a trace
3. Click on a span to see correlated logs (trace_id matching)

**Logs → Traces:**
1. In Grafana Explore, query Loki logs
2. Click on `trace_id` field
3. Jump to Tempo to view full trace

## Grafana Dashboards

Two dashboards are automatically provisioned:

### 1. Golden Signals Overview

Displays:
- Request rate (RPS) by service
- Error rate by service
- Latency (p95, p99) by service
- Top routes by latency
- Top routes by error rate

### 2. SLO & Error Budget

Displays:
- **Availability SLI**: 99.9% successful requests (non-5xx) for gateway
- **Error Budget**: Remaining budget for 30-day window
- **Latency SLI**: 95% of requests under 300ms (p95 thresholding)

**SLO Specifications:**
- Availability: 99.9% over 30 days for gateway service
- Latency: 95% requests under 300ms over 30 days for gateway service

**Burn Rate Alerts:**
- Fast burn: 14.4x error rate (consumes 30-day budget in 5 hours) → Page alert
- Slow burn: 6x error rate (consumes 30-day budget in 6 hours) → Ticket alert
- Latency alert: p95 > 300ms → Ticket alert

## Alerting

Alerts are configured in `prometheus/alerts.yml` and evaluated by Prometheus. Alertmanager routes them based on severity:

- **severity: page** - Fast-burn availability violations (immediate attention)
- **severity: ticket** - Slow-burn availability and latency violations (investigate)

View active alerts:
- Prometheus: http://localhost:9090/alerts
- Alertmanager: http://localhost:9093

### Triggering Alerts

To trigger an alert:

```bash
# Inject high error rate
make chaos-errors SERVICE=gateway RATE=0.15

# Or high latency
make chaos-latency SERVICE=gateway LATENCY=1000
```

Wait 5-10 minutes for the alert to fire (depending on evaluation interval).

## Service APIs

### Gateway (port 8000)

- `GET /` - Health check
- `GET /browse` - Browse catalog (calls catalog service)
- `POST /purchase` - Purchase items (calls checkout service)
- `GET /metrics` - Prometheus metrics

### Catalog (port 8001)

- `GET /` - Health check
- `GET /items` - List catalog items
- `GET /metrics` - Prometheus metrics

**Chaos Injection:**
- `CHAOS_LATENCY_MS` - Add latency (milliseconds)
- `CHAOS_ERROR_RATE` - Error rate (0.0-1.0)

### Checkout (port 8002)

- `GET /` - Health check
- `POST /checkout` - Process checkout/payment
- `GET /metrics` - Prometheus metrics

**Chaos Injection:**
- `CHAOS_LATENCY_MS` - Add latency (milliseconds)
- `CHAOS_ERROR_RATE` - Error rate (0.0-1.0)

## Exploring Correlation in Grafana

### Step 1: Find a trace from metrics

1. Open Grafana → Explore → Prometheus
2. Query: `rate(http_requests_total{service="gateway"}[5m])`
3. Click on a data point → View exemplars
4. Click on an exemplar to jump to Tempo trace

### Step 2: View logs from a trace

1. Open Grafana → Explore → Tempo
2. Search for traces by service name or operation
3. Click on a trace to view spans
4. Click on a span → "Logs for this span" to see correlated logs

### Step 3: Find traces from logs

1. Open Grafana → Explore → Loki
2. Query: `{service="gateway"} |= "ERROR"`
3. Click on a log line with `trace_id`
4. Click on the `trace_id` value → Jump to Tempo

### Step 4: View SLO dashboards

1. Navigate to "SLO & Error Budget" dashboard
2. Observe availability SLI and error budget
3. Inject chaos to see SLO violations
4. Check Prometheus alerts to see when thresholds are breached

## Troubleshooting

### Services not starting

```bash
# Check logs
docker compose logs gateway
docker compose logs catalog
docker compose logs checkout

# Restart a service
docker compose restart gateway
```

### No metrics appearing

1. Verify services are exposing metrics:
   ```bash
   curl http://localhost:8000/metrics
   ```

2. Check Prometheus targets: http://localhost:9090/targets

3. Verify scrape configs in `prometheus/prometheus.yml`

### No logs in Loki

1. Check Promtail logs:
   ```bash
   docker compose logs promtail
   ```

2. Verify Docker labels are set in `docker-compose.yml`

3. Check Loki is receiving logs: http://localhost:3100/ready

### No traces in Tempo

1. Verify services are exporting traces:
   - Check environment variables: `OTEL_EXPORTER_OTLP_ENDPOINT`
   - Check service logs for OTLP export errors

2. Verify Tempo is listening: http://localhost:3200/ready

3. Check Tempo config: `tempo/tempo-config.yml`

### Dashboards not loading

1. Check Grafana provisioning logs:
   ```bash
   docker compose logs grafana | grep -i "provisioning\|dashboard"
   ```

2. Verify dashboard files exist in `grafana/dashboards/`

3. Manually import dashboards if needed (they should auto-load)

## Makefile Commands

```bash
make up          # Start all services
make down        # Stop all services
make logs        # View logs from all services
make load        # Generate load to services
make chaos-latency SERVICE=<name> LATENCY=<ms>  # Inject latency
make chaos-errors SERVICE=<name> RATE=<0.0-1.0> # Inject errors
make chaos-reset SERVICE=<name>                 # Reset chaos (set to 0)
make restart     # Restart all services
make clean       # Stop and remove volumes (clean slate)
```

## Architecture Notes

### OpenTelemetry Integration

- Auto-instrumentation for FastAPI (HTTP server)
- Auto-instrumentation for HTTPX (HTTP client)
- Trace context propagation via W3C Trace Context headers
- OTLP gRPC exporter to Tempo

### Logging

- Structured JSON logs to stdout
- Promtail tails Docker container logs
- JSON parsing extracts fields as labels in Loki
- Trace correlation via `trace_id` and `span_id` fields

### Metrics

- Prometheus client library with standard HTTP metrics
- Histogram buckets optimized for web latency (5ms to 10s)
- Consistent labels across services for aggregation

### SLO Implementation

- Simplified error budget calculation (not full multi-window burn rate)
- Availability SLI: `(successful requests / total requests)`
- Error budget: `1 - ((error_rate) / (1 - SLO))`
- Burn rate alerts use simplified thresholds

For production, consider using more sophisticated SLO tooling like Sloth or implementing full multi-window multi-burn rate calculations.

## License

MIT

## Contributing

This is a demonstration project. Feel free to fork and extend for your own observability needs!

