"""
Request context middleware.

Attaches a unique request_id to every request for distributed tracing.
Injects it into:
  1. structlog context — all log lines for this request carry request_id
  2. Response header X-Request-ID — clients can correlate errors to logs
"""
from __future__ import annotations

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

logger = structlog.get_logger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: object) -> Response:
        request_id = str(uuid.uuid4())
        start_time = time.perf_counter()

        # Make request_id available on the request state for audit logging
        request.state.request_id = request_id

        # Bind to structlog context — cleared automatically after response
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        import inspect
        if inspect.iscoroutinefunction(call_next):
            response: Response = await call_next(request)  # type: ignore[arg-type]
        else:
            response = await call_next(request)  # type: ignore[arg-type, misc]

        duration_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "request_complete",
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )

        response.headers["X-Request-ID"] = request_id
        return response
