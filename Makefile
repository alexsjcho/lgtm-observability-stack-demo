.PHONY: up down logs load chaos-latency chaos-errors chaos-reset restart clean

# Default target
help:
	@echo "Available commands:"
	@echo "  make up              - Start all services"
	@echo "  make down            - Stop all services"
	@echo "  make logs            - View logs from all services"
	@echo "  make load            - Generate load to services"
	@echo "  make chaos-latency   - Inject latency (SERVICE=<name> LATENCY=<ms>)"
	@echo "  make chaos-errors    - Inject errors (SERVICE=<name> RATE=<0.0-1.0>)"
	@echo "  make chaos-reset     - Reset chaos (SERVICE=<name>)"
	@echo "  make restart         - Restart all services"
	@echo "  make clean           - Stop and remove volumes"

up:
	docker compose up -d
	@echo "Waiting for services to be healthy..."
	@sleep 5
	@echo "Services started. Grafana: http://localhost:3000 (admin/admin)"

down:
	docker compose down

logs:
	docker compose logs -f

load:
	@echo "Generating load to services..."
	@echo "Press Ctrl+C to stop"
	@echo ""
	@while true; do \
		curl -s http://localhost:8000/ > /dev/null; \
		curl -s http://localhost:8000/browse > /dev/null; \
		curl -s -X POST http://localhost:8000/purchase \
			-H "Content-Type: application/json" \
			-d '{"items": [{"id": "1", "price": 19.99, "quantity": 1}]}' > /dev/null; \
		sleep 1; \
	done

load-quick:
	@echo "Generating quick load (100 requests, then stopping)..."
	@for i in $$(seq 1 100); do \
		curl -s http://localhost:8000/ > /dev/null; \
		curl -s http://localhost:8000/browse > /dev/null; \
		curl -s -X POST http://localhost:8000/purchase \
			-H "Content-Type: application/json" \
			-d '{"items": [{"id": "1", "price": 19.99, "quantity": 1}]}' > /dev/null; \
		sleep 0.2; \
	done
	@echo "Done! Generated 300 requests. Wait 30 seconds, then check Grafana."

chaos-latency:
	@if [ -z "$(SERVICE)" ] || [ -z "$(LATENCY)" ]; then \
		echo "Usage: make chaos-latency SERVICE=<name> LATENCY=<ms>"; \
		echo "Example: make chaos-latency SERVICE=catalog LATENCY=500"; \
		exit 1; \
	fi
	@python3 scripts/chaos.py $(SERVICE) CHAOS_LATENCY_MS $(LATENCY)
	docker compose stop $(SERVICE)
	docker compose up -d $(SERVICE)
	@echo "Injected $(LATENCY)ms latency into $(SERVICE)"

chaos-errors:
	@if [ -z "$(SERVICE)" ] || [ -z "$(RATE)" ]; then \
		echo "Usage: make chaos-errors SERVICE=<name> RATE=<0.0-1.0>"; \
		echo "Example: make chaos-errors SERVICE=checkout RATE=0.1"; \
		exit 1; \
	fi
	@python3 scripts/chaos.py $(SERVICE) CHAOS_ERROR_RATE $(RATE)
	docker compose stop $(SERVICE)
	docker compose up -d $(SERVICE)
	@echo "Injected $(RATE) error rate into $(SERVICE)"

chaos-reset:
	@if [ -z "$(SERVICE)" ]; then \
		echo "Usage: make chaos-reset SERVICE=<name>"; \
		echo "Example: make chaos-reset SERVICE=catalog"; \
		exit 1; \
	fi
	@python3 scripts/chaos.py $(SERVICE) CHAOS_LATENCY_MS 0
	@python3 scripts/chaos.py $(SERVICE) CHAOS_ERROR_RATE 0
	docker compose stop $(SERVICE)
	docker compose up -d $(SERVICE)
	@echo "Reset chaos for $(SERVICE)"

restart:
	docker compose restart

clean:
	docker compose down -v
	@echo "Removed all containers and volumes"

