"""
Progress routes — student analytics, history, and Dabbu intervention trigger.

GET  /api/progress                — full progress data for authenticated student
POST /api/progress/snapshot       — force a named snapshot (NAGA or student)
POST /api/progress/log-activity   — record a study event (streak calendar)
POST /api/progress/block-complete — mark a study plan block complete
POST /api/progress/dabbu-analyze  — Dabbu analyzes student and proposes intervention if needed
GET  /api/progress/interventions  — list all intervention proposals for student
GET  /api/dabbu/naga/interventions         — NAGA: all pending interventions
POST /api/dabbu/naga/interventions/approve — NAGA approves an intervention
POST /api/dabbu/naga/interventions/amend   — NAGA amends and approves an intervention
POST /api/dabbu/naga/interventions/dismiss — NAGA dismisses an intervention
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from agents.progress_tracker import (
    analyze_for_dabbu, get_progress_data, log_activity,
    log_block_completion, take_snapshot,
)
from api.middleware import require_auth

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/progress", tags=["progress"])

NAGA_USER_ID = "naga"
INTERVENTIONS_PATH = Path("data/dabbu/interventions.jsonl")
Path("data/dabbu").mkdir(parents=True, exist_ok=True)


# ── Pydantic models ────────────────────────────────────────────────────────────

class SnapshotRequest(BaseModel):
    label: str = "manual"


class BlockCompleteRequest(BaseModel):
    block_id: str
    subject: str
    topic: str
    session_type: str = "STUDY"


class InterventionAmendRequest(BaseModel):
    intervention_id: str
    naga_note: str
    amended_actions: Optional[list[dict]] = None


class InterventionDecisionRequest(BaseModel):
    intervention_id: str
    naga_note: str = ""


# ── Helpers ────────────────────────────────────────────────────────────────────

def _read_interventions() -> list[dict]:
    if not INTERVENTIONS_PATH.exists():
        return []
    out = []
    with open(INTERVENTIONS_PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except Exception:
                    continue
    return out


def _save_interventions(records: list[dict]) -> None:
    with open(INTERVENTIONS_PATH, "w") as f:
        for r in records:
            f.write(json.dumps(r, default=str) + "\n")


def _append_intervention(record: dict) -> None:
    with open(INTERVENTIONS_PATH, "a") as f:
        f.write(json.dumps(record, default=str) + "\n")


def _get_active_plan(student_id: str) -> Optional[dict]:
    p = Path(f"data/study_plans/{student_id}_active.json")
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    return None


# ── Student routes ─────────────────────────────────────────────────────────────

@router.get("/due-reviews")
async def get_due_reviews(auth_id: str = Depends(require_auth)):
    """Return SM-2 topics whose review is due today — drives the home-page banner."""
    from api.main import _students
    from datetime import date
    student = _students.get(auth_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    today = date.today()
    due = []
    for w in student.weakness_map:
        if not getattr(w, "next_review_date", None):
            continue
        review_date = w.next_review_date.date() if hasattr(w.next_review_date, "date") else w.next_review_date
        if review_date <= today:
            due.append({"subject": w.subject, "topic": w.topic, "score_pct": round(w.score_pct * 100, 1)})
    due.sort(key=lambda x: x["score_pct"])  # weakest first
    return {"count": len(due), "due": due}


@router.get("")
async def get_progress(auth_id: str = Depends(require_auth)):
    """Full progress data for the authenticated student."""
    from api.main import _students
    student = _students.get(auth_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    active_plan = _get_active_plan(auth_id)
    return get_progress_data(student, active_plan)


@router.post("/snapshot")
async def force_snapshot(req: SnapshotRequest, auth_id: str = Depends(require_auth)):
    """Force a named snapshot of the current weakness_map."""
    from api.main import _students
    student = _students.get(auth_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    take_snapshot(student, label=req.label)
    return {"status": "ok", "label": req.label}


@router.post("/log-activity")
async def record_activity(auth_id: str = Depends(require_auth)):
    """Record a study event (call from any study interaction to keep streak alive)."""
    log_activity(auth_id)
    return {"status": "ok"}


@router.post("/block-complete")
async def complete_block(req: BlockCompleteRequest, auth_id: str = Depends(require_auth)):
    """Mark a study plan block as completed (persisted to progress store)."""
    log_block_completion(
        student_id=auth_id,
        block_id=req.block_id,
        subject=req.subject,
        topic=req.topic,
        session_type=req.session_type,
    )
    return {"status": "ok", "block_id": req.block_id}


@router.post("/dabbu-analyze")
async def trigger_dabbu_analysis(auth_id: str = Depends(require_auth)):
    """
    Dabbu analyzes the student's progress. If issues are detected, Dabbu proposes
    an intervention and notifies NAGA. Student sees a summary of what was sent.
    """
    from api.main import _students
    from agents.dabbu_agent import get_dabbu

    student = _students.get(auth_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    active_plan = _get_active_plan(auth_id)
    analysis = analyze_for_dabbu(student, active_plan)

    intervention = None
    if analysis["severity"] in ("medium", "high"):
        intervention = get_dabbu().propose_progress_intervention(student, analysis)

    return {
        "analysis": analysis,
        "intervention_proposed": intervention is not None,
        "intervention": intervention,
        "message": (
            "Dabbu has flagged some areas that need attention and sent NAGA a proposal."
            if intervention else
            "Progress looks on track — keep it up!"
        ),
    }


@router.get("/interventions")
async def list_my_interventions(auth_id: str = Depends(require_auth)):
    """Student: see their own approved interventions."""
    records = _read_interventions()
    mine = [r for r in records if r.get("student_id") == auth_id and r.get("status") == "approved"]
    return {"interventions": mine, "count": len(mine)}


# ── NAGA routes (mounted on /api/dabbu to match existing pattern) ──────────────

intervention_router = APIRouter(prefix="/api/dabbu", tags=["dabbu"])


@intervention_router.get("/naga/interventions")
async def naga_list_interventions(
    status: str = "pending",
    auth_id: str = Depends(require_auth),
):
    """NAGA: list intervention proposals by status (pending / approved / amended / dismissed)."""
    if auth_id != NAGA_USER_ID:
        raise HTTPException(status_code=403, detail="NAGA access only")
    records = _read_interventions()
    filtered = [r for r in records if status == "all" or r.get("status") == status]
    return {"interventions": filtered, "count": len(filtered)}


@intervention_router.post("/naga/interventions/approve")
async def naga_approve_intervention(
    req: InterventionDecisionRequest,
    auth_id: str = Depends(require_auth),
):
    """NAGA approves Dabbu's intervention proposal — student is notified."""
    if auth_id != NAGA_USER_ID:
        raise HTTPException(status_code=403, detail="NAGA access only")
    return _update_intervention_status(req.intervention_id, "approved", req.naga_note)


@intervention_router.post("/naga/interventions/amend")
async def naga_amend_intervention(
    req: InterventionAmendRequest,
    auth_id: str = Depends(require_auth),
):
    """NAGA amends Dabbu's intervention actions before approving."""
    if auth_id != NAGA_USER_ID:
        raise HTTPException(status_code=403, detail="NAGA access only")

    records = _read_interventions()
    found = False
    for r in records:
        if r.get("intervention_id") == req.intervention_id:
            r["status"] = "approved"
            r["naga_note"] = req.naga_note
            r["amended_at"] = datetime.utcnow().isoformat()
            r["amended_by"] = "naga"
            if req.amended_actions:
                r["original_actions"] = r.get("actions", [])
                r["actions"] = req.amended_actions
            found = True
            student_id = r.get("student_id")
            break

    if not found:
        raise HTTPException(status_code=404, detail="Intervention not found")

    _save_interventions(records)

    # Notify student
    if student_id:
        _notify_student_intervention(student_id, records[-1] if records else {}, amended=True)

    return {"status": "approved", "amended": True, "intervention_id": req.intervention_id}


@intervention_router.post("/naga/interventions/dismiss")
async def naga_dismiss_intervention(
    req: InterventionDecisionRequest,
    auth_id: str = Depends(require_auth),
):
    """NAGA dismisses an intervention (no action needed)."""
    if auth_id != NAGA_USER_ID:
        raise HTTPException(status_code=403, detail="NAGA access only")
    return _update_intervention_status(req.intervention_id, "dismissed", req.naga_note)


def _update_intervention_status(intervention_id: str, new_status: str, naga_note: str) -> dict:
    records = _read_interventions()
    found = False
    student_id = None
    updated_record = None
    for r in records:
        if r.get("intervention_id") == intervention_id:
            r["status"] = new_status
            r["naga_note"] = naga_note
            r["decided_at"] = datetime.utcnow().isoformat()
            found = True
            student_id = r.get("student_id")
            updated_record = r
            break
    if not found:
        raise HTTPException(status_code=404, detail="Intervention not found")
    _save_interventions(records)
    if new_status == "approved" and student_id and updated_record:
        _notify_student_intervention(student_id, updated_record, amended=False)
    return {"status": new_status, "intervention_id": intervention_id}


def _notify_student_intervention(student_id: str, record: dict, amended: bool) -> None:
    from models.mentor import NotificationType
    from agents.dabbu_agent import _notify
    actions_text = "; ".join(
        a.get("description", "") for a in record.get("actions", [])[:3]
    )
    _notify(
        user_id=student_id,
        ntype=NotificationType.STUDY_PLAN_APPROVED,  # reuse — intervention approved
        title="NAGA has reviewed your progress plan" + (" (with adjustments)" if amended else ""),
        body=(
            f"Recommended focus: {actions_text}. "
            + (f"NAGA's note: {record.get('naga_note', '')}" if record.get("naga_note") else "")
        ),
        data={"intervention_id": record.get("intervention_id"), "type": "progress_intervention"},
    )
