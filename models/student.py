import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


def get_available_exams() -> dict:
    config_path = os.path.join(os.path.dirname(__file__), "..", "data", "exams.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


class Language(str, Enum):
    ENGLISH = "en"
    HINDI = "hi"


@dataclass
class WeaknessMap:
    subject: str
    topic: str
    score_pct: float
    attempts: int
    last_attempted: datetime = field(default_factory=datetime.utcnow)
    # SM-2 spaced repetition fields
    ease_factor: float = 2.5        # starts at 2.5, decreases on wrong answers
    interval_days: int = 1          # days until next review
    next_review_date: datetime = field(default_factory=datetime.utcnow)

    def update_sm2(self, quality: int) -> None:
        """
        Update SM-2 scheduling after a review. quality: 0–5
        (0-1 = wrong, 2 = barely correct, 3 = correct with effort, 4-5 = easy)
        """
        if quality < 3:
            self.interval_days = 1
        elif self.interval_days == 1:
            self.interval_days = 6
        else:
            self.interval_days = round(self.interval_days * self.ease_factor)

        self.ease_factor = max(
            1.3,
            self.ease_factor + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02),
        )
        now = datetime.utcnow()
        self.next_review_date = now + timedelta(days=self.interval_days)
        self.last_attempted = now

    def to_dict(self) -> dict:
        return {
            "subject": self.subject,
            "topic": self.topic,
            "score_pct": self.score_pct,
            "attempts": self.attempts,
            "last_attempted": self.last_attempted.isoformat(),
            "ease_factor": self.ease_factor,
            "interval_days": self.interval_days,
            "next_review_date": self.next_review_date.isoformat(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "WeaknessMap":
        return cls(
            subject=d["subject"],
            topic=d["topic"],
            score_pct=d["score_pct"],
            attempts=d.get("attempts", 0),
            last_attempted=datetime.fromisoformat(d.get("last_attempted", datetime.utcnow().isoformat())),
            ease_factor=d.get("ease_factor", 2.5),
            interval_days=d.get("interval_days", 1),
            next_review_date=datetime.fromisoformat(d.get("next_review_date", datetime.utcnow().isoformat())),
        )


@dataclass
class StudentProfile:
    student_id: str
    google_sub: str
    exam_target: str  # e.g. "rrb_alp", refers to exams.json keys
    preferred_language: Language
    diagnostic_done: bool = False
    diagnostic_stage: int = 1  # Stage 1: broad, 2: specific, 3: atomic
    diagnostic_score: float = 0.0 # Score of the last diagnostic test
    weakness_map: list[WeaknessMap] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    study_streak_days: int = 0
    total_questions_attempted: int = 0
    # Per-PDF: ALP/Technician students register their ITI trade; JE students register their engineering discipline
    trade: str = ""                     # e.g. "Electrician", "Fitter" (rrb_alp, rrb_technician)
    engineering_discipline: str = ""    # e.g. "Civil", "Electrical", "Mechanical" (rrb_je)

    def to_dict(self) -> dict:
        return {
            "student_id": self.student_id,
            "exam_target": self.exam_target,
            "preferred_language": self.preferred_language.value,
            "diagnostic_done": self.diagnostic_done,
            "diagnostic_stage": self.diagnostic_stage,
            "diagnostic_score": self.diagnostic_score,
            "weakness_map": [w.to_dict() for w in self.weakness_map],
            "created_at": self.created_at.isoformat(),
            "study_streak_days": self.study_streak_days,
            "total_questions_attempted": self.total_questions_attempted,
            "trade": self.trade,
            "engineering_discipline": self.engineering_discipline,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "StudentProfile":
        return cls(
            student_id=d["student_id"],
            google_sub=d.get("google_sub", ""),
            exam_target=d["exam_target"],
            preferred_language=Language(d["preferred_language"]),
            diagnostic_done=d.get("diagnostic_done", False),
            diagnostic_stage=d.get("diagnostic_stage", 1),
            diagnostic_score=d.get("diagnostic_score", 0.0),
            weakness_map=[WeaknessMap.from_dict(w) for w in d.get("weakness_map", [])],
            created_at=datetime.fromisoformat(d.get("created_at", datetime.utcnow().isoformat())),
            study_streak_days=d.get("study_streak_days", 0),
            total_questions_attempted=d.get("total_questions_attempted", 0),
            trade=d.get("trade", ""),
            engineering_discipline=d.get("engineering_discipline", ""),
        )
