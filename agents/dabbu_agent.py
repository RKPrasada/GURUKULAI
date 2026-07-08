"""
Dabbu — autonomous background AI agent.

Dabbu runs independently to:
  1. Generate personalised study plans (proposes to NAGA for approval)
  2. Detect when >50% of students on an exam struggle with the same topic
     and suggest NAGA schedule a class
  3. Submit AI-generated study notes for NAGA approval before publishing
  4. Flag YouTube videos for NAGA content review
  5. Suggest students take a mid-plan re-diagnostic when need arises

All proposals go through NAGA (human) before reaching students.
No action modifies student data directly — Dabbu only writes to:
  - data/study_plans/{student_id}_proposed.json
  - data/mentor/notifications.jsonl
  - data/notes/{exam}/{subject}/{topic}.md  (status=pending)
  - data/dabbu/proposals.jsonl              (audit trail)
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from agents.base import call_gemini
from agents.exam_utils import exam_name, load_syllabus
from models.mentor import Notification, NotificationType
from models.student import StudentProfile, WeaknessMap
from models.study_plan import (
    DayPlan, PlanStatus, SessionBlock, SessionType, StudyPlan, WeekPlan,
)

logger = logging.getLogger(__name__)

DATA_DIR = Path("data")
STUDY_PLANS_DIR = DATA_DIR / "study_plans"
NOTES_DIR = DATA_DIR / "notes"
PROPOSALS_DIR = DATA_DIR / "dabbu"
MENTOR_DIR = DATA_DIR / "mentor"
NOTIFICATIONS_FILE = MENTOR_DIR / "notifications.jsonl"

for _d in (STUDY_PLANS_DIR, PROPOSALS_DIR, MENTOR_DIR):
    _d.mkdir(parents=True, exist_ok=True)

NAGA_USER_ID = "naga"

# Slot multiplier by weakness severity
_SLOT_WEIGHT = {
    "critical": 3,   # score < 0.30
    "weak": 2,       # score 0.30–0.60
    "normal": 1,     # score > 0.60 or not attempted
}

# Daily study schedule: 5 × 2hr blocks starting at 7am, 9am, 11am, 2pm, 4pm
_DAILY_SLOTS = [7, 9, 11, 14, 16]  # start hours


# ── Notification helper ────────────────────────────────────────────────────────

def _notify(user_id: str, ntype: NotificationType, title: str, body: str, data: dict = {}) -> None:
    MENTOR_DIR.mkdir(parents=True, exist_ok=True)
    n = Notification(
        notification_id=str(uuid.uuid4()),
        user_id=user_id,
        type=ntype,
        title=title,
        body=body,
        data=data,
    )
    with open(NOTIFICATIONS_FILE, "a") as f:
        f.write(json.dumps(n.to_dict()) + "\n")


def _log_proposal(proposal: dict) -> None:
    path = PROPOSALS_DIR / "proposals.jsonl"
    with open(path, "a") as f:
        f.write(json.dumps({**proposal, "logged_at": datetime.utcnow().isoformat()}) + "\n")


# ── Topic-weight computation ───────────────────────────────────────────────────

def _topic_weights(weakness_map: list[WeaknessMap], syllabus: dict) -> list[dict]:
    """
    Return [{subject, topic, subtopic, weight, priority}] for every SUBTOPIC in the
    syllabus (Subject → Topic → Subtopic). Weakness is tracked at topic level, so
    each subtopic inherits its parent topic's priority. Weak topics get weight=3
    (critical) / weight=2 (weak) so their subtopics recur more often in the
    schedule → more study + practice sessions on weak areas.
    Topics with no subtopics fall back to a single topic-level entry.
    """
    from datetime import date as _date
    today = _date.today()
    wm_index = {(w.subject.lower(), w.topic.lower()): w for w in weakness_map}
    result = []
    for subj in syllabus.get("subjects", []):
        subj_name = subj["name"]
        for topic_obj in subj.get("topics", []):
            topic_name = topic_obj["name"]
            w = wm_index.get((subj_name.lower(), topic_name.lower()))
            if w is None:
                weight, priority = 1, "normal"
            elif w.score_pct < 0.30:
                weight, priority = 3, "critical"
            elif w.score_pct < 0.60:
                weight, priority = 2, "weak"
            else:
                weight, priority = 1, "normal"
            # SM-2: topics whose review is due today get bumped to weight=4
            if w is not None and hasattr(w, "next_review_date") and w.next_review_date:
                review_date = w.next_review_date.date() if hasattr(w.next_review_date, "date") else w.next_review_date
                if review_date <= today:
                    weight = max(weight, 3)
                    priority = "critical" if priority != "critical" else priority

            subtopics = [
                (s if isinstance(s, str) else s.get("name", ""))
                for s in topic_obj.get("subtopics", [])
            ]
            subtopics = [s for s in subtopics if s] or [""]  # ensure ≥1 entry
            for sub in subtopics:
                result.append({
                    "subject": subj_name,
                    "topic": topic_name,
                    "subtopic": sub,
                    "weight": weight,
                    "priority": priority,
                    "score_pct": w.score_pct if w else None,
                })
    return result


# ── Study plan generation ──────────────────────────────────────────────────────

class DabbuAgent:
    """Autonomous background agent — proposals only, no direct student mutations."""

    def generate_study_plan(
        self,
        student: StudentProfile,
        exam_date: Optional[str] = None,
    ) -> StudyPlan:
        """
        Build a weekly/daily study plan tailored to the student's diagnostic results.
        Saves to data/study_plans/{student_id}_proposed.json and notifies NAGA.
        Returns the StudyPlan (status=PROPOSED) for API response.
        """
        score = student.diagnostic_score
        exam_key = student.exam_target

        # Duration decision
        if exam_date:
            target = date.fromisoformat(exam_date)
            days_left = (target - date.today()).days
            duration_months = max(1, round(days_left / 30))
        elif score > 0.70:
            duration_months = 3
        elif score >= 0.40:
            duration_months = 6
        else:
            duration_months = 12

        total_days = duration_months * 30
        start = date.today()
        end = start + timedelta(days=total_days - 1)

        syllabus = load_syllabus(exam_key)
        topic_list = _topic_weights(student.weakness_map, syllabus)

        weak_topics = sorted({
            f"{t['subject']} → {t['topic']}"
            for t in topic_list
            if t["priority"] in ("critical", "weak")
        })

        weeks = self._build_weeks(topic_list, start, total_days)
        total_hours = sum(w.total_hours for w in weeks)

        plan = StudyPlan(
            plan_id=str(uuid.uuid4()),
            student_id=student.student_id,
            exam_target=exam_key,
            status=PlanStatus.PROPOSED,
            duration_months=duration_months,
            start_date=start.isoformat(),
            end_date=end.isoformat(),
            exam_date=exam_date,
            weeks=weeks,
            weak_topics=weak_topics,
            diagnostic_score=score,
            total_study_hours=total_hours,
        )

        # Save proposed plan
        plan_path = STUDY_PLANS_DIR / f"{student.student_id}_proposed.json"
        plan_path.write_text(json.dumps(plan.to_dict(), indent=2, ensure_ascii=False))

        # Notify NAGA
        exam_display = exam_name(exam_key)
        weak_count = len(weak_topics)  # distinct weak subject→topic pairs
        _notify(
            user_id=NAGA_USER_ID,
            ntype=NotificationType.STUDY_PLAN_PROPOSED,
            title=f"Dabbu: Study plan ready for {student.student_id[:8]}",
            body=(
                f"Exam: {exam_display} | Score: {score*100:.0f}% | "
                f"Duration: {duration_months} months | "
                f"Weak topics: {weak_count} | "
                f"Total hours: {total_hours:.0f}h"
            ),
            data={
                "student_id": student.student_id,
                "plan_id": plan.plan_id,
                "plan_path": str(plan_path),
                "action": "study_plan_approval",
            },
        )

        _log_proposal({
            "type": "study_plan_proposed",
            "student_id": student.student_id,
            "plan_id": plan.plan_id,
            "duration_months": duration_months,
            "weak_topics_count": weak_count,
        })

        logger.info(
            "Dabbu: study plan %s proposed for student %s (%d months, %d weak topics)",
            plan.plan_id, student.student_id, duration_months, weak_count,
        )
        return plan

    def _build_weeks(
        self,
        topic_list: list[dict],
        start: date,
        total_days: int,
    ) -> list[WeekPlan]:
        """
        Distribute topics across weeks proportionally by weight.
        Each day gets up to 5 × 2hr blocks (10 hrs max).
        Sunday is always a rest day.
        """
        if not topic_list:
            return []

        total_weight = sum(t["weight"] for t in topic_list)
        num_weeks = max(1, (total_days + 6) // 7)

        # Each week gets a slice of the topic queue proportional to calendar weeks
        # Expand topic list with repetitions based on weight
        expanded: list[dict] = []
        for t in topic_list:
            expanded.extend([t] * t["weight"])

        # Interleave subjects for variety (avoid 10 days of only Maths)
        by_subject: dict[str, list[dict]] = {}
        for t in expanded:
            by_subject.setdefault(t["subject"], []).append(t)

        interleaved: list[dict] = []
        while any(by_subject.values()):
            for subj in list(by_subject.keys()):
                if by_subject[subj]:
                    interleaved.append(by_subject[subj].pop(0))
                else:
                    del by_subject[subj]

        # Distribute topics across all available slots
        slots_per_week = 5 * 6  # 5 slots/day × 6 study days (Sun = rest)
        total_slots = num_weeks * slots_per_week
        # Cycle through topic list to fill all slots
        cycled = [interleaved[i % len(interleaved)] for i in range(total_slots)]

        weeks: list[WeekPlan] = []
        topic_cursor = 0
        current = start

        for week_num in range(1, num_weeks + 1):
            week_start = current
            week_end = current + timedelta(days=6)
            # Build subject theme for the week (most common subject in this week's batch)
            week_topics = cycled[topic_cursor: topic_cursor + slots_per_week]
            if week_topics:
                subj_counts: dict[str, int] = {}
                for t in week_topics:
                    subj_counts[t["subject"]] = subj_counts.get(t["subject"], 0) + 1
                theme_subj = max(subj_counts, key=lambda s: subj_counts[s])
            else:
                theme_subj = ""

            days: list[DayPlan] = []
            for offset in range(7):
                day_date = current + timedelta(days=offset)
                if day_date > start + timedelta(days=total_days - 1):
                    break
                dow = day_date.strftime("%A")
                if dow == "Sunday":
                    days.append(DayPlan(
                        day_date=day_date.isoformat(),
                        day_of_week=dow,
                        is_rest_day=True,
                    ))
                    continue

                blocks: list[SessionBlock] = []
                for slot_hr in _DAILY_SLOTS:
                    if topic_cursor >= len(cycled):
                        break
                    t = cycled[topic_cursor]
                    topic_cursor += 1
                    # Decide session type: mock on Saturdays slot-5, practice for weak, study otherwise
                    if dow == "Saturday" and slot_hr == _DAILY_SLOTS[-1]:
                        stype = SessionType.MOCK
                        subj, topic_name, subtopic_name = "", "", ""
                    elif t["priority"] in ("critical", "weak"):
                        stype = SessionType.PRACTICE
                        subj, topic_name, subtopic_name = t["subject"], t["topic"], t.get("subtopic", "")
                    else:
                        stype = SessionType.STUDY
                        subj, topic_name, subtopic_name = t["subject"], t["topic"], t.get("subtopic", "")

                    priority_map = {"critical": 3, "weak": 2, "normal": 1}
                    blocks.append(SessionBlock(
                        block_id=str(uuid.uuid4())[:8],
                        start_hour=slot_hr,
                        duration_hours=2,
                        subject=subj,
                        topic=topic_name,
                        subtopic=subtopic_name,
                        session_type=stype,
                        priority=priority_map.get(t["priority"], 1),
                    ))

                total_hours = sum(b.duration_hours for b in blocks)
                days.append(DayPlan(
                    day_date=day_date.isoformat(),
                    day_of_week=dow,
                    blocks=blocks,
                    total_hours=float(total_hours),
                ))

            week_total = sum(d.total_hours for d in days)
            weeks.append(WeekPlan(
                week_number=week_num,
                start_date=week_start.isoformat(),
                end_date=week_end.isoformat(),
                theme=theme_subj,
                days=days,
                total_hours=week_total,
            ))
            current += timedelta(days=7)

        return weeks

    # ── Common weak areas across students ─────────────────────────────────────

    def detect_common_weak_areas(self, exam_key: str, db_path: str = "vidyabot.db") -> list[dict]:
        """
        Scan all StudentProfiles for exam_key, find topics where >50% of students
        scored below 0.50. Returns list of {subject, topic, student_count, fail_pct}.
        """
        import sqlite3
        struggling: dict[tuple, list[float]] = {}
        total_students = 0

        try:
            conn = sqlite3.connect(db_path)
            rows = conn.execute(
                "SELECT weakness_map_json, exam_target FROM students WHERE exam_target = ?",
                (exam_key,),
            ).fetchall()
            conn.close()
        except Exception as e:
            logger.error("Dabbu: detect_common_weak_areas DB error: %s", e)
            return []

        for row in rows:
            try:
                wm_data = json.loads(row[0] or "[]")
            except Exception:
                continue
            total_students += 1
            for w in wm_data:
                key = (w.get("subject", ""), w.get("topic", ""))
                struggling.setdefault(key, []).append(w.get("score_pct", 1.0))

        if not total_students:
            return []

        threshold = total_students * 0.50
        results = []
        for (subject, topic), scores in struggling.items():
            failing = [s for s in scores if s < 0.50]
            if len(failing) >= threshold:
                results.append({
                    "subject": subject,
                    "topic": topic,
                    "student_count": len(failing),
                    "total_students": total_students,
                    "fail_pct": round(len(failing) / total_students * 100, 1),
                    "avg_score": round(sum(failing) / len(failing) * 100, 1),
                })

        results.sort(key=lambda r: r["fail_pct"], reverse=True)
        logger.info(
            "Dabbu: %d/%d topics flagged as common weak areas for %s",
            len(results), len(struggling), exam_key,
        )
        return results

    def suggest_naga_class(
        self, exam_key: str, subject: str, topic: str, student_count: int, fail_pct: float
    ) -> None:
        """Notify NAGA that >50% of students are struggling — suggest a live class."""
        exam_display = exam_name(exam_key)
        _notify(
            user_id=NAGA_USER_ID,
            ntype=NotificationType.CLASS_SUGGESTED,
            title=f"Dabbu: Class needed — {topic} ({subject})",
            body=(
                f"{student_count} students ({fail_pct:.0f}%) are struggling with "
                f"'{topic}' in {subject} for {exam_display}. "
                f"Consider scheduling a live group class."
            ),
            data={
                "exam_key": exam_key,
                "subject": subject,
                "topic": topic,
                "student_count": student_count,
                "fail_pct": fail_pct,
                "action": "suggest_class",
            },
        )
        _log_proposal({
            "type": "class_suggested",
            "exam_key": exam_key,
            "subject": subject,
            "topic": topic,
            "student_count": student_count,
            "fail_pct": fail_pct,
        })
        logger.info(
            "Dabbu: suggested class for %s/%s (%d students, %.0f%% failing)",
            subject, topic, student_count, fail_pct,
        )

    def run_common_weakness_scan(self, exam_key: str) -> int:
        """
        Full pipeline: scan → find common weak areas → notify NAGA for each.
        Returns number of suggestions sent.
        """
        areas = self.detect_common_weak_areas(exam_key)
        for area in areas:
            self.suggest_naga_class(
                exam_key=exam_key,
                subject=area["subject"],
                topic=area["topic"],
                student_count=area["student_count"],
                fail_pct=area["fail_pct"],
            )
        return len(areas)

    # ── Notes approval ─────────────────────────────────────────────────────────

    def submit_note_for_approval(
        self,
        exam: str,
        subject: str,
        topic: str,
        note_path: str,
        preview: str = "",
    ) -> None:
        """
        Notify NAGA that Dabbu has generated notes for exam/subject/topic.
        Notes are at note_path with status=pending. NAGA approves → status=approved.
        """
        _notify(
            user_id=NAGA_USER_ID,
            ntype=NotificationType.NOTE_PENDING_APPROVAL,
            title=f"Dabbu: Notes ready — {topic} ({subject})",
            body=(
                f"AI-generated notes for '{topic}' ({subject}, {exam.upper()}) "
                f"are pending your review.\n\nPreview: {preview[:200] if preview else '(see file)'}"
            ),
            data={
                "exam": exam,
                "subject": subject,
                "topic": topic,
                "note_path": note_path,
                "action": "note_approval",
            },
        )
        _log_proposal({
            "type": "note_submitted",
            "exam": exam,
            "subject": subject,
            "topic": topic,
            "note_path": note_path,
        })

    # ── YouTube content review ─────────────────────────────────────────────────

    def submit_video_for_review(
        self,
        video: dict,
        topic: str,
        flag_reason: str = "Pending safety review",
    ) -> None:
        """
        Notify NAGA that a YouTube video needs content review before showing to students.
        video: {video_id, title, channel, url}
        """
        _notify(
            user_id=NAGA_USER_ID,
            ntype=NotificationType.VIDEO_PENDING_REVIEW,
            title=f"Dabbu: Video review — {video.get('title', '')[:50]}",
            body=(
                f"Topic: {topic}\n"
                f"Channel: {video.get('channel', 'Unknown')}\n"
                f"Reason flagged: {flag_reason}\n"
                f"URL: {video.get('url', '')}"
            ),
            data={
                "video_id": video.get("video_id", ""),
                "title": video.get("title", ""),
                "channel": video.get("channel", ""),
                "url": video.get("url", ""),
                "topic": topic,
                "flag_reason": flag_reason,
                "action": "video_review",
            },
        )
        _log_proposal({
            "type": "video_flagged",
            "video_id": video.get("video_id", ""),
            "title": video.get("title", ""),
            "topic": topic,
            "flag_reason": flag_reason,
        })

    # ── NAGA approval actions ──────────────────────────────────────────────────

    def approve_study_plan(self, student_id: str, naga_note: str = "") -> Optional[StudyPlan]:
        """
        NAGA approves a proposed study plan.
        Moves status from PROPOSED → APPROVED, copies to active plan, notifies student.
        """
        proposed_path = STUDY_PLANS_DIR / f"{student_id}_proposed.json"
        if not proposed_path.exists():
            logger.warning("Dabbu: no proposed plan found for %s", student_id)
            return None

        plan_data = json.loads(proposed_path.read_text())
        plan_data["status"] = PlanStatus.APPROVED.value
        plan_data["naga_note"] = naga_note
        plan_data["approved_at"] = datetime.utcnow().isoformat()

        active_path = STUDY_PLANS_DIR / f"{student_id}_active.json"
        active_path.write_text(json.dumps(plan_data, indent=2, ensure_ascii=False))
        proposed_path.unlink()

        _notify(
            user_id=student_id,
            ntype=NotificationType.STUDY_PLAN_APPROVED,
            title="Your study plan is ready!",
            body=(
                f"NAGA has approved your {plan_data.get('duration_months')}-month study plan. "
                f"Start from today — {plan_data.get('start_date')}."
                + (f"\nNote from NAGA: {naga_note}" if naga_note else "")
            ),
            data={"plan_id": plan_data.get("plan_id"), "action": "view_study_plan"},
        )

        _log_proposal({
            "type": "study_plan_approved",
            "student_id": student_id,
            "plan_id": plan_data.get("plan_id"),
            "approved_by": NAGA_USER_ID,
        })

        logger.info("Dabbu: study plan approved for student %s", student_id)
        return StudyPlan.from_dict(plan_data)

    def reject_study_plan(self, student_id: str, reason: str = "") -> bool:
        """NAGA rejects the proposed plan. Student keeps their current active plan."""
        proposed_path = STUDY_PLANS_DIR / f"{student_id}_proposed.json"
        if not proposed_path.exists():
            return False

        plan_data = json.loads(proposed_path.read_text())
        plan_data["status"] = PlanStatus.REJECTED.value
        plan_data["naga_note"] = reason

        rejected_path = STUDY_PLANS_DIR / f"{student_id}_rejected_{plan_data.get('plan_id', 'x')[:8]}.json"
        rejected_path.write_text(json.dumps(plan_data, indent=2, ensure_ascii=False))
        proposed_path.unlink()

        _log_proposal({
            "type": "study_plan_rejected",
            "student_id": student_id,
            "plan_id": plan_data.get("plan_id"),
            "reason": reason,
        })
        return True

    def get_active_plan(self, student_id: str) -> Optional[StudyPlan]:
        """Load the currently active study plan for a student."""
        path = STUDY_PLANS_DIR / f"{student_id}_active.json"
        if not path.exists():
            return None
        try:
            return StudyPlan.from_dict(json.loads(path.read_text()))
        except Exception as e:
            logger.error("Dabbu: failed to load active plan for %s: %s", student_id, e)
            return None

    def get_proposed_plan(self, student_id: str) -> Optional[StudyPlan]:
        """Load the pending proposed study plan (awaiting NAGA approval)."""
        path = STUDY_PLANS_DIR / f"{student_id}_proposed.json"
        if not path.exists():
            return None
        try:
            return StudyPlan.from_dict(json.loads(path.read_text()))
        except Exception as e:
            logger.error("Dabbu: failed to load proposed plan for %s: %s", student_id, e)
            return None


    # ── Mid-plan re-diagnostic suggestion ─────────────────────────────────────

    def check_diagnostic_needed(self, student: StudentProfile) -> Optional[str]:
        """
        Evaluate whether the student should take an additional diagnostic test.
        Returns a reason string if a re-diagnostic is recommended, or None if not needed.

        Three triggers:
          A) Time checkpoint  — every 4 weeks since last diagnostic / plan start
          B) Milestone        — at 25%, 50%, 75% of plan elapsed
          C) Persistent weakness — any topic stayed "critical" (score<0.30) for 14+ days
                                   without improvement (ease_factor not rising)
        """
        active_plan = self.get_active_plan(student.student_id)

        # ── A: Time checkpoint (every 4 weeks = 28 days) ──────────────────────
        last_diag_time = student.created_at   # best proxy: when student was created / last diagnostic
        # Look for most recent weakness_map entry as proxy for last diagnostic date
        if student.weakness_map:
            last_attempted = max(w.last_attempted for w in student.weakness_map)
            days_since = (datetime.utcnow() - last_attempted).days
            if days_since >= 28:
                return (
                    f"It's been {days_since} days since your last diagnostic. "
                    f"A quick re-test will show how much your weak areas have improved "
                    f"and let Dabbu update your study plan."
                )

        # ── B: Plan milestone (25%, 50%, 75% elapsed) ─────────────────────────
        if active_plan and active_plan.start_date and active_plan.end_date:
            try:
                plan_start = date.fromisoformat(active_plan.start_date)
                plan_end = date.fromisoformat(active_plan.end_date)
                total_days = (plan_end - plan_start).days or 1
                elapsed_days = (date.today() - plan_start).days
                elapsed_pct = elapsed_days / total_days

                for milestone in (0.25, 0.50, 0.75):
                    # Fire within a ±3 day window around each milestone
                    if abs(elapsed_pct - milestone) <= (3 / total_days):
                        pct_label = f"{int(milestone * 100)}%"
                        return (
                            f"You've reached the {pct_label} milestone of your study plan! "
                            f"A short diagnostic now will confirm your progress and let Dabbu "
                            f"adjust the remaining schedule to focus on what matters most."
                        )
            except (ValueError, ZeroDivisionError):
                pass

        # ── C: Persistent critical weakness (no improvement in 14+ days) ──────
        critical_stale = [
            w for w in student.weakness_map
            if w.score_pct < 0.30
            and (datetime.utcnow() - w.last_attempted).days >= 14
            and w.ease_factor <= 1.5   # SM-2 ease factor low → still struggling
        ]
        if critical_stale:
            topic_names = ", ".join(
                f"{w.subject} → {w.topic}" for w in critical_stale[:3]
            )
            return (
                f"You've been studying but these topics remain very weak: {topic_names}. "
                f"A focused re-diagnostic will help Dabbu understand the exact gap "
                f"and restructure your practice sessions."
            )

        return None

    def suggest_rediagnostic(self, student: StudentProfile) -> bool:
        """
        Run check_diagnostic_needed and, if a reason is found, send the student
        a DIAGNOSTIC_RECOMMENDED notification. Returns True if suggestion was sent.
        """
        reason = self.check_diagnostic_needed(student)
        if not reason:
            return False

        _notify(
            user_id=student.student_id,
            ntype=NotificationType.DIAGNOSTIC_RECOMMENDED,
            title="Dabbu recommends a re-diagnostic",
            body=reason,
            data={
                "action": "start_diagnostic",
                "exam_key": student.exam_target,
                "reason_code": (
                    "time_checkpoint" if "days since" in reason
                    else "milestone" if "milestone" in reason
                    else "persistent_weakness"
                ),
            },
        )

        # FYI copy to NAGA — no action needed, just visibility
        reason_code = (
            "time_checkpoint" if "days since" in reason
            else "milestone" if "milestone" in reason
            else "persistent_weakness"
        )
        _notify(
            user_id=NAGA_USER_ID,
            ntype=NotificationType.DIAGNOSTIC_RECOMMENDED,
            title=f"FYI: Re-diagnostic suggested to {student.student_id[:8]}",
            body=f"[{reason_code}] {reason}",
            data={
                "student_id": student.student_id,
                "exam_key": student.exam_target,
                "reason_code": reason_code,
                "fyi_only": True,
            },
        )

        _log_proposal({
            "type": "diagnostic_recommended",
            "student_id": student.student_id,
            "exam_key": student.exam_target,
            "reason": reason[:200],
        })

        logger.info(
            "Dabbu: re-diagnostic suggested to student %s — %s",
            student.student_id, reason[:80],
        )
        return True


    # ── Progress intervention ──────────────────────────────────────────────────

    def propose_progress_intervention(self, student: StudentProfile, analysis: dict) -> dict:
        """
        Given a progress analysis dict (from progress_tracker.analyze_for_dabbu),
        build a targeted action list, save the intervention proposal, and notify NAGA.
        Returns the intervention record.
        """
        actions = []

        for t in analysis.get("critical_stuck", [])[:3]:
            actions.append({
                "type": "extra_practice",
                "priority": "high",
                "subject": t["subject"],
                "topic": t["topic"],
                "description": (
                    f"Schedule 3 extra practice sessions for '{t['topic']}' "
                    f"(current score {t['score_pct']*100:.0f}% — critical)."
                ),
            })

        for t in analysis.get("stagnant_topics", [])[:2]:
            actions.append({
                "type": "approach_change",
                "priority": "medium",
                "subject": t["subject"],
                "topic": t["topic"],
                "description": (
                    f"'{t['topic']}' has not improved across last 3 checks "
                    f"(score stuck at ~{t['score_pct']*100:.0f}%). "
                    f"Try a different resource or live Q&A session."
                ),
            })

        for t in analysis.get("declining_topics", [])[:2]:
            actions.append({
                "type": "urgent_review",
                "priority": "high",
                "subject": t["subject"],
                "topic": t["topic"],
                "description": (
                    f"'{t['topic']}' score dropped by {t['drop']*100:.0f}pp in the last snapshot. "
                    f"Immediate revision session recommended."
                ),
            })

        if analysis.get("overdue_reviews"):
            overdue_names = ", ".join(
                t["topic"] for t in analysis["overdue_reviews"][:3]
            )
            actions.append({
                "type": "sm2_catch_up",
                "priority": "medium",
                "description": (
                    f"{len(analysis['overdue_reviews'])} SM-2 reviews overdue: {overdue_names}. "
                    f"Review these topics today to avoid forgetting curve."
                ),
            })

        if analysis.get("inactive_7d"):
            actions.append({
                "type": "inactivity_alert",
                "priority": "high",
                "description": (
                    "Student has not logged any study activity in 7+ days. "
                    "Send an encouragement message and check if there are obstacles."
                ),
            })

        if analysis.get("low_plan_completion"):
            actions.append({
                "type": "plan_catch_up",
                "priority": "medium",
                "description": (
                    f"Study plan completion is at {analysis['plan_completion_pct']:.0f}% "
                    f"(target ≥70%). Consider rescheduling missed sessions."
                ),
            })

        severity = analysis.get("severity", "low")
        summary = (
            f"Student ({student.exam_target.upper()}) "
            f"avg score {analysis['avg_score']*100:.0f}% | "
            f"severity: {severity.upper()} | "
            f"{len(actions)} action(s) recommended."
        )

        from pathlib import Path
        import uuid
        intervention = {
            "intervention_id": str(uuid.uuid4()),
            "student_id": student.student_id,
            "exam_target": student.exam_target,
            "proposed_at": datetime.utcnow().isoformat(),
            "status": "pending",
            "severity": severity,
            "summary": summary,
            "actions": actions,
            "analysis_snapshot": {
                "avg_score": analysis["avg_score"],
                "stagnant_count": len(analysis.get("stagnant_topics", [])),
                "declining_count": len(analysis.get("declining_topics", [])),
                "critical_stuck_count": len(analysis.get("critical_stuck", [])),
                "overdue_reviews": len(analysis.get("overdue_reviews", [])),
                "plan_completion_pct": analysis.get("plan_completion_pct", 0.0),
            },
            "naga_note": "",
        }

        # Write to interventions file
        interventions_path = Path("data/dabbu/interventions.jsonl")
        with open(interventions_path, "a") as f:
            f.write(json.dumps(intervention, default=str) + "\n")

        # Notify NAGA
        _notify(
            user_id=NAGA_USER_ID,
            ntype=NotificationType.STUDY_PLAN_PROPOSED,
            title=f"Dabbu: Progress intervention needed — {severity.upper()} severity",
            body=(
                f"{summary}\n"
                f"Actions: {len(actions)} recommendation(s). "
                f"Review in the Approvals tab."
            ),
            data={
                "intervention_id": intervention["intervention_id"],
                "student_id": student.student_id,
                "severity": severity,
                "action": "review_intervention",
            },
        )

        # FYI to student
        _notify(
            user_id=student.student_id,
            ntype=NotificationType.DIAGNOSTIC_RECOMMENDED,
            title="Dabbu has reviewed your progress",
            body=(
                f"Dabbu spotted some patterns in your study data and has sent "
                f"NAGA a set of recommendations. You'll be notified once NAGA reviews them."
            ),
            data={
                "intervention_id": intervention["intervention_id"],
                "severity": severity,
                "fyi_only": True,
            },
        )

        _log_proposal({
            "type": "progress_intervention",
            "intervention_id": intervention["intervention_id"],
            "student_id": student.student_id,
            "severity": severity,
            "actions_count": len(actions),
        })

        logger.info(
            "Dabbu: progress intervention proposed for %s — severity=%s, %d actions",
            student.student_id, severity, len(actions),
        )
        return intervention


# Module-level singleton
_dabbu: DabbuAgent | None = None


def get_dabbu() -> DabbuAgent:
    global _dabbu
    if _dabbu is None:
        _dabbu = DabbuAgent()
    return _dabbu
