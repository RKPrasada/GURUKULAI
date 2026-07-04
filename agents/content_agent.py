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

SYSTEM_PROMPT_EN = """You are an expert tutor for Indian competitive exams.
Generate comprehensive study notes in Markdown for the given topic.
Structure: ## Key Concepts | ## Formulas & Rules | ## Solved Examples (2) | ## Common Mistakes | ## Memory Tricks
Keep it concise, exam-focused, and accurate.
Use only the supplied exam syllabus and skill context. If the topic is outside the supplied syllabus, reply exactly:
I'm here to help you study. What topic would you like?"""

SYSTEM_PROMPT_HI = """आप भारतीय प्रतियोगी परीक्षाओं के लिए एक विशेषज्ञ शिक्षक हैं।
दिए गए विषय के लिए Markdown में व्यापक अध्ययन नोट्स तैयार करें।
संरचना: ## मुख्य अवधारणाएं | ## सूत्र और नियम | ## हल उदाहरण (2) | ## सामान्य गलतियां | ## याद करने की तकनीकें
केवल दिए गए परीक्षा सिलेबस और skill context का उपयोग करें। यदि topic दिए गए सिलेबस से बाहर है, तो ठीक यही लिखें:
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

    def generate_notes(self, student: StudentProfile, topic: str) -> str:
        system = SYSTEM_PROMPT_HI if student.preferred_language.value == "hi" else SYSTEM_PROMPT_EN
        lang_instruction = "Respond entirely in Hindi (Devanagari script)." if student.preferred_language.value == "hi" else ""
        exam_key = exam_value(student.exam_target)
        prompt = (
            f"Exam: {exam_name(exam_key)} ({exam_key})\n"
            f"Approved syllabus outline:\n{compact_syllabus(exam_key)}\n\n"
            f"Generate study notes for topic: **{topic}**. "
            f"{lang_instruction}"
        )
        notes = call_gemini(prompt, system)
        return notes or _offline_notes(topic, exam_key, student.preferred_language.value)

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

        notes = self.generate_notes(student, enriched_topic)
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
            max_results=5,  # fetch extra so filter has candidates to work with
        )
        from agents.content_filter import filter_videos
        safe_videos = filter_videos(raw_videos, topic=topic)
        return tag({
            "topic": topic,
            "notes": notes,
            "pending_action": pending.to_dict(),
            "youtube_videos": safe_videos[:3],  # show max 3 safe videos
        }, CardType.NOTE)
