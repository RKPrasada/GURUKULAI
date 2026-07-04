"""
Mock test data models.

MockPaper   — a complete timed exam paper with all questions embedded
MockSession — a student's in-progress or completed attempt at a paper
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

# ── Exam-pattern configs ───────────────────────────────────────────────────────
# negative_marking: marks deducted per wrong answer (positive float)
# pass_marks: indicative passing threshold (%)

EXAM_CONFIGS: dict[str, dict] = {
    "rrb_ntpc": {
        "name": "RRB NTPC CBT-1",
        "total_questions": 100,
        "duration_mins": 90,
        "negative_marking": round(1 / 3, 4),
        "marks_per_question": 1,
        "pass_marks_pct": 0.40,
        "sections": [
            {"name": "Mathematics",                   "count": 30,
             "topics": ["Number System", "Fractions", "LCM & HCF", "Ratio & Proportion",
                        "Percentages", "Profit & Loss", "Simple & Compound Interest",
                        "Time & Work", "Time & Distance", "Mensuration", "Statistics"]},
            {"name": "General Intelligence & Reasoning", "count": 30,
             "topics": ["Analogies", "Coding-Decoding", "Blood Relations", "Syllogism",
                        "Series Completion", "Puzzles", "Direction Sense", "Venn Diagrams",
                        "Data Sufficiency", "Statement & Conclusion"]},
            {"name": "General Awareness",             "count": 40,
             "topics": ["Indian History", "Indian Geography", "Indian Polity",
                        "Indian Economy", "Science & Technology", "Current Affairs",
                        "Sports", "Culture & Art"]},
        ],
    },
    "rrb_alp": {
        "name": "RRB ALP CBT-1",
        "total_questions": 75,
        "duration_mins": 60,
        "negative_marking": round(1 / 3, 4),
        "marks_per_question": 1,
        "pass_marks_pct": 0.40,
        "sections": [
            {"name": "Mathematics",       "count": 20,
             "topics": ["Number System", "Ratio", "Algebra", "Mensuration", "Trigonometry"]},
            {"name": "Reasoning",         "count": 25,
             "topics": ["Coding-Decoding", "Series", "Puzzles", "Analogies", "Logical Venn"]},
            {"name": "General Science",   "count": 20,
             "topics": ["Physics", "Chemistry", "Biology"]},
            {"name": "General Awareness", "count": 10,
             "topics": ["Current Affairs", "Indian History", "Geography"]},
        ],
    },
    "rrb_technician": {
        "name": "RRB Technician CBT-2 Part A",
        "total_questions": 100,
        "duration_mins": 90,
        "negative_marking": round(1 / 3, 4),
        "marks_per_question": 1,
        "pass_marks_pct": 0.40,
        "sections": [
            {"name": "Mathematics",                   "count": 25,
             "topics": ["Number System", "Fractions", "Ratio & Proportion", "LCM & HCF",
                        "Percentages", "Mensuration", "Statistics", "Time & Work"]},
            {"name": "Reasoning",                     "count": 25,
             "topics": ["Coding-Decoding", "Series Completion", "Analogies", "Puzzles",
                        "Direction Sense", "Blood Relations", "Venn Diagrams"]},
            {"name": "Basic Science & Engineering",   "count": 40,
             "topics": ["Engineering Drawing", "Units & Measurements", "Mass Weight Density",
                        "Work Power Energy", "Speed & Velocity", "Heat & Temperature",
                        "Basic Electricity", "Levers & Simple Machines",
                        "Occupational Safety", "Environment & Pollution", "IT Literacy"]},
            {"name": "Current Affairs",               "count": 10,
             "topics": ["National Events", "Sports", "Science & Technology", "Awards",
                        "Government Schemes"]},
        ],
    },
    "rrb_je": {
        "name": "RRB JE CBT-1",
        "total_questions": 100,
        "duration_mins": 90,
        "negative_marking": round(1 / 3, 4),
        "marks_per_question": 1,
        "pass_marks_pct": 0.40,
        "sections": [
            {"name": "Mathematics",      "count": 30,
             "topics": ["Number System", "Algebra", "Geometry", "Trigonometry", "Mensuration",
                        "Statistics", "Ratio & Proportion", "Time & Work", "Profit & Loss"]},
            {"name": "Reasoning",        "count": 25,
             "topics": ["Analogies", "Coding-Decoding", "Series", "Syllogism", "Puzzles",
                        "Data Sufficiency", "Statement & Conclusion", "Venn Diagrams"]},
            {"name": "General Awareness", "count": 15,
             "topics": ["Indian History", "Indian Polity", "Indian Economy",
                        "Current Affairs", "Sports", "Culture & Art"]},
            {"name": "General Science",  "count": 30,
             "topics": ["Physics — NCERT 10th", "Chemistry — NCERT 10th",
                        "Biology — NCERT 10th", "Environment & Ecology"]},
        ],
    },
    "rrb_group_d": {
        "name": "RRB Group D CBT",
        "total_questions": 100,
        "duration_mins": 90,
        "negative_marking": round(1 / 3, 4),
        "marks_per_question": 1,
        "pass_marks_pct": 0.40,
        "sections": [
            {"name": "Mathematics",       "count": 25,
             "topics": ["Number System", "Fractions", "Mensuration", "Time & Work", "Statistics"]},
            {"name": "Reasoning",         "count": 30,
             "topics": ["Analogies", "Coding", "Puzzles", "Series", "Statement & Conclusion"]},
            {"name": "General Science",   "count": 25,
             "topics": ["Physics", "Chemistry", "Biology", "Environmental Science"]},
            {"name": "General Awareness", "count": 20,
             "topics": ["Indian History", "Geography", "Polity", "Current Affairs"]},
        ],
    },
    "nda": {
        "name": "NDA Mathematics",
        "total_questions": 120,
        "duration_mins": 150,
        "negative_marking": round(1 / 3, 4),
        "marks_per_question": 2.5,
        "pass_marks_pct": 0.35,
        "sections": [
            {"name": "Algebra",            "count": 20, "topics": ["Sets", "Complex Numbers", "Matrices", "Quadratics", "Permutations"]},
            {"name": "Calculus",           "count": 20, "topics": ["Limits", "Continuity", "Differentiation", "Integration", "Differential Equations"]},
            {"name": "Trigonometry",       "count": 20, "topics": ["Identities", "Inverse Trig", "Properties of Triangles"]},
            {"name": "Coordinate Geometry","count": 20, "topics": ["Straight Lines", "Circles", "Conics"]},
            {"name": "Statistics",         "count": 20, "topics": ["Probability", "Distributions", "Correlation"]},
            {"name": "Vectors & 3D",       "count": 20, "topics": ["Vectors", "3D Geometry"]},
        ],
    },
    "jee": {
        "name": "JEE Mains",
        "total_questions": 75,
        "duration_mins": 180,
        "negative_marking": 1.0,
        "marks_per_question": 4,
        "pass_marks_pct": 0.35,
        "sections": [
            {"name": "Physics",    "count": 25,
             "topics": ["Mechanics", "Thermodynamics", "Electrostatics", "Magnetism",
                        "Optics", "Modern Physics", "Waves"]},
            {"name": "Chemistry",  "count": 25,
             "topics": ["Organic Chemistry", "Inorganic Chemistry", "Physical Chemistry",
                        "Equilibrium", "Thermodynamics", "Electrochemistry"]},
            {"name": "Mathematics","count": 25,
             "topics": ["Algebra", "Calculus", "Coordinate Geometry", "Vectors",
                        "Probability", "Trigonometry"]},
        ],
    },
    "neet": {
        "name": "NEET UG",
        "total_questions": 180,
        "duration_mins": 200,
        "negative_marking": 1.0,
        "marks_per_question": 4,
        "pass_marks_pct": 0.40,
        "sections": [
            {"name": "Physics",  "count": 45,
             "topics": ["Mechanics", "Thermodynamics", "Electrostatics", "Optics",
                        "Modern Physics", "Waves", "Magnetism"]},
            {"name": "Chemistry","count": 45,
             "topics": ["Physical Chemistry", "Organic Chemistry", "Inorganic Chemistry",
                        "Biomolecules", "Polymers", "Environmental Chemistry"]},
            {"name": "Biology",  "count": 90,
             "topics": ["Cell Biology", "Genetics", "Evolution", "Human Physiology",
                        "Plant Physiology", "Ecology", "Biotechnology", "Microbes"]},
        ],
    },
}

DIFFICULTY_DISTRIBUTION = {"easy": 0.30, "medium": 0.50, "hard": 0.20}


@dataclass
class MockQuestion:
    question_id: str
    section: str
    topic: str
    difficulty: str          # "easy" | "medium" | "hard"
    question_text_en: str
    options: list[str]
    correct_index: int
    explanation_en: str
    marks: float = 1.0
    negative_marks: float = round(1 / 3, 4)

    def to_dict(self, include_answer: bool = True) -> dict:
        d = {
            "question_id": self.question_id,
            "section": self.section,
            "topic": self.topic,
            "difficulty": self.difficulty,
            "question_text_en": self.question_text_en,
            "options": self.options,
            "marks": self.marks,
            "negative_marks": self.negative_marks,
        }
        if include_answer:
            d["correct_index"] = self.correct_index
            d["explanation_en"] = self.explanation_en
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "MockQuestion":
        return cls(
            question_id=d.get("question_id", str(uuid.uuid4())),
            section=d["section"],
            topic=d["topic"],
            difficulty=d.get("difficulty", "medium"),
            question_text_en=d["question_text_en"],
            options=d["options"],
            correct_index=d["correct_index"],
            explanation_en=d.get("explanation_en", ""),
            marks=d.get("marks", 1.0),
            negative_marks=d.get("negative_marks", round(1 / 3, 4)),
        )


@dataclass
class MockPaper:
    paper_id: str
    exam_key: str
    exam_name: str
    generated_at: str
    scheduled_date: str         # "YYYY-MM-DD" — Saturday this paper is for
    total_questions: int
    duration_mins: int
    negative_marking: float
    marks_per_question: float
    sections: list[dict]        # [{name, questions:[MockQuestion.to_dict()], count}]
    difficulty_distribution: dict
    generation_method: str = "llm"   # "llm" | "fallback_archive"

    @property
    def all_questions(self) -> list[dict]:
        """Flat list of all questions across sections (with answers, for scoring)."""
        qs = []
        for s in self.sections:
            qs.extend(s.get("questions", []))
        return qs

    def to_dict(self, include_answers: bool = True) -> dict:
        sections_out = []
        for s in self.sections:
            qs = s.get("questions", [])
            if not include_answers:
                qs = [{k: v for k, v in q.items() if k not in ("correct_index", "explanation_en")}
                      for q in qs]
            sections_out.append({**s, "questions": qs})
        return {
            "paper_id": self.paper_id,
            "exam_key": self.exam_key,
            "exam_name": self.exam_name,
            "generated_at": self.generated_at,
            "scheduled_date": self.scheduled_date,
            "total_questions": self.total_questions,
            "duration_mins": self.duration_mins,
            "negative_marking": self.negative_marking,
            "marks_per_question": self.marks_per_question,
            "sections": sections_out,
            "difficulty_distribution": self.difficulty_distribution,
            "generation_method": self.generation_method,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MockPaper":
        return cls(
            paper_id=d["paper_id"],
            exam_key=d["exam_key"],
            exam_name=d["exam_name"],
            generated_at=d["generated_at"],
            scheduled_date=d["scheduled_date"],
            total_questions=d["total_questions"],
            duration_mins=d["duration_mins"],
            negative_marking=d["negative_marking"],
            marks_per_question=d.get("marks_per_question", 1.0),
            sections=d["sections"],
            difficulty_distribution=d.get("difficulty_distribution", {}),
            generation_method=d.get("generation_method", "llm"),
        )


@dataclass
class MockSession:
    session_id: str
    student_id: str
    exam_key: str
    paper_id: str
    started_at: str
    duration_mins: int
    total_questions: int
    answers: list[int]        # -1 = not answered
    flagged: list[int]        # question indices marked for review
    submitted: bool = False
    submitted_at: Optional[str] = None
    timed_out: bool = False
    score: Optional[float] = None
    max_score: Optional[float] = None
    section_scores: Optional[list[dict]] = None
    rank_estimate_pct: Optional[float] = None

    @property
    def seconds_elapsed(self) -> int:
        try:
            start = datetime.fromisoformat(self.started_at)
            return int((datetime.utcnow() - start).total_seconds())
        except Exception:
            return 0

    @property
    def seconds_remaining(self) -> int:
        return max(0, self.duration_mins * 60 - self.seconds_elapsed)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "student_id": self.student_id,
            "exam_key": self.exam_key,
            "paper_id": self.paper_id,
            "started_at": self.started_at,
            "duration_mins": self.duration_mins,
            "total_questions": self.total_questions,
            "answers": self.answers,
            "flagged": self.flagged,
            "submitted": self.submitted,
            "submitted_at": self.submitted_at,
            "timed_out": self.timed_out,
            "score": self.score,
            "max_score": self.max_score,
            "section_scores": self.section_scores,
            "rank_estimate_pct": self.rank_estimate_pct,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MockSession":
        return cls(
            session_id=d["session_id"],
            student_id=d["student_id"],
            exam_key=d["exam_key"],
            paper_id=d["paper_id"],
            started_at=d["started_at"],
            duration_mins=d["duration_mins"],
            total_questions=d["total_questions"],
            answers=d.get("answers", []),
            flagged=d.get("flagged", []),
            submitted=d.get("submitted", False),
            submitted_at=d.get("submitted_at"),
            timed_out=d.get("timed_out", False),
            score=d.get("score"),
            max_score=d.get("max_score"),
            section_scores=d.get("section_scores"),
            rank_estimate_pct=d.get("rank_estimate_pct"),
        )
