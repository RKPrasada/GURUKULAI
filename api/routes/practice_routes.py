"""
Practice session routes — topic-specific MCQ practice using circular question banks.

POST /api/practice/start   — fetch questions for a topic practice session
POST /api/practice/submit  — score answers, update weakness_map
GET  /api/practice/banks/{exam_key}  — bank stats (admin / NAGA)
POST /api/practice/seed/{exam_key}   — seed topic banks from general bank (NAGA only)
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from agents.practice_bank import get_practice_bank
from agents.exam_utils import load_syllabus
from api.middleware import require_auth
from models.student import WeaknessMap

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/practice", tags=["practice"])

NAGA_USER_ID = "naga"

# In-process session store (same pattern as diagnostic sessions)
_practice_sessions: dict[str, dict] = {}


# ── Pydantic models ─────────────────────────────────────────────────────────────

class StartPracticeRequest(BaseModel):
    exam_key: str
    subject: str
    topic: str
    subtopic: str = ""
    count: int = 10
    difficulty: str = "adaptive"   # easy | medium | hard | adaptive


class SubmitPracticeRequest(BaseModel):
    session_id: str
    answers: list[int]   # -1 = not attempted


class MorePracticeRequest(BaseModel):
    session_id: str


SESSION_QUESTION_CAP = 100   # max questions a single session can grow to


# ── Routes ──────────────────────────────────────────────────────────────────────

@router.post("/start")
async def start_practice(
    req: StartPracticeRequest,
    auth_id: str = Depends(require_auth),
):
    """
    Start a topic practice session.
    Returns questions from the 200Q circular buffer for this topic.
    LLM silently adds 20 fresh questions to the buffer in the background.
    """
    if req.count < 1 or req.count > 50:
        raise HTTPException(status_code=400, detail="count must be between 1 and 50")

    mgr = get_practice_bank()
    questions = mgr.get_questions(
        exam_key=req.exam_key,
        subject=req.subject,
        topic=req.topic,
        subtopic=req.subtopic,
        count=req.count,
        difficulty=req.difficulty,
    )

    scope = f"{req.topic} → {req.subtopic}" if req.subtopic else req.topic
    if not questions:
        raise HTTPException(
            status_code=503,
            detail=f"No questions available for {scope}. Try again shortly.",
        )

    session_id = str(uuid.uuid4())
    _practice_sessions[session_id] = {
        "student_id": auth_id,
        "exam_key": req.exam_key,
        "subject": req.subject,
        "topic": req.topic,
        "subtopic": req.subtopic,
        "difficulty": req.difficulty,
        "questions": questions,
        "seen_ids": {q["question_id"] for q in questions},
        "started_at": datetime.utcnow().isoformat(),
    }

    return {
        "session_id": session_id,
        "exam_key": req.exam_key,
        "subject": req.subject,
        "topic": req.topic,
        "subtopic": req.subtopic,
        "questions": questions,
        "total": len(questions),
        "cap": SESSION_QUESTION_CAP,
    }


@router.post("/more")
async def more_practice(req: MorePracticeRequest, auth_id: str = Depends(require_auth)):
    """
    Fetch the next batch of 10 questions for an ongoing session.
    Skips questions already shown, caps the session at SESSION_QUESTION_CAP (100).
    """
    session = _practice_sessions.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Practice session not found or expired")
    if session["student_id"] != auth_id:
        raise HTTPException(status_code=403, detail="Session belongs to a different student")

    seen = session.get("seen_ids", set())
    already = len(session["questions"])
    remaining = SESSION_QUESTION_CAP - already
    if remaining <= 0:
        return {"questions": [], "total": already, "cap_reached": True}

    batch = min(10, remaining)
    mgr = get_practice_bank()
    new_qs = mgr.get_questions(
        exam_key=session["exam_key"],
        subject=session["subject"],
        topic=session["topic"],
        subtopic=session.get("subtopic", ""),
        count=batch,
        difficulty=session.get("difficulty", "adaptive"),
        exclude_ids=seen,
    )
    if not new_qs:
        # Bank exhausted for this subtopic (no unseen questions available yet)
        return {"questions": [], "total": already, "exhausted": True}

    session["questions"].extend(new_qs)
    seen.update(q["question_id"] for q in new_qs)
    session["seen_ids"] = seen

    total = len(session["questions"])
    return {
        "questions": new_qs,
        "total": total,
        "cap_reached": total >= SESSION_QUESTION_CAP,
    }


@router.post("/submit")
async def submit_practice(
    req: SubmitPracticeRequest,
    auth_id: str = Depends(require_auth),
):
    """
    Score a completed practice session and update the student's weakness_map.
    """
    session = _practice_sessions.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Practice session not found or expired")
    if session["student_id"] != auth_id:
        raise HTTPException(status_code=403, detail="Session belongs to a different student")

    questions = session["questions"]
    answers = req.answers

    if len(answers) != len(questions):
        raise HTTPException(
            status_code=400,
            detail=f"Expected {len(questions)} answers, got {len(answers)}",
        )

    # Score
    correct = sum(
        1 for q, a in zip(questions, answers)
        if a != -1 and a == q.get("correct_index", -2)
    )
    attempted = sum(1 for a in answers if a != -1)
    score_pct = correct / len(questions)

    # Per-question review payload
    review = []
    for q, a in zip(questions, answers):
        review.append({
            "question_id": q.get("question_id"),
            "question_text": q.get("question_text_en", ""),
            "options": q.get("options", []),
            "your_answer": a,
            "correct_index": q.get("correct_index", 0),
            "correct": a != -1 and a == q.get("correct_index", -2),
            "explanation": q.get("explanation_en", ""),
        })

    # Update student weakness_map via the students store
    from api.main import _students, _save_student_fn
    student = _students.get(auth_id)
    if student:
        subject = session["subject"]
        topic = session["topic"]
        existing = next(
            (w for w in student.weakness_map if w.subject == subject and w.topic == topic),
            None,
        )
        if existing:
            total_attempts = existing.attempts + len(questions)
            existing.score_pct = (
                existing.score_pct * existing.attempts + score_pct * len(questions)
            ) / total_attempts
            existing.attempts = total_attempts
            existing.last_attempted = datetime.utcnow()
            # SM-2 update: quality 0-5 mapped from score
            quality = round(score_pct * 5)
            existing.update_sm2(quality)
        else:
            student.weakness_map.append(WeaknessMap(
                subject=subject,
                topic=topic,
                score_pct=score_pct,
                attempts=len(questions),
                last_attempted=datetime.utcnow(),
            ))
        _save_student_fn(student)

        # Log this session to the progress tracker
        from agents.progress_tracker import log_session
        started_at = session.get("started_at", datetime.utcnow().isoformat())
        try:
            started_dt = datetime.fromisoformat(started_at)
            duration_mins = round((datetime.utcnow() - started_dt).total_seconds() / 60)
        except Exception:
            duration_mins = None
        log_session(
            student_id=auth_id,
            session_type="practice",
            subject=session["subject"],
            topic=session["topic"],
            correct=correct,
            total=len(questions),
            duration_mins=duration_mins,
            exam_key=session.get("exam_key", ""),
        )

    del _practice_sessions[req.session_id]

    return {
        "session_id": req.session_id,
        "topic": session["topic"],
        "subject": session["subject"],
        "score_pct": round(score_pct * 100, 1),
        "correct": correct,
        "attempted": attempted,
        "total": len(questions),
        "review": review,
        "message": (
            f"Well done! {correct}/{len(questions)} correct on {session['topic']}."
            if score_pct >= 0.7
            else f"{correct}/{len(questions)} on {session['topic']} — keep practising, you'll get there."
        ),
    }


@router.get("/syllabus")
async def get_practice_syllabus(auth_id: str = Depends(require_auth)):
    """Return subjects and topics for the student's exam — drives the practice selector UI."""
    from api.main import _students
    from agents.exam_utils import exam_value
    student = _students.get(auth_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    exam_key = exam_value(student.exam_target)
    syllabus = load_syllabus(exam_key)
    subjects = [
        {
            "name": s["name"],
            "topics": [
                {
                    "name": t["name"],
                    "subtopics": [str(st) for st in t.get("subtopics", [])],
                }
                for t in s.get("topics", [])
            ],
        }
        for s in syllabus.get("subjects", [])
    ]
    return {"exam_key": exam_key, "subjects": subjects}


@router.get("/banks/{exam_key}")
async def get_bank_stats(
    exam_key: str,
    auth_id: str = Depends(require_auth),
):
    """Bank size per topic — available to NAGA and the student for their own exam."""
    from api.main import _students
    student = _students.get(auth_id)
    if auth_id != NAGA_USER_ID and (not student or student.exam_target != exam_key):
        raise HTTPException(status_code=403, detail="Access restricted to your own exam")

    mgr = get_practice_bank()
    stats = mgr.bank_stats(exam_key)
    total = sum(stats.values())
    return {
        "exam_key": exam_key,
        "topics": stats,
        "total_questions": total,
        "buffer_max_per_topic": 200,
    }


@router.post("/seed/{exam_key}")
async def seed_practice_banks(
    exam_key: str,
    auth_id: str = Depends(require_auth),
):
    """Seed topic banks from the general question bank (NAGA only). One-time setup."""
    if auth_id != NAGA_USER_ID:
        raise HTTPException(status_code=403, detail="NAGA access only")

    syllabus = load_syllabus(exam_key)
    mgr = get_practice_bank()
    total = mgr.seed_all_from_general_bank(exam_key, syllabus)

    return {
        "exam_key": exam_key,
        "questions_distributed": total,
        "message": f"Seeded {total} questions from general bank into topic practice banks for {exam_key}.",
    }
