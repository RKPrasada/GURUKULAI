import json
import logging
import random
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from agents.base import call_gemini
from agents.question_validator import filter_questions
from agents.exam_utils import compact_syllabus, exam_name, exam_value, load_syllabus
from models.student import StudentProfile, WeaknessMap, get_available_exams
from models.ui_schema import CardType, tag

_QUESTION_BANK_DIR = Path(__file__).parent.parent / "data" / "question_banks"
_LLM_TIMEOUT = 20.0       # seconds per model attempt for diagnostic batches
_LLM_NEW_QUESTIONS = 20   # fresh LLM questions per session; rest come from question bank
_BANK_TARGET = 1000       # circular buffer cap — oldest questions evicted when full
_BANK_EVICT = 50          # evict this many oldest questions when bank hits _BANK_TARGET
_bank_lock = threading.Lock()  # one writer at a time per process

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert MCQ writer for Indian competitive exams.
Write realistic, knowledge-testing questions — NOT vague or generic ones.
Each question must have exactly 4 options and 1 correct answer.
Do NOT write questions like 'Which is a key concept of X' — write specific factual/numerical questions.
Return ONLY valid JSON (no markdown fences): {"questions": [...]}
Each question object:
{
  "subject": "Mathematics",
  "topic": "Number System",
  "difficulty": 1,
  "question_text": "What is the LCM of 12 and 18?",
  "options": ["24", "36", "48", "72"],
  "correct_index": 1,
  "explanation": "LCM(12,18) = 36 because ..."
}
difficulty: 1=easy, 2=medium, 3=hard. Mix all three."""


def _subjects_for_exam(exam_key: str) -> list[dict]:
    """Return list of {subject, topics, count} for parallel generation."""
    syllabus = load_syllabus(exam_key)
    subjects = syllabus.get("subjects", [])
    total_q = syllabus.get("total_questions", 100)
    total_weight = sum(s.get("weight", 1) for s in subjects)
    result = []
    for s in subjects:
        weight = s.get("weight", 1)
        count = max(1, round(total_q * weight / total_weight))
        topics = [t.get("name", "") for t in s.get("topics", [])]
        result.append({
            "subject": s.get("name", "General"),
            "topics": topics,
            "count": count,
        })
    # Normalise counts to total_q
    allocated = sum(r["count"] for r in result)
    if allocated != total_q and result:
        result[-1]["count"] += total_q - allocated
    return result


def _normalize_subject(s: str) -> str:
    """Lowercase, strip punctuation/spaces for fuzzy subject matching."""
    return "".join(c for c in s.lower() if c.isalnum())


def _load_from_question_bank(exam_key: str, subject: str, count: int) -> list[dict]:
    path = _QUESTION_BANK_DIR / f"{exam_key}.json"
    if not path.exists():
        return []
    try:
        all_qs = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(all_qs, list):
            all_qs = all_qs.get("questions", [])
        # Fuzzy subject match: strip punctuation/spaces for comparison
        # so "General Intelligence & Reasoning" == "General Intelligence and Reasoning"
        norm_target = _normalize_subject(subject)
        if norm_target:
            filtered = [
                q for q in all_qs
                if _normalize_subject(q.get("subject", "")) == norm_target
                or norm_target in _normalize_subject(q.get("subject", ""))
            ]
            pool = filtered if len(filtered) >= max(1, count // 2) else all_qs
        else:
            pool = all_qs  # empty subject = full bank fetch
        sampled = random.sample(pool, min(count, len(pool)))
        result = []
        for q in sampled:
            text = q.get("question_text", "")
            expl = q.get("explanation", "")
            result.append({
                "question_id": q.get("id", str(uuid.uuid4())),
                "subject": q.get("subject", subject),
                "topic": q.get("topic", "General"),
                "difficulty": 1,
                "question_text_en": text,
                "question_text_hi": text,
                "options": q.get("options", []),
                "correct_index": q.get("correct_index", 0),
                "explanation_en": expl,
                "explanation_hi": expl,
            })
        return result
    except Exception as e:
        logger.error(f"Failed to load question bank for {exam_key}/{subject}: {e}")
        return []


def _append_to_bank(exam_key: str, new_questions: list[dict]) -> int:
    """
    Persist LLM-generated questions to the circular bank. Returns new bank size.
    When the bank hits _BANK_TARGET, the oldest _BANK_EVICT questions are removed
    before appending — ensuring the bank always reflects the freshest questions.
    """
    if not new_questions:
        return 0
    path = _QUESTION_BANK_DIR / f"{exam_key}.json"
    with _bank_lock:
        existing: list[dict] = []
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                existing = data if isinstance(data, list) else data.get("questions", [])
            except Exception:
                existing = []

        # Guard-rail: reject placeholder / template / circular questions
        new_questions, _ = filter_questions(new_questions, source=f"LLM/{exam_key}")
        if not new_questions:
            return len(existing)

        # Deduplicate against existing bank
        known = {q.get("question_text", "").strip().lower()[:120] for q in existing}
        to_add = []
        for q in new_questions:
            key = q.get("question_text", "").strip().lower()[:120]
            if key and key not in known:
                to_add.append({
                    "id": q.get("id") or f"{exam_key}_{uuid.uuid4().hex[:8]}",
                    "subject": q.get("subject", ""),
                    "topic": q.get("topic", ""),
                    "difficulty": q.get("difficulty", 1),
                    "question_text": q.get("question_text") or q.get("question_text_en", ""),
                    "options": q.get("options", []),
                    "correct_index": q.get("correct_index", 0),
                    "explanation": q.get("explanation") or q.get("explanation_en", ""),
                })
                known.add(key)

        if not to_add:
            return len(existing)

        # Circular eviction: if adding would exceed _BANK_TARGET, evict oldest first
        if len(existing) + len(to_add) > _BANK_TARGET:
            evict = max(_BANK_EVICT, len(existing) + len(to_add) - _BANK_TARGET)
            existing = existing[evict:]
            logger.info(f"Bank {exam_key}: evicted {evict} oldest questions (circular refresh)")

        existing.extend(to_add)
        path.write_text(json.dumps(existing, indent=2, ensure_ascii=False))
        logger.info(f"Bank {exam_key}: +{len(to_add)} questions → {len(existing)} total")
        return len(existing)


def _generate_subject_batch(exam_key: str, exam_display: str, subject: str,
                            topics: list[str], total_count: int,
                            llm_count: int, stage: int) -> list[dict]:
    """Generate total_count questions: llm_count via LLM + rest from question bank."""
    bank_count = total_count - llm_count
    questions: list[dict] = []

    # --- LLM slice ---
    if llm_count > 0:
        topics_str = ", ".join(topics[:15]) if topics else subject
        stage_hint = {1: "broad concept", 2: "specific formula/rule", 3: "tricky edge-case"}[stage]
        prompt = (
            f"Exam: {exam_display} ({exam_key})\n"
            f"Subject: {subject}\n"
            f"Topics to cover: {topics_str}\n\n"
            f"Generate exactly {llm_count} {stage_hint} MCQs. "
            f"Spread questions across the topics listed. "
            f"Each question must be solvable in under 90 seconds. "
            f"Return ONLY valid JSON: {{\"questions\": [...]}}"
        )
        raw = call_gemini(prompt, SYSTEM_PROMPT, timeout=_LLM_TIMEOUT)
        if raw:
            clean = raw.strip()
            for fence in ("```json", "```"):
                if clean.startswith(fence):
                    clean = clean[len(fence):]
            if clean.endswith("```"):
                clean = clean[:-3]
            try:
                data = json.loads(clean.strip())
                raw_qs = data.get("questions", [])[:llm_count]
                # Stamp IDs before saving to bank
                for q in raw_qs:
                    if not q.get("id"):
                        q["id"] = f"{exam_key}_{uuid.uuid4().hex[:8]}"
                # Validate before serving — same guard-rail as the question bank
                raw_qs, rejected = filter_questions(raw_qs, source=f"LLM-serve/{exam_key}/{subject}")
                if rejected:
                    logger.warning(f"Filtered {len(rejected)} placeholder LLM questions for {subject}")
                questions = raw_qs
            except Exception as e:
                logger.error(f"Failed to parse LLM batch for {subject}: {e}")
        if not questions:
            logger.warning(f"LLM unavailable or all questions invalid for {subject}, filling all {total_count} from bank")
            return _load_from_question_bank(exam_key, subject, total_count)

        # Persist new LLM questions to circular bank (oldest evicted at _BANK_TARGET)
        _append_to_bank(exam_key, questions)

        # Convert LLM format → serving format
        serving = []
        for q in questions:
            text = q.get("question_text", "")
            expl = q.get("explanation", "")
            serving.append({
                "question_id": q.get("id", str(uuid.uuid4())),
                "subject": q.get("subject", subject),
                "topic": q.get("topic", "General"),
                "difficulty": q.get("difficulty", 1),
                "question_text_en": text,
                "question_text_hi": text,
                "options": q.get("options", []),
                "correct_index": q.get("correct_index", 0),
                "explanation_en": expl,
                "explanation_hi": expl,
            })
        questions = serving

    # --- Bank slice (fills the remaining quota) ---
    bank_questions = _load_from_question_bank(exam_key, subject, bank_count)
    questions.extend(bank_questions)

    random.shuffle(questions)
    return questions


class DiagnosticAgent:
    def __init__(self):
        self._sessions: dict[str, dict] = {}
        self._exams_cache = get_available_exams()

    def start_diagnostic(self, student: StudentProfile, paper_id: str = "p1") -> dict:
        session_id = str(uuid.uuid4())
        exam_key = exam_value(student.exam_target)
        stage = student.diagnostic_stage

        exam_config = self._exams_cache.get(exam_key)
        if not exam_config:
            return {"error": f"Exam {exam_key} not configured."}

        paper_config = next(
            (p for p in exam_config["papers"] if p["id"] == paper_id),
            exam_config["papers"][0]
        )
        question_count = paper_config.get("question_count", 100)
        duration_minutes = paper_config.get("duration_minutes", 90)
        exam_display = exam_config["name"]

        # Build per-subject batches and generate in parallel
        batches = _subjects_for_exam(exam_key)
        if not batches:
            batches = [{"subject": "General", "topics": [], "count": question_count}]

        # Scale counts to match question_count if syllabus total differs
        total_in_batches = sum(b["count"] for b in batches)
        if total_in_batches != question_count:
            scale = question_count / total_in_batches
            for b in batches:
                b["count"] = max(1, round(b["count"] * scale))
            batches[-1]["count"] += question_count - sum(b["count"] for b in batches)

        # Distribute LLM quota proportionally across subjects
        # e.g. 20 LLM questions split across Math/Reasoning/GK by their weight
        llm_total = min(_LLM_NEW_QUESTIONS, question_count)
        for b in batches:
            b["llm_count"] = max(0, round(llm_total * b["count"] / question_count))
        # Correct rounding drift on last batch
        batches[-1]["llm_count"] += llm_total - sum(b["llm_count"] for b in batches)

        # Always serve from the question bank — guaranteed <500ms response.
        # LLM enrichment runs in the background and deposits fresh questions for
        # future sessions. We never block the student on LLM calls.
        questions: list[dict] = []
        for b in batches:
            bank_q = _load_from_question_bank(exam_key, b["subject"], b["count"])
            questions.extend(bank_q)
            logger.info(f"Bank: {len(bank_q)}/{b['count']} for {b['subject']}")

        # Background thread: enrich bank for future sessions (never blocks the response)
        def _enrich_bank_async():
            with ThreadPoolExecutor(max_workers=len(batches)) as pool:
                futures = {
                    pool.submit(
                        _generate_subject_batch,
                        exam_key, exam_display, b["subject"], b["topics"],
                        b["llm_count"], b["llm_count"], stage
                    ): b["subject"]
                    for b in batches if b.get("llm_count", 0) > 0
                }
                for future in as_completed(futures):
                    subject = futures[future]
                    try:
                        future.result()
                        logger.info(f"Bank enriched asynchronously for {subject}")
                    except Exception as e:
                        logger.warning(f"Async bank enrichment failed for {subject}: {e}")

        threading.Thread(target=_enrich_bank_async, daemon=True, name="diag-enrich").start()

        # Deduplicate across all subject batches (LLM sometimes repeats questions,
        # and bank sampling is independent per subject so the same question can appear twice)
        seen: set[str] = set()
        unique: list[dict] = []
        for q in questions:
            key = (q.get("question_text_en") or "").strip().lower()[:120]
            if key and key not in seen:
                seen.add(key)
                unique.append(q)
        questions = unique

        # Pad if dedup left us short — pull extras from the full bank across all subjects
        if len(questions) < question_count:
            extras = _load_from_question_bank(exam_key, "", question_count * 2)
            for q in extras:
                key = (q.get("question_text_en") or "").strip().lower()[:120]
                if key and key not in seen:
                    seen.add(key)
                    questions.append(q)
                    if len(questions) >= question_count:
                        break
            logger.info(f"Bank served {len(questions)}/{question_count} for {exam_key}")

        if not questions:
            return {"error": "Could not generate questions. Please try again."}

        self._sessions[session_id] = {
            "student_id": student.student_id,
            "questions": questions,
            "stage": stage,
        }

        return tag({
            "session_id": session_id,
            "questions": questions,
            "total": len(questions),
            "duration_minutes": duration_minutes,
            "stage": stage,
            "exam_name": exam_display,
        }, CardType.DIAGNOSTIC)

    def submit_answers(self, student: StudentProfile, session_id: str, answers: list[int]) -> dict:
        session = self._sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}

        questions = session["questions"]
        stage = session["stage"]

        # Score per topic — keep full topic granularity, no aggregation to subject level.
        # With 100 questions and ~30 topics, each topic gets 3-4 questions which is
        # sufficient signal without collapsing to "Mathematics / General Concepts".
        topic_scores: dict[tuple, list[bool]] = {}
        for q, ans in zip(questions, answers):
            key = (q.get("subject", "General"), q.get("topic", "General"))
            correct = (ans == q.get("correct_index", -1))
            topic_scores.setdefault(key, []).append(correct)

        weakness_map = student.weakness_map
        for (subject, topic), results in topic_scores.items():
            score_pct = sum(results) / len(results)
            existing = next(
                (w for w in weakness_map if w.subject == subject and w.topic == topic), None
            )
            if existing:
                total_attempts = existing.attempts + len(results)
                existing.score_pct = (
                    existing.score_pct * existing.attempts + score_pct * len(results)
                ) / total_attempts
                existing.attempts = total_attempts
                existing.last_attempted = datetime.utcnow()
            else:
                weakness_map.append(WeaknessMap(
                    subject=subject,
                    topic=topic,
                    score_pct=score_pct,
                    attempts=len(results),
                    last_attempted=datetime.utcnow(),
                ))

        weakness_map.sort(key=lambda w: w.score_pct)
        student.weakness_map = weakness_map
        student.total_questions_attempted += len(answers)

        total_correct = sum(1 for q, a in zip(questions, answers) if a == q.get("correct_index", -1))
        score_pct = total_correct / len(questions) if questions else 0
        student.diagnostic_score = score_pct

        # Stage 1 is sufficient to build a study plan — mark diagnostic done immediately
        # so the student can access the study plan right away. Additional stages are
        # offered as optional refinements, not blockers.
        student.diagnostic_done = True

        if stage == 3:
            next_steps_msg = "Diagnostic complete! Your detailed weakness map is ready."
        elif score_pct < 0.40:
            student.diagnostic_stage += 1
            next_steps_msg = (
                f"Score: {score_pct*100:.0f}%. Weakness map saved — you can go to Study Plan now, "
                f"or take Stage {student.diagnostic_stage} for deeper accuracy."
            )
        elif score_pct <= 0.70:
            student.diagnostic_stage += 1
            next_steps_msg = (
                f"Score: {score_pct*100:.0f}%. Your study plan is ready — or take "
                f"Stage {student.diagnostic_stage} to refine weak topics further."
            )
        else:
            student.diagnostic_stage += 1
            next_steps_msg = (
                f"Score: {score_pct*100:.0f}%. Strong foundation — study plan is ready. "
                f"Stage {student.diagnostic_stage} available for edge-case refinement."
            )

        return tag({
            "weakness_map": [w.to_dict() for w in weakness_map],
            "total_correct": total_correct,
            "total_questions": len(questions),
            "score_pct": score_pct,
            "stage_completed": stage,
            "next_steps": next_steps_msg,
            "summary": self._build_summary(weakness_map, student.preferred_language.value),
        }, CardType.DIAG_RESULT)

    def _build_summary(self, weakness_map: list[WeaknessMap], language: str) -> str:
        weak = [w for w in weakness_map if w.score_pct < 0.4]
        if language == "hi":
            if not weak:
                return "बहुत बढ़िया! आपकी नींव मज़बूत है।"
            topics = ", ".join(f"{w.subject} → {w.topic}" for w in weak[:5])
            return f"इन topics पर ध्यान दें: {topics}"
        if not weak:
            return "Great foundation! Moving to targeted practice."
        topics = ", ".join(f"{w.subject} → {w.topic}" for w in weak[:5])
        return f"Focus areas: {topics}"

    async def run(self, student: StudentProfile, message: str) -> dict:
        msg_lower = message.lower()
        if not student.diagnostic_done:
            if student.diagnostic_stage > 1 and any(
                w in msg_lower for w in ["skip", "later", "study", "start studying"]
            ):
                student.diagnostic_done = True
                return {
                    "message": "Understood. Starting your study plan based on current results.",
                    "weakness_map": [w.to_dict() for w in student.weakness_map],
                }
            return self.start_diagnostic(student)
        return {
            "message": "Diagnostic already completed.",
            "weakness_map": [w.to_dict() for w in student.weakness_map],
        }
