"""
Mock paper generator — creates full exam-pattern papers via LLM.

Bank layout (no question count limit — unlike practice banks):
  data/mock_banks/{exam_key}/current_paper.json   ← live paper (students take this)
  data/mock_banks/{exam_key}/archive/YYYY-MM-DD.json  ← weekly archive

Strategy:
  1. Generate section-by-section via LLM (validate each question with 9-check guard)
  2. Save as current_paper.json + archive copy
  3. If LLM unavailable or fails, fall back to current_paper.json (previous week's paper)
  4. Called by MockScheduler 1 hour before Saturday's mock test slot
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from agents.base import call_gemini
from models.mock_test import (
    DIFFICULTY_DISTRIBUTION, EXAM_CONFIGS, MockPaper, MockQuestion,
)

logger = logging.getLogger(__name__)

MOCK_BANK_DIR = Path("data/mock_banks")
MOCK_BANK_DIR.mkdir(parents=True, exist_ok=True)

# Minimum questions that must pass validation to accept a section
_MIN_VALID_RATIO = 0.80

# ── Prompt builder ─────────────────────────────────────────────────────────────

def _build_section_prompt(
    exam_name: str,
    section_name: str,
    topics: list[str],
    total: int,
    easy: int,
    medium: int,
    hard: int,
    negative_marking: float,
    marks_per_q: float,
) -> str:
    return f"""You are an expert question setter for {exam_name} (Indian competitive exam).

Generate exactly {total} MCQ questions for the section "{section_name}".
Topics to cover: {', '.join(topics)}.

Difficulty split: {easy} Easy, {medium} Medium, {hard} Hard.
- Easy: direct recall or single-step; a prepared student answers in <30s
- Medium: 2-step application; takes 60-90s
- Hard: multi-step, tricky, or computation-heavy; takes 90-120s

Each correct answer: +{marks_per_q} marks. Each wrong: -{negative_marking:.3f} marks. Unattempted: 0.

Return ONLY valid JSON — an array of exactly {total} objects, no markdown, no prose:
[
  {{
    "section": "{section_name}",
    "topic": "<specific topic from the list>",
    "difficulty": "<easy|medium|hard>",
    "question_text_en": "<clear, unambiguous question>",
    "options": ["<option A>", "<option B>", "<option C>", "<option D>"],
    "correct_index": <0-3>,
    "explanation_en": "<concise explanation of why the answer is correct>"
  }},
  ...
]

Rules:
- All four options must be plausible and distinct (no obviously wrong distractors)
- Options must not give away the answer (avoid "all of the above" / "none of the above")
- Questions must be self-contained (no "refer to passage" or image references)
- Vary topics across the {total} questions — don't repeat the same topic back-to-back
- Difficulty must match: {easy} easy, {medium} medium, {hard} hard (in any order)
- Numbers and formulas must be correct
"""


# ── Validation ─────────────────────────────────────────────────────────────────

def _validate_question(q: dict) -> bool:
    """9-check guard adapted for mock questions."""
    try:
        text = q.get("question_text_en", "")
        options = q.get("options", [])
        correct = q.get("correct_index", -1)
        explanation = q.get("explanation_en", "")
        difficulty = q.get("difficulty", "")

        if len(text.strip()) < 15:                          return False  # too short
        if len(options) != 4:                               return False  # must have 4 options
        if not all(len(str(o).strip()) >= 1 for o in options): return False  # empty options
        if len(set(str(o).strip().lower() for o in options)) < 3: return False  # duplicate options
        if correct not in (0, 1, 2, 3):                    return False  # invalid index
        if len(explanation.strip()) < 10:                   return False  # no explanation
        if difficulty not in ("easy", "medium", "hard"):    return False  # invalid difficulty
        if q.get("section", ""):
            pass
        if "image" in text.lower() or "figure" in text.lower() or "diagram" in text.lower():
            return False  # image-dependent
        if len(text) > 800:                                 return False  # too long
        return True
    except Exception:
        return False


def _parse_questions(raw: str, section: str, negative_marks: float, marks: float) -> list[dict]:
    """Parse LLM response into a list of validated question dicts."""
    raw = raw.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw.strip())

    # Find JSON array
    start = raw.find("[")
    end = raw.rfind("]") + 1
    if start == -1 or end == 0:
        logger.warning("MockGen: no JSON array found in LLM response")
        return []

    try:
        items = json.loads(raw[start:end])
    except json.JSONDecodeError as e:
        logger.warning("MockGen: JSON parse error — %s", e)
        return []

    valid = []
    for item in items:
        if not isinstance(item, dict):
            continue
        item.setdefault("section", section)
        item["negative_marks"] = negative_marks
        item["marks"] = marks
        item["question_id"] = f"mock-{section[:4].lower()}-{str(uuid.uuid4())[:8]}"
        if _validate_question(item):
            valid.append(item)
        else:
            logger.debug("MockGen: question failed validation — '%s'", str(item)[:60])

    return valid


# ── Section generator ──────────────────────────────────────────────────────────

def _generate_section(
    exam_name: str,
    section_cfg: dict,
    negative_marking: float,
    marks_per_q: float,
    max_retries: int = 3,
) -> list[dict]:
    section_name = section_cfg["name"]
    topics = section_cfg["topics"]
    target = section_cfg["count"]

    easy   = max(1, round(target * DIFFICULTY_DISTRIBUTION["easy"]))
    hard   = max(1, round(target * DIFFICULTY_DISTRIBUTION["hard"]))
    medium = target - easy - hard

    prompt = _build_section_prompt(
        exam_name=exam_name,
        section_name=section_name,
        topics=topics,
        total=target,
        easy=easy,
        medium=medium,
        hard=hard,
        negative_marking=negative_marking,
        marks_per_q=marks_per_q,
    )

    for attempt in range(1, max_retries + 1):
        logger.info("MockGen: generating '%s' — %dQ (attempt %d/%d)", section_name, target, attempt, max_retries)
        raw = call_gemini(prompt, system="You are a precise JSON API. Return only valid JSON, no commentary.")
        if not raw:
            logger.warning("MockGen: LLM returned empty for section '%s'", section_name)
            time.sleep(2)
            continue

        questions = _parse_questions(raw, section_name, negative_marking, marks_per_q)
        ratio = len(questions) / target

        if ratio >= _MIN_VALID_RATIO:
            # Trim or mark if we got slightly more/fewer
            questions = questions[:target]
            logger.info("MockGen: '%s' — %d/%d valid questions", section_name, len(questions), target)
            return questions

        logger.warning(
            "MockGen: '%s' — only %d/%d valid (%.0f%%), retrying",
            section_name, len(questions), target, ratio * 100,
        )
        time.sleep(3)

    logger.error("MockGen: failed to generate enough questions for '%s' after %d attempts", section_name, max_retries)
    return []


# ── Bank helpers ───────────────────────────────────────────────────────────────

def _bank_dir(exam_key: str) -> Path:
    p = MOCK_BANK_DIR / exam_key
    p.mkdir(parents=True, exist_ok=True)
    return p


def _current_paper_path(exam_key: str) -> Path:
    return _bank_dir(exam_key) / "current_paper.json"


def _archive_path(exam_key: str, scheduled_date: str) -> Path:
    archive = _bank_dir(exam_key) / "archive"
    archive.mkdir(parents=True, exist_ok=True)
    return archive / f"{scheduled_date}.json"


def load_current_paper(exam_key: str) -> Optional[MockPaper]:
    """Load the current (live) paper for an exam, or None if none exists."""
    path = _current_paper_path(exam_key)
    if not path.exists():
        return None
    try:
        return MockPaper.from_dict(json.loads(path.read_text()))
    except Exception as e:
        logger.error("MockGen: failed to load current paper for %s — %s", exam_key, e)
        return None


def paper_status(exam_key: str) -> dict:
    """Return metadata about the current paper without loading full questions."""
    path = _current_paper_path(exam_key)
    if not path.exists():
        return {"available": False, "exam_key": exam_key}
    try:
        data = json.loads(path.read_text())
        return {
            "available": True,
            "exam_key": exam_key,
            "paper_id": data.get("paper_id"),
            "scheduled_date": data.get("scheduled_date"),
            "generated_at": data.get("generated_at"),
            "total_questions": data.get("total_questions"),
            "duration_mins": data.get("duration_mins"),
            "generation_method": data.get("generation_method"),
            "section_names": [s["name"] for s in data.get("sections", [])],
        }
    except Exception:
        return {"available": False, "exam_key": exam_key}


def list_archive(exam_key: str) -> list[dict]:
    """List all archived papers for an exam (most recent first)."""
    archive_dir = _bank_dir(exam_key) / "archive"
    if not archive_dir.exists():
        return []
    papers = []
    for p in sorted(archive_dir.glob("*.json"), reverse=True):
        try:
            d = json.loads(p.read_text())
            papers.append({
                "paper_id": d.get("paper_id"),
                "scheduled_date": d.get("scheduled_date"),
                "generated_at": d.get("generated_at"),
                "total_questions": d.get("total_questions"),
                "generation_method": d.get("generation_method"),
            })
        except Exception:
            continue
    return papers


# ── Main generation entry point ────────────────────────────────────────────────

def generate_paper(exam_key: str, scheduled_date: Optional[str] = None) -> Optional[MockPaper]:
    """
    Generate a full exam paper via LLM and save it to the mock bank.
    Returns the MockPaper on success, None if generation failed completely.

    scheduled_date: ISO date string (defaults to next Saturday).
    If LLM fails for any section, falls back to the current archived paper.
    """
    config = EXAM_CONFIGS.get(exam_key)
    if not config:
        logger.error("MockGen: unknown exam key '%s'", exam_key)
        return None

    if not scheduled_date:
        today = date.today()
        days_to_saturday = (5 - today.weekday()) % 7 or 7
        scheduled_date = (today if today.weekday() == 5 else
                          __import__("datetime").date.today() +
                          __import__("datetime").timedelta(days=days_to_saturday)).isoformat()

    logger.info(
        "MockGen: starting paper generation for %s (%s), scheduled %s",
        config["name"], exam_key, scheduled_date,
    )

    sections_out = []
    failed_sections = []
    total_generated = 0

    for section_cfg in config["sections"]:
        questions = _generate_section(
            exam_name=config["name"],
            section_cfg=section_cfg,
            negative_marking=config["negative_marking"],
            marks_per_q=config["marks_per_question"],
        )
        if not questions:
            failed_sections.append(section_cfg["name"])
            continue

        sections_out.append({
            "name": section_cfg["name"],
            "count": len(questions),
            "questions": questions,
        })
        total_generated += len(questions)
        time.sleep(1)   # polite delay between sections

    if not sections_out:
        logger.error("MockGen: all sections failed for %s — using fallback if available", exam_key)
        fallback = load_current_paper(exam_key)
        if fallback:
            logger.info("MockGen: using fallback (previous paper %s)", fallback.paper_id)
            fallback.generation_method = "fallback_archive"
            return fallback
        return None

    if failed_sections:
        logger.warning("MockGen: sections %s failed — paper partial", failed_sections)

    # Difficulty distribution
    all_qs = [q for s in sections_out for q in s["questions"]]
    diff_counts: dict[str, int] = {"easy": 0, "medium": 0, "hard": 0}
    for q in all_qs:
        diff_counts[q.get("difficulty", "medium")] += 1

    paper = MockPaper(
        paper_id=f"{exam_key}-{scheduled_date}",
        exam_key=exam_key,
        exam_name=config["name"],
        generated_at=datetime.utcnow().isoformat(),
        scheduled_date=scheduled_date,
        total_questions=total_generated,
        duration_mins=config["duration_mins"],
        negative_marking=config["negative_marking"],
        marks_per_question=config["marks_per_question"],
        sections=sections_out,
        difficulty_distribution=diff_counts,
        generation_method="llm" if not failed_sections else "llm_partial",
    )

    # Save current paper
    paper_dict = paper.to_dict(include_answers=True)
    _current_paper_path(exam_key).write_text(
        json.dumps(paper_dict, ensure_ascii=False, indent=2)
    )

    # Archive
    _archive_path(exam_key, scheduled_date).write_text(
        json.dumps(paper_dict, ensure_ascii=False, indent=2)
    )

    logger.info(
        "MockGen: paper saved for %s — %d questions, date %s, difficulty %s",
        exam_key, total_generated, scheduled_date, diff_counts,
    )
    return paper
