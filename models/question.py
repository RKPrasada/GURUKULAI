from __future__ import annotations
from dataclasses import dataclass



@dataclass
class Question:
    question_id: str
    exam: str
    subject: str
    topic: str
    difficulty: int  # 1=easy 2=medium 3=hard
    question_text_en: str
    options: list[str]
    correct_index: int  # 0-3
    explanation_en: str
    question_text_hi: str | None = None
    explanation_hi: str | None = None
    source_year: int | None = None

    def to_dict(self) -> dict:
        return {
            "question_id": self.question_id,
            "exam": self.exam,
            "subject": self.subject,
            "topic": self.topic,
            "difficulty": self.difficulty,
            "question_text_en": self.question_text_en,
            "question_text_hi": self.question_text_hi,
            "options": self.options,
            "correct_index": self.correct_index,
            "explanation_en": self.explanation_en,
            "explanation_hi": self.explanation_hi,
            "source_year": self.source_year,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Question":
        import uuid
        return cls(
            question_id=d.get("question_id") or f"mcq_{uuid.uuid4().hex[:8]}",
            exam=d.get("exam", "rrb_ntpc"),
            subject=d.get("subject", "General"),
            topic=d.get("topic", "General"),
            difficulty=int(d.get("difficulty", 1)),
            question_text_en=d.get("question_text_en", "Missing question text"),
            question_text_hi=d.get("question_text_hi"),
            options=d.get("options", ["Option A", "Option B", "Option C", "Option D"]),
            correct_index=int(d.get("correct_index", 0)),
            explanation_en=d.get("explanation_en", "Missing explanation"),
            explanation_hi=d.get("explanation_hi"),
            source_year=d.get("source_year"),
        )
