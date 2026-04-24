"""Trace ID propagation and response timing middleware."""

import time
import uuid


class TraceMiddleware:
    """Propagate X-Trace-ID and add X-Response-Time to every request."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()
        trace_id = None

        # Extract trace ID from incoming headers
        for name, value in scope.get("headers", []):
            if name == b"x-trace-id":
                trace_id = value.decode()
                break
        if not trace_id:
            trace_id = uuid.uuid4().hex

        # Stash trace_id on scope so request.state can pick it up
        scope.setdefault("state", {})["trace_id"] = trace_id

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-trace-id", trace_id.encode()))
                elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
                headers.append((b"x-response-time", f"{elapsed_ms}ms".encode()))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)


def add_trace_middleware(app):
    """Register trace/timing middleware on a FastAPI app."""
    app.add_middleware(TraceMiddleware)
