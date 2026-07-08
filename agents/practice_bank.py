"""
Subtopic-specific practice bank — 200Q circular buffer per subtopic.

Layout: data/practice_banks/{exam_key}/{topic_slug}__{subtopic_slug}.json
        (topic-level banks stay at {topic_slug}.json when no subtopic given)
Each file is a plain JSON list, max 200 questions.
When the buffer is full, the oldest 20 are evicted before appending new ones.

Usage:
  mgr = PracticeBankManager()
  questions = mgr.get_questions(exam_key, subject, topic, subtopic, count=10)
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


def _bank_path(exam_key: str, topic: str, subtopic: str = "") -> Path:
    exam_dir = BANKS_DIR / exam_key
    exam_dir.mkdir(parents=True, exist_ok=True)
    if subtopic and _slug(subtopic) != _slug(topic):
        return exam_dir / f"{_slug(topic)}__{_slug(subtopic)}.json"
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
    exam_key: str, subject: str, topic: str, count: int, subtopic: str = ""
) -> list[dict]:
    """Ask LLM for `count` MCQs on a specific subtopic (or topic if none given)."""
    focus = subtopic or topic
    scope = f"{topic} → {subtopic}" if subtopic else topic
    prompt = (
        f"Exam: {exam_key.upper().replace('_', ' ')}\n"
        f"Subject: {subject}\n"
        f"Topic: {topic}\n"
        + (f"Subtopic: {subtopic}\n" if subtopic else "")
        + f"\nGenerate exactly {count} MCQs for practice. IMPORTANT:\n"
        f"- ALL questions must be strictly about '{focus}' — no other topics.\n"
        f"- Cover ALL major question types that appear for '{focus}' in the exam.\n"
        f"- For math topics, include: formula application, word problems, reverse calculations.\n"
        f"- Mix difficulty: at least 4 easy, 8 medium, 8 hard.\n"
        f"- Questions must be specific — include numbers, formulas where relevant.\n"
        f"- Do NOT write vague questions like 'Which is a concept of {focus}'.\n"
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
                q["id"] = f"{exam_key}_{_slug(focus)}_{uuid.uuid4().hex[:6]}"
            q.setdefault("subject", subject)
            q.setdefault("topic", topic)
            if subtopic:
                q.setdefault("subtopic", subtopic)
        return qs
    except Exception as e:
        logger.error("Practice bank LLM parse error for %s/%s: %s", exam_key, scope, e)
        return []


def _norm(s: str) -> str:
    """Lowercase, strip punctuation/spaces for fuzzy matching."""
    return "".join(c for c in s.lower() if c.isalnum())


def _load_general_bank(exam_key: str) -> list[dict]:
    path = GENERAL_BANKS_DIR / f"{exam_key}.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else data.get("questions", [])
    except Exception:
        return []


def _seed_topic_only(exam_key: str, topic: str) -> list[dict]:
    """Topic-specific questions from the general bank (exact/fuzzy topic match).
    These are safe to persist into the topic bank because they genuinely belong."""
    all_qs = _load_general_bank(exam_key)
    if not all_qs:
        return []
    topic_norm = _norm(topic)
    return [
        q for q in all_qs
        if _norm(q.get("topic", "")) and (
            _norm(q.get("topic", "")) == topic_norm
            or topic_norm in _norm(q.get("topic", ""))
            or _norm(q.get("topic", "")) in topic_norm
        )
    ]


def _seed_from_general_bank(exam_key: str, subject: str, topic: str) -> list[dict]:
    """Guaranteed question source from the general exam bank, most-specific first.
    Free-tier LLMs are frequently rate-limited (HTTP 429), so this must be able to
    serve every topic on its own — it never returns empty if the bank has anything.

    Tiers (topic questions always come first, then top up):
      1. Exact/fuzzy topic match — directly relevant.
      2. Same-subject questions — on-subject when the topic isn't catalogued
         (e.g. 'Fractions' typed in the AI Tutor, which lives under Mathematics).
      3. Whole exam bank — last resort so practice is never blank."""
    all_qs = _load_general_bank(exam_key)
    if not all_qs:
        return []
    topic_norm = _norm(topic)
    subj_norm = _norm(subject)

    def _dedup_extend(dst: list[dict], src: list[dict], seen: set) -> None:
        for q in src:
            key = _norm(q.get("question_text", ""))[:80]
            if key and key not in seen:
                seen.add(key)
                dst.append(q)

    seen: set[str] = set()
    result: list[dict] = []

    # Tier 1 — topic match
    topic_matched = [
        q for q in all_qs
        if _norm(q.get("topic", "")) and (
            _norm(q.get("topic", "")) == topic_norm
            or topic_norm in _norm(q.get("topic", ""))
            or _norm(q.get("topic", "")) in topic_norm
        )
    ]
    _dedup_extend(result, topic_matched, seen)

    # Tier 2 — same-subject top-up (only if topic matches are sparse)
    if len(result) < 10 and subj_norm and subj_norm != "general":
        subject_matched = [
            q for q in all_qs
            if _norm(q.get("subject", "")) == subj_norm
            or (subj_norm in _norm(q.get("subject", "")) and _norm(q.get("subject", "")))
        ]
        _dedup_extend(result, subject_matched, seen)

    # Tier 3 — whole exam bank so we never return empty
    if len(result) < 10:
        _dedup_extend(result, all_qs, seen)

    return result


class PracticeBankManager:
    """Manages 200Q circular buffers for topic-specific practice."""

    def get_questions(
        self,
        exam_key: str,
        subject: str,
        topic: str,
        subtopic: str = "",
        count: int = 10,
        difficulty: str = "adaptive",
        exclude_ids: Optional[set[str]] = None,
    ) -> list[dict]:
        """
        Return `count` questions instantly from the subtopic bank.
        LLM enrichment runs in a background thread to grow the bank for future sessions.

        Strategy (LLM is NEVER on the critical path — it's frequently rate-limited):
          1. Serve from the subtopic bank if it already has questions (<100ms).
          2. Else seed parent-topic questions from the general bank → persist.
          3. Else top up from same-subject questions in the general bank directly.
          4. Always fire background LLM enrichment to grow the subtopic bank.

        `exclude_ids` — question_ids already shown this session (pagination), skipped.
        """
        exclude_ids = exclude_ids or set()

        # Resolve free-text topic/subtopic against the syllabus. 'Fractions' →
        # subject 'Mathematics', canonical parent topic 'Number System'. We key the
        # bank on the student's ORIGINAL topic+subtopic (so the bank fills with
        # subtopic-specific questions over time) but seed from the parent topic's
        # catalogued general-bank questions (general bank has no subtopic tags).
        from agents.exam_utils import resolve_topic
        lookup = subtopic or topic
        resolved_subject, canonical_topic = resolve_topic(exam_key, lookup)
        if resolved_subject:
            subject = resolved_subject
        elif not subject or subject.lower() == "general":
            subject = "General"
        seed_topic = canonical_topic or topic

        path = _bank_path(exam_key, topic, subtopic)
        bank = _read_bank(path)

        # If subtopic bank empty, seed parent-topic questions and persist them
        if not bank:
            topic_seed = _seed_topic_only(exam_key, seed_topic)
            if topic_seed:
                self._append(path, exam_key, topic, topic_seed)
                bank = _read_bank(path)

        # Always enrich in the background — grows the subtopic bank when the LLM
        # is up, no-op when rate-limited. Never blocks the student.
        def _enrich():
            qs = _generate_topic_questions(exam_key, subject, topic, LLM_PER_SESSION, subtopic=subtopic)
            if qs:
                self._append(path, exam_key, topic, qs)
                logger.info("Practice bank enriched: +%d for %s/%s", len(qs), exam_key, _slug(subtopic or topic))
        threading.Thread(target=_enrich, daemon=True, name=f"practice-{_slug(subtopic or topic)}").start()

        # Top up from the general bank when the bank is thin (few catalogued
        # questions + LLM rate-limited). Served directly, not persisted.
        if len(bank) < count + len(exclude_ids):
            fallback = _seed_from_general_bank(exam_key, subject, seed_topic)
            seen = {_norm(q.get("question_text", "") or q.get("question_text_en", ""))[:80] for q in bank}
            for q in fallback:
                key = _norm(q.get("question_text", ""))[:80]
                if key and key not in seen:
                    seen.add(key)
                    bank.append(q)

        if not bank:
            logger.error("Practice bank: no questions for %s/%s/%s", exam_key, topic, subtopic)
            return []

        # Drop questions already seen this session (pagination)
        if exclude_ids:
            bank = [q for q in bank if q.get("id", "") not in exclude_ids]
            if not bank:
                return []

        # Apply difficulty filter — fall back to full bank if too few match
        if difficulty != "adaptive":
            diff_map = {"easy": 1, "medium": 2, "hard": 3}
            diff_val = diff_map.get(difficulty, 0)
            filtered = [q for q in bank if q.get("difficulty") == diff_val]
            pool = filtered if len(filtered) >= max(1, count // 2) else bank
        else:
            pool = bank

        sample = random.sample(pool, min(count, len(pool)))
        return [self._to_serving_format(q, subject, topic, subtopic) for q in sample]

    def add_questions(
        self, exam_key: str, subject: str, topic: str, subtopic: str, questions: list[dict]
    ) -> int:
        """Persist NAGA-provided questions into the subtopic bank. Returns count added.
        Stamps ids + subject/topic/subtopic so they serve and dedupe correctly.
        NAGA is a trusted human source, so these skip the aggressive length
        guard-rail that (over-)filters LLM output — only structurally-invalid
        questions (missing text or not exactly 4 options) are dropped."""
        stamped = []
        for q in questions:
            q = dict(q)
            if not q.get("question_text") or len(q.get("options") or []) != 4:
                continue
            if not q.get("id"):
                q["id"] = f"{exam_key}_{_slug(subtopic or topic)}_{uuid.uuid4().hex[:6]}"
            q.setdefault("subject", subject)
            q.setdefault("topic", topic)
            if subtopic:
                q.setdefault("subtopic", subtopic)
            stamped.append(q)
        path = _bank_path(exam_key, topic, subtopic)
        before = len(_read_bank(path))
        self._append(path, exam_key, subtopic or topic, stamped, trusted=True)
        return len(_read_bank(path)) - before

    def _append(self, path: Path, exam_key: str, topic: str, new_qs: list[dict],
                trusted: bool = False) -> None:
        """Thread-safe circular buffer append — evicts oldest EVICT_BATCH when full.
        trusted=True skips the LLM guard-rail (used for human-authored NAGA content)."""
        if trusted:
            validated = [q for q in new_qs if q.get("question_text") and len(q.get("options") or []) == 4]
        else:
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

    def _to_serving_format(self, q: dict, subject: str, topic: str, subtopic: str = "") -> dict:
        text = q.get("question_text", "")
        expl = q.get("explanation", "")
        return {
            "question_id": q.get("id", str(uuid.uuid4())),
            "subject": q.get("subject", subject),
            "topic": q.get("topic", topic),
            "subtopic": q.get("subtopic", subtopic),
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
