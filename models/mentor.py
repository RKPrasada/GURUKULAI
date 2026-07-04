"""Data models for NAGA mentor system."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class QuestionStatus(str, Enum):
    PENDING = "pending"       # Awaiting NAGA approval
    APPROVED = "approved"     # Visible to all students
    RESOLVED = "resolved"     # Marked resolved
    REJECTED = "rejected"     # Rejected by NAGA


class ClassType(str, Enum):
    GROUP = "group"           # Open to all / RSVP students
    ONE_TO_ONE = "one_to_one"  # Private session with one student


class MeetingRequestStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    CANCELLED = "cancelled"


class NotificationType(str, Enum):
    QUESTION_APPROVED = "question_approved"
    QUESTION_ANSWERED = "question_answered"
    CLASS_SCHEDULED = "class_scheduled"
    CLASS_CANCELLED = "class_cancelled"
    MEETING_ACCEPTED = "meeting_accepted"
    MEETING_DECLINED = "meeting_declined"
    MEETING_REQUEST = "meeting_request"         # To NAGA
    NEW_QUESTION = "new_question"               # To NAGA
    # Dabbu → NAGA approval queue
    STUDY_PLAN_PROPOSED = "study_plan_proposed"
    CLASS_SUGGESTED = "class_suggested"
    NOTE_PENDING_APPROVAL = "note_pending"
    VIDEO_PENDING_REVIEW = "video_pending"
    # NAGA → Student outcomes
    STUDY_PLAN_APPROVED = "study_plan_approved"
    NOTE_PUBLISHED = "note_published"
    # Dabbu → Student direct suggestions
    DIAGNOSTIC_RECOMMENDED = "diagnostic_recommended"


@dataclass
class Question:
    question_id: str
    student_id: str
    student_name: str
    subject: str
    topic: str
    content: str
    status: QuestionStatus = QuestionStatus.PENDING
    upvotes: int = 0
    upvoted_by: list = field(default_factory=list)
    answer: Optional[str] = None
    answered_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    approved_at: Optional[datetime] = None
    class_id: Optional[str] = None  # Linked class if NAGA schedules one

    def to_dict(self) -> dict:
        return {
            "question_id": self.question_id,
            "student_id": self.student_id,
            "student_name": self.student_name,
            "subject": self.subject,
            "topic": self.topic,
            "content": self.content,
            "status": self.status.value,
            "upvotes": self.upvotes,
            "upvoted_by": self.upvoted_by,
            "answer": self.answer,
            "answered_at": self.answered_at.isoformat() if self.answered_at else None,
            "created_at": self.created_at.isoformat(),
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "class_id": self.class_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Question":
        return cls(
            question_id=d["question_id"],
            student_id=d["student_id"],
            student_name=d.get("student_name", ""),
            subject=d["subject"],
            topic=d["topic"],
            content=d["content"],
            status=QuestionStatus(d.get("status", "pending")),
            upvotes=d.get("upvotes", 0),
            upvoted_by=d.get("upvoted_by", []),
            answer=d.get("answer"),
            answered_at=datetime.fromisoformat(d["answered_at"]) if d.get("answered_at") else None,
            created_at=datetime.fromisoformat(d["created_at"]),
            approved_at=datetime.fromisoformat(d["approved_at"]) if d.get("approved_at") else None,
            class_id=d.get("class_id"),
        )


@dataclass
class ScheduledClass:
    class_id: str
    title: str
    description: str
    subject: str
    topic: str
    class_type: ClassType
    scheduled_at: datetime
    duration_minutes: int = 60
    meet_link: str = ""
    calendar_event_id: str = ""
    created_by: str = "naga"
    rsvp_list: list = field(default_factory=list)      # [{student_id, name, status}]
    target_student_id: Optional[str] = None            # For 1-to-1
    linked_question_ids: list = field(default_factory=list)
    max_students: int = 50
    status: str = "scheduled"                          # scheduled, completed, cancelled
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "class_id": self.class_id,
            "title": self.title,
            "description": self.description,
            "subject": self.subject,
            "topic": self.topic,
            "class_type": self.class_type.value,
            "scheduled_at": self.scheduled_at.isoformat(),
            "duration_minutes": self.duration_minutes,
            "meet_link": self.meet_link,
            "calendar_event_id": self.calendar_event_id,
            "created_by": self.created_by,
            "rsvp_list": self.rsvp_list,
            "target_student_id": self.target_student_id,
            "linked_question_ids": self.linked_question_ids,
            "max_students": self.max_students,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ScheduledClass":
        return cls(
            class_id=d["class_id"],
            title=d["title"],
            description=d["description"],
            subject=d["subject"],
            topic=d["topic"],
            class_type=ClassType(d["class_type"]),
            scheduled_at=datetime.fromisoformat(d["scheduled_at"]),
            duration_minutes=d.get("duration_minutes", 60),
            meet_link=d.get("meet_link", ""),
            calendar_event_id=d.get("calendar_event_id", ""),
            created_by=d.get("created_by", "naga"),
            rsvp_list=d.get("rsvp_list", []),
            target_student_id=d.get("target_student_id"),
            linked_question_ids=d.get("linked_question_ids", []),
            max_students=d.get("max_students", 50),
            status=d.get("status", "scheduled"),
            created_at=datetime.fromisoformat(d["created_at"]),
        )


@dataclass
class MeetingRequest:
    request_id: str
    student_id: str
    student_name: str
    student_email: str
    message: str
    preferred_times: list = field(default_factory=list)  # List of ISO datetime strings
    status: MeetingRequestStatus = MeetingRequestStatus.PENDING
    class_id: Optional[str] = None   # Set when NAGA accepts and creates a meet
    naga_note: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    responded_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "student_id": self.student_id,
            "student_name": self.student_name,
            "student_email": self.student_email,
            "message": self.message,
            "preferred_times": self.preferred_times,
            "status": self.status.value,
            "class_id": self.class_id,
            "naga_note": self.naga_note,
            "created_at": self.created_at.isoformat(),
            "responded_at": self.responded_at.isoformat() if self.responded_at else None,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MeetingRequest":
        return cls(
            request_id=d["request_id"],
            student_id=d["student_id"],
            student_name=d.get("student_name", ""),
            student_email=d.get("student_email", ""),
            message=d["message"],
            preferred_times=d.get("preferred_times", []),
            status=MeetingRequestStatus(d.get("status", "pending")),
            class_id=d.get("class_id"),
            naga_note=d.get("naga_note", ""),
            created_at=datetime.fromisoformat(d["created_at"]),
            responded_at=datetime.fromisoformat(d["responded_at"]) if d.get("responded_at") else None,
        )


@dataclass
class Notification:
    notification_id: str
    user_id: str
    type: NotificationType
    title: str
    body: str
    read: bool = False
    data: dict = field(default_factory=dict)   # Extra context (class_id, question_id, etc.)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "notification_id": self.notification_id,
            "user_id": self.user_id,
            "type": self.type.value,
            "title": self.title,
            "body": self.body,
            "read": self.read,
            "data": self.data,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Notification":
        return cls(
            notification_id=d["notification_id"],
            user_id=d["user_id"],
            type=NotificationType(d["type"]),
            title=d["title"],
            body=d["body"],
            read=d.get("read", False),
            data=d.get("data", {}),
            created_at=datetime.fromisoformat(d["created_at"]),
        )
