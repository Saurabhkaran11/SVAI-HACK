"""Guardrails for a public deployment (PUBLIC_MODE=1).

Everyone shares one brain and one free-tier LLM quota, so we:
- rate-limit each visitor (by IP) on AI calls and on ingestion,
- keep destructive admin actions (reset) behind ADMIN_TOKEN.
"""
from __future__ import annotations

import threading
import time
from collections import deque

from fastapi import Request
from fastapi.responses import JSONResponse

from ..config import settings

AI_PATHS = {"/ask", "/compare", "/impact"}
INGEST_PATHS = {"/upload", "/url", "/sample", "/persona", "/memory", "/profile"}
ADMIN_PATHS = {"/reset"}


class SlidingWindow:
    """Per-key request log; allows `limit` hits per `window_s` seconds."""

    def __init__(self, limit: int, window_s: float, max_keys: int = 10_000):
        self.limit, self.window, self.max_keys = limit, window_s, max_keys
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def hit(self, key: str, now: float | None = None) -> float:
        """Record a hit. Returns 0 if allowed, else seconds until the next slot frees up."""
        now = time.monotonic() if now is None else now
        with self._lock:
            q = self._hits.setdefault(key, deque())
            while q and now - q[0] >= self.window:
                q.popleft()
            if len(q) >= self.limit:
                return max(1.0, self.window - (now - q[0]))
            q.append(now)
            if len(self._hits) > self.max_keys:  # drop idle visitors so memory stays bounded
                for k in [k for k, v in self._hits.items() if not v or now - v[-1] >= self.window]:
                    self._hits.pop(k, None)
            return 0.0


ai_limit = SlidingWindow(settings.rate_ai_per_min, 60)
ingest_limit = SlidingWindow(settings.rate_ingest_per_hour, 3600)


def client_ip(request: Request) -> str:
    """The visitor's address as seen by our own proxies — never the client-controlled left end of the header."""
    hops = settings.trusted_proxy_hops
    parts = [p.strip() for p in request.headers.get("x-forwarded-for", "").split(",") if p.strip()]
    if hops > 0 and parts:
        return parts[-hops] if len(parts) >= hops else parts[0]
    return request.client.host if request.client else "unknown"


async def public_guard(request: Request, call_next):
    if not settings.public_mode or request.method != "POST":
        return await call_next(request)
    path = request.url.path
    if path in ADMIN_PATHS:
        if not settings.admin_token or request.headers.get("x-admin-token") != settings.admin_token:
            return JSONResponse(status_code=403, content={"detail": "Reset is turned off on the public demo."})
    limiter, what = (ai_limit, "questions") if path in AI_PATHS else (ingest_limit, "uploads") if path in INGEST_PATHS else (None, "")
    if limiter:
        wait = limiter.hit(client_ip(request))
        if wait:
            secs = int(wait) + 1
            return JSONResponse(status_code=429, headers={"Retry-After": str(secs)}, content={
                "detail": f"You're sending {what} faster than this shared demo allows. Try again in {secs}s."})
    return await call_next(request)
