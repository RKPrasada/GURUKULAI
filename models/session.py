from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class SessionType(str, Enum):
    DIAGNOSTIC = "diagnostic"
    STUDY = "study"
    TEST = "test"
    REVIEW = "review"


@dataclass
class StudySession:
    session_id: str
    student_id: str
    exam_target: str
    session_type: SessionType
    started_at: datetime = field(default_factory=datetime.utcnow)
    last_active: datetime = field(default_factory=datetime.utcnow)
    questions_answered: int = 0
    correct_answers: int = 0
    current_topic: str | None = None
    data: dict = field(default_factory=dict)

    @property
    def accuracy(self) -> float:
        if self.questions_answered == 0:
            return 0.0
        return self.correct_answers / self.questions_answered

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "student_id": self.student_id,
            "exam_target": self.exam_target,
            "session_type": self.session_type.value,
            "started_at": self.started_at.isoformat(),
            "last_active": self.last_active.isoformat(),
            "questions_answered": self.questions_answered,
            "correct_answers": self.correct_answers,
            "current_topic": self.current_topic,
            "data": self.data,
        }
