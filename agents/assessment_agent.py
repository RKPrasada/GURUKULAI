from __future__ import annotations
import json
import logging
import random
import uuid

from agents.base import call_gemini
from agents.exam_utils import compact_syllabus, exam_name, exam_value, is_exam_scope_query
from agents.question_bank import get_questions_for_exam
from agents.question_validator import filter_questions
from models.question import Question
from models.student import StudentProfile
from models.ui_schema import CardType, tag

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an MCQ generator for Indian competitive exams.
Generate {n} multiple-choice questions on the given topic.
Rules: 1 unambiguous correct answer, solvable in under 90 seconds, syllabus-accurate.
Write specific factual/numerical questions. Do NOT write template questions like "Which is a key concept of X" or options like "A core principle of X" / "An unrelated concept to X".
Return ONLY valid JSON:
{
  "questions": [
    {
      "question_id": "q_001",
      "subject": "Mathematics",
      "topic": "Algebra",
      "difficulty": 1,
      "question_text_en": "...",
      "question_text_hi": "...",
      "options": ["A", "B", "C", "D"],
      "correct_index": 0,
      "explanation_en": "...",
      "explanation_hi": "..."
    }
  ]
}"""


def _fallback_questions(exam: str, topic: str | None, difficulty: int, n: int) -> list[Question]:
    """Pull questions from the local question bank when Gemini fails to return valid JSON."""
    exam_key = exam.value if hasattr(exam, "value") else str(exam)
    bank = get_questions_for_exam(exam_key, limit=n * 3)
    if topic:
        filtered = [q for q in bank if q["topic"].lower() == topic.lower() or q["subject"].lower() == topic.lower()]
    else:
        filtered = bank
    if not filtered:
        filtered = bank
    diff_filtered = [q for q in filtered if q.get("difficulty") == difficulty]
    pool = diff_filtered if len(diff_filtered) >= n else filtered
    chosen = random.sample(pool, min(n, len(pool)))
    result = []
    for q in chosen:
        result.append(Question(
            question_id=q.get("id", f"mcq_{uuid.uuid4().hex[:8]}"),
            exam=exam,
            subject=q["subject"],
            topic=q["topic"],
            difficulty=q.get("difficulty", difficulty),
            question_text_en=q.get("question_text_en", q.get("question_text", "")),
            question_text_hi=q.get("question_text_hi"),
            options=q["options"],
            correct_index=q["correct_index"],
            explanation_en=q.get("explanation_en", q.get("explanation", "")),
            explanation_hi=q.get("explanation_hi"),
        ))
    return result


class AssessmentAgent:
    def __init__(self):
        self._sessions: dict[str, dict] = {}

    def get_adaptive_difficulty(self, student: StudentProfile) -> int:
        if not student.weakness_map:
            return 1
        avg = sum(w.score_pct for w in student.weakness_map) / len(student.weakness_map)
        if avg < 0.40:
            return 1
        if avg < 0.70:
            return 2
        return 3

    def generate_questions(self, student: StudentProfile, topic: str | None = None, n: int = 10, requested_difficulty: str = "adaptive") -> list[Question]:
        if requested_difficulty == "easy":
            difficulty = 1
        elif requested_difficulty == "medium":
            difficulty = 2
        elif requested_difficulty == "hard":
            difficulty = 3
        else:
            difficulty = self.get_adaptive_difficulty(student)

        if topic is None and student.weakness_map:
            sorted_weaknesses = sorted(student.weakness_map, key=lambda w: w.score_pct)
            topic = sorted_weaknesses[0].topic

        topic = topic or "General"
        exam_key = exam_value(student.exam_target)

        # ── 1. Serve from topic practice bank immediately ─────────────────────
        # PracticeBankManager handles bank-first + async LLM enrichment internally.
        # This is always fast (<100ms) after the first-ever call for a topic.
        if topic != "General":
            try:
                from agents.practice_bank import get_practice_bank
                # Infer subject from syllabus for this topic
                subject = self._find_subject(exam_key, topic)
                bank_qs = get_practice_bank().get_questions(exam_key, subject, topic, count=n)
                if bank_qs:
                    # Filter by difficulty if not adaptive
                    if requested_difficulty != "adaptive":
                        filtered = [q for q in bank_qs if q.get("difficulty") == difficulty]
                        bank_qs = filtered if len(filtered) >= n // 2 else bank_qs
                    return [Question.from_dict({**q, "exam": exam_key}) for q in bank_qs[:n]]
            except Exception as e:
                logger.warning("Practice bank unavailable (%s) — falling back to LLM", e)

        # ── 2. Fallback: question bank for "General" or if practice bank fails ─
        fallback = _fallback_questions(exam_key, topic if topic != "General" else None, difficulty, n)
        if fallback:
            return fallback

        # ── 3. Last resort: LLM (slow, only if bank truly empty) ─────────────
        prompt = (
            f"Exam: {exam_name(exam_key)} ({exam_key})\n"
            f"Approved syllabus outline:\n{compact_syllabus(exam_key)}\n\n"
            f"Generate {n} MCQs on '{topic}' for this exam only. "
            f"ALL questions must be strictly about '{topic}'. "
            f"Difficulty level: {difficulty} (1=easy,2=medium,3=hard). "
            f"If the topic is outside the approved syllabus, return JSON with an empty questions array. "
            f"Return JSON only."
        )
        raw = call_gemini(prompt, SYSTEM_PROMPT.replace("{n}", str(n)))
        try:
            clean_raw = (raw or "").strip()
            for fence in ("```json", "```"):
                if clean_raw.startswith(fence):
                    clean_raw = clean_raw[len(fence):]
            if clean_raw.endswith("```"):
                clean_raw = clean_raw[:-3]

            data = json.loads(clean_raw.strip())
            q_list = data.get("questions") or data.get("MCQs") or data.get("mcqs") or []
            if not q_list:
                raise ValueError("No questions in LLM response")

            q_list, rejected = filter_questions(q_list, source=f"LLM-serve/assessment/{exam_key}")
            if rejected:
                logger.warning("Filtered %d placeholder questions for %s", len(rejected), topic)
            if not q_list:
                raise ValueError("All LLM questions failed validation")

            return [Question.from_dict({**q, "exam": exam_key}) for q in q_list]
        except Exception as e:
            logger.error("generate_questions LLM failed for %s: %s", topic, e)
            return []

    def _find_subject(self, exam_key: str, topic: str) -> str:
        """Return the syllabus subject that owns this topic, or 'General'."""
        try:
            from agents.exam_utils import load_syllabus
            syllabus = load_syllabus(exam_key)
            for subj in syllabus.get("subjects", []):
                for t in subj.get("topics", []):
                    if t.get("name", "").lower() == topic.lower():
                        return subj["name"]
        except Exception:
            pass
        return "General"

    def start_session(self, student: StudentProfile, topic: str | None = None, requested_difficulty: str = "adaptive") -> dict:
        if topic and not is_exam_scope_query(topic, student.exam_target):
            message_text = (
                "मैं आपकी पढ़ाई में मदद के लिए यहाँ हूँ। आप कौन सा विषय पढ़ना चाहेंगे?"
                if student.preferred_language.value == "hi"
                else "I'm here to help you study. What topic would you like?"
            )
            return tag({"response": message_text}, CardType.ALERT)
        questions = self.generate_questions(student, topic, requested_difficulty=requested_difficulty)
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = {
            "questions": [q.to_dict() for q in questions],
            "current_index": 0,
            "score": 0,
        }
        return tag({
            "session_id": session_id,
            "total": len(questions),
            "difficulty": self.get_adaptive_difficulty(student),
            "first_question": questions[0].to_dict() if questions else None,
        }, CardType.QUIZ)

    def evaluate_answer(self, session_id: str, question_id: str, answer_index: int) -> dict:
        session = self._sessions.get(session_id, {})
        questions = session.get("questions", [])
        q = next((x for x in questions if x["question_id"] == question_id), None)
        if not q:
            return {"error": "Question not found"}

        correct = answer_index == q["correct_index"]
        if correct:
            session["score"] = session.get("score", 0) + 1

        idx = session.get("current_index", 0) + 1
        session["current_index"] = idx
        next_q = questions[idx] if idx < len(questions) else None

        return tag({
            "correct": correct,
            "correct_index": q["correct_index"],
            "explanation_en": q["explanation_en"],
            "explanation_hi": q.get("explanation_hi"),
            "score": session["score"],
            "answered": idx,
            "total": len(questions),
            "next_question": next_q,
            "session_complete": next_q is None,
        }, CardType.QUIZ_RESULT)

    async def run(self, student: StudentProfile, message: str) -> dict:
        topic = None
        if len(message) > 20:
            for kw in ["on ", "about ", "for "]:
                if kw in message.lower():
                    idx = message.lower().index(kw) + len(kw)
                    topic = message[idx:].strip()[:80]
                    break
            if not topic:
                topic = message.strip()[:80]
        if topic and not is_exam_scope_query(topic, student.exam_target):
            message_text = (
                "मैं आपकी पढ़ाई में मदद के लिए यहाँ हूँ। आप कौन सा विषय पढ़ना चाहेंगे?"
                if student.preferred_language.value == "hi"
                else "I'm here to help you study. What topic would you like?"
            )
            return tag({"response": message_text}, CardType.ALERT)
        return self.start_session(student, topic)
