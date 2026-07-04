from __future__ import annotations
"""
IAM middleware for VidyaBot API.

Issues a signed session token on login (demo or OAuth).
Every protected route validates the token via the `require_auth` dependency.
Token format: HMAC-SHA256 signed, carries student_id + expiry.
"""

import hashlib
import hmac
import json
import logging
import os
import time

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

SECRET = os.getenv("APP_SECRET_KEY", "dev-secret-change-in-production-32chars")
TOKEN_TTL = 86400 * 7  # 7 days

_bearer = HTTPBearer(auto_error=False)


def _sign(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True)
    sig = hmac.new(SECRET.encode(), raw.encode(), hashlib.sha256).hexdigest()
    import base64
    token = base64.urlsafe_b64encode(f"{raw}|{sig}".encode()).decode()
    return token


def _verify(token: str) -> dict | None:
    try:
        import base64
        decoded = base64.urlsafe_b64decode(token.encode()).decode()
        raw, sig = decoded.rsplit("|", 1)
        expected = hmac.new(SECRET.encode(), raw.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(raw)
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


def issue_token(student_id: str) -> str:
    payload = {
        "sub": student_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + TOKEN_TTL,
    }
    return _sign(payload)


async def require_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> str:
    """FastAPI dependency — returns student_id or raises 401."""
    # Allow health check without auth
    if request.url.path in ("/health", "/auth/login", "/auth/callback", "/api/student/demo", "/docs", "/openapi.json"):
        return ""

    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    payload = _verify(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return payload["sub"]


async def require_self(
    student_id: str,
    auth_student_id: str = Depends(require_auth),
) -> str:
    """Ensures the authenticated student can only access their own data."""
    if auth_student_id and auth_student_id != student_id:
        raise HTTPException(status_code=403, detail="Access denied: can only access your own data")
    return student_id
