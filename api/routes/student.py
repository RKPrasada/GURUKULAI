from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.middleware import require_auth, require_self
from models.student import Language

router = APIRouter(prefix="/api/student", tags=["student"])

_students: dict = {}


class UpdateExamRequest(BaseModel):
    exam_target: str
    preferred_language: str = "en"


@router.get("/{student_id}")
async def get_student(
    student_id: str,
    _: str = Depends(require_auth),
):
    student = _students.get(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student.to_dict()


@router.put("/{student_id}/exam")
async def update_exam(
    student_id: str,
    req: UpdateExamRequest,
    auth_id: str = Depends(require_auth),
):
    if auth_id and auth_id != student_id:
        raise HTTPException(status_code=403, detail="Access denied")
    student = _students.get(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    student.exam_target = req.exam_target
    student.preferred_language = Language(req.preferred_language)
    return student.to_dict()


@router.get("/{student_id}/weakness")
async def get_weakness_map(
    student_id: str,
    _: str = Depends(require_auth),
):
    student = _students.get(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return {"weakness_map": [w.to_dict() for w in student.weakness_map]}


@router.get("/{student_id}/progress")
async def get_progress(
    student_id: str,
    _: str = Depends(require_auth),
):
    student = _students.get(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    from agents.progress_agent import ProgressAgent
    agent = ProgressAgent()
    return agent.get_progress_summary(student)


def set_students_store(store: dict):
    global _students
    _students = store
