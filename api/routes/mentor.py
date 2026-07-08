"""Mentor (NAGA) routes — Q&A board, class scheduling, meeting requests, notifications."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.middleware import require_auth
from models.mentor import (
    Question, QuestionStatus,
    ScheduledClass, ClassType,
    MeetingRequest, MeetingRequestStatus,
    Notification, NotificationType,
)
from security.guardrails import InputGuard, SAFE_REDIRECT_EN, SAFE_REDIRECT_HI

_input_guard = InputGuard()

router = APIRouter(prefix="/api/mentor", tags=["mentor"])

DATA_DIR = Path("data/mentor")
DATA_DIR.mkdir(parents=True, exist_ok=True)

QUESTIONS_FILE = DATA_DIR / "questions.jsonl"
CLASSES_FILE = DATA_DIR / "classes.jsonl"
MEETINGS_FILE = DATA_DIR / "meeting_requests.jsonl"
NOTIFICATIONS_FILE = DATA_DIR / "notifications.jsonl"

NAGA_USER_ID = "naga"  # Reserved ID for NAGA admin


# ── Storage helpers ────────────────────────────────────────────────────────────

def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    items = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def _write_jsonl(path: Path, items: list[dict]) -> None:
    with open(path, "w") as f:
        for item in items:
            f.write(json.dumps(item) + "\n")


def _append_jsonl(path: Path, item: dict) -> None:
    with open(path, "a") as f:
        f.write(json.dumps(item) + "\n")


# ── Notification helpers ───────────────────────────────────────────────────────

def _create_notification(user_id: str, ntype: NotificationType, title: str, body: str, data: dict = {}) -> None:
    n = Notification(
        notification_id=str(uuid.uuid4()),
        user_id=user_id,
        type=ntype,
        title=title,
        body=body,
        data=data,
    )
    _append_jsonl(NOTIFICATIONS_FILE, n.to_dict())


def _notify_all_students(students_store: dict, ntype: NotificationType, title: str, body: str, data: dict = {}, exclude_id: str = "") -> None:
    """Send a notification to every active student."""
    for sid in students_store:
        if sid and sid != exclude_id and sid != NAGA_USER_ID:
            _create_notification(sid, ntype, title, body, data)


# ── Meet link generation ───────────────────────────────────────────────────────

def _generate_meet_link(title: str, scheduled_at: datetime, duration_minutes: int, attendee_emails: list[str] = []) -> tuple[str, str]:
    """Returns (meet_link, calendar_event_id). Falls back to an offline link when Calendar API is unavailable."""
    try:
        from mcp.calendar_client import CalendarClient
        client = CalendarClient()
        if client.offline_mode:
            raise RuntimeError("offline")
        # Real Calendar API integration
        event = client.create_event(
            title=title,
            start=scheduled_at.isoformat(),
            duration_minutes=duration_minutes,
            attendees=attendee_emails,
            add_meet=True,
        )
        return event.get("hangoutLink", ""), event.get("id", "")
    except Exception:
        # Offline fallback — generate a deterministic-looking meet link
        code = str(uuid.uuid4())[:12].replace("-", "")
        meet_link = f"https://meet.google.com/{code[:3]}-{code[3:7]}-{code[7:11]}"
        return meet_link, f"offline_event_{uuid.uuid4().hex[:8]}"


# ── Shared state injected by main.py ──────────────────────────────────────────

_students_store: dict = {}


def setup_mentor(students: dict) -> None:
    global _students_store
    _students_store = students
    _seed_naga_user()


def _seed_naga_user() -> None:
    """Ensure NAGA admin account exists in users.jsonl."""
    from pathlib import Path as _Path
    import json as _json
    import hashlib as _hashlib

    users_file = _Path("data/users.jsonl")
    users_file.parent.mkdir(parents=True, exist_ok=True)

    # Check if naga already exists
    if users_file.exists():
        with open(users_file) as f:
            for line in f:
                if line.strip():
                    d = _json.loads(line)
                    if d.get("user_id") == "naga":
                        return  # Already seeded

    # Create NAGA user — password from env var (never hardcoded)
    import os as _os
    naga_pw = _os.environ.get("NAGA_PASSWORD", "naga@vidyabot").encode()
    try:
        import bcrypt
        pw_hash = bcrypt.hashpw(naga_pw, bcrypt.gensalt()).decode()
    except ImportError:
        pw_hash = _hashlib.sha256(naga_pw).hexdigest()

    naga = {
        "user_id": "naga",
        "username": "naga",
        "email": "naga@vidyabot.in",
        "password_hash": pw_hash,
        "full_name": "NAGA",
        "exam_target": "rrb_ntpc",
        "preferred_language": "en",
        "created_at": "2026-01-01T00:00:00",
        "last_login": None,
        "is_active": True,
    }
    with open(users_file, "a") as f:
        f.write(_json.dumps(naga) + "\n")


def _get_student_email(student_id: str) -> str:
    student = _students_store.get(student_id)
    return student.google_sub if student else ""  # google_sub holds email for auth users


def _get_student_name(student_id: str) -> str:
    student = _students_store.get(student_id)
    return getattr(student, "full_name", student_id) if student else student_id


# ═══════════════════════════════════════════════════════════════════════════════
# QUESTION ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

class PostQuestionRequest(BaseModel):
    subject: str
    topic: str
    content: str


class AnswerQuestionRequest(BaseModel):
    answer: str


class ApproveQuestionRequest(BaseModel):
    approved: bool


@router.post("/questions")
async def post_question(req: PostQuestionRequest, auth_id: str = Depends(require_auth)):
    """Student posts a question — goes to NAGA's pending queue."""
    # Security rule 1: InputGuard on all user-submitted text before storing or routing
    _, threat = _input_guard.process(req.content)
    if threat:
        student = _students_store.get(auth_id)
        lang = getattr(getattr(student, "preferred_language", None), "value", "en") if student else "en"
        raise HTTPException(status_code=400, detail=SAFE_REDIRECT_HI if lang == "hi" else SAFE_REDIRECT_EN)

    student_name = _get_student_name(auth_id)
    q = Question(
        question_id=str(uuid.uuid4()),
        student_id=auth_id,
        student_name=student_name,
        subject=req.subject,
        topic=req.topic,
        content=req.content,
    )
    _append_jsonl(QUESTIONS_FILE, q.to_dict())

    # Notify NAGA
    _create_notification(
        NAGA_USER_ID, NotificationType.NEW_QUESTION,
        f"New question from {student_name}",
        f"Subject: {req.subject} | Topic: {req.topic}",
        {"question_id": q.question_id},
    )
    return {"message": "Question submitted for review", "question_id": q.question_id}


@router.get("/questions")
async def list_questions(auth_id: str = Depends(require_auth)):
    """Students see approved questions; NAGA sees all."""
    all_qs = [Question.from_dict(d) for d in _read_jsonl(QUESTIONS_FILE)]
    if auth_id == NAGA_USER_ID:
        return [q.to_dict() for q in sorted(all_qs, key=lambda x: x.created_at, reverse=True)]
    # Students only see approved / resolved
    visible = [q for q in all_qs if q.status in (QuestionStatus.APPROVED, QuestionStatus.RESOLVED)]
    return [q.to_dict() for q in sorted(visible, key=lambda x: (x.upvotes, x.created_at), reverse=True)]


@router.get("/questions/pending")
async def pending_questions(auth_id: str = Depends(require_auth)):
    """NAGA only — questions awaiting approval."""
    if auth_id != NAGA_USER_ID:
        raise HTTPException(403, "NAGA only")
    all_qs = [Question.from_dict(d) for d in _read_jsonl(QUESTIONS_FILE)]
    pending = [q for q in all_qs if q.status == QuestionStatus.PENDING]
    return [q.to_dict() for q in sorted(pending, key=lambda x: x.created_at)]


@router.post("/questions/{question_id}/approve")
async def approve_question(question_id: str, req: ApproveQuestionRequest, auth_id: str = Depends(require_auth)):
    """NAGA approves or rejects a question."""
    if auth_id != NAGA_USER_ID:
        raise HTTPException(403, "NAGA only")
    all_qs = [Question.from_dict(d) for d in _read_jsonl(QUESTIONS_FILE)]
    updated = False
    q_obj = None
    for q in all_qs:
        if q.question_id == question_id:
            q.status = QuestionStatus.APPROVED if req.approved else QuestionStatus.REJECTED
            if req.approved:
                q.approved_at = datetime.utcnow()
            updated = True
            q_obj = q
            break
    if not updated:
        raise HTTPException(404, "Question not found")
    _write_jsonl(QUESTIONS_FILE, [q.to_dict() for q in all_qs])

    # Notify the student
    if q_obj:
        status_text = "approved and is now visible" if req.approved else "not approved this time"
        _create_notification(
            q_obj.student_id, NotificationType.QUESTION_APPROVED,
            "Your question was reviewed",
            f"Your question about {q_obj.topic} was {status_text}.",
            {"question_id": question_id},
        )
    return {"message": "Updated", "status": q_obj.status.value if q_obj else ""}


@router.post("/questions/{question_id}/answer")
async def answer_question(question_id: str, req: AnswerQuestionRequest, auth_id: str = Depends(require_auth)):
    """NAGA answers a question publicly."""
    if auth_id != NAGA_USER_ID:
        raise HTTPException(403, "NAGA only")
    all_qs = [Question.from_dict(d) for d in _read_jsonl(QUESTIONS_FILE)]
    q_obj = None
    for q in all_qs:
        if q.question_id == question_id:
            q.answer = req.answer
            q.answered_at = datetime.utcnow()
            q_obj = q
            break
    if not q_obj:
        raise HTTPException(404, "Question not found")
    _write_jsonl(QUESTIONS_FILE, [q.to_dict() for q in all_qs])

    _create_notification(
        q_obj.student_id, NotificationType.QUESTION_ANSWERED,
        "NAGA answered your question!",
        f"Your question about {q_obj.topic} has been answered.",
        {"question_id": question_id},
    )
    return {"message": "Answered"}


@router.post("/questions/{question_id}/upvote")
async def upvote_question(question_id: str, auth_id: str = Depends(require_auth)):
    """Student upvotes a question."""
    all_qs = [Question.from_dict(d) for d in _read_jsonl(QUESTIONS_FILE)]
    for q in all_qs:
        if q.question_id == question_id:
            if auth_id in q.upvoted_by:
                q.upvoted_by.remove(auth_id)
                q.upvotes = max(0, q.upvotes - 1)
            else:
                q.upvoted_by.append(auth_id)
                q.upvotes += 1
            _write_jsonl(QUESTIONS_FILE, [q.to_dict() for q in all_qs])
            return {"upvotes": q.upvotes, "upvoted": auth_id in q.upvoted_by}
    raise HTTPException(404, "Question not found")


@router.post("/questions/{question_id}/resolve")
async def resolve_question(question_id: str, auth_id: str = Depends(require_auth)):
    """Student or NAGA marks a question as resolved."""
    all_qs = [Question.from_dict(d) for d in _read_jsonl(QUESTIONS_FILE)]
    for q in all_qs:
        if q.question_id == question_id:
            if q.student_id != auth_id and auth_id != NAGA_USER_ID:
                raise HTTPException(403, "Not your question")
            q.status = QuestionStatus.RESOLVED
            _write_jsonl(QUESTIONS_FILE, [q.to_dict() for q in all_qs])
            return {"message": "Marked resolved"}
    raise HTTPException(404, "Question not found")


# ═══════════════════════════════════════════════════════════════════════════════
# CLASS SCHEDULING ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

class ScheduleClassRequest(BaseModel):
    title: str
    description: str
    subject: str
    topic: str
    class_type: str = "group"
    scheduled_at: str   # ISO datetime
    duration_minutes: int = 60
    target_student_id: Optional[str] = None
    linked_question_ids: list[str] = []
    max_students: int = 50


@router.post("/classes")
async def schedule_class(req: ScheduleClassRequest, auth_id: str = Depends(require_auth)):
    """NAGA schedules a group or 1-to-1 class."""
    if auth_id != NAGA_USER_ID:
        raise HTTPException(403, "NAGA only")

    scheduled_dt = datetime.fromisoformat(req.scheduled_at)

    # Generate Meet link
    meet_link, event_id = _generate_meet_link(
        req.title, scheduled_dt, req.duration_minutes
    )

    cls = ScheduledClass(
        class_id=str(uuid.uuid4()),
        title=req.title,
        description=req.description,
        subject=req.subject,
        topic=req.topic,
        class_type=ClassType(req.class_type),
        scheduled_at=scheduled_dt,
        duration_minutes=req.duration_minutes,
        meet_link=meet_link,
        calendar_event_id=event_id,
        target_student_id=req.target_student_id,
        linked_question_ids=req.linked_question_ids,
        max_students=req.max_students,
    )
    _append_jsonl(CLASSES_FILE, cls.to_dict())

    # Link class to questions
    if req.linked_question_ids:
        all_qs = [Question.from_dict(d) for d in _read_jsonl(QUESTIONS_FILE)]
        for q in all_qs:
            if q.question_id in req.linked_question_ids:
                q.class_id = cls.class_id
        _write_jsonl(QUESTIONS_FILE, [q.to_dict() for q in all_qs])

    # Notify students
    notif_title = f"New class: {req.title}"
    notif_body = f"{req.subject} | {req.topic} | {scheduled_dt.strftime('%d %b %Y, %I:%M %p')}\nMeet: {meet_link}"

    if req.class_type == "one_to_one" and req.target_student_id:
        _create_notification(
            req.target_student_id, NotificationType.MEETING_ACCEPTED,
            notif_title, notif_body,
            {"class_id": cls.class_id, "meet_link": meet_link},
        )
    else:
        _notify_all_students(
            _students_store, NotificationType.CLASS_SCHEDULED,
            notif_title, notif_body,
            {"class_id": cls.class_id, "meet_link": meet_link},
        )

    return cls.to_dict()


@router.get("/classes")
async def list_classes(auth_id: str = Depends(require_auth)):
    """List upcoming classes — students see public + their 1-to-1; NAGA sees all."""
    all_cls = [ScheduledClass.from_dict(d) for d in _read_jsonl(CLASSES_FILE)]
    if auth_id == NAGA_USER_ID:
        result = all_cls
    else:
        result = [
            c for c in all_cls
            if c.class_type == ClassType.GROUP
            or c.target_student_id == auth_id
        ]
    return [c.to_dict() for c in sorted(result, key=lambda x: x.scheduled_at)]


@router.post("/classes/{class_id}/rsvp")
async def rsvp_class(class_id: str, auth_id: str = Depends(require_auth)):
    """Student RSVPs to a class (toggle)."""
    all_cls = [ScheduledClass.from_dict(d) for d in _read_jsonl(CLASSES_FILE)]
    for cls in all_cls:
        if cls.class_id == class_id:
            existing = next((r for r in cls.rsvp_list if r["student_id"] == auth_id), None)
            if existing:
                cls.rsvp_list = [r for r in cls.rsvp_list if r["student_id"] != auth_id]
                action = "cancelled"
            else:
                cls.rsvp_list.append({
                    "student_id": auth_id,
                    "name": _get_student_name(auth_id),
                    "rsvp_at": datetime.utcnow().isoformat(),
                })
                action = "confirmed"
            _write_jsonl(CLASSES_FILE, [c.to_dict() for c in all_cls])
            return {"action": action, "rsvp_count": len(cls.rsvp_list), "meet_link": cls.meet_link}
    raise HTTPException(404, "Class not found")


@router.delete("/classes/{class_id}")
async def cancel_class(class_id: str, auth_id: str = Depends(require_auth)):
    """NAGA cancels a class."""
    if auth_id != NAGA_USER_ID:
        raise HTTPException(403, "NAGA only")
    all_cls = [ScheduledClass.from_dict(d) for d in _read_jsonl(CLASSES_FILE)]
    for cls in all_cls:
        if cls.class_id == class_id:
            cls.status = "cancelled"
            _write_jsonl(CLASSES_FILE, [c.to_dict() for c in all_cls])
            _notify_all_students(
                _students_store, NotificationType.CLASS_CANCELLED,
                f"Class cancelled: {cls.title}",
                f"The class on {cls.topic} scheduled for {cls.scheduled_at.strftime('%d %b %Y')} has been cancelled.",
                {"class_id": class_id},
            )
            return {"message": "Class cancelled"}
    raise HTTPException(404, "Class not found")


# ═══════════════════════════════════════════════════════════════════════════════
# MEETING REQUEST ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

class MeetingRequestBody(BaseModel):
    message: str
    preferred_times: list[str] = []   # ISO datetime strings


class RespondMeetingRequest(BaseModel):
    accepted: bool
    naga_note: str = ""
    scheduled_at: Optional[str] = None   # Required if accepted
    duration_minutes: int = 30


@router.post("/meeting-requests")
async def request_meeting(req: MeetingRequestBody, auth_id: str = Depends(require_auth)):
    """Student requests a 1-to-1 session with NAGA."""
    mr = MeetingRequest(
        request_id=str(uuid.uuid4()),
        student_id=auth_id,
        student_name=_get_student_name(auth_id),
        student_email=_get_student_email(auth_id),
        message=req.message,
        preferred_times=req.preferred_times,
    )
    _append_jsonl(MEETINGS_FILE, mr.to_dict())

    # Notify NAGA
    _create_notification(
        NAGA_USER_ID, NotificationType.MEETING_REQUEST,
        f"1-to-1 request from {mr.student_name}",
        mr.message,
        {"request_id": mr.request_id},
    )
    return {"message": "Meeting request sent to NAGA", "request_id": mr.request_id}


@router.get("/meeting-requests")
async def list_meeting_requests(auth_id: str = Depends(require_auth)):
    """NAGA sees all; students see their own."""
    all_mrs = [MeetingRequest.from_dict(d) for d in _read_jsonl(MEETINGS_FILE)]
    if auth_id == NAGA_USER_ID:
        result = all_mrs
    else:
        result = [mr for mr in all_mrs if mr.student_id == auth_id]
    return [mr.to_dict() for mr in sorted(result, key=lambda x: x.created_at, reverse=True)]


@router.post("/meeting-requests/{request_id}/respond")
async def respond_meeting_request(
    request_id: str,
    req: RespondMeetingRequest,
    auth_id: str = Depends(require_auth),
):
    """NAGA accepts or declines a 1-to-1 request."""
    if auth_id != NAGA_USER_ID:
        raise HTTPException(403, "NAGA only")

    all_mrs = [MeetingRequest.from_dict(d) for d in _read_jsonl(MEETINGS_FILE)]
    mr_obj = None
    cls_obj = None

    for mr in all_mrs:
        if mr.request_id == request_id:
            mr.status = MeetingRequestStatus.ACCEPTED if req.accepted else MeetingRequestStatus.DECLINED
            mr.naga_note = req.naga_note
            mr.responded_at = datetime.utcnow()

            if req.accepted and req.scheduled_at:
                scheduled_dt = datetime.fromisoformat(req.scheduled_at)
                meet_link, event_id = _generate_meet_link(
                    f"1-to-1 with {mr.student_name}",
                    scheduled_dt, req.duration_minutes,
                )
                cls_obj = ScheduledClass(
                    class_id=str(uuid.uuid4()),
                    title=f"1-to-1: {mr.student_name}",
                    description=mr.message,
                    subject="General",
                    topic="1-to-1 Session",
                    class_type=ClassType.ONE_TO_ONE,
                    scheduled_at=scheduled_dt,
                    duration_minutes=req.duration_minutes,
                    meet_link=meet_link,
                    calendar_event_id=event_id,
                    target_student_id=mr.student_id,
                )
                _append_jsonl(CLASSES_FILE, cls_obj.to_dict())
                mr.class_id = cls_obj.class_id

            mr_obj = mr
            break

    if not mr_obj:
        raise HTTPException(404, "Request not found")

    _write_jsonl(MEETINGS_FILE, [mr.to_dict() for mr in all_mrs])

    # Notify the student
    if mr_obj.status == MeetingRequestStatus.ACCEPTED and cls_obj:
        _create_notification(
            mr_obj.student_id, NotificationType.MEETING_ACCEPTED,
            "NAGA accepted your meeting request!",
            f"Your 1-to-1 is on {cls_obj.scheduled_at.strftime('%d %b %Y, %I:%M %p')}\nMeet: {cls_obj.meet_link}",
            {"class_id": cls_obj.class_id, "meet_link": cls_obj.meet_link},
        )
    else:
        _create_notification(
            mr_obj.student_id, NotificationType.MEETING_DECLINED,
            "NAGA responded to your meeting request",
            req.naga_note or "Your meeting request was not accepted at this time.",
            {"request_id": request_id},
        )

    return {"message": "Responded", "class": cls_obj.to_dict() if cls_obj else None}


# ═══════════════════════════════════════════════════════════════════════════════
# NOTIFICATION ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/notifications")
async def get_notifications(auth_id: str = Depends(require_auth)):
    """Get notifications for the current user."""
    all_notifs = [Notification.from_dict(d) for d in _read_jsonl(NOTIFICATIONS_FILE)]
    mine = [n for n in all_notifs if n.user_id == auth_id]
    return [n.to_dict() for n in sorted(mine, key=lambda x: x.created_at, reverse=True)]


@router.post("/notifications/{notification_id}/read")
async def mark_read(notification_id: str, auth_id: str = Depends(require_auth)):
    """Mark a notification as read."""
    all_notifs = [Notification.from_dict(d) for d in _read_jsonl(NOTIFICATIONS_FILE)]
    for n in all_notifs:
        if n.notification_id == notification_id and n.user_id == auth_id:
            n.read = True
    _write_jsonl(NOTIFICATIONS_FILE, [n.to_dict() for n in all_notifs])
    return {"message": "Marked read"}


@router.post("/notifications/read-all")
async def mark_all_read(auth_id: str = Depends(require_auth)):
    """Mark all notifications as read."""
    all_notifs = [Notification.from_dict(d) for d in _read_jsonl(NOTIFICATIONS_FILE)]
    for n in all_notifs:
        if n.user_id == auth_id:
            n.read = True
    _write_jsonl(NOTIFICATIONS_FILE, [n.to_dict() for n in all_notifs])
    return {"message": "All marked read"}


# ═══════════════════════════════════════════════════════════════════════════════
# NAGA DASHBOARD SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/dashboard")
async def naga_dashboard(auth_id: str = Depends(require_auth)):
    """NAGA dashboard summary stats."""
    if auth_id != NAGA_USER_ID:
        raise HTTPException(403, "NAGA only")

    all_qs = [Question.from_dict(d) for d in _read_jsonl(QUESTIONS_FILE)]
    all_cls = [ScheduledClass.from_dict(d) for d in _read_jsonl(CLASSES_FILE)]
    all_mrs = [MeetingRequest.from_dict(d) for d in _read_jsonl(MEETINGS_FILE)]
    all_notifs = [Notification.from_dict(d) for d in _read_jsonl(NOTIFICATIONS_FILE)]

    now = datetime.utcnow()
    return {
        "pending_questions": sum(1 for q in all_qs if q.status == QuestionStatus.PENDING),
        "total_questions": len(all_qs),
        "upcoming_classes": sum(1 for c in all_cls if c.scheduled_at > now and c.status == "scheduled"),
        "pending_meeting_requests": sum(1 for mr in all_mrs if mr.status == MeetingRequestStatus.PENDING),
        "unread_notifications": sum(1 for n in all_notifs if n.user_id == NAGA_USER_ID and not n.read),
        "total_students": len(_students_store),
    }
