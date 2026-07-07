"""
Dabbu API routes — study plan generation, NAGA approval workflow, content moderation.

Student endpoints:
  POST /api/dabbu/study-plan          — trigger Dabbu to generate a plan
  GET  /api/dabbu/study-plan          — get active (approved) plan
  GET  /api/dabbu/study-plan/proposed — get proposed plan (pending NAGA approval)
  POST /api/dabbu/check-progress      — check if re-diagnostic is recommended

NAGA-only endpoints:
  GET  /api/dabbu/naga/pending              — all pending proposals (plans + notes + videos)
  POST /api/dabbu/naga/approve-plan         — approve a student's study plan
  POST /api/dabbu/naga/reject-plan          — reject a student's study plan
  POST /api/dabbu/naga/scan-weaknesses      — trigger common-weakness scan for an exam
  POST /api/dabbu/naga/notes/approve        — approve a pending note
  POST /api/dabbu/naga/notes/reject         — reject a pending note
  GET  /api/dabbu/naga/videos               — list flagged YouTube videos
  POST /api/dabbu/naga/videos/approve       — approve a flagged video
  POST /api/dabbu/naga/videos/reject        — reject/block a flagged video
  POST /api/dabbu/naga/videos/blacklist     — permanently blacklist a channel or video
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from agents.dabbu_agent import get_dabbu
from api.middleware import require_auth
from models.student import StudentProfile

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dabbu", tags=["dabbu"])

NAGA_USER_ID = "naga"
STUDY_PLANS_DIR = Path("data/study_plans")
STUDY_PLANS_DIR.mkdir(parents=True, exist_ok=True)


# ── Pydantic models ────────────────────────────────────────────────────────────

class GeneratePlanRequest(BaseModel):
    exam_date: Optional[str] = None   # ISO date, e.g. "2026-12-15"


class ApprovePlanRequest(BaseModel):
    student_id: str
    naga_note: str = ""


class RejectPlanRequest(BaseModel):
    student_id: str
    reason: str = ""


class WeaknessScanRequest(BaseModel):
    exam_key: str


class NoteApprovalRequest(BaseModel):
    exam: str
    subject: str
    topic: str
    naga_note: str = ""


class VideoActionRequest(BaseModel):
    video_id: str
    naga_note: str = ""


class BlacklistRequest(BaseModel):
    video_id: Optional[str] = None
    channel: Optional[str] = None


class KeywordRequest(BaseModel):
    word: str
    tier: str   # "blocked" or "flagged"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _require_naga(auth_id: str) -> None:
    if auth_id != NAGA_USER_ID:
        raise HTTPException(status_code=403, detail="NAGA access only")


def _get_student_from_store(student_id: str, students_store: dict) -> StudentProfile:
    student = students_store.get(student_id)
    if not student:
        # Lazy-load from DB on cache miss (e.g. fresh Cloud Run cold-start)
        try:
            from api.main import _load_student_from_db
            student = _load_student_from_db(student_id)
            if student:
                students_store[student_id] = student
        except Exception:
            pass
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")
    return student


# ── Student routes ─────────────────────────────────────────────────────────────

@router.post("/study-plan")
async def generate_study_plan(
    req: GeneratePlanRequest,
    auth_id: str = Depends(require_auth),
):
    """
    Trigger Dabbu to generate a personalised study plan for the authenticated student.
    The plan is sent to NAGA for approval — student sees it only after NAGA approves.
    Returns the proposed plan immediately so the student knows it's in review.
    """
    from api.main import _students  # import here to avoid circular at module load
    student = _get_student_from_store(auth_id, _students)

    # Auto-heal: if the student has a weakness_map they clearly completed the diagnostic,
    # even if the flag wasn't persisted (e.g. server restart before save completed).
    if not student.diagnostic_done and student.weakness_map:
        student.diagnostic_done = True
        from api.main import _save_student_to_db
        try:
            _save_student_to_db(student)
        except Exception:
            pass

    if not student.diagnostic_done:
        raise HTTPException(
            status_code=400,
            detail="Complete the diagnostic test first before generating a study plan.",
        )

    dabbu = get_dabbu()
    # Check if a re-diagnostic is advisable before building a new plan
    rediag_reason = dabbu.check_diagnostic_needed(student)
    plan = dabbu.generate_study_plan(student, exam_date=req.exam_date)
    return {
        "status": "proposed",
        "message": "Study plan submitted for NAGA approval. You'll be notified when it's ready.",
        "plan": plan.to_dict(),
        "rediagnostic_suggested": rediag_reason,  # non-null = Dabbu recommends a re-test first
    }


@router.get("/study-plan")
async def get_active_plan(auth_id: str = Depends(require_auth)):
    """Get the student's current active (NAGA-approved) study plan."""
    dabbu = get_dabbu()
    plan = dabbu.get_active_plan(auth_id)
    if not plan:
        return {"plan": None, "message": "No active study plan yet. Request one to get started."}
    return {"plan": plan.to_dict()}


@router.get("/study-plan/proposed")
async def get_proposed_plan(auth_id: str = Depends(require_auth)):
    """Get the student's pending proposed study plan (awaiting NAGA approval)."""
    dabbu = get_dabbu()
    plan = dabbu.get_proposed_plan(auth_id)
    if not plan:
        return {"plan": None, "message": "No study plan pending approval."}
    return {"plan": plan.to_dict()}


# ── NAGA-only routes ───────────────────────────────────────────────────────────

@router.get("/naga/pending")
async def list_pending_proposals(auth_id: str = Depends(require_auth)):
    """List all proposed study plans awaiting NAGA approval."""
    _require_naga(auth_id)

    proposals = []
    for path in sorted(STUDY_PLANS_DIR.glob("*_proposed.json")):
        try:
            data = json.loads(path.read_text())
            proposals.append({
                "student_id": data.get("student_id"),
                "plan_id": data.get("plan_id"),
                "exam_target": data.get("exam_target"),
                "duration_months": data.get("duration_months"),
                "total_study_hours": data.get("total_study_hours"),
                "weak_topics_count": len(data.get("weak_topics", [])),
                "diagnostic_score": data.get("diagnostic_score"),
                "created_at": data.get("created_at"),
            })
        except Exception:
            continue

    return {"pending_plans": proposals, "count": len(proposals)}


@router.post("/naga/approve-plan")
async def approve_study_plan(
    req: ApprovePlanRequest,
    auth_id: str = Depends(require_auth),
):
    """NAGA approves a student's proposed study plan."""
    _require_naga(auth_id)

    dabbu = get_dabbu()
    plan = dabbu.approve_study_plan(student_id=req.student_id, naga_note=req.naga_note)
    if not plan:
        raise HTTPException(status_code=404, detail=f"No proposed plan found for student {req.student_id}")

    return {
        "status": "approved",
        "plan_id": plan.plan_id,
        "student_id": req.student_id,
        "message": f"Study plan approved and sent to student {req.student_id}.",
    }


@router.post("/naga/reject-plan")
async def reject_study_plan(
    req: RejectPlanRequest,
    auth_id: str = Depends(require_auth),
):
    """NAGA rejects a proposed study plan (student keeps their current active plan)."""
    _require_naga(auth_id)

    dabbu = get_dabbu()
    ok = dabbu.reject_study_plan(student_id=req.student_id, reason=req.reason)
    if not ok:
        raise HTTPException(status_code=404, detail=f"No proposed plan found for student {req.student_id}")

    return {
        "status": "rejected",
        "student_id": req.student_id,
        "message": "Plan rejected. Student retains their current active plan.",
    }


@router.post("/naga/scan-weaknesses")
async def scan_weak_areas(
    req: WeaknessScanRequest,
    auth_id: str = Depends(require_auth),
):
    """
    Trigger Dabbu to scan all students for exam_key, detect common weak areas (>50%),
    and notify NAGA with class suggestions for each one.
    """
    _require_naga(auth_id)

    dabbu = get_dabbu()
    count = dabbu.run_common_weakness_scan(req.exam_key)

    return {
        "exam_key": req.exam_key,
        "suggestions_sent": count,
        "message": (
            f"Dabbu found {count} common weak areas for {req.exam_key}. "
            f"Check your notifications for class suggestions."
            if count else
            f"No common weak areas found for {req.exam_key} yet. Need more students to complete the diagnostic."
        ),
    }


@router.post("/check-progress")
async def check_progress(auth_id: str = Depends(require_auth)):
    """
    Dabbu evaluates whether the student should take an additional diagnostic test.
    Called by the frontend periodically (e.g., on app open / study plan page load).
    If a re-diagnostic is recommended, Dabbu sends a notification and returns the reason.
    """
    from api.main import _students
    student = _get_student_from_store(auth_id, _students)

    if not student.diagnostic_done:
        return {"suggested": False, "reason": None}

    dabbu = get_dabbu()
    sent = dabbu.suggest_rediagnostic(student)
    reason = dabbu.check_diagnostic_needed(student) if not sent else None

    return {
        "suggested": sent,
        "reason": reason,
        "message": (
            "Dabbu recommends a re-diagnostic. Check your notifications."
            if sent else
            "No re-diagnostic needed right now. Keep following your study plan!"
        ),
    }


# ── NAGA notes approval routes ─────────────────────────────────────────────────

@router.get("/naga/notes")
async def list_pending_notes(auth_id: str = Depends(require_auth)):
    """List all AI-generated notes pending NAGA approval."""
    _require_naga(auth_id)
    from scripts.notes_generation import list_pending_notes as _list
    return {"pending_notes": _list(), "count": len(_list())}


@router.post("/naga/notes/approve")
async def approve_note(req: NoteApprovalRequest, auth_id: str = Depends(require_auth)):
    """NAGA approves a generated note — makes it visible to students."""
    _require_naga(auth_id)
    from scripts.notes_generation import approve_note as _approve
    from models.mentor import NotificationType
    from api.routes.mentor import _create_notification

    ok = _approve(req.exam, req.subject, req.topic, naga_note=req.naga_note)
    if not ok:
        raise HTTPException(status_code=404, detail="Note not found")

    # Notify all students on this exam
    from api.main import _students
    for sid, student in _students.items():
        if sid != NAGA_USER_ID and student.exam_target == req.exam:
            _create_notification(
                sid,
                NotificationType.NOTE_PUBLISHED,
                f"New notes: {req.topic}",
                f"Notes for '{req.topic}' ({req.subject}) are now available in your Study section.",
                data={"exam": req.exam, "subject": req.subject, "topic": req.topic},
            )

    return {"status": "approved", "exam": req.exam, "subject": req.subject, "topic": req.topic}


@router.post("/naga/notes/reject")
async def reject_note(
    req: NoteApprovalRequest,
    background_tasks: BackgroundTasks,
    auth_id: str = Depends(require_auth),
):
    """NAGA rejects a note — immediately triggers LLM regeneration in the background."""
    _require_naga(auth_id)
    from scripts.notes_generation import reject_note as _reject, regenerate_note as _regen
    ok = _reject(req.exam, req.subject, req.topic, reason=req.naga_note)
    if not ok:
        raise HTTPException(status_code=404, detail="Note not found")
    # Kick off a fresh LLM generation; the new version will appear in Approvals
    background_tasks.add_task(_regen, req.exam, req.subject, req.topic)
    return {"status": "rejected", "topic": req.topic, "reason": req.naga_note,
            "regenerating": True}


# ── NAGA YouTube video moderation routes ───────────────────────────────────────

@router.get("/naga/videos")
async def list_flagged_videos(
    status: str = "pending",
    auth_id: str = Depends(require_auth),
):
    """List flagged YouTube videos by status: pending | blocked | approved | all."""
    _require_naga(auth_id)
    from agents.content_filter import list_flagged_videos as _list
    videos = _list(status=status)
    return {"videos": videos, "count": len(videos), "status_filter": status}


@router.post("/naga/videos/approve")
async def approve_video(req: VideoActionRequest, auth_id: str = Depends(require_auth)):
    """NAGA approves a flagged video — it will be shown to students."""
    _require_naga(auth_id)
    from agents.content_filter import approve_video as _approve
    ok = _approve(req.video_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Video not found in flagged list")
    return {"status": "approved", "video_id": req.video_id}


@router.post("/naga/videos/reject")
async def reject_video(req: VideoActionRequest, auth_id: str = Depends(require_auth)):
    """NAGA rejects/blocks a flagged video."""
    _require_naga(auth_id)
    from agents.content_filter import reject_video as _reject
    ok = _reject(req.video_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Video not found in flagged list")
    return {"status": "blocked", "video_id": req.video_id}


@router.post("/naga/videos/blacklist")
async def blacklist_content(req: BlacklistRequest, auth_id: str = Depends(require_auth)):
    """Permanently blacklist a channel and/or a specific video ID."""
    _require_naga(auth_id)
    from agents.content_filter import blacklist_channel, blacklist_video
    actions = []
    if req.channel:
        blacklist_channel(req.channel)
        actions.append(f"channel '{req.channel}'")
    if req.video_id:
        blacklist_video(req.video_id)
        actions.append(f"video '{req.video_id}'")
    if not actions:
        raise HTTPException(status_code=400, detail="Provide channel or video_id")
    return {"blacklisted": actions, "message": f"Permanently blocked: {', '.join(actions)}"}


# ── NAGA keyword management routes ────────────────────────────────────────────

@router.get("/naga/keywords")
async def get_keywords(auth_id: str = Depends(require_auth)):
    """Return current blocked/flagged keyword lists."""
    _require_naga(auth_id)
    from agents.content_filter import get_keywords as _get
    return _get()


@router.post("/naga/keywords/add")
async def add_keyword(req: KeywordRequest, auth_id: str = Depends(require_auth)):
    """Add a word to the 'blocked' or 'flagged' keyword tier."""
    _require_naga(auth_id)
    from agents.content_filter import add_keyword as _add
    added = _add(req.word, req.tier)
    if not added:
        return {"status": "already_present", "word": req.word, "tier": req.tier}
    return {"status": "added", "word": req.word, "tier": req.tier}


@router.post("/naga/keywords/remove")
async def remove_keyword(req: KeywordRequest, auth_id: str = Depends(require_auth)):
    """Remove a word from the 'blocked' or 'flagged' keyword tier."""
    _require_naga(auth_id)
    from agents.content_filter import remove_keyword as _remove
    removed = _remove(req.word, req.tier)
    if not removed:
        raise HTTPException(status_code=404, detail=f"'{req.word}' not found in {req.tier} list")
    return {"status": "removed", "word": req.word, "tier": req.tier}


# ── Unified NAGA pending queue ─────────────────────────────────────────────────

@router.get("/naga/all-pending")
async def all_pending(auth_id: str = Depends(require_auth)):
    """
    Single endpoint for NAGA Approvals tab — returns all pending items:
    study plans, notes, and flagged videos.
    """
    _require_naga(auth_id)
    from scripts.notes_generation import list_pending_notes as _notes
    from agents.content_filter import list_flagged_videos as _videos

    plans = []
    for path in sorted(STUDY_PLANS_DIR.glob("*_proposed.json")):
        try:
            d = json.loads(path.read_text())
            plans.append({
                "type": "study_plan",
                "student_id": d.get("student_id"),
                "plan_id": d.get("plan_id"),
                "exam_target": d.get("exam_target"),
                "duration_months": d.get("duration_months"),
                "diagnostic_score": d.get("diagnostic_score"),
                "weak_topics_count": len(d.get("weak_topics", [])),
                "total_study_hours": d.get("total_study_hours"),
                "created_at": d.get("created_at"),
            })
        except Exception:
            continue

    notes = [{"type": "note", **n} for n in _notes()]
    videos = [{"type": "video", **v} for v in _videos(status="pending")]

    return {
        "study_plans": plans,
        "notes": notes,
        "videos": videos,
        "totals": {
            "study_plans": len(plans),
            "notes": len(notes),
            "videos": len(videos),
            "total": len(plans) + len(notes) + len(videos),
        },
    }


# ── Knowledge Base stats ────────────────────────────────────────────────────────

@router.get("/knowledge-base/stats")
async def knowledge_base_stats(auth_id: str = Depends(require_auth)):
    """Return vector store stats for the NAGA dashboard KB widget."""
    from agents.notes_vector_store import stats as vs_stats
    return vs_stats()
