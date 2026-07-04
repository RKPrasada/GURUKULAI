"""Study plan data model — produced by Dabbu, approved by NAGA, followed by student."""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional


class PlanStatus(str, Enum):
    PROPOSED = "proposed"   # Dabbu generated; awaiting NAGA approval
    APPROVED = "approved"   # NAGA approved; visible to student
    REJECTED = "rejected"   # NAGA rejected; student keeps previous plan
    ACTIVE = "active"       # Student is currently following this plan
    COMPLETED = "completed"


class SessionType(str, Enum):
    STUDY = "study"         # New material / weak topic revision
    PRACTICE = "practice"  # Topic-specific MCQ practice
    MOCK = "mock"           # Full timed mock test
    REVISION = "revision"  # Quick review of previously studied topics
    REST = "rest"           # Scheduled break


@dataclass
class SessionBlock:
    block_id: str
    start_hour: int          # 0-22 (24h clock)
    duration_hours: int = 2
    subject: str = ""
    topic: str = ""
    session_type: SessionType = SessionType.STUDY
    priority: int = 1        # 1=normal, 2=important, 3=critical (weak area)
    completed: bool = False
    rescheduled: bool = False

    def to_dict(self) -> dict:
        return {
            "block_id": self.block_id,
            "start_hour": self.start_hour,
            "duration_hours": self.duration_hours,
            "subject": self.subject,
            "topic": self.topic,
            "session_type": self.session_type.value,
            "priority": self.priority,
            "completed": self.completed,
            "rescheduled": self.rescheduled,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SessionBlock":
        return cls(
            block_id=d["block_id"],
            start_hour=d["start_hour"],
            duration_hours=d.get("duration_hours", 2),
            subject=d.get("subject", ""),
            topic=d.get("topic", ""),
            session_type=SessionType(d.get("session_type", "study")),
            priority=d.get("priority", 1),
            completed=d.get("completed", False),
            rescheduled=d.get("rescheduled", False),
        )


@dataclass
class DayPlan:
    day_date: str           # ISO date string: "2026-07-10"
    day_of_week: str        # "Monday"
    blocks: list[SessionBlock] = field(default_factory=list)
    total_hours: float = 0.0
    is_rest_day: bool = False

    def to_dict(self) -> dict:
        return {
            "day_date": self.day_date,
            "day_of_week": self.day_of_week,
            "blocks": [b.to_dict() for b in self.blocks],
            "total_hours": self.total_hours,
            "is_rest_day": self.is_rest_day,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "DayPlan":
        return cls(
            day_date=d["day_date"],
            day_of_week=d.get("day_of_week", ""),
            blocks=[SessionBlock.from_dict(b) for b in d.get("blocks", [])],
            total_hours=d.get("total_hours", 0.0),
            is_rest_day=d.get("is_rest_day", False),
        )


@dataclass
class WeekPlan:
    week_number: int        # 1-indexed within the plan
    start_date: str         # ISO date
    end_date: str           # ISO date
    theme: str = ""         # e.g. "Mathematics — Foundation", "Physics — Circuits"
    days: list[DayPlan] = field(default_factory=list)
    total_hours: float = 0.0

    def to_dict(self) -> dict:
        return {
            "week_number": self.week_number,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "theme": self.theme,
            "days": [d.to_dict() for d in self.days],
            "total_hours": self.total_hours,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "WeekPlan":
        return cls(
            week_number=d["week_number"],
            start_date=d["start_date"],
            end_date=d["end_date"],
            theme=d.get("theme", ""),
            days=[DayPlan.from_dict(day) for day in d.get("days", [])],
            total_hours=d.get("total_hours", 0.0),
        )


@dataclass
class StudyPlan:
    plan_id: str
    student_id: str
    exam_target: str
    status: PlanStatus = PlanStatus.PROPOSED
    duration_months: int = 6
    start_date: str = ""    # ISO date
    end_date: str = ""      # ISO date
    exam_date: Optional[str] = None   # Target exam date if provided
    weeks: list[WeekPlan] = field(default_factory=list)
    weak_topics: list[str] = field(default_factory=list)      # Topics given 2x/3x weight
    diagnostic_score: float = 0.0
    naga_note: str = ""     # NAGA's approval note or rejection reason
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    approved_at: Optional[str] = None
    total_study_hours: float = 0.0

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "student_id": self.student_id,
            "exam_target": self.exam_target,
            "status": self.status.value,
            "duration_months": self.duration_months,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "exam_date": self.exam_date,
            "weeks": [w.to_dict() for w in self.weeks],
            "weak_topics": self.weak_topics,
            "diagnostic_score": self.diagnostic_score,
            "naga_note": self.naga_note,
            "created_at": self.created_at,
            "approved_at": self.approved_at,
            "total_study_hours": self.total_study_hours,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "StudyPlan":
        return cls(
            plan_id=d["plan_id"],
            student_id=d["student_id"],
            exam_target=d["exam_target"],
            status=PlanStatus(d.get("status", "proposed")),
            duration_months=d.get("duration_months", 6),
            start_date=d.get("start_date", ""),
            end_date=d.get("end_date", ""),
            exam_date=d.get("exam_date"),
            weeks=[WeekPlan.from_dict(w) for w in d.get("weeks", [])],
            weak_topics=d.get("weak_topics", []),
            diagnostic_score=d.get("diagnostic_score", 0.0),
            naga_note=d.get("naga_note", ""),
            created_at=d.get("created_at", datetime.utcnow().isoformat()),
            approved_at=d.get("approved_at"),
            total_study_hours=d.get("total_study_hours", 0.0),
        )
