# Pre-Launch Checklist

## ✅ Repository Structure
- [x] Docker Compose configuration
- [x] Three services (gateway, catalog, checkout) with Dockerfiles
- [x] Prometheus configuration and alerts
- [x] Loki and Promtail configurations
- [x] Tempo configuration
- [x] Grafana provisioning (datasources, dashboards)
- [x] Alertmanager configuration
- [x] README.md with comprehensive documentation
- [x] Makefile with helper commands
- [x] Chaos injection script

## ✅ Services Implementation
- [x] Gateway service (FastAPI) - port 8000
  - [x] OpenTelemetry instrumentation
  - [x] Prometheus metrics (/metrics)
  - [x] Structured JSON logs with trace_id/span_id
  - [x] Calls catalog and checkout services
  - [x] Trace context propagation
- [x] Catalog service (FastAPI) - port 8001
  - [x] OpenTelemetry instrumentation
  - [x] Prometheus metrics (/metrics)
  - [x] Structured JSON logs with trace_id/span_id
  - [x] Chaos injection (latency, errors)
- [x] Checkout service (FastAPI) - port 8002
  - [x] OpenTelemetry instrumentation
  - [x] Prometheus metrics (/metrics)
  - [x] Structured JSON logs with trace_id/span_id
  - [x] Chaos injection (latency, errors)

## ✅ Observability Stack
- [x] Prometheus
  - [x] Scrape configs for all 3 services
  - [x] Alert rules for SLO violations
  - [x] Recording rules (if needed)
- [x] Loki
  - [x] Configuration file
  - [x] Data retention settings
- [x] Promtail
  - [x] Docker service discovery config
  - [x] JSON log parsing pipeline
  - [x] Label extraction (service, route, method, status, trace_id, span_id)
- [x] Tempo
  - [x] OTLP gRPC receiver (port 4317)
  - [x] OTLP HTTP receiver (port 4318)
  - [x] API endpoint (port 3200)
- [x] Grafana
  - [x] Datasource provisioning (Prometheus, Loki, Tempo)
  - [x] Dashboard provisioning
  - [x] Correlation configuration (exemplars, derived fields)
- [x] Alertmanager
  - [x] Alert routing configuration

## ✅ Dashboards
- [x] Golden Signals Overview
  - [x] Request rate (RPS) by service
  - [x] Error rate by service
  - [x] Latency (p95, p99) by service
  - [x] Top routes by latency
  - [x] Top routes by errors
- [x] SLO & Error Budget
  - [x] Availability SLI (99.9% target)
  - [x] Error budget remaining
  - [x] Latency SLI (95% < 300ms)
  - [x] SLO targets as reference lines

## ✅ Alerting
- [x] Fast-burn availability alert (14.4x error rate)
- [x] Slow-burn availability alert (6x error rate)
- [x] Latency alert (p95 > 300ms)
- [x] High error rate alert (catch-all)

## ✅ Documentation
- [x] README.md with:
  - [x] Architecture overview
  - [x] Prerequisites
  - [x] Quick start instructions
  - [x] Service API documentation
  - [x] Chaos engineering instructions
  - [x] Correlation workflow (metrics → traces → logs)
  - [x] Troubleshooting guide
- [x] Makefile commands documented
- [x] SLO specifications explained

## 🚀 Ready to Launch

### Quick Start Commands

```bash
# 1. Start everything
docker compose up -d

# 2. Wait 30-60 seconds for services to be healthy
docker compose ps

# 3. Access Grafana
# Open http://localhost:3000 (admin/admin)

# 4. Generate traffic
make load

# 5. View dashboards
# Navigate to Dashboards in Grafana UI
```

### Verification Steps

1. **Services are running:**
   ```bash
   docker compose ps
   # All services should show "Up" status
   ```

2. **Metrics are being scraped:**
   - Open http://localhost:9090/targets
   - All targets should show as "UP"

3. **Logs are flowing:**
   - In Grafana Explore → Loki
   - Query: `{service="gateway"}`
   - Should see log lines

4. **Traces are being collected:**
   - In Grafana Explore → Tempo
   - Search for traces by service name
   - Should see trace data

5. **Dashboards are loaded:**
   - In Grafana → Dashboards
   - Should see "Golden Signals Overview" and "SLO & Error Budget"

6. **Correlation works:**
   - In Prometheus dashboard, click on a data point
   - Should see exemplar link to Tempo
   - In Tempo trace, click on span → should see "Logs for this span"

### Known Limitations

- SLO calculations are simplified (not full multi-window burn rate)
- Error budget is an approximation over rolling window
- Chaos injection requires docker-compose.yml edit and restart (script helps but manual method documented)
- Promtail docker service discovery requires Docker socket access

### Next Steps (Optional Enhancements)

- Add more sophisticated SLO tooling (Sloth, etc.)
- Add more realistic application logic
- Add database/service dependencies
- Add load testing scripts
- Add Grafana alerting rules (beyond Prometheus)
- Add more dashboards (service-specific, etc.)

