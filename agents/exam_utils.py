import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).parent.parent / "data"
SYLLABUS_DIR = DATA_DIR / "syllabus"

APPROVED_EXAMS = {
    "rrb_ntpc", "rrb_alp", "rrb_group_d", "rrb_technician", "rrb_je",
    "nda", "jee", "neet",
}
EXAM_ALIASES = {
    "rrb_ntpc": "rrb_ntpc",
    "ntpc": "rrb_ntpc",
    "rrb": "rrb_ntpc",
    "rrb_alp": "rrb_alp",
    "alp": "rrb_alp",
    "assistant loco pilot": "rrb_alp",
    "rrb_group_d": "rrb_group_d",
    "group_d": "rrb_group_d",
    "group d": "rrb_group_d",
    "rrb_technician": "rrb_technician",
    "technician": "rrb_technician",
    "rrb_je": "rrb_je",
    "je": "rrb_je",
    "junior engineer": "rrb_je",
    "nda": "nda",
    "jee": "jee",
    "jee main": "jee",
    "jee mains": "jee",
    "neet": "neet",
}


def exam_value(exam: Any) -> str:
    value = exam.value if hasattr(exam, "value") else str(exam)
    return EXAM_ALIASES.get(value.lower(), value.lower())


@lru_cache(maxsize=16)
def load_syllabus(exam: str) -> dict:
    key = exam_value(exam)
    path = SYLLABUS_DIR / f"{key}.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def exam_name(exam: Any) -> str:
    syllabus = load_syllabus(exam_value(exam))
    return syllabus.get("exam") or exam_value(exam).upper()


def syllabus_terms(exam: Any) -> set[str]:
    syllabus = load_syllabus(exam_value(exam))
    terms: set[str] = {exam_name(exam).lower(), exam_value(exam).replace("_", " ")}
    for subject in syllabus.get("subjects", []):
        terms.add(subject.get("name", "").lower())
        for topic in subject.get("topics", []):
            terms.add(topic.get("name", "").lower())
            for subtopic in topic.get("subtopics", []):
                terms.add(str(subtopic).lower())
    return {term for term in terms if term}


def compact_syllabus(exam: Any) -> str:
    syllabus = load_syllabus(exam_value(exam))
    lines: list[str] = []
    for subject in syllabus.get("subjects", []):
        topic_names = [topic.get("name", "") for topic in subject.get("topics", [])]
        lines.append(f"- {subject.get('name')}: {', '.join(t for t in topic_names if t)}")
    return "\n".join(lines)


def is_exam_scope_query(text: str, exam: Any) -> bool:
    if exam_value(exam) not in APPROVED_EXAMS:
        return False
    lowered = text.lower()
    if any(alias in lowered for alias in EXAM_ALIASES):
        return True
    words = set(re.findall(r"[a-zA-Z][a-zA-Z&'-]+", lowered))
    if not words:
        return True
    for term in syllabus_terms(exam):
        term_words = set(re.findall(r"[a-zA-Z][a-zA-Z&'-]+", term))
        if term_words and (term in lowered or words & term_words):
            return True
    return False
