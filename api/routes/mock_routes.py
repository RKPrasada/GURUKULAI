"""
Mock test routes.

GET  /api/mock/status/{exam_key}         — paper availability + metadata
GET  /api/mock/paper/{exam_key}          — full paper WITHOUT answers (student view)
POST /api/mock/session/start             — start or resume a session
PUT  /api/mock/session/{session_id}      — autosave answers + flagged mid-test
POST /api/mock/session/{session_id}/submit — submit, score, save to progress
GET  /api/mock/session/{session_id}      — get a session (resume / results)
GET  /api/mock/history                   — student's past completed sessions
POST /api/mock/generate/{exam_key}       — NAGA: manually trigger paper generation
GET  /api/mock/archive/{exam_key}        — NAGA: list all archived papers
"""

from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel

from api.rate_limit import rate_limit
from agents.mock_paper_generator import (
    list_archive, load_current_paper, paper_status,
)
from api.middleware import require_auth
from models.mock_test import MockSession

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/mock", tags=["mock"])

NAGA_USER_ID = "naga"
SESSIONS_DIR = Path("data/mock_sessions")
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

_session_lock = threading.Lock()


# ── Pydantic models ────────────────────────────────────────────────────────────

class StartSessionRequest(BaseModel):
    exam_key: str


class AutosaveRequest(BaseModel):
    answers: list[int]
    flagged: list[int]


class SubmitRequest(BaseModel):
    answers: list[int]
    flagged: list[int]
    timed_out: bool = False


# ── Session helpers ────────────────────────────────────────────────────────────

def _session_path(student_id: str, session_id: str) -> Path:
    d = SESSIONS_DIR / student_id
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{session_id}.json"


def _save_session(session: MockSession) -> None:
    path = _session_path(session.student_id, session.session_id)
    with _session_lock:
        path.write_text(json.dumps(session.to_dict(), ensure_ascii=False, indent=2))


def _load_session(student_id: str, session_id: str) -> Optional[MockSession]:
    path = _session_path(student_id, session_id)
    if not path.exists():
        return None
    try:
        return MockSession.from_dict(json.loads(path.read_text()))
    except Exception:
        return None


def _active_session(student_id: str, exam_key: str) -> Optional[MockSession]:
    """Return an in-progress (not submitted, not timed-out) session for this exam."""
    d = SESSIONS_DIR / student_id
    if not d.exists():
        return None
    for f in d.glob("*.json"):
        try:
            s = MockSession.from_dict(json.loads(f.read_text()))
            if s.exam_key == exam_key and not s.submitted and s.seconds_remaining > 0:
                return s
        except Exception:
            continue
    return None


def _student_history(student_id: str) -> list[dict]:
    d = SESSIONS_DIR / student_id
    if not d.exists():
        return []
    results = []
    for f in sorted(d.glob("*.json"), reverse=True):
        try:
            s = MockSession.from_dict(json.loads(f.read_text()))
            if s.submitted:
                results.append({
                    "session_id": s.session_id,
                    "exam_key": s.exam_key,
                    "paper_id": s.paper_id,
                    "started_at": s.started_at,
                    "submitted_at": s.submitted_at,
                    "timed_out": s.timed_out,
                    "score": s.score,
                    "max_score": s.max_score,
                    "score_pct": round(s.score / s.max_score * 100, 1) if s.max_score else 0,
                    "rank_estimate_pct": s.rank_estimate_pct,
                    "section_scores": s.section_scores,
                })
        except Exception:
            continue
    return results


# ── Scorer ────────────────────────────────────────────────────────────────────

def _score_session(session: MockSession, paper_data: dict) -> MockSession:
    """
    Score submitted answers against the paper.
    Updates session.score, section_scores, rank_estimate_pct in-place.
    """
    all_questions: list[dict] = []
    section_map: list[tuple[str, int, int]] = []   # (name, start_idx, end_idx)
    idx = 0
    for sec in paper_data.get("sections", []):
        start = idx
        for q in sec.get("questions", []):
            all_questions.append(q)
            idx += 1
        section_map.append((sec["name"], start, idx))

    answers = session.answers
    total_score = 0.0
    max_score = 0.0
    section_scores = []

    for sec_name, start, end in section_map:
        sec_score = 0.0
        sec_max = 0.0
        correct_count = 0
        wrong_count = 0
        unattempted = 0

        for qi in range(start, min(end, len(answers))):
            q = all_questions[qi]
            marks = float(q.get("marks", 1.0))
            neg = float(q.get("negative_marks", 1 / 3))
            sec_max += marks
            a = answers[qi]
            if a == -1:
                unattempted += 1
            elif a == q.get("correct_index", -2):
                sec_score += marks
                correct_count += 1
            else:
                sec_score -= neg
                wrong_count += 1

        section_scores.append({
            "name": sec_name,
            "score": round(sec_score, 2),
            "max_score": round(sec_max, 2),
            "correct": correct_count,
            "wrong": wrong_count,
            "unattempted": unattempted,
            "accuracy_pct": round(correct_count / max(correct_count + wrong_count, 1) * 100, 1),
        })
        total_score += sec_score
        max_score += sec_max

    session.score = round(total_score, 2)
    session.max_score = round(max_score, 2)
    session.section_scores = section_scores

    # Simple rank estimate: scoring above pass threshold
    pass_pct = paper_data.get("pass_marks_pct", 0.40)
    score_ratio = total_score / max_score if max_score else 0
    # Rough rank percentile: linear between 0% (below pass) and 95% (near perfect)
    if score_ratio <= pass_pct:
        rank_pct = max(0.0, score_ratio / pass_pct * 30)
    else:
        rank_pct = 30 + (score_ratio - pass_pct) / (1 - pass_pct) * 65
    session.rank_estimate_pct = round(min(rank_pct, 99.0), 1)

    return session


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/status/{exam_key}")
async def get_paper_status(exam_key: str, auth_id: str = Depends(require_auth)):
    """Check if a paper is ready for this exam, and whether student has an active/past session."""
    status = paper_status(exam_key)
    active = _active_session(auth_id, exam_key)
    history = _student_history(auth_id)
    past = [h for h in history if h["exam_key"] == exam_key]
    return {
        **status,
        "active_session_id": active.session_id if active else None,
        "seconds_remaining": active.seconds_remaining if active else None,
        "past_attempts": len(past),
        "best_score_pct": max((h["score_pct"] for h in past), default=None),
    }


@router.get("/paper/{exam_key}")
async def get_paper(exam_key: str, auth_id: str = Depends(require_auth)):
    """Return the current paper WITHOUT correct answers (student-safe view)."""
    paper = load_current_paper(exam_key)
    if not paper:
        raise HTTPException(status_code=404, detail=f"No paper available for {exam_key} yet. Check back closer to Saturday.")
    return paper.to_dict(include_answers=False)


@router.post("/session/start")
async def start_session(req: StartSessionRequest, auth_id: str = Depends(require_auth)):
    """Start a new mock test session (or return existing active session to resume)."""
    # Check for in-progress session
    active = _active_session(auth_id, req.exam_key)
    if active:
        paper = load_current_paper(req.exam_key)
        return {
            "session_id": active.session_id,
            "resumed": True,
            "seconds_remaining": active.seconds_remaining,
            "answers": active.answers,
            "flagged": active.flagged,
            "paper": paper.to_dict(include_answers=False) if paper else None,
        }

    paper = load_current_paper(req.exam_key)
    if not paper:
        raise HTTPException(status_code=404, detail="No paper available yet.")

    session = MockSession(
        session_id=str(uuid.uuid4()),
        student_id=auth_id,
        exam_key=req.exam_key,
        paper_id=paper.paper_id,
        started_at=datetime.utcnow().isoformat(),
        duration_mins=paper.duration_mins,
        total_questions=paper.total_questions,
        answers=[-1] * paper.total_questions,
        flagged=[],
    )
    _save_session(session)

    # Log activity for streak
    from agents.progress_tracker import log_activity
    log_activity(auth_id)

    return {
        "session_id": session.session_id,
        "resumed": False,
        "seconds_remaining": session.seconds_remaining,
        "answers": session.answers,
        "flagged": session.flagged,
        "paper": paper.to_dict(include_answers=False),
    }


@router.put("/session/{session_id}")
async def autosave(session_id: str, req: AutosaveRequest, auth_id: str = Depends(require_auth)):
    """Autosave answers + flagged state mid-test (called every 30s from frontend)."""
    session = _load_session(auth_id, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.submitted:
        raise HTTPException(status_code=400, detail="Session already submitted")
    if session.seconds_remaining <= 0:
        raise HTTPException(status_code=400, detail="Session timed out")
    session.answers = req.answers
    session.flagged = req.flagged
    _save_session(session)
    return {"saved": True, "seconds_remaining": session.seconds_remaining}


@router.post("/session/{session_id}/submit")
async def submit_session(
    session_id: str,
    req: SubmitRequest,
    auth_id: str = Depends(require_auth),
):
    """
    Submit the mock test. Scores answers, updates weakness_map, logs progress.
    """
    session = _load_session(auth_id, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.submitted:
        return {"already_submitted": True, "session": session.to_dict()}

    # Load paper WITH answers for scoring
    paper = load_current_paper(session.exam_key)
    if not paper:
        raise HTTPException(status_code=500, detail="Paper not found for scoring")

    session.answers = req.answers
    session.flagged = req.flagged
    session.submitted = True
    session.submitted_at = datetime.utcnow().isoformat()
    session.timed_out = req.timed_out

    paper_dict = paper.to_dict(include_answers=True)
    session = _score_session(session, paper_dict)
    _save_session(session)

    # Update weakness_map from section performance
    from api.main import _students, _save_student_fn
    from agents.progress_tracker import log_session, take_snapshot
    student = _students.get(auth_id)

    if student and session.section_scores:
        for sec in session.section_scores:
            if sec["total"] if "total" in sec else (sec["correct"] + sec["wrong"] + sec["unattempted"]):
                total_q = sec["correct"] + sec["wrong"] + sec["unattempted"]
                if total_q == 0:
                    continue
                score_pct = sec["correct"] / total_q
                from models.student import WeaknessMap
                subject = sec["name"]
                existing = next(
                    (w for w in student.weakness_map if w.subject == subject and w.topic == "Mock Test"),
                    None,
                )
                if existing:
                    total_a = existing.attempts + total_q
                    existing.score_pct = (existing.score_pct * existing.attempts + score_pct * total_q) / total_a
                    existing.attempts = total_a
                    existing.update_sm2(round(score_pct * 5))
                else:
                    student.weakness_map.append(WeaknessMap(
                        subject=subject, topic="Mock Test",
                        score_pct=score_pct, attempts=total_q,
                    ))

        student.total_questions_attempted = (student.total_questions_attempted or 0) + session.total_questions
        _save_student_fn(student)

        # Log session to progress tracker
        overall_correct = sum(s["correct"] for s in session.section_scores)
        log_session(
            student_id=auth_id,
            session_type="mock",
            subject="Full Paper",
            topic=paper.exam_name,
            correct=overall_correct,
            total=session.total_questions,
            duration_mins=paper.duration_mins - session.seconds_remaining // 60,
            exam_key=session.exam_key,
        )
        take_snapshot(student, label="mock_completed")

    return {
        "submitted": True,
        "score": session.score,
        "max_score": session.max_score,
        "score_pct": round(session.score / session.max_score * 100, 1) if session.max_score else 0,
        "rank_estimate_pct": session.rank_estimate_pct,
        "section_scores": session.section_scores,
        "timed_out": session.timed_out,
        "session_id": session.session_id,
    }


@router.get("/session/{session_id}")
async def get_session(session_id: str, auth_id: str = Depends(require_auth)):
    """Get session state — used for results page and resume."""
    session = _load_session(auth_id, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    result = session.to_dict()
    result["seconds_remaining"] = session.seconds_remaining

    # If submitted, include paper WITH answers for review
    if session.submitted:
        paper = load_current_paper(session.exam_key)
        if paper:
            result["paper"] = paper.to_dict(include_answers=True)

    return result


@router.get("/history")
async def get_history(auth_id: str = Depends(require_auth)):
    """Student's past mock test attempts (most recent first)."""
    return {"history": _student_history(auth_id)}


# ── NAGA routes ────────────────────────────────────────────────────────────────

_rl_generate = rate_limit(5, 3600)  # 5 manual generations / hour / user


@router.post("/generate/{exam_key}")
async def manual_generate(
    exam_key: str,
    request: Request,
    background_tasks: BackgroundTasks,
    auth_id: str = Depends(require_auth),
    _rl: None = Depends(_rl_generate),
    scheduled_date: Optional[str] = None,
):
    """NAGA: trigger paper generation manually. Runs in background."""
    if auth_id != NAGA_USER_ID:
        raise HTTPException(status_code=403, detail="NAGA access only")

    from scripts.mock_scheduler import run_generation_for_exam

    def _gen():
        run_generation_for_exam(exam_key, scheduled_date=scheduled_date)

    background_tasks.add_task(_gen)
    return {
        "status": "generating",
        "exam_key": exam_key,
        "message": f"Paper generation started for {exam_key}. Check /api/mock/status/{exam_key} in a few minutes.",
    }


@router.get("/archive/{exam_key}")
async def get_archive(exam_key: str, auth_id: str = Depends(require_auth)):
    """NAGA: list all archived papers for an exam."""
    if auth_id != NAGA_USER_ID:
        raise HTTPException(status_code=403, detail="NAGA access only")
    return {"exam_key": exam_key, "archive": list_archive(exam_key)}
