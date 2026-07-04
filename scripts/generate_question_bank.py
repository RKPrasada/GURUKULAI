"""
Regenerate all question bank files with real, exam-quality MCQs.
Run: python scripts/generate_question_bank.py
"""
import json
import os
import sys
import uuid
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.base import call_gemini
from agents.exam_utils import load_syllabus
from agents.question_validator import filter_questions

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BANK_DIR = Path(__file__).parent.parent / "data" / "question_banks"
QUESTIONS_PER_TOPIC = 15

SYSTEM_PROMPT = """You are an expert MCQ writer for Indian competitive exams.
Write challenging, realistic questions that test actual knowledge — NOT definitions or vague concepts.

Rules:
- Questions must be specific, factual, and require genuine understanding to answer
- Each question must have exactly 4 options
- Options must be plausible (no obviously wrong choices like "unrelated concept")
- One clearly correct answer
- Include a concise explanation for the correct answer
- Vary difficulty: mix easy (40%), medium (40%), hard (20%)
- No two questions should test the same fact

Return ONLY valid JSON (no markdown fences):
{
  "questions": [
    {
      "subject": "...",
      "topic": "...",
      "difficulty": 1,
      "question_text": "...",
      "options": ["A", "B", "C", "D"],
      "correct_index": 0,
      "explanation": "..."
    }
  ]
}"""


EXAM_CONTEXT = {
    "rrb_ntpc": "RRB NTPC CBT1 (Railway Recruitment Board Non-Technical Popular Categories). Questions are at 10th/12th standard level. Focus on exam-pattern questions that appear in actual RRB NTPC papers.",
    "nda": "NDA (National Defence Academy) entrance exam. Mathematics is at 12th standard. General Ability tests Physics, Chemistry, History, Geography, Current Events at a high level.",
    "jee": "JEE Main/Advanced (Joint Entrance Examination). Questions are at 12th standard (NCERT + beyond). Include numerical, conceptual and application-type questions.",
    "neet": "NEET (National Eligibility cum Entrance Test). Questions are NCERT-based (Class 11 & 12). Focus on Biology, Physics and Chemistry for medical entrance.",
}


def generate_topic_questions(exam_key: str, exam_context: str,
                              subject: str, topic: str, subtopics: list[str]) -> list[dict]:
    subtopic_str = ", ".join(subtopics[:10]) if subtopics else topic
    prompt = (
        f"Exam: {exam_context}\n"
        f"Subject: {subject}\n"
        f"Topic: {topic}\n"
        f"Subtopics to cover: {subtopic_str}\n\n"
        f"Generate exactly {QUESTIONS_PER_TOPIC} MCQs for this topic.\n"
        f"Spread questions across all subtopics listed.\n"
        f"Make questions exam-realistic — the kind that appear in actual {exam_key.upper()} papers.\n"
        f"Do NOT write placeholder or vague questions like 'which is a key concept of X'.\n"
        f"Write specific, knowledge-testing questions with numerical values, names, formulas, dates where relevant."
    )
    raw = call_gemini(prompt, SYSTEM_PROMPT, timeout=45.0)
    if not raw:
        logger.warning(f"No response for {exam_key}/{subject}/{topic}")
        return []

    clean = raw.strip()
    # Strip markdown fences
    for fence in ("```json", "```"):
        if clean.startswith(fence):
            clean = clean[len(fence):]
    if clean.endswith("```"):
        clean = clean[:-3]

    try:
        data = json.loads(clean.strip())
        questions = data.get("questions", [])
        # Stamp IDs and normalize fields
        result = []
        for q in questions:
            topic_slug = topic.lower().replace(" ", "_").replace("&", "and")[:8]
            subj_slug = subject.lower().replace(" ", "_")[:3]
            result.append({
                "id": f"{exam_key}_{subj_slug}_{topic_slug}_{uuid.uuid4().hex[:6]}",
                "subject": q.get("subject", subject),
                "topic": q.get("topic", topic),
                "difficulty": q.get("difficulty", 1),
                "question_text": q.get("question_text", ""),
                "options": q.get("options", []),
                "correct_index": q.get("correct_index", 0),
                "explanation": q.get("explanation", ""),
            })
        return result
    except Exception as e:
        logger.error(f"JSON parse error for {exam_key}/{topic}: {e}\nRaw: {raw[:200]}")
        return []


def dedup(questions: list[dict]) -> list[dict]:
    seen = set()
    result = []
    for q in questions:
        key = q["question_text"].strip().lower()[:120]
        if key and key not in seen:
            seen.add(key)
            result.append(q)
    return result


def regenerate_exam(exam_key: str):
    syl = load_syllabus(exam_key)
    ctx = EXAM_CONTEXT.get(exam_key, exam_key.upper())
    tasks = []
    for subj in syl.get("subjects", []):
        for topic in subj.get("topics", []):
            subtopics = [s if isinstance(s, str) else s.get("name", "")
                         for s in topic.get("subtopics", [])]
            tasks.append((subj["name"], topic["name"], subtopics))

    logger.info(f"{exam_key}: generating questions for {len(tasks)} topics …")
    all_questions: list[dict] = []

    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {
            pool.submit(generate_topic_questions, exam_key, ctx, subj, topic, subs): (subj, topic)
            for subj, topic, subs in tasks
        }
        for future in as_completed(futures):
            subj, topic = futures[future]
            try:
                qs = future.result()
                all_questions.extend(qs)
                logger.info(f"  {exam_key}/{topic}: {len(qs)} questions")
            except Exception as e:
                logger.error(f"  {exam_key}/{topic} FAILED: {e}")

    all_questions = dedup(all_questions)
    all_questions, rejected = filter_questions(all_questions, source=exam_key)
    logger.info(
        f"{exam_key}: {len(all_questions)} unique questions after dedup "
        f"({len(rejected)} rejected by guard-rail)"
    )

    out_path = BANK_DIR / f"{exam_key}.json"
    out_path.write_text(json.dumps(all_questions, indent=2, ensure_ascii=False))
    logger.info(f"{exam_key}: saved to {out_path}")
    return len(all_questions)


if __name__ == "__main__":
    exams = sys.argv[1:] or ["rrb_ntpc", "nda", "jee", "neet"]
    for exam in exams:
        count = regenerate_exam(exam)
        print(f"\n✓ {exam}: {count} questions written\n")
