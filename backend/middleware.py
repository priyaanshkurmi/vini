import time
import logging
from collections import defaultdict
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("vini.ratelimit")

# Simple in-memory rate limiter
# 30 requests per minute per IP
RATE_LIMIT    = 30
WINDOW_SECS   = 60


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        ip  = request.client.host
        now = time.time()

        # Remove timestamps outside the window
        self._requests[ip] = [
            t for t in self._requests[ip]
            if now - t < WINDOW_SECS
        ]

        if len(self._requests[ip]) >= RATE_LIMIT:
            logger.warning(f"Rate limit hit for {ip}")
            return Response(
                content='{"detail":"Too many requests. Slow down."}',
                status_code=429,
                media_type="application/json",
            )

        self._requests[ip].append(now)
        return await call_next(request)