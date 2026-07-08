from __future__ import annotations
import logging

from agents.base import call_gemini
from agents.exam_utils import compact_syllabus, exam_name, exam_value, is_exam_scope_query
from mcp.drive_client import DriveClient
from mcp.youtube_client import YouTubeClient
from models.student import StudentProfile
import re
from agents.skill_loader import load_for_topic
from models.ui_schema import CardType, tag
from security.vibe_diff import get_vibe_diff

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_EN = """You are an expert tutor for Indian competitive exams (RRB, NDA, JEE, NEET).
Generate comprehensive study notes in Markdown for the given topic.

Use EXACTLY this structure — every section is mandatory:

## 📖 Concept Overview
Clear definition and explanation in simple language. State WHY this topic matters for the exam.

## 🔑 Key Formulas & Rules
Bullet list of every formula, rule, or theorem — with variable definitions.

## ✅ Solved Examples
Identify ALL major question types that appear for this topic in the exam.
Provide one fully-worked example for each type (minimum 4, typically 5–7).
Cover easy, medium, and hard variants across the types.
For EACH example:
**Type:** [name the question type, e.g. "Finding SP given CP and profit%"]
**Problem:** [State the problem clearly with specific numbers]
**Solution:**
Step 1: [explain each step]
Step 2: ...
**Answer:** [highlight the answer clearly]

## ⚠️ Common Mistakes
Bullet list of errors students make and how to avoid them.

## 🧠 Memory Tricks
Mnemonics, shortcuts, or patterns to remember formulas.

## 🎯 Exam Tips
1-3 specific tips on how this topic appears in exams (question patterns, traps, weightage).

Rules:
- Be concise but complete — exam-focused.
- Use only the supplied exam syllabus. If the topic is outside the syllabus, reply EXACTLY:
  I'm here to help you study. What topic would you like?
- Never make up facts. If uncertain, say so and suggest the student verify from NCERT/official sources."""

SYSTEM_PROMPT_HI = """आप भारतीय प्रतियोगी परीक्षाओं (RRB, NDA, JEE, NEET) के लिए एक विशेषज्ञ शिक्षक हैं।
दिए गए विषय के लिए Markdown में संपूर्ण अध्ययन नोट्स तैयार करें।

यह संरचना अनिवार्य रूप से उपयोग करें:

## 📖 अवधारणा का अवलोकन
सरल भाषा में परिभाषा और व्याख्या। परीक्षा में यह विषय क्यों महत्वपूर्ण है।

## 🔑 मुख्य सूत्र और नियम
हर सूत्र, नियम या प्रमेय की बुलेट सूची — चर की परिभाषाओं के साथ।

## ✅ हल किए गए उदाहरण
इस topic में परीक्षा में आने वाले सभी प्रमुख प्रश्न प्रकारों की पहचान करें।
प्रत्येक प्रकार के लिए एक पूरी तरह हल किया गया उदाहरण दें (कम से कम 4, आमतौर पर 5–7)।
प्रत्येक उदाहरण के लिए:
**प्रकार:** [प्रश्न का प्रकार जैसे "CP और लाभ% से SP निकालना"]
**प्रश्न:** [विशिष्ट संख्याओं के साथ स्पष्ट रूप से प्रश्न लिखें]
**हल:**
चरण 1: [प्रत्येक चरण समझाएं]
चरण 2: ...
**उत्तर:** [उत्तर स्पष्ट रूप से हाइलाइट करें]

## ⚠️ सामान्य गलतियां
छात्र जो गलतियां करते हैं और उनसे कैसे बचें।

## 🧠 याद करने की तकनीकें
सूत्र याद रखने के लिए मेमोनिक्स, शॉर्टकट या पैटर्न।

## 🎯 परीक्षा टिप्स
इस विषय में प्रश्नों के पैटर्न और भारांक पर 1-3 विशिष्ट सुझाव।

नियम:
- संक्षिप्त लेकिन संपूर्ण रहें।
- केवल दिए गए सिलेबस का उपयोग करें। यदि विषय सिलेबस से बाहर है तो ठीक यही लिखें:
  मैं आपकी पढ़ाई में मदद के लिए यहाँ हूँ। आप कौन सा विषय पढ़ना चाहेंगे?"""

def _offline_notes(topic: str, exam: str, language: str) -> str:
    if language == "hi":
        return (
            f"# {topic}\n\n"
            "## मुख्य अवधारणाएं\n"
            f"- यह topic आपके {exam_name(exam)} syllabus से जोड़ा गया है।\n"
            "- अभी Gemini उपलब्ध नहीं है, इसलिए विस्तृत AI notes के बजाय syllabus-safe outline दिखाई जा रही है।\n\n"
            "## अभ्यास योजना\n"
            "- पहले concept पढ़ें।\n"
            "- फिर 10 timed MCQs हल करें।\n"
            "- गलत प्रश्नों की error log बनाएं।\n\n"
            "## अगला कदम\n"
            "Practice Test में इसी topic पर quiz शुरू करें।"
        )
    return (
        f"# {topic}\n\n"
        "## Key Concepts\n"
        f"- This topic is being handled within the {exam_name(exam)} syllabus.\n"
        "- Gemini is unavailable, so VidyaBot is showing a syllabus-safe outline instead of invented notes.\n\n"
        "## Practice Plan\n"
        "- Study the concept from your class notes or textbook.\n"
        "- Solve 10 timed MCQs from the Practice Test section.\n"
        "- Add every mistake to your error log and revise the formula/rule behind it.\n\n"
        "## Next Step\n"
        "Start a topic quiz from Practice Test for targeted drills."
    )


class ContentAgent:
    def __init__(self, drive_client: DriveClient | None = None, youtube_client: YouTubeClient | None = None):
        self._drive = drive_client or DriveClient()
        self._youtube = youtube_client or YouTubeClient()

    def generate_notes(self, student: StudentProfile, topic: str) -> tuple[str, bool]:
        """
        Return (notes_markdown, cache_hit).

        cache_hit=True  → served from the NAGA-approved vector store (no LLM call).
        cache_hit=False → generated fresh by LLM and queued for NAGA approval.
        """
        exam_key = exam_value(student.exam_target)
        lang     = student.preferred_language.value

        # Separate the clean topic name from the orchestrator-injected skill
        # context. The skill context guides the LLM but must NEVER be echoed to
        # the student (e.g. in the offline fallback or the note header).
        parts = topic.split("\n\n[Skill Context]", 1)
        clean_topic = parts[0].strip()
        skill_ctx = parts[1].strip() if len(parts) > 1 else ""

        # ── 1. Semantic cache lookup (query with the clean topic) ─────────────
        try:
            from agents.notes_vector_store import search as vs_search
            hit = vs_search(clean_topic, exam_key, lang)
            if hit:
                logger.info(
                    "ContentAgent: cache HIT  topic=%r  similarity=%.3f  exam=%s",
                    clean_topic, hit["similarity"], exam_key,
                )
                return hit["content"], True
        except Exception as e:
            logger.warning("ContentAgent: vector store lookup failed (%s) — falling back to LLM", e)

        # ── 2. LLM generation ─────────────────────────────────────────────────
        system = SYSTEM_PROMPT_HI if lang == "hi" else SYSTEM_PROMPT_EN
        lang_instruction = "Respond entirely in Hindi (Devanagari script)." if lang == "hi" else ""
        skill_block = f"Teaching guidance (do NOT repeat verbatim):\n{skill_ctx}\n\n" if skill_ctx else ""
        prompt = (
            f"Exam: {exam_name(exam_key)} ({exam_key})\n"
            f"Approved syllabus outline:\n{compact_syllabus(exam_key)}\n\n"
            f"{skill_block}"
            f"Generate study notes for topic: **{clean_topic}**. "
            f"{lang_instruction}"
        )
        # Offline fallback uses the CLEAN topic only — never the skill context
        notes = call_gemini(prompt, system) or _offline_notes(clean_topic, exam_key, lang)

        # ── 3. Queue for NAGA approval → will enter vector store on approval ──
        self._queue_for_naga(topic, exam_key, lang, notes, student_id=student.student_id)

        return notes, False

    def _queue_for_naga(self, topic: str, exam_key: str, lang: str, content: str, student_id: str = "") -> None:
        """Save LLM-generated notes as pending so NAGA can approve and publish to KB.
        Resolves the free-text topic into syllabus subject/topic/subtopic so notes
        are catalogued at the right level (e.g. 'Fractions' → Mathematics /
        Number System / Fractions)."""
        try:
            from datetime import datetime
            from agents.exam_utils import resolve_topic, _norm_topic
            from scripts.notes_generation import _note_paths, _read_meta, _write_meta

            # Strip skill context injected by the orchestrator — store only the clean topic name
            clean_topic = topic.split("\n\n[Skill Context]")[0].strip()

            # Resolve to (subject, canonical_topic). If the query is a subtopic,
            # keep it as the subtopic; otherwise it's the topic itself.
            resolved_subject, canonical_topic = resolve_topic(exam_key, clean_topic)
            subject = resolved_subject or "General"
            if canonical_topic and _norm_topic(clean_topic) != _norm_topic(canonical_topic):
                note_topic, note_subtopic = canonical_topic, clean_topic
            else:
                note_topic, note_subtopic = (canonical_topic or clean_topic), ""

            note_path, meta_path = _note_paths(exam_key, subject, note_topic, note_subtopic)
            existing = _read_meta(meta_path)
            if existing.get("status") == "approved":
                return  # never overwrite an approved note

            note_path.write_text(content, encoding="utf-8")
            _write_meta(meta_path, {
                "exam": exam_key, "subject": subject, "topic": note_topic,
                "subtopic": note_subtopic, "lang": lang, "note_path": str(note_path),
                "status": "pending",
                "generated_at": datetime.utcnow().isoformat(),
                "source": "content_agent",
                "student_id": student_id,
            })
            logger.info("ContentAgent: queued notes for NAGA  exam=%s  %s/%s/%s  student=%s",
                        exam_key, subject, note_topic, note_subtopic or "-", student_id)
        except Exception as e:
            logger.warning("ContentAgent: could not queue notes for NAGA: %s", e)

    def _extract_topic(self, text: str) -> str:
        match = re.search(r'(?i)\b(explain|notes on|tell me about|what is|notes for|about)\s+(.*)', text)
        if match:
            return match.group(2).strip()[:80]
        return text.strip()[:80]

    async def run(self, student: StudentProfile, query: str) -> dict:
        topic = self._extract_topic(query)
        if not is_exam_scope_query(topic, student.exam_target):
            message = (
                "मैं आपकी पढ़ाई में मदद के लिए यहाँ हूँ। आप कौन सा विषय पढ़ना चाहेंगे?"
                if student.preferred_language.value == "hi"
                else "I'm here to help you study. What topic would you like?"
            )
            return tag({"response": message}, CardType.ALERT)

        skill_ctx = load_for_topic(topic, student.exam_target)
        enriched_topic = f"{topic}\n\n[Skill Context]\n{skill_ctx}" if skill_ctx else topic

        notes, cache_hit = self.generate_notes(student, enriched_topic)
        pending = get_vibe_diff().register(
            student_id=student.student_id,
            action_name="save_to_drive",
            description=f"Save study notes for '{topic}' to Google Drive?",
            payload={
                "topic": topic,
                "content": notes,
                "exam": exam_value(student.exam_target),
            },
        )
        raw_videos = self._youtube.search_videos(
            query=topic,
            exam=student.exam_target,
            max_results=6,  # fetch extra — most will be queued for NAGA, few approved yet
        )
        from agents.content_filter import naga_gate_videos
        approved_videos = naga_gate_videos(raw_videos, topic=topic)
        return tag({
            "topic":          topic,
            "notes":          notes,
            "cache_hit":      cache_hit,
            "pending_action": pending.to_dict(),
            "youtube_videos": approved_videos[:3],
        }, CardType.NOTE)
