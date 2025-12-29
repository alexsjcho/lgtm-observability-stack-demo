import os
import time
import json
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
import httpx
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource

# Configure OpenTelemetry
resource = Resource.create({
    "service.name": os.getenv("OTEL_SERVICE_NAME", "gateway"),
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

# Instrument HTTP client
HTTPXClientInstrumentor().instrument()
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
CATALOG_URL = os.getenv("CATALOG_URL", "http://catalog:8001")
CHECKOUT_URL = os.getenv("CHECKOUT_URL", "http://checkout:8002")
SERVICE_NAME = "gateway"

# HTTP client with trace context propagation
client = httpx.AsyncClient(timeout=30.0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    yield
    await client.aclose()


app = FastAPI(title="Gateway Service", lifespan=lifespan)

# Instrument FastAPI
FastAPIInstrumentor.instrument_app(app)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Middleware to capture metrics and logs with trace correlation"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        span = trace.get_current_span()
        trace_id = format(span.get_span_context().trace_id, '032x') if span else None
        span_id = format(span.get_span_context().span_id, '016x') if span else None
        
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


@app.get("/browse")
async def browse():
    """Browse catalog items"""
    with tracer.start_as_current_span("gateway.browse") as span:
        try:
            response = await client.get(f"{CATALOG_URL}/items")
            response.raise_for_status()
            items = response.json()
            span.set_attribute("catalog.items.count", len(items.get("items", [])))
            return {"items": items.get("items", [])}
        except Exception as e:
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            raise


@app.post("/purchase")
async def purchase(request: Request):
    """Purchase endpoint that calls checkout"""
    with tracer.start_as_current_span("gateway.purchase") as span:
        try:
            body = await request.json()
            span.set_attribute("purchase.items", len(body.get("items", [])))
            
            response = await client.post(
                f"{CHECKOUT_URL}/checkout",
                json=body,
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()
            span.set_attribute("checkout.order_id", result.get("order_id", "unknown"))
            return result
        except httpx.HTTPStatusError as e:
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            return JSONResponse(
                status_code=e.response.status_code,
                content={"error": "Checkout service error"}
            )
        except Exception as e:
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            raise


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

