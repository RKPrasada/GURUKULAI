"""
Topic-specific practice bank — 200Q circular buffer per topic.

Layout: data/practice_banks/{exam_key}/{topic_slug}.json
Each file is a plain JSON list, max 200 questions.
When the buffer is full, the oldest 20 are evicted before appending new ones.

Usage:
  mgr = PracticeBankManager()
  questions = mgr.get_questions(exam_key, subject, topic, count=20)
"""

from __future__ import annotations

import json
import logging
import threading
import uuid
from pathlib import Path
from typing import Optional
import random

from agents.base import call_gemini
from agents.question_validator import filter_questions

logger = logging.getLogger(__name__)

BANKS_DIR = Path("data/practice_banks")
GENERAL_BANKS_DIR = Path("data/question_banks")
BANKS_DIR.mkdir(parents=True, exist_ok=True)

BUFFER_MAX = 200       # max questions per topic bank
EVICT_BATCH = 20       # oldest N removed when buffer is full
LLM_PER_SESSION = 20  # fresh LLM questions fetched per practice session
LLM_TIMEOUT = 25.0

_lock = threading.Lock()

SYSTEM_PROMPT = """You are an expert MCQ writer for Indian competitive exams.
Write specific, knowledge-testing questions — NOT vague or generic ones.
Each question: exactly 4 options, 1 correct answer, concise explanation.
Do NOT write questions like 'Which is a key concept of X' — write factual, numerical, or rule-based questions.
Return ONLY valid JSON (no markdown fences): {"questions": [...]}
Each question object:
{
  "subject": "...",
  "topic": "...",
  "difficulty": 1,
  "question_text": "...",
  "options": ["A", "B", "C", "D"],
  "correct_index": 0,
  "explanation": "..."
}
difficulty: 1=easy, 2=medium, 3=hard. Mix all three."""


def _slug(text: str) -> str:
    return text.lower().replace(" ", "_").replace("&", "and").replace("/", "_")[:40]


def _bank_path(exam_key: str, topic: str) -> Path:
    exam_dir = BANKS_DIR / exam_key
    exam_dir.mkdir(parents=True, exist_ok=True)
    return exam_dir / f"{_slug(topic)}.json"


def _read_bank(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def _write_bank(path: Path, questions: list[dict]) -> None:
    path.write_text(json.dumps(questions, indent=2, ensure_ascii=False))


def _generate_topic_questions(
    exam_key: str, subject: str, topic: str, count: int
) -> list[dict]:
    """Ask LLM for `count` MCQs on a specific topic."""
    prompt = (
        f"Exam: {exam_key.upper().replace('_', ' ')}\n"
        f"Subject: {subject}\n"
        f"Topic: {topic}\n\n"
        f"Generate exactly {count} MCQs for practice on this topic.\n"
        f"Mix difficulty: easy, medium, hard.\n"
        f"Questions must be specific — include numbers, formulas, dates, names where relevant.\n"
        f"Do NOT repeat questions that test the same fact.\n"
        f"Return ONLY valid JSON: {{\"questions\": [...]}}"
    )
    raw = call_gemini(prompt, SYSTEM_PROMPT, timeout=LLM_TIMEOUT)
    if not raw:
        return []

    clean = raw.strip()
    for fence in ("```json", "```"):
        if clean.startswith(fence):
            clean = clean[len(fence):]
    if clean.endswith("```"):
        clean = clean[:-3]

    try:
        qs = json.loads(clean.strip()).get("questions", [])[:count]
        for q in qs:
            if not q.get("id"):
                q["id"] = f"{exam_key}_{_slug(topic)}_{uuid.uuid4().hex[:6]}"
            q.setdefault("subject", subject)
            q.setdefault("topic", topic)
        return qs
    except Exception as e:
        logger.error("Practice bank LLM parse error for %s/%s: %s", exam_key, topic, e)
        return []


def _seed_from_general_bank(exam_key: str, subject: str, topic: str) -> list[dict]:
    """Pull topic-matching questions from the general exam question bank as fallback."""
    path = GENERAL_BANKS_DIR / f"{exam_key}.json"
    if not path.exists():
        return []
    try:
        all_qs = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(all_qs, list):
            all_qs = all_qs.get("questions", [])
        matched = [
            q for q in all_qs
            if q.get("topic", "").lower() == topic.lower()
            or q.get("subject", "").lower() == subject.lower()
        ]
        return matched
    except Exception:
        return []


class PracticeBankManager:
    """Manages 200Q circular buffers for topic-specific practice."""

    def get_questions(
        self,
        exam_key: str,
        subject: str,
        topic: str,
        count: int = 20,
    ) -> list[dict]:
        """
        Return `count` questions for a practice session on this topic.
        Strategy:
          1. Always try LLM first for `LLM_PER_SESSION` fresh questions.
          2. Append them to the circular buffer.
          3. Sample `count` from the full buffer (LLM + existing).
          4. If LLM fails, fall back to general bank + existing buffer.
        """
        path = _bank_path(exam_key, topic)

        # Generate fresh LLM questions and append to buffer
        llm_qs = _generate_topic_questions(exam_key, subject, topic, LLM_PER_SESSION)
        if llm_qs:
            self._append(path, exam_key, topic, llm_qs)
        else:
            logger.warning("Practice bank: LLM unavailable for %s/%s — using existing bank", exam_key, topic)
            # Seed from general bank if topic bank is empty
            if not path.exists() or not _read_bank(path):
                seed = _seed_from_general_bank(exam_key, subject, topic)
                if seed:
                    self._append(path, exam_key, topic, seed)

        bank = _read_bank(path)
        if not bank:
            logger.error("Practice bank: no questions available for %s/%s", exam_key, topic)
            return []

        # Shuffle and return requested count
        sample = random.sample(bank, min(count, len(bank)))
        return [self._to_serving_format(q, subject, topic) for q in sample]

    def _append(self, path: Path, exam_key: str, topic: str, new_qs: list[dict]) -> None:
        """Thread-safe circular buffer append — evicts oldest EVICT_BATCH when full."""
        validated, _ = filter_questions(new_qs, source=f"practice/{exam_key}/{topic}")
        if not validated:
            return

        with _lock:
            bank = _read_bank(path)

            # Deduplicate against existing
            known = {q.get("question_text", "").strip().lower()[:120] for q in bank}
            to_add = []
            for q in validated:
                key = q.get("question_text", "").strip().lower()[:120]
                if key and key not in known:
                    to_add.append(q)
                    known.add(key)

            if not to_add:
                return

            # Evict oldest batch if buffer would exceed max
            if len(bank) + len(to_add) > BUFFER_MAX:
                evict = max(EVICT_BATCH, len(bank) + len(to_add) - BUFFER_MAX)
                bank = bank[evict:]  # oldest are at the front

            bank.extend(to_add)
            _write_bank(path, bank)
            logger.info(
                "Practice bank %s/%s: +%d questions → %d total",
                exam_key, topic, len(to_add), len(bank),
            )

    def _to_serving_format(self, q: dict, subject: str, topic: str) -> dict:
        text = q.get("question_text", "")
        expl = q.get("explanation", "")
        return {
            "question_id": q.get("id", str(uuid.uuid4())),
            "subject": q.get("subject", subject),
            "topic": q.get("topic", topic),
            "difficulty": q.get("difficulty", 1),
            "question_text_en": text,
            "question_text_hi": text,
            "options": q.get("options", []),
            "correct_index": q.get("correct_index", 0),
            "explanation_en": expl,
            "explanation_hi": expl,
        }

    def bank_stats(self, exam_key: str) -> dict:
        """Return per-topic bank sizes for an exam. Used by admin/debug endpoints."""
        exam_dir = BANKS_DIR / exam_key
        if not exam_dir.exists():
            return {}
        stats = {}
        for f in sorted(exam_dir.glob("*.json")):
            try:
                qs = json.loads(f.read_text())
                stats[f.stem] = len(qs)
            except Exception:
                stats[f.stem] = 0
        return stats

    def seed_all_from_general_bank(self, exam_key: str, syllabus: dict) -> int:
        """
        One-time seeding: distribute existing general bank questions into topic banks.
        Called by admin or on first setup. Returns total questions distributed.
        """
        path = GENERAL_BANKS_DIR / f"{exam_key}.json"
        if not path.exists():
            return 0
        try:
            all_qs = json.loads(path.read_text())
            if not isinstance(all_qs, list):
                all_qs = all_qs.get("questions", [])
        except Exception:
            return 0

        # Index by topic
        by_topic: dict[str, tuple[str, list[dict]]] = {}
        for subj in syllabus.get("subjects", []):
            subj_name = subj["name"]
            for topic_obj in subj.get("topics", []):
                t_name = topic_obj["name"]
                by_topic[t_name.lower()] = (subj_name, [])

        for q in all_qs:
            t = q.get("topic", "").lower()
            if t in by_topic:
                by_topic[t][1].append(q)

        total = 0
        for t_lower, (subj_name, qs) in by_topic.items():
            if not qs:
                continue
            # Find original topic name
            orig_topic = next(
                (t for t in (
                    topic_obj["name"]
                    for s in syllabus.get("subjects", [])
                    for topic_obj in s.get("topics", [])
                ) if t.lower() == t_lower),
                t_lower,
            )
            bank_p = _bank_path(exam_key, orig_topic)
            self._append(bank_p, exam_key, orig_topic, qs)
            total += len(qs)

        logger.info("Practice bank seed: %d questions distributed across topics for %s", total, exam_key)
        return total


# Module-level singleton
_manager: PracticeBankManager | None = None


def get_practice_bank() -> PracticeBankManager:
    global _manager
    if _manager is None:
        _manager = PracticeBankManager()
    return _manager
