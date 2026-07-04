from __future__ import annotations
import json
import logging
from zoneinfo import ZoneInfo

from agents.base import call_gemini
from agents.exam_utils import compact_syllabus, exam_name, exam_value, load_syllabus
from mcp.calendar_client import CalendarClient
from mcp.gmail_client import GmailClient
from models.student import StudentProfile
from models.ui_schema import CardType, tag

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")

SYSTEM_PROMPT = """You are a study planner for Indian competitive exam students.
Create a long-term study schedule. Rules:
- Prioritise topics with low scores (under 60%).
- Group the plan by weeks or months depending on the requested duration.
- Ensure all major subjects are covered.

Return JSON with week-by-week drill-down:
{
  "plan_type": "long_term",
  "total_hours": 300,
  "exam_target": "...",
  "plan": [
    {
      "week": "Week 1",
      "focus": "Number System",
      "days": [
        {
          "day": 1,
          "sessions": [
            {"time": "06:30", "duration_minutes": 60, "topic": "LCM & HCF", "activity": "Concept + examples"}
          ]
        }
      ]
    }
  ]
}
"""


def _syllabus_units(exam: str) -> list[dict]:
    syllabus = load_syllabus(exam)
    units: list[dict] = []
    for subject in syllabus.get("subjects", []):
        for topic in subject.get("topics", []):
            subtopics = topic.get("subtopics", []) or [topic.get("name", "Revision")]
            units.append({
                "subject": subject.get("name", "General"),
                "topic": topic.get("name", "Revision"),
                "subtopics": subtopics,
            })
    return units


def _prioritized_units(student: StudentProfile, exam: str) -> list[dict]:
    units = _syllabus_units(exam)
    if not student.weakness_map:
        return units

    def score_unit(unit: dict) -> tuple[int, float]:
        best_rank = 999
        best_score = 1.0
        for idx, weakness in enumerate(sorted(student.weakness_map, key=lambda w: w.score_pct)):
            weakness_topic = weakness.topic.lower()
            weakness_subject = weakness.subject.lower()
            topic = unit["topic"].lower()
            subject = unit["subject"].lower()
            subtopics = " ".join(unit["subtopics"]).lower()
            if weakness_topic != "general concepts" and (weakness_topic in topic or weakness_topic in subtopics):
                best_rank = min(best_rank, idx)
                best_score = min(best_score, weakness.score_pct)
            elif weakness_subject and weakness_subject in subject:
                best_rank = min(best_rank, idx + 20)
                best_score = min(best_score, weakness.score_pct)
        return best_rank, best_score

    return sorted(units, key=score_unit)


def _build_syllabus_plan(student: StudentProfile, avg_score: float = 0.5) -> dict:
    exam = exam_value(student.exam_target)
    if avg_score < 0.4:
        week_count = 48
    elif avg_score <= 0.7:
        week_count = 24
    else:
        week_count = 12

    units = _prioritized_units(student, exam) or [{"subject": "General", "topic": "Revision", "subtopics": ["Revision"]}]
    activities = [
        ("06:30", 60, "Concept + formula notes"),
        ("18:30", 45, "Solved examples"),
        ("20:00", 45, "Timed practice"),
    ]
    plan = []
    for week_index in range(week_count):
        unit = units[week_index % len(units)]
        subtopics = unit["subtopics"]
        days = []
        for day in range(1, 7):
            subtopic = subtopics[(day - 1) % len(subtopics)]
            days.append({
                "day": day,
                "label": f"Day {day}",
                "sessions": [
                    {
                        "time": time,
                        "duration_minutes": duration,
                        "topic": f"{unit['subject']} - {unit['topic']} - {subtopic}",
                        "activity": activity,
                    }
                    for time, duration, activity in activities
                ],
            })
        days.append({
            "day": 7,
            "label": "Day 7",
            "sessions": [
                {
                    "time": "09:00",
                    "duration_minutes": 90,
                    "topic": f"{unit['subject']} - {unit['topic']}",
                    "activity": "Weekly revision + sectional test",
                },
                {
                    "time": "18:00",
                    "duration_minutes": 60,
                    "topic": f"{unit['subject']} - {unit['topic']}",
                    "activity": "Error log and formula revision",
                },
            ],
        })
        plan.append({
            "week": f"Week {week_index + 1}",
            "focus": f"{unit['subject']} - {unit['topic']}",
            "days": days,
        })

    return {
        "plan_type": "syllabus_drill_down",
        "plan": plan,
        "total_hours": week_count * 16,
        "hours_per_week": 16,
        "exam_target": exam,
    }


class ProgressAgent:
    def __init__(self, calendar_client: CalendarClient | None = None, gmail_client: GmailClient | None = None):
        self._calendar = calendar_client or CalendarClient()
        self._gmail = gmail_client or GmailClient()

    def generate_plan(self, student: StudentProfile) -> dict:
        if not student.weakness_map:
            avg_score = 0.5
        else:
            avg_score = sum(w.score_pct for w in student.weakness_map) / len(student.weakness_map)
            
        if not student.weakness_map:
            return _build_syllabus_plan(student, avg_score)

        weak_info = "\n".join(
            f"- {w.subject} / {w.topic}: {w.score_pct*100:.0f}% accuracy"
            for w in sorted(student.weakness_map, key=lambda x: x.score_pct)[:10]
        )
        
        if avg_score < 0.4:
            duration_instruction = "Create a 1-year study schedule grouped by Month (Month 1 to Month 12)."
        elif avg_score <= 0.7:
            duration_instruction = "Create a 6-month study schedule grouped by Week (Week 1 to Week 24)."
        else:
            duration_instruction = "Create a 3-month study schedule grouped by Week (Week 1 to Week 12)."
            
        exam_val = exam_value(student.exam_target)

        prompt = (
            f"Student exam: {exam_name(exam_val)} ({exam_val})\n"
            f"Approved syllabus outline:\n{compact_syllabus(exam_val)}\n\n"
            f"Overall average accuracy: {avg_score*100:.0f}%\n"
            f"Weak areas:\n{weak_info}\n"
            f"{duration_instruction}\n"
            f"Return JSON only."
        )
        raw = call_gemini(prompt, SYSTEM_PROMPT)
        try:
            return json.loads(raw)
        except Exception:
            logger.error("Failed to parse plan JSON, using syllabus-derived plan")
            return _build_syllabus_plan(student, avg_score)

    def create_calendar_events(self, student: StudentProfile, plan: dict) -> dict:
        events = []
        for block in plan.get("plan", []):
            day_blocks = block.get("days", [block])
            for day in day_blocks:
                if "sessions" in day:
                    for session in day.get("sessions", []):
                        events.append({
                            "date": day.get("date", block.get("week", day.get("label", ""))),
                            "time": session.get("time", "10:00"),
                            "topic": session.get("topic", "Study Session"),
                            "duration_minutes": session.get("duration_minutes", 60),
                            "exam": exam_value(student.exam_target),
                        })
                elif "date" in day and "sessions" in day:
                    events.append({
                        "date": day["date"],
                        "time": "10:00",
                        "topic": day.get("topic", "Study Session"),
                        "duration_minutes": 60,
                        "exam": exam_value(student.exam_target),
                    })
        if not events:
            logger.warning("No specific daily events found in long-term plan to add to calendar.")
            return {"status": "skipped", "reason": "long_term_plan"}
            
        return self._calendar.create_study_events(student.student_id, json.dumps(events))

    def send_weekly_digest(self, student: StudentProfile, to_email: str, student_name: str) -> bool:
        from datetime import date
        week_num = date.today().isocalendar()[1]
        summary = {
            "week": f"Week {week_num}",
            "exam": exam_value(student.exam_target),
            "topics_studied": list({w.topic for w in student.weakness_map}),
            "weak_areas": [w.topic for w in student.weakness_map if w.score_pct < 0.5],
            "questions_attempted": student.total_questions_attempted,
            "accuracy_pct": (
                sum(w.score_pct for w in student.weakness_map) / len(student.weakness_map) * 100
                if student.weakness_map else 0
            ),
            "streak_days": student.study_streak_days,
        }
        return self._gmail.send_progress_digest(to_email, student_name, summary)

    def get_progress_summary(self, student: StudentProfile) -> dict:
        by_subject: dict[str, list[float]] = {}
        for w in student.weakness_map:
            by_subject.setdefault(w.subject, []).append(w.score_pct)

        return {
            "streak_days": student.study_streak_days,
            "total_questions": student.total_questions_attempted,
            "overall_accuracy": (
                sum(w.score_pct for w in student.weakness_map) / len(student.weakness_map)
                if student.weakness_map else 0
            ),
            "subject_accuracy": {
                subj: sum(scores) / len(scores) for subj, scores in by_subject.items()
            },
            "weak_topics": [w.to_dict() for w in student.weakness_map if w.score_pct < 0.6],
            "strong_topics": [w.to_dict() for w in student.weakness_map if w.score_pct >= 0.8],
        }

    async def run(self, student: StudentProfile, message: str = "") -> dict:
        plan = self.generate_plan(student)
        summary = self.get_progress_summary(student)
        return tag({"plan": plan, "summary": summary}, CardType.PLAN)
