"""
Nightly notes generation script — Dabbu generates topic notes for NAGA approval.

Run manually:   python scripts/notes_generation.py [exam_key ...]
Run as cron:    0 2 * * * cd /path/to/vidyabot && python scripts/notes_generation.py

For each exam → subject → topic:
  1. Generate markdown notes via LLM (basics → exam level)
  2. Save to data/notes/{exam}/{subject_slug}/{topic_slug}.md  (status = pending)
  3. Write sidecar  data/notes/{exam}/{subject_slug}/{topic_slug}.meta.json
  4. Notify NAGA via Dabbu so the note appears in the Approvals tab

Notes are NOT visible to students until NAGA approves them.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.base import call_gemini
from agents.exam_utils import load_syllabus
from agents.dabbu_agent import get_dabbu

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

NOTES_DIR = Path("data/notes")
NOTES_DIR.mkdir(parents=True, exist_ok=True)

SYSTEM_PROMPT = """You are an expert tutor for Indian competitive exams.
Generate thorough, exam-focused study notes in Markdown for the given topic.

Structure (use these exact headings):
## Overview
(2-3 lines: what this topic is and why it matters for the exam)

## Key Concepts
(bullet points covering all core ideas; include definitions, formulas, important values)

## Formulas & Rules
(numbered list; each formula on its own line with a brief explanation)

## Solved Examples
(exactly 2 worked examples with step-by-step solutions; use real numbers)

## Common Mistakes
(bullet list of errors students make in exams, with the correct approach)

## Memory Tricks
(mnemonics, shortcuts, visual patterns, or analogies that help retention)

## Exam-Level Practice Questions
(3 MCQs at increasing difficulty with correct answer marked — no explanation here, just Q+options+answer)

Rules:
- Be specific: include actual formulas, dates, values, names — not vague descriptions
- Exam level: questions must match real RRB NTPC / NDA / JEE / NEET difficulty
- Length: 600-1200 words — comprehensive but not padded
- No placeholder text; if you cannot write accurate notes, say so explicitly"""


def _slug(text: str) -> str:
    return text.lower().replace(" ", "_").replace("&", "and").replace("/", "_")[:40]


def _note_paths(exam: str, subject: str, topic: str) -> tuple[Path, Path]:
    """Return (note_path, meta_path)."""
    subj_dir = NOTES_DIR / exam / _slug(subject)
    subj_dir.mkdir(parents=True, exist_ok=True)
    base = subj_dir / _slug(topic)
    return base.with_suffix(".md"), base.with_suffix(".meta.json")


def _read_meta(meta_path: Path) -> dict:
    if not meta_path.exists():
        return {}
    try:
        return json.loads(meta_path.read_text())
    except Exception:
        return {}


def _write_meta(meta_path: Path, meta: dict) -> None:
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False))


def generate_topic_notes(exam: str, subject: str, topic: str, subtopics: list[str]) -> str | None:
    """Call LLM to generate notes for one topic. Returns markdown string or None on failure."""
    subtopic_str = ", ".join(subtopics[:12]) if subtopics else "all subtopics"
    prompt = (
        f"Exam: {exam.upper().replace('_', ' ')}\n"
        f"Subject: {subject}\n"
        f"Topic: {topic}\n"
        f"Subtopics to cover: {subtopic_str}\n\n"
        f"Generate complete study notes for '{topic}' as described in the system prompt.\n"
        f"Target audience: students preparing for {exam.upper().replace('_', ' ')} exam.\n"
        f"Cover the topic from basics to exam-level difficulty."
    )
    raw = call_gemini(prompt, SYSTEM_PROMPT, timeout=45.0)
    if not raw or len(raw.strip()) < 200:
        logger.warning("Notes generation: empty/short response for %s/%s/%s", exam, subject, topic)
        return None
    return raw.strip()


def process_topic(exam: str, subject: str, topic: str, subtopics: list[str], force: bool = False) -> str:
    """
    Generate + save notes for one topic. Returns status: 'generated', 'skipped', 'failed'.
    Skips if an approved note already exists (unless force=True).
    """
    note_path, meta_path = _note_paths(exam, subject, topic)
    meta = _read_meta(meta_path)

    # Skip already-approved notes unless forced
    if not force and meta.get("status") == "approved":
        logger.info("Notes: skipping %s/%s/%s (already approved)", exam, subject, topic)
        return "skipped"

    notes = generate_topic_notes(exam, subject, topic, subtopics)
    if not notes:
        return "failed"

    # Save note with pending status
    note_path.write_text(notes, encoding="utf-8")
    _write_meta(meta_path, {
        "exam": exam,
        "subject": subject,
        "topic": topic,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
        "approved_at": None,
        "rejected_at": None,
        "naga_note": "",
        "note_path": str(note_path),
    })

    # Notify NAGA via Dabbu
    preview = notes[:300].replace("\n", " ")
    get_dabbu().submit_note_for_approval(
        exam=exam,
        subject=subject,
        topic=topic,
        note_path=str(note_path),
        preview=preview,
    )

    logger.info("Notes: generated %s/%s/%s → %s", exam, subject, topic, note_path)
    return "generated"


def run_exam(exam: str, force: bool = False) -> dict:
    """Generate notes for all topics in an exam. Returns {generated, skipped, failed}."""
    syllabus = load_syllabus(exam)
    if not syllabus.get("subjects"):
        logger.warning("Notes: no syllabus found for %s", exam)
        return {"generated": 0, "skipped": 0, "failed": 0}

    counts = {"generated": 0, "skipped": 0, "failed": 0}
    for subj in syllabus["subjects"]:
        subject = subj["name"]
        for topic_obj in subj.get("topics", []):
            topic = topic_obj["name"]
            subtopics = [
                s if isinstance(s, str) else s.get("name", "")
                for s in topic_obj.get("subtopics", [])
            ]
            status = process_topic(exam, subject, topic, subtopics, force=force)
            counts[status] += 1
            # Polite delay between LLM calls to avoid rate-limiting
            if status == "generated":
                time.sleep(2)

    logger.info(
        "Notes: %s done — generated=%d skipped=%d failed=%d",
        exam, counts["generated"], counts["skipped"], counts["failed"],
    )
    return counts


def approve_note(exam: str, subject: str, topic: str, naga_note: str = "") -> bool:
    """NAGA approves a note — updates meta status to 'approved'."""
    _, meta_path = _note_paths(exam, subject, topic)
    meta = _read_meta(meta_path)
    if not meta:
        return False
    meta["status"] = "approved"
    meta["approved_at"] = datetime.utcnow().isoformat()
    meta["naga_note"] = naga_note
    _write_meta(meta_path, meta)
    logger.info("Notes: approved %s/%s/%s", exam, subject, topic)
    return True


def reject_note(exam: str, subject: str, topic: str, reason: str = "") -> bool:
    """NAGA rejects a note — marks it rejected so it gets regenerated next run."""
    _, meta_path = _note_paths(exam, subject, topic)
    meta = _read_meta(meta_path)
    if not meta:
        return False
    meta["status"] = "rejected"
    meta["rejected_at"] = datetime.utcnow().isoformat()
    meta["naga_note"] = reason
    _write_meta(meta_path, meta)
    return True


def list_pending_notes() -> list[dict]:
    """Return all notes with status=pending across all exams."""
    pending = []
    for meta_path in sorted(NOTES_DIR.rglob("*.meta.json")):
        meta = _read_meta(meta_path)
        if meta.get("status") == "pending":
            note_path = Path(meta.get("note_path", ""))
            preview = ""
            if note_path.exists():
                try:
                    preview = note_path.read_text(encoding="utf-8")[:400]
                except Exception:
                    pass
            pending.append({**meta, "preview": preview})
    return pending


def get_note_content(exam: str, subject: str, topic: str) -> str | None:
    """Return note markdown if it exists and is approved."""
    note_path, meta_path = _note_paths(exam, subject, topic)
    meta = _read_meta(meta_path)
    if not note_path.exists():
        return None
    if meta.get("status") != "approved":
        return None
    try:
        return note_path.read_text(encoding="utf-8")
    except Exception:
        return None


if __name__ == "__main__":
    exams = sys.argv[1:] or ["rrb_ntpc", "nda", "jee", "neet"]
    force = "--force" in exams
    exams = [e for e in exams if e != "--force"]

    total = {"generated": 0, "skipped": 0, "failed": 0}
    for exam in exams:
        logger.info("=== Generating notes for %s ===", exam)
        result = run_exam(exam, force=force)
        for k in total:
            total[k] += result[k]

    print(f"\nDone: {total['generated']} generated, {total['skipped']} skipped, {total['failed']} failed")
    print("NAGA has been notified for each pending note.")
