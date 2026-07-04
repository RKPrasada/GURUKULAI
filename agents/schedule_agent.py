import json
import logging
from datetime import datetime

from agents.base import call_gemini
from models.student import StudentProfile
from models.ui_schema import CardType, tag

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert study planner for competitive exams.
Generate a comprehensive study schedule in JSON based on the student's level and available hours.
Level mapping:
Beginner (<40% diagnostic) -> ~12 months plan
Moderate (40-60% diagnostic) -> ~6 months plan
Good (>60% diagnostic) -> ~3-4 months plan

Include daily/weekly modules covering the entire syllabus.
Each module should have:
- title: string
- type: "video" | "practice" | "reading"
- topic: string
- duration_hours: number
- completed: boolean (false by default)

Return ONLY valid JSON with this structure:
{
  "schedule_type": "weekly",
  "total_duration_months": 6,
  "modules": [
    {
      "id": "mod_001",
      "title": "Week 1: Fundamentals of Mathematics",
      "type": "video",
      "topic": "Number System",
      "duration_hours": 2,
      "completed": false
    }
  ]
}
"""


class ScheduleAgent:
    def __init__(self):
        self._schedules: dict[str, dict] = {}

    def generate_schedule(self, student: StudentProfile, preference: str = "weekly", hours_per_day: int = 2) -> dict:
        level = "beginner"
        if student.diagnostic_score >= 0.60:
            level = "good"
        elif student.diagnostic_score >= 0.40:
            level = "moderate"

        prompt = (
            f"Generate a {preference} study schedule for {student.exam_target.upper()} exam. "
            f"Student level: {level}. Available time: {hours_per_day} hours/day. "
            f"Weaknesses: {', '.join([w.topic for w in student.weakness_map[:3]])}. "
            f"Respond in JSON only."
        )
        raw = call_gemini(prompt, SYSTEM_PROMPT)
        try:
            schedule = json.loads(raw)
        except Exception:
            logger.error("Failed to parse schedule JSON from Gemini")
            schedule = {"error": "Could not generate schedule at this time. Please try again."}

        self._schedules[student.student_id] = schedule
        return tag({"schedule": schedule}, CardType.SCHEDULE)

    async def run(self, student: StudentProfile, message: str) -> dict:
        msg_lower = message.lower()
        if "regenerate schedule" in msg_lower or "reschedule" in msg_lower:
            # Re-generate based on current stats
            return self.generate_schedule(student)
        
        existing = self._schedules.get(student.student_id)
        if existing:
            return tag({"schedule": existing}, CardType.SCHEDULE)
            
        return self.generate_schedule(student)
