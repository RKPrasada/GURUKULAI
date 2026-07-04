from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.middleware import require_auth
from mcp.drive_client import DriveClient
from security.quarantine import get_quarantine_manager
from security.vibe_diff import get_vibe_diff

router = APIRouter(prefix="/api/session", tags=["session"])

_students: dict = {}
_orchestrator = None
_diagnostic = None
_assessment = None


class ChatRequest(BaseModel):
    message: str
    # student_id is optional for backwards compat with old Streamlit frontend
    student_id: str | None = None


class DiagnosticSubmit(BaseModel):
    session_id: str
    answers: dict[str, int] | list[int]
    student_id: str | None = None


class AssessmentStart(BaseModel):
    difficulty: str = "adaptive"
    topic: str | None = None
    student_id: str | None = None


class AssessmentAnswer(BaseModel):
    session_id: str
    answers: dict[str, int] | None = None
    question_id: str | None = None
    answer_index: int | None = None
    student_id: str | None = None


class VibeDiffConfirm(BaseModel):
    token: str
    student_id: str | None = None


_load_student_fn = None
_save_student_fn = None


def _resolve_student_id(auth_id: str, req_id: str | None) -> str:
    """Returns auth token's student_id, falling back to body field for legacy callers."""
    return auth_id if auth_id else (req_id or "")


def _get_student(student_id: str):
    """Look up student in memory; lazy-load from DB on cache miss."""
    student = _students.get(student_id)
    if student is None and _load_student_fn:
        student = _load_student_fn(student_id)
        if student:
            _students[student_id] = student
    return student


@router.post("/diagnostic/start")
async def start_diagnostic(auth_id: str = Depends(require_auth)):
    student = _get_student(auth_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return _diagnostic.start_diagnostic(student)


@router.post("/diagnostic/submit")
async def submit_diagnostic(req: DiagnosticSubmit, auth_id: str = Depends(require_auth)):
    student_id = _resolve_student_id(auth_id, req.student_id)
    student = _get_student(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    # Normalize answers: dict {question_id: answer_index} or list [answer_index, ...]
    if isinstance(req.answers, dict):
        answers = list(req.answers.values())
    else:
        answers = req.answers
    result = _diagnostic.submit_answers(student, req.session_id, answers)
    if _save_student_fn:
        _save_student_fn(student)
    return result


@router.post("/chat")
async def chat(req: ChatRequest, auth_id: str = Depends(require_auth)):
    student_id = _resolve_student_id(auth_id, req.student_id)

    qm = get_quarantine_manager()
    blocked, remaining = qm.is_quarantined(student_id)
    if blocked:
        mins = int(remaining // 60)
        return {
            "response": f"Your account is temporarily suspended for {mins} minutes due to policy violations. "
                        f"Please contact support if you believe this is an error.",
            "quarantined": True,
            "remaining_seconds": int(remaining),
        }

    student = _get_student(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    result = await _orchestrator.handle(student, req.message)

    if isinstance(result, dict) and result.get("threat"):
        newly_quarantined = qm.record_threat(student_id, result["threat"])
        result["threat_count"] = qm.threat_count(student_id)
        if newly_quarantined:
            result["quarantined"] = True

    return result


@router.post("/assessment/start")
async def start_assessment(req: AssessmentStart, auth_id: str = Depends(require_auth)):
    student_id = _resolve_student_id(auth_id, req.student_id)
    student = _get_student(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return _assessment.start_session(student, req.topic, requested_difficulty=req.difficulty)


@router.post("/assessment/answer")
async def submit_answer(req: AssessmentAnswer, auth_id: str = Depends(require_auth)):
    if req.question_id is None or req.answer_index is None:
        raise HTTPException(status_code=422, detail="Provide 'question_id' and 'answer_index'")
    return _assessment.evaluate_answer(req.session_id, req.question_id, req.answer_index)


@router.get("/pending-actions/{student_id}")
async def get_pending_actions(student_id: str, _: str = Depends(require_auth)):
    vd = get_vibe_diff()
    return {"pending": vd.pending_for_student(student_id)}


@router.post("/confirm-action")
async def confirm_action(req: VibeDiffConfirm, auth_id: str = Depends(require_auth)):
    student_id = _resolve_student_id(auth_id, req.student_id)
    vd = get_vibe_diff()
    success, action = vd.confirm(req.token, student_id)
    if not success:
        raise HTTPException(status_code=400, detail="Action token invalid, expired, or not yours")
    if action and action.action_name == "save_to_drive":
        payload = action.payload
        result = DriveClient().save_study_notes(
            student_id=student_id,
            topic=payload["topic"],
            content=payload["content"],
            exam=payload.get("exam", "general"),
        )
        return {"confirmed": True, "action": action.action_name, "result": result}
    return {"confirmed": True, "action": action.action_name if action else None}


@router.post("/cancel-action")
async def cancel_action(req: VibeDiffConfirm, auth_id: str = Depends(require_auth)):
    student_id = _resolve_student_id(auth_id, req.student_id)
    vd = get_vibe_diff()
    cancelled = vd.cancel(req.token, student_id)
    return {"cancelled": cancelled}


def setup_agents(students: dict, orchestrator, diagnostic, assessment, load_fn=None, save_fn=None):
    global _students, _orchestrator, _diagnostic, _assessment, _load_student_fn, _save_student_fn
    _students = students
    _orchestrator = orchestrator
    _diagnostic = diagnostic
    _assessment = assessment
    _load_student_fn = load_fn
    _save_student_fn = save_fn
