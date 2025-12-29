import os
import time
import json
import logging
import random
import asyncio
from contextlib import asynccontextmanager
from typing import List, Dict

from fastapi import FastAPI, Request, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource

# Configure OpenTelemetry
resource = Resource.create({
    "service.name": os.getenv("OTEL_SERVICE_NAME", "catalog"),
    "service.version": "1.0.0",
})

trace.set_tracer_provider(TracerProvider(resource=resource))
tracer_provider = trace.get_tracer_provider()

otlp_exporter = OTLPSpanExporter(
    endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://tempo:4317"),
    insecure=True,
)
span_processor = BatchSpanProcessor(otlp_exporter)
tracer_provider.add_span_processor(span_processor)

tracer = trace.get_tracer(__name__)

LoggingInstrumentor().instrument()

# Configure structured JSON logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(message)s'))
logger.addHandler(handler)

# Prometheus metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['service', 'route', 'method', 'status']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['service', 'route', 'method', 'status'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Environment variables
SERVICE_NAME = "catalog"
CHAOS_LATENCY_MS = int(os.getenv("CHAOS_LATENCY_MS", "0"))
CHAOS_ERROR_RATE = float(os.getenv("CHAOS_ERROR_RATE", "0"))

# Mock catalog data
CATALOG_ITEMS = [
    {"id": "1", "name": "Widget A", "price": 19.99, "stock": 100},
    {"id": "2", "name": "Widget B", "price": 29.99, "stock": 50},
    {"id": "3", "name": "Widget C", "price": 39.99, "stock": 25},
    {"id": "4", "name": "Widget D", "price": 49.99, "stock": 10},
    {"id": "5", "name": "Widget E", "price": 59.99, "stock": 5},
]

app = FastAPI(title="Catalog Service")
FastAPIInstrumentor.instrument_app(app)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Middleware to capture metrics and logs with trace correlation"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        span = trace.get_current_span()
        trace_id = format(span.get_span_context().trace_id, '032x') if span else None
        span_id = format(span.get_span_context().span_id, '016x') if span else None
        
        # Apply chaos injection: latency
        if CHAOS_LATENCY_MS > 0:
            jitter = random.uniform(-CHAOS_LATENCY_MS * 0.2, CHAOS_LATENCY_MS * 0.2)
            delay_ms = max(0, CHAOS_LATENCY_MS + jitter)
            await asyncio.sleep(delay_ms / 1000.0)
        
        # Apply chaos injection: errors
        if CHAOS_ERROR_RATE > 0 and random.random() < CHAOS_ERROR_RATE:
            duration_ms = (time.time() - start_time) * 1000
            status = 503
            route = request.url.path
            method = request.method
            
            REQUEST_COUNT.labels(
                service=SERVICE_NAME,
                route=route,
                method=method,
                status=status
            ).inc()
            
            REQUEST_DURATION.labels(
                service=SERVICE_NAME,
                route=route,
                method=method,
                status=status
            ).observe(time.time() - start_time)
            
            log_data = {
                "timestamp": time.time(),
                "level": "ERROR",
                "service": SERVICE_NAME,
                "route": route,
                "method": method,
                "status": status,
                "latency_ms": round(duration_ms, 2),
                "trace_id": trace_id,
                "span_id": span_id,
                "msg": f"Chaos injection: {method} {route} {status}"
            }
            logger.info(json.dumps(log_data))
            
            return Response(
                status_code=503,
                content=json.dumps({"error": "Service temporarily unavailable (chaos)"})
            )
        
        response = await call_next(request)
        
        duration_ms = (time.time() - start_time) * 1000
        route = request.url.path
        method = request.method
        status = response.status_code
        
        # Record metrics
        REQUEST_COUNT.labels(
            service=SERVICE_NAME,
            route=route,
            method=method,
            status=status
        ).inc()
        
        REQUEST_DURATION.labels(
            service=SERVICE_NAME,
            route=route,
            method=method,
            status=status
        ).observe(time.time() - start_time)
        
        # Structured log
        log_data = {
            "timestamp": time.time(),
            "level": "ERROR" if status >= 500 else "WARN" if status >= 400 else "INFO",
            "service": SERVICE_NAME,
            "route": route,
            "method": method,
            "status": status,
            "latency_ms": round(duration_ms, 2),
            "trace_id": trace_id,
            "span_id": span_id,
            "msg": f"{method} {route} {status}"
        }
        logger.info(json.dumps(log_data))
        
        return response


app.add_middleware(ObservabilityMiddleware)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"service": SERVICE_NAME, "status": "healthy"}


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/items")
async def get_items():
    """Get catalog items"""
    with tracer.start_as_current_span("catalog.get_items") as span:
        span.set_attribute("catalog.items.count", len(CATALOG_ITEMS))
        return {"items": CATALOG_ITEMS}


if __name__ == "__main__":
    import uvicorn
    import asyncio
    uvicorn.run(app, host="0.0.0.0", port=8001)

