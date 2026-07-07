from __future__ import annotations
"""
Sliding-window rate limiter for the Gurukul AI API.

State is in-process (dict of deques), which is correct for Cloud Run
single-instance deployments. If the app ever runs with multiple
replicas, migrate the counters to Redis.

Usage:
    from api.rate_limit import rate_limit

    # in a router:
    @router.post("/my-endpoint")
    async def handler(
        request: Request,
        auth_id: str = Depends(require_auth),
        _: None = Depends(rate_limit(20, 60)),          # 20 req/min, keyed by user
    ):
        ...

Key selection:
  - rate_limit() with authenticated routes → uses Bearer token sub (student_id)
  - rate_limit(key="ip") → uses client IP (for login/register)
"""

import collections
import threading
import time
from typing import Callable, Literal

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# (key_string, limit, window_secs) → deque of hit timestamps
_windows: dict[tuple[str, int, int], collections.deque] = collections.defaultdict(collections.deque)
_lock = threading.Lock()

_bearer = HTTPBearer(auto_error=False)


def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(
    limit: int,
    window_secs: int,
    key: Literal["user", "ip"] = "user",
) -> Callable:
    """
    Return a FastAPI dependency that enforces *limit* requests per *window_secs*.

    key="user" → keyed by the authenticated student_id (from Bearer token).
    key="ip"   → keyed by client IP (for unauthenticated routes like login).
    """

    async def _dep(
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    ) -> None:
        if key == "ip":
            bucket_key = _client_ip(request)
        else:
            # Extract student_id from the validated token payload, which is
            # already verified by require_auth earlier in the dependency chain.
            # We re-read it here without re-validating to avoid import cycles.
            import base64, json as _json, hmac as _hmac, hashlib as _hs, os as _os
            secret = _os.getenv("APP_SECRET_KEY", "dev-secret-change-in-production-32chars")
            if credentials:
                try:
                    decoded = base64.urlsafe_b64decode(credentials.credentials).decode()
                    raw, sig = decoded.rsplit("|", 1)
                    expected = _hmac.new(secret.encode(), raw.encode(), _hs.sha256).hexdigest()
                    if _hmac.compare_digest(sig, expected):
                        payload = _json.loads(raw)
                        bucket_key = payload.get("sub", _client_ip(request))
                    else:
                        bucket_key = _client_ip(request)
                except Exception:
                    bucket_key = _client_ip(request)
            else:
                bucket_key = _client_ip(request)

        window_id = (bucket_key, limit, window_secs)
        now = time.monotonic()
        cutoff = now - window_secs

        with _lock:
            dq = _windows[window_id]
            # Evict timestamps outside the current window
            while dq and dq[0] < cutoff:
                dq.popleft()
            if len(dq) >= limit:
                retry_after = int(window_secs - (now - dq[0])) + 1
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded — max {limit} requests per {window_secs}s. "
                           f"Try again in {retry_after}s.",
                    headers={"Retry-After": str(retry_after)},
                )
            dq.append(now)

    return _dep
