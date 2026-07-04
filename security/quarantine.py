from __future__ import annotations
"""
Stateful quarantine: tracks injection attempts per student.
After THRESHOLD attempts within WINDOW_SECONDS, the student is blocked
for QUARANTINE_SECONDS. State is in-memory + persisted to SQLite.
"""

import hashlib
import logging
import sqlite3
import time
from pathlib import Path

logger = logging.getLogger(__name__)

THRESHOLD = 3             # attempts before quarantine
WINDOW_SECONDS = 600      # 10-minute rolling window
QUARANTINE_SECONDS = 1800 # 30-minute block


class QuarantineManager:
    def __init__(self, db_path: str = "vidyabot.db"):
        self._db = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self._db)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS threat_attempts (
                student_hash TEXT NOT NULL,
                threat_type TEXT NOT NULL,
                attempted_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS quarantine (
                student_hash TEXT PRIMARY KEY,
                quarantined_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                reason TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_threat_student
                ON threat_attempts(student_hash, attempted_at);
        """)
        conn.commit()
        conn.close()

    def _hash(self, student_id: str) -> str:
        return hashlib.sha256(student_id.encode()).hexdigest()[:32]

    def record_threat(self, student_id: str, threat_type: str) -> bool:
        """Record a threat attempt. Returns True if student is now quarantined."""
        h = self._hash(student_id)
        now = time.time()
        window_start = now - WINDOW_SECONDS

        conn = sqlite3.connect(self._db)
        try:
            conn.execute(
                "INSERT INTO threat_attempts (student_hash, threat_type, attempted_at) VALUES (?,?,?)",
                (h, threat_type, now),
            )
            count = conn.execute(
                "SELECT COUNT(*) FROM threat_attempts WHERE student_hash=? AND attempted_at > ?",
                (h, window_start),
            ).fetchone()[0]

            if count >= THRESHOLD:
                expires = now + QUARANTINE_SECONDS
                conn.execute(
                    "INSERT OR REPLACE INTO quarantine (student_hash, quarantined_at, expires_at, reason) VALUES (?,?,?,?)",
                    (h, now, expires, f"Exceeded {THRESHOLD} injection attempts in {WINDOW_SECONDS}s"),
                )
                logger.warning(f"Student {h[:8]}... QUARANTINED until {expires}")
                conn.commit()
                return True

            conn.commit()
            return False
        finally:
            conn.close()

    def is_quarantined(self, student_id: str) -> tuple[bool, float]:
        """Returns (is_blocked, seconds_remaining)."""
        h = self._hash(student_id)
        now = time.time()
        conn = sqlite3.connect(self._db)
        row = conn.execute(
            "SELECT expires_at FROM quarantine WHERE student_hash=? AND expires_at > ?",
            (h, now),
        ).fetchone()
        conn.close()
        if row:
            return True, row[0] - now
        return False, 0.0

    def lift_quarantine(self, student_id: str):
        h = self._hash(student_id)
        conn = sqlite3.connect(self._db)
        conn.execute("DELETE FROM quarantine WHERE student_hash=?", (h,))
        conn.commit()
        conn.close()

    def threat_count(self, student_id: str) -> int:
        h = self._hash(student_id)
        window_start = time.time() - WINDOW_SECONDS
        conn = sqlite3.connect(self._db)
        count = conn.execute(
            "SELECT COUNT(*) FROM threat_attempts WHERE student_hash=? AND attempted_at > ?",
            (h, window_start),
        ).fetchone()[0]
        conn.close()
        return count


# Singleton used across the app
_manager: QuarantineManager | None = None


def get_quarantine_manager(db_path: str = "vidyabot.db") -> QuarantineManager:
    global _manager
    if _manager is None:
        _manager = QuarantineManager(db_path)
    return _manager
