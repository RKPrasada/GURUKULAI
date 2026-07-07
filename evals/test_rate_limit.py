"""
Smoke tests for the sliding-window rate limiter (api/rate_limit.py).

These tests run against the rate_limit module directly — no HTTP server
needed — so they're fast and deterministic.
"""
from __future__ import annotations

import asyncio
import time
import pytest

from unittest.mock import MagicMock
from fastapi import HTTPException


# ── helpers ────────────────────────────────────────────────────────────────────

def _make_request(ip: str = "1.2.3.4", token: str | None = None):
    req = MagicMock()
    req.headers = {"X-Forwarded-For": ip} if ip else {}
    req.client = MagicMock()
    req.client.host = ip
    creds = MagicMock()
    creds.credentials = token or ""
    return req, creds


async def _call_dep(dep, ip="1.2.3.4", token=None):
    from fastapi.security import HTTPAuthorizationCredentials
    req, creds = _make_request(ip, token)
    await dep(request=req, credentials=creds)


# ── tests ──────────────────────────────────────────────────────────────────────

class TestRateLimitIP:
    """IP-keyed rate limiter (login/register protection)."""

    def test_allows_under_limit(self):
        from api.rate_limit import rate_limit
        dep = rate_limit(5, 60, key="ip")
        for _ in range(5):
            asyncio.run(_call_dep(dep, ip="10.0.0.1"))

    def test_blocks_over_limit(self):
        from api.rate_limit import rate_limit
        dep = rate_limit(3, 60, key="ip")
        for _ in range(3):
            asyncio.run(_call_dep(dep, ip="10.0.0.2"))
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(_call_dep(dep, ip="10.0.0.2"))
        assert exc_info.value.status_code == 429

    def test_retry_after_header(self):
        from api.rate_limit import rate_limit
        dep = rate_limit(1, 30, key="ip")
        asyncio.run(_call_dep(dep, ip="10.0.0.3"))
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(_call_dep(dep, ip="10.0.0.3"))
        assert "Retry-After" in exc_info.value.headers

    def test_different_ips_independent(self):
        from api.rate_limit import rate_limit
        dep = rate_limit(2, 60, key="ip")
        asyncio.run(_call_dep(dep, ip="10.1.0.1"))
        asyncio.run(_call_dep(dep, ip="10.1.0.1"))
        # Second IP should still be allowed
        asyncio.run(_call_dep(dep, ip="10.1.0.2"))

    def test_window_resets_after_expiry(self):
        """Requests older than the window do not count toward the limit."""
        from api.rate_limit import rate_limit, _windows
        import time as t_mod

        dep = rate_limit(2, 60, key="ip")
        ip_key = "10.2.0.1"

        # Manually pre-populate the window with two expired timestamps
        window_id = (ip_key, 2, 60)
        old_ts = t_mod.monotonic() - 120  # 2 minutes ago — outside the 60s window
        _windows[window_id].append(old_ts)
        _windows[window_id].append(old_ts)

        # Both are expired, so this call should succeed (not raise 429)
        asyncio.run(_call_dep(dep, ip=ip_key))


class TestRateLimitUser:
    """User-keyed rate limiter (LLM endpoint protection)."""

    def test_allows_under_limit(self):
        from api.rate_limit import rate_limit
        dep = rate_limit(10, 60, key="user")
        for _ in range(10):
            asyncio.run(_call_dep(dep, ip="5.5.5.5"))

    def test_blocks_over_limit(self):
        from api.rate_limit import rate_limit
        dep = rate_limit(3, 60, key="user")
        for _ in range(3):
            asyncio.run(_call_dep(dep, ip="6.6.6.6"))
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(_call_dep(dep, ip="6.6.6.6"))
        assert exc_info.value.status_code == 429

    def test_error_message_contains_limit(self):
        from api.rate_limit import rate_limit
        dep = rate_limit(2, 60, key="user")
        for _ in range(2):
            asyncio.run(_call_dep(dep, ip="7.7.7.7"))
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(_call_dep(dep, ip="7.7.7.7"))
        assert "2" in exc_info.value.detail
        assert "60" in exc_info.value.detail
