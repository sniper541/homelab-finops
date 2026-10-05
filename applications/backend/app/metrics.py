"""Bounded HTTP labels; no URLs, user IDs, query strings or payloads are exported."""
import os
import time
from contextlib import asynccontextmanager

from prometheus_client import Counter, Gauge, Histogram, start_http_server

REQUESTS = Counter("finops_http_requests_total", "Completed API requests", ["method", "route", "status"])
DURATION = Histogram("finops_http_request_duration_seconds", "API response duration", ["method", "route"],
                     buckets=(.01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10))
INFLIGHT = Gauge("finops_http_requests_in_flight", "Currently executing API requests")


@asynccontextmanager
async def metrics_lifespan(app):
    # One uvicorn process per pod. A multi-worker deployment needs multiprocess collectors.
    server = thread = None
    if os.getenv("METRICS_PORT"):
        server, thread = start_http_server(int(os.environ["METRICS_PORT"]), addr="0.0.0.0")
    try:
        yield
    finally:
        if server:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


class HTTPMetrics:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("path") in ("/health/live", "/health/ready"):
            return await self.app(scope, receive, send)
        method = scope["method"] if scope["method"] in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"} else "OTHER"
        status = 500
        started = time.perf_counter()
        INFLIGHT.inc()

        async def observed_send(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, observed_send)
        finally:
            route = getattr(scope.get("route"), "path", "unmatched")
            REQUESTS.labels(method, route, str(status)).inc()
            DURATION.labels(method, route).observe(time.perf_counter() - started)
            INFLIGHT.dec()
