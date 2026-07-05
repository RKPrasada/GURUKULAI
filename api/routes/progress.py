from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.middleware import require_auth
from models.ui_schema import CardType
from security.vibe_diff import get_vibe_diff

router = APIRouter(prefix="/api/progress", tags=["progress"])

_students: dict = {}
_progress_agent = None


class DigestRequest(BaseModel):
    student_id: str
    email: str
    name: str = "Student"


@router.get("/{student_id}/plan")
async def get_study_plan(student_id: str, _: str = Depends(require_auth)):
    student = _students.get(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return _progress_agent.generate_plan(student)


@router.post("/{student_id}/schedule")
async def create_schedule(student_id: str, _: str = Depends(require_auth)):
    """Registers a Vibe Diff pending action — client must confirm before events are created."""
    student = _students.get(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    vd = get_vibe_diff()
    plan = _progress_agent.generate_plan(student)
    day_count = len(plan.get("plan", []))
    session_count = sum(len(d.get("sessions", [])) for d in plan.get("plan", []))

    pending = vd.register(
        student_id=student_id,
        action_name="create_calendar_events",
        description=f"Create {session_count} calendar events across {day_count} days in your Google Calendar (Asia/Kolkata)?",
        payload={"plan": plan},
    )
    return {
        "_card_type": CardType.VIBE_DIFF.value,
        "requires_confirmation": True,
        "pending_action": pending.to_dict(),
        "message": "Please confirm this action via POST /api/session/confirm-action",
    }


@router.post("/{student_id}/schedule/execute")
async def execute_schedule(student_id: str, token: str, _: str = Depends(require_auth)):
    """Execute calendar creation after Vibe Diff confirmation."""
    vd = get_vibe_diff()
    success, action = vd.confirm(token, student_id)
    if not success:
        raise HTTPException(status_code=400, detail="Confirmation token invalid or expired")

    student = _students.get(student_id)
    result = _progress_agent.create_calendar_events(student, action.payload["plan"])
    return result


@router.post("/{student_id}/digest")
async def send_digest(student_id: str, req: DigestRequest, _: str = Depends(require_auth)):
    """Registers a Vibe Diff for Gmail send — requires user confirmation."""
    student = _students.get(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    vd = get_vibe_diff()
    pending = vd.register(
        student_id=student_id,
        action_name="send_gmail_digest",
        description=f"Send weekly progress report to {req.email}?",
        payload={"email": req.email, "name": req.name},
    )
    return {
        "_card_type": CardType.VIBE_DIFF.value,
        "requires_confirmation": True,
        "pending_action": pending.to_dict(),
        "message": f"Confirm sending report to {req.email} via POST /api/session/confirm-action",
    }


@router.post("/{student_id}/digest/execute")
async def execute_digest(student_id: str, token: str, _: str = Depends(require_auth)):
    """Execute Gmail send after Vibe Diff confirmation."""
    vd = get_vibe_diff()
    success, action = vd.confirm(token, student_id)
    if not success:
        raise HTTPException(status_code=400, detail="Confirmation token invalid or expired")

    student = _students.get(student_id)
    payload = action.payload
    success = _progress_agent.send_weekly_digest(student, payload["email"], payload["name"])
    return {"sent": success, "to": payload["email"]}


def setup_progress(students: dict, progress_agent):
    global _students, _progress_agent
    _students = students
    _progress_agent = progress_agent
