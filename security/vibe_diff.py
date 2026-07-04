from __future__ import annotations
"""
Vibe Diff — MFA layer for high-stakes, irreversible agent actions.

Before executing actions like sending Gmail or creating Calendar events,
the agent registers a "pending action" and the UI must confirm it.
Unconfirmed actions expire after EXPIRY_SECONDS.
"""

import hashlib
import secrets
import time
from dataclasses import dataclass, field
from typing import Callable, Any

EXPIRY_SECONDS = 300  # 5-minute confirmation window

# Risk levels
LOW = "low"       # read-only, fully reversible
MEDIUM = "medium" # creates data, deletable
HIGH = "high"     # sends external communication, calendar events
CRITICAL = "critical"  # billing, data deletion, mass communication

# Registry of which actions are high-stakes
ACTION_RISK = {
    "send_gmail_digest":        HIGH,
    "create_calendar_events":   MEDIUM,
    "save_to_drive":            LOW,
    "search_youtube":           LOW,
    "start_diagnostic":         LOW,
    "submit_diagnostic":        MEDIUM,
    "delete_student_data":      CRITICAL,
}


@dataclass
class PendingAction:
    token: str
    student_id: str
    action_name: str
    risk_level: str
    description: str
    payload: dict
    created_at: float = field(default_factory=time.time)
    confirmed: bool = False

    @property
    def is_expired(self) -> bool:
        return time.time() - self.created_at > EXPIRY_SECONDS

    @property
    def expires_in(self) -> int:
        return max(0, int(EXPIRY_SECONDS - (time.time() - self.created_at)))

    def to_dict(self) -> dict:
        return {
            "token": self.token,
            "action_name": self.action_name,
            "risk_level": self.risk_level,
            "description": self.description,
            "expires_in": self.expires_in,
            "requires_confirmation": True,
        }


class VibeDiff:
    """Gate high-stakes actions behind explicit user confirmation."""

    def __init__(self):
        self._pending: dict[str, PendingAction] = {}

    def _cleanup(self):
        expired = [t for t, a in self._pending.items() if a.is_expired]
        for t in expired:
            del self._pending[t]

    def requires_confirmation(self, action_name: str) -> bool:
        return action_name in ACTION_RISK

    def register(self, student_id: str, action_name: str, description: str, payload: dict) -> PendingAction:
        """Register a high-stakes action. Returns PendingAction for the UI to display."""
        self._cleanup()
        token = secrets.token_urlsafe(16)
        risk = ACTION_RISK.get(action_name, MEDIUM)
        action = PendingAction(
            token=token,
            student_id=student_id,
            action_name=action_name,
            risk_level=risk,
            description=description,
            payload=payload,
        )
        self._pending[token] = action
        return action

    def confirm(self, token: str, student_id: str) -> tuple[bool, PendingAction | None]:
        """Confirm a pending action. Returns (success, action)."""
        self._cleanup()
        action = self._pending.get(token)
        if not action:
            return False, None
        if action.is_expired:
            del self._pending[token]
            return False, None
        if action.student_id != student_id:
            return False, None
        action.confirmed = True
        del self._pending[token]
        return True, action

    def cancel(self, token: str, student_id: str) -> bool:
        action = self._pending.get(token)
        if action and action.student_id == student_id:
            del self._pending[token]
            return True
        return False

    def pending_for_student(self, student_id: str) -> list[dict]:
        self._cleanup()
        return [a.to_dict() for a in self._pending.values() if a.student_id == student_id]


# Singleton
_vibe_diff: VibeDiff | None = None


def get_vibe_diff() -> VibeDiff:
    global _vibe_diff
    if _vibe_diff is None:
        _vibe_diff = VibeDiff()
    return _vibe_diff
