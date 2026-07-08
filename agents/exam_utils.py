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


def _norm_topic(s: str) -> str:
    """Lowercase, strip punctuation/spaces for fuzzy topic matching."""
    return "".join(c for c in s.lower() if c.isalnum())


@lru_cache(maxsize=16)
def _topic_index(exam: str) -> dict[str, tuple[str, str]]:
    """Build {normalized_name: (subject, canonical_topic)} for an exam.

    Maps BOTH syllabus topics and their subtopics to (subject, topic), so a
    free-text query like 'Fractions' resolves to ('Mathematics', 'Number System')
    because 'Fractions' is a subtopic of 'Number System'.
    """
    syllabus = load_syllabus(exam)
    index: dict[str, tuple[str, str]] = {}
    for subject in syllabus.get("subjects", []):
        subj_name = subject.get("name", "")
        for topic in subject.get("topics", []):
            topic_name = topic.get("name", "")
            if topic_name:
                index[_norm_topic(topic_name)] = (subj_name, topic_name)
            # Subtopics resolve to their parent topic
            for sub in topic.get("subtopics", []):
                key = _norm_topic(str(sub))
                if key and key not in index:
                    index[key] = (subj_name, topic_name)
    return index


def resolve_topic(exam: Any, topic: str) -> tuple[str, str]:
    """Resolve a free-text topic to (subject, canonical_topic) using the syllabus.

    Resolution order:
      1. Exact topic/subtopic name match.
      2. Fuzzy match — query is a substring of a known name or vice versa.
      3. Unresolved → ('', topic) so callers can fall back.

    Examples (RRB NTPC):
      'Fractions'       -> ('Mathematics', 'Number System')
      'Number System'   -> ('Mathematics', 'Number System')
      'quadratic eqn'   -> ('Mathematics', 'Algebra')
    """
    exam_key = exam_value(exam)
    index = _topic_index(exam_key)
    q = _norm_topic(topic)
    if not q:
        return ("", topic)
    # Exact
    if q in index:
        return index[q]
    # Fuzzy: query contains a key or a key contains the query (min 4 chars each)
    for key, (subj, canon) in index.items():
        if len(key) >= 4 and len(q) >= 4 and (q in key or key in q):
            return (subj, canon)
    return ("", topic)


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
        if not term_words:
            continue
        # Exact word match
        if term in lowered or words & term_words:
            return True
        # Singular/plural and stem variants: "fraction" matches "fractions",
        # "lcm" matches "lcms", etc. — bidirectional substring, min 4 chars.
        if any(
            len(w) >= 4 and len(t) >= 4 and (w in t or t in w)
            for w in words for t in term_words
        ):
            return True
    return False
