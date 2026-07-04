"""
A2UI schema — every agent response carries a _card_type so frontends
can dispatch to the correct renderer without inspecting key names.
"""

from enum import Enum


class CardType(str, Enum):
    NOTE       = "note_card"         # ContentAgent: notes + video + drive
    QUIZ       = "quiz_card"         # AssessmentAgent: first question of a session
    QUIZ_RESULT = "quiz_result_card" # AssessmentAgent: answer evaluation
    DIAGNOSTIC  = "diagnostic_card"  # DiagnosticAgent: start (question list)
    DIAG_RESULT = "diag_result_card" # DiagnosticAgent: submit (weakness map)
    PLAN        = "plan_card"        # ProgressAgent: 7-day schedule
    FEEDBACK    = "feedback_card"    # FeedbackAgent: wrong-answer explanation
    ALERT       = "alert_card"       # Guardrail / quarantine rejection
    VIBE_DIFF   = "vibe_diff_card"   # Pending confirmation gate
    SCHEDULE    = "schedule_card"    # ScheduleAgent: full study schedule
    NAGA_INTERACTION = "naga_interaction_card" # NagaAgent: meeting requests, QA


def tag(response: dict, card_type: CardType) -> dict:
    """Stamp _card_type on a response dict. Returns the same dict."""
    response["_card_type"] = card_type.value
    return response
