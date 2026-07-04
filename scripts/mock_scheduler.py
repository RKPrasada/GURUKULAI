"""
Mock test Saturday scheduler.

Runs as a background thread inside FastAPI lifespan.
Every 10 minutes, checks:
  - Is today Saturday?
  - Is the current time within the 1-hour advance window before the mock slot?
  - Has a paper already been generated for today?

If all three conditions are met, triggers paper generation for every exam
that has at least one active student.

Mock test slot: 16:00 Saturday (matches Dabbu study plan's Saturday last slot).
Generation trigger: 15:00–15:10 Saturday (1 hour in advance).

Can also be triggered manually via:
  POST /api/mock/generate/{exam_key}   (NAGA only)
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import date, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Day-of-week index for Saturday (Python: Monday=0 … Saturday=5)
SATURDAY = 5

# Mock test starts at 16:00; trigger generation at 15:00 (60 min ahead)
MOCK_HOUR = 16
TRIGGER_HOUR = MOCK_HOUR - 1   # 15

# Poll interval (seconds)
POLL_INTERVAL = 600   # 10 minutes

# Track which dates we have already triggered generation for
_triggered: set[str] = set()
_lock = threading.Lock()


def _next_saturday() -> date:
    today = date.today()
    days = (SATURDAY - today.weekday()) % 7
    if days == 0:
        return today
    return today.replace(day=today.day + days)


def _should_trigger_now() -> bool:
    now = datetime.now()
    return (
        now.weekday() == SATURDAY
        and now.hour == TRIGGER_HOUR
    )


def _get_active_exam_keys() -> list[str]:
    """
    Return exam keys that have at least one student in the DB.
    Falls back to all configured keys if DB is unavailable.
    """
    import os, sqlite3
    from models.mock_test import EXAM_CONFIGS

    db_path = os.getenv("DATABASE_URL", "sqlite:///./vidyabot.db").replace("sqlite:///", "")
    try:
        conn = sqlite3.connect(db_path)
        rows = conn.execute("SELECT DISTINCT exam_target FROM students").fetchall()
        conn.close()
        keys = [r[0] for r in rows if r[0] in EXAM_CONFIGS]
        return keys if keys else list(EXAM_CONFIGS.keys())
    except Exception:
        return list(EXAM_CONFIGS.keys())


def _notify_students(exam_key: str, paper_id: str) -> None:
    """Send a mock test reminder notification to all students on this exam."""
    import os, sqlite3, json, uuid
    from pathlib import Path

    db_path = os.getenv("DATABASE_URL", "sqlite:///./vidyabot.db").replace("sqlite:///", "")
    notif_path = Path("data/mentor/notifications.jsonl")
    notif_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            "SELECT student_id FROM students WHERE exam_target = ?", (exam_key,)
        ).fetchall()
        conn.close()
    except Exception:
        return

    for (student_id,) in rows:
        n = {
            "notification_id": str(uuid.uuid4()),
            "user_id": student_id,
            "type": "mock_test_ready",
            "title": "Mock Test starts in 1 hour!",
            "body": (
                f"Your weekly mock test paper is ready. "
                f"The test begins at {MOCK_HOUR}:00 today (Saturday). "
                f"Make sure you have 90–200 minutes free. Good luck!"
            ),
            "data": {"exam_key": exam_key, "paper_id": paper_id, "action": "start_mock_test"},
            "read": False,
            "created_at": datetime.utcnow().isoformat(),
        }
        with open(notif_path, "a") as f:
            f.write(json.dumps(n) + "\n")


def run_generation_for_exam(exam_key: str, scheduled_date: str | None = None) -> bool:
    """
    Generate a new paper for exam_key and notify students.
    Returns True on success.
    """
    from agents.mock_paper_generator import generate_paper
    paper = generate_paper(exam_key, scheduled_date=scheduled_date)
    if paper:
        _notify_students(exam_key, paper.paper_id)
        logger.info("MockScheduler: paper ready for %s — %s", exam_key, paper.paper_id)
        return True
    logger.error("MockScheduler: generation failed for %s", exam_key)
    return False


def _scheduler_loop() -> None:
    """Background thread: check every POLL_INTERVAL seconds."""
    logger.info("MockScheduler: started (checks every %ds)", POLL_INTERVAL)
    while True:
        try:
            if _should_trigger_now():
                today_str = date.today().isoformat()
                with _lock:
                    already_done = today_str in _triggered

                if not already_done:
                    logger.info("MockScheduler: Saturday trigger firing for %s", today_str)
                    exam_keys = _get_active_exam_keys()
                    for exam_key in exam_keys:
                        run_generation_for_exam(exam_key, scheduled_date=today_str)
                    with _lock:
                        _triggered.add(today_str)
        except Exception as e:
            logger.error("MockScheduler: loop error — %s", e)

        time.sleep(POLL_INTERVAL)


def start_scheduler() -> threading.Thread:
    """Start the scheduler as a daemon thread. Call from FastAPI lifespan."""
    t = threading.Thread(target=_scheduler_loop, daemon=True, name="MockScheduler")
    t.start()
    return t
