import sys
import os
import pytest
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents.diagnostic_agent import DiagnosticAgent
from agents.question_bank import get_questions_for_exam
from models.student import StudentProfile, Language, WeaknessMap


@pytest.fixture
def student():
    return StudentProfile(
        student_id="test_student_001",
        google_sub="mock_sub",
        exam_target="rrb_ntpc",
        preferred_language=Language.ENGLISH,
    )


@pytest.fixture
def agent():
    return DiagnosticAgent()


def test_diagnostic_returns_correct_questions(agent, student):
    result = agent.start_diagnostic(student)
    assert result["total"] == 100, f"Expected 100 questions, got {result['total']}"
    assert len(result["questions"]) == 100


def test_each_question_has_4_options(agent, student):
    result = agent.start_diagnostic(student)
    for q in result["questions"]:
        assert len(q["options"]) == 4, f"Question {q['question_id']} has {len(q['options'])} options"


def test_correct_index_in_range(agent, student):
    result = agent.start_diagnostic(student)
    for q in result["questions"]:
        assert 0 <= q["correct_index"] <= 3, f"correct_index out of range: {q['correct_index']}"


    
def test_explanation_present(agent, student):
    result = agent.start_diagnostic(student)
    for q in result["questions"]:
        assert q.get("explanation_en") or q.get("explanation"), f"Missing explanation for {q.get('id', q.get('question_id'))}"


def test_question_ids_unique(agent, student):
    result = agent.start_diagnostic(student)
    ids = [q.get("id", q.get("question_id")) for q in result["questions"]]
    assert len(ids) == len(set(ids)), "Duplicate questions found in diagnostic test"


def test_weakness_map_identifies_low_scores(agent, student):
    result = agent.start_diagnostic(student)
    session_id = result["session_id"]
    # All wrong answers
    answers = [1 if q["correct_index"] == 0 else 0 for q in result["questions"]]
    submission = agent.submit_answers(student, session_id, answers)
    weakness_map = submission["weakness_map"]
    assert len(weakness_map) > 0, "Weakness map should not be empty"
    scores = [w["score_pct"] for w in weakness_map]
    assert all(0.0 <= s <= 1.0 for s in scores), "Scores should be between 0 and 1"


def test_weakness_map_sorted_weakest_first(agent, student):
    result = agent.start_diagnostic(student)
    session_id = result["session_id"]
    answers = [q["correct_index"] for q in result["questions"]]  # all correct
    submission = agent.submit_answers(student, session_id, answers)
    wm = submission["weakness_map"]
    if len(wm) > 1:
        scores = [w["score_pct"] for w in wm]
        assert scores == sorted(scores), "Weakness map should be sorted weakest first"





