"""
Progress tracking layer for Gurukul AI.

Stores three data streams per student:
  data/progress/{student_id}/snapshots.jsonl  — weekly weakness_map snapshots
  data/progress/{student_id}/sessions.jsonl   — every practice / mock session
  data/progress/{student_id}/activity.jsonl   — daily activity timestamps (streak calendar)

Public API:
  take_snapshot(student)           — call after diagnostic or study-plan milestone
  log_session(student_id, ...)     — call after every practice/mock submit
  log_activity(student_id)         — call on any study interaction (updates streak calendar)
  get_progress_data(student)       — assemble full progress payload for the API
  analyze_for_dabbu(student)       — return an InterventionSummary for Dabbu to act on
"""

from __future__ import annotations

import json
import logging
import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

PROGRESS_DIR = Path("data/progress")
PROGRESS_DIR.mkdir(parents=True, exist_ok=True)

TARGET_SCORE = 0.80   # 80% is the universal target for all topics


# ── File helpers ───────────────────────────────────────────────────────────────

def _student_dir(student_id: str) -> Path:
    p = PROGRESS_DIR / student_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def _snapshots_path(student_id: str) -> Path:
    return _student_dir(student_id) / "snapshots.jsonl"


def _sessions_path(student_id: str) -> Path:
    return _student_dir(student_id) / "sessions.jsonl"


def _activity_path(student_id: str) -> Path:
    return _student_dir(student_id) / "activity.jsonl"


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except Exception:
                    continue
    return out


def _append_jsonl(path: Path, record: dict) -> None:
    with open(path, "a") as f:
        f.write(json.dumps(record, default=str) + "\n")


# ── Snapshot ───────────────────────────────────────────────────────────────────

def take_snapshot(student, label: str = "periodic") -> None:
    """Save current weakness_map as a dated snapshot."""
    snap = {
        "snapshot_id": str(uuid.uuid4()),
        "date": date.today().isoformat(),
        "week": date.today().isocalendar()[1],
        "label": label,   # "diagnostic", "plan_approved", "periodic", "manual"
        "avg_score": (
            sum(w.score_pct for w in student.weakness_map) / len(student.weakness_map)
            if student.weakness_map else 0.0
        ),
        "total_attempts": sum(w.attempts for w in student.weakness_map),
        "topics": [
            {
                "subject": w.subject,
                "topic": w.topic,
                "score_pct": round(w.score_pct, 4),
                "attempts": w.attempts,
                "ease_factor": round(w.ease_factor, 3),
                "interval_days": w.interval_days,
                "next_review_date": w.next_review_date.isoformat(),
            }
            for w in student.weakness_map
        ],
    }
    _append_jsonl(_snapshots_path(student.student_id), snap)
    logger.info("ProgressTracker: snapshot '%s' for %s (avg %.0f%%)",
                label, student.student_id, snap["avg_score"] * 100)


# ── Session log ────────────────────────────────────────────────────────────────

def log_session(
    student_id: str,
    session_type: str,   # "practice" | "mock" | "diagnostic"
    subject: str,
    topic: str,
    correct: int,
    total: int,
    duration_mins: Optional[int] = None,
    exam_key: str = "",
) -> None:
    """Log a completed practice/mock/diagnostic session."""
    record = {
        "session_id": str(uuid.uuid4()),
        "date": date.today().isoformat(),
        "datetime": datetime.utcnow().isoformat(),
        "session_type": session_type,
        "exam_key": exam_key,
        "subject": subject,
        "topic": topic,
        "correct": correct,
        "total": total,
        "score_pct": round(correct / total, 4) if total else 0.0,
        "duration_mins": duration_mins,
    }
    _append_jsonl(_sessions_path(student_id), record)
    log_activity(student_id)


# ── Activity / streak calendar ─────────────────────────────────────────────────

def log_activity(student_id: str) -> None:
    """Record a study event for the streak calendar (one record per event)."""
    _append_jsonl(_activity_path(student_id), {
        "date": date.today().isoformat(),
        "ts": datetime.utcnow().isoformat(),
    })


def _build_streak_calendar(student_id: str, days: int = 60) -> list[dict]:
    """Return one entry per day for the past `days` days."""
    activity = _read_jsonl(_activity_path(student_id))
    counts: dict[str, int] = defaultdict(int)
    for a in activity:
        counts[a["date"]] += 1

    today = date.today()
    calendar = []
    for i in range(days - 1, -1, -1):
        d = (today - timedelta(days=i)).isoformat()
        calendar.append({"date": d, "count": counts.get(d, 0)})
    return calendar


# ── Weekly history ─────────────────────────────────────────────────────────────

def _weekly_topic_history(student_id: str) -> dict[str, list[dict]]:
    """
    Returns {topic_key: [{week, date, score_pct}, ...]} from all snapshots.
    topic_key = "subject::topic"
    """
    snaps = _read_jsonl(_snapshots_path(student_id))
    history: dict[str, list[dict]] = defaultdict(list)
    for snap in snaps:
        for t in snap.get("topics", []):
            key = f"{t['subject']}::{t['topic']}"
            history[key].append({
                "date": snap["date"],
                "week": snap.get("week"),
                "label": snap.get("label", ""),
                "score_pct": t["score_pct"],
            })
    return dict(history)


# ── Study plan completion ──────────────────────────────────────────────────────

def log_block_completion(student_id: str, block_id: str, subject: str, topic: str, session_type: str) -> None:
    """Record a completed study plan block."""
    _append_jsonl(_student_dir(student_id) / "plan_completions.jsonl", {
        "date": date.today().isoformat(),
        "block_id": block_id,
        "subject": subject,
        "topic": topic,
        "session_type": session_type,
    })
    log_activity(student_id)


def _plan_completion_stats(student_id: str, active_plan: Optional[dict]) -> dict:
    """Return overall and per-type completion stats for the active plan."""
    completions = _read_jsonl(_student_dir(student_id) / "plan_completions.jsonl")
    completed_ids = {c["block_id"] for c in completions}

    if not active_plan:
        return {"has_plan": False, "completed": len(completed_ids), "total": 0, "pct": 0.0}

    total_blocks = 0
    type_totals: dict[str, int] = defaultdict(int)
    type_done: dict[str, int] = defaultdict(int)

    for week in active_plan.get("weeks", []):
        for day in week.get("days", []):
            for block in day.get("blocks", []):
                bid = block.get("block_id", "")
                stype = block.get("session_type", "STUDY")
                total_blocks += 1
                type_totals[stype] += 1
                if bid in completed_ids or block.get("completed", False):
                    type_done[stype] += 1

    completed_total = sum(type_done.values())
    return {
        "has_plan": True,
        "completed": completed_total,
        "total": total_blocks,
        "pct": round(completed_total / total_blocks * 100, 1) if total_blocks else 0.0,
        "by_type": {t: {"done": type_done[t], "total": type_totals[t]} for t in type_totals},
    }


# ── Main data assembly ─────────────────────────────────────────────────────────

def get_progress_data(student, active_plan: Optional[dict] = None) -> dict:
    """Assemble the full progress payload for the API endpoint."""
    sid = student.student_id
    snaps = _read_jsonl(_snapshots_path(sid))
    sessions = _read_jsonl(_sessions_path(sid))

    # Initial scores — first snapshot labelled 'diagnostic' or the oldest snapshot
    initial_snap = next((s for s in snaps if s.get("label") == "diagnostic"), snaps[0] if snaps else None)
    initial_scores: dict[str, float] = {}
    if initial_snap:
        for t in initial_snap.get("topics", []):
            initial_scores[f"{t['subject']}::{t['topic']}"] = t["score_pct"]

    # Current scores + SM-2
    current_topics = []
    for w in student.weakness_map:
        key = f"{w.subject}::{w.topic}"
        days_until_review = (w.next_review_date.date() - date.today()).days
        current_topics.append({
            "subject": w.subject,
            "topic": w.topic,
            "score_pct": round(w.score_pct, 4),
            "attempts": w.attempts,
            "ease_factor": round(w.ease_factor, 3),
            "interval_days": w.interval_days,
            "next_review_date": w.next_review_date.date().isoformat(),
            "days_until_review": days_until_review,
            "overdue": days_until_review < 0,
            "ease_label": (
                "Hard" if w.ease_factor < 1.8
                else "Moderate" if w.ease_factor < 2.3
                else "Good" if w.ease_factor < 2.8
                else "Easy"
            ),
            "initial_score_pct": round(initial_scores.get(key, w.score_pct), 4),
            "target_score_pct": TARGET_SCORE,
            "improvement": round(w.score_pct - initial_scores.get(key, w.score_pct), 4),
        })

    # Weekly history per topic
    topic_history = _weekly_topic_history(sid)

    # Practice session history (most recent 50)
    recent_sessions = sorted(sessions, key=lambda s: s["datetime"], reverse=True)[:50]

    # Session counts per subject
    subject_sessions: dict[str, int] = defaultdict(int)
    for s in sessions:
        subject_sessions[s.get("subject", "Unknown")] += 1

    # Streak calendar
    calendar = _build_streak_calendar(sid, days=60)

    # Plan completion
    plan_stats = _plan_completion_stats(sid, active_plan)

    # Overdue review count (SM-2)
    overdue_count = sum(1 for t in current_topics if t["overdue"])

    return {
        "student_id": sid,
        "generated_at": datetime.utcnow().isoformat(),
        "summary": {
            "avg_score_pct": round(
                sum(w.score_pct for w in student.weakness_map) / len(student.weakness_map), 4
            ) if student.weakness_map else 0.0,
            "topics_on_target": sum(1 for t in current_topics if t["score_pct"] >= TARGET_SCORE),
            "topics_total": len(current_topics),
            "overdue_reviews": overdue_count,
            "total_sessions": len(sessions),
            "streak_days": student.study_streak_days,
            "plan_completion_pct": plan_stats["pct"],
        },
        "current_topics": current_topics,
        "topic_history": topic_history,
        "recent_sessions": recent_sessions,
        "subject_sessions": dict(subject_sessions),
        "streak_calendar": calendar,
        "plan_stats": plan_stats,
        "snapshots_count": len(snaps),
    }


# ── Dabbu analysis ─────────────────────────────────────────────────────────────

def analyze_for_dabbu(student, active_plan: Optional[dict] = None) -> dict:
    """
    Produce a structured analysis Dabbu uses to decide if intervention is warranted.
    Returns a dict with flags and severity so Dabbu can craft a targeted proposal.
    """
    data = get_progress_data(student, active_plan)
    topics = data["current_topics"]
    sessions = _read_jsonl(_sessions_path(student.student_id))
    snaps = _read_jsonl(_snapshots_path(student.student_id))

    # Flag 1: stagnant topics — score unchanged across last 2+ snapshots
    stagnant = []
    topic_history = data["topic_history"]
    for t in topics:
        key = f"{t['subject']}::{t['topic']}"
        hist = topic_history.get(key, [])
        if len(hist) >= 2:
            scores = [h["score_pct"] for h in hist[-3:]]
            variance = max(scores) - min(scores)
            if variance < 0.03 and t["score_pct"] < TARGET_SCORE:
                stagnant.append({**t, "recent_scores": scores})

    # Flag 2: declining topics — score decreased in most recent snapshot
    declining = []
    for t in topics:
        key = f"{t['subject']}::{t['topic']}"
        hist = topic_history.get(key, [])
        if len(hist) >= 2 and hist[-1]["score_pct"] < hist[-2]["score_pct"] - 0.05:
            declining.append({**t, "drop": round(hist[-2]["score_pct"] - hist[-1]["score_pct"], 3)})

    # Flag 3: low plan completion
    plan_stats = data["plan_stats"]
    low_completion = plan_stats["has_plan"] and plan_stats["pct"] < 70.0

    # Flag 4: overdue SM-2 reviews
    overdue = [t for t in topics if t["overdue"]]

    # Flag 5: no activity in 7+ days
    calendar = data["streak_calendar"]
    recent_7 = calendar[-7:]
    inactive_7d = all(d["count"] == 0 for d in recent_7)

    # Flag 6: critical topics (score < 0.30) that haven't improved
    critical_stuck = [t for t in topics if t["score_pct"] < 0.30 and t["improvement"] <= 0.05]

    # Severity
    issues = (
        len(stagnant) * 2
        + len(declining) * 2
        + (5 if inactive_7d else 0)
        + len(critical_stuck) * 3
        + (3 if low_completion else 0)
        + len(overdue)
    )
    severity = "high" if issues >= 8 else "medium" if issues >= 4 else "low"

    return {
        "student_id": student.student_id,
        "exam_target": student.exam_target,
        "avg_score": data["summary"]["avg_score_pct"],
        "stagnant_topics": stagnant,
        "declining_topics": declining,
        "critical_stuck": critical_stuck,
        "overdue_reviews": overdue,
        "low_plan_completion": low_completion,
        "plan_completion_pct": plan_stats.get("pct", 0.0),
        "inactive_7d": inactive_7d,
        "severity": severity,
        "issues_score": issues,
    }
