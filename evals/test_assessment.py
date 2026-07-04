import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents.assessment_agent import AssessmentAgent
from models.student import StudentProfile, Language, WeaknessMap
from datetime import datetime


def make_student(score_pct: float) -> StudentProfile:
    s = StudentProfile(
        student_id="test_assess_001",
        google_sub="mock",
        exam_target="jee",
        preferred_language=Language.ENGLISH,
    )
    s.weakness_map = [WeaknessMap("Mathematics", "Algebra", score_pct, 10, datetime.utcnow())]
    return s


@pytest.fixture
def agent():
    return AssessmentAgent()


def test_adaptive_difficulty_easy_for_low_scores(agent):
    student = make_student(0.25)
    assert agent.get_adaptive_difficulty(student) == 1


def test_adaptive_difficulty_medium_for_average_scores(agent):
    student = make_student(0.55)
    assert agent.get_adaptive_difficulty(student) == 2


def test_adaptive_difficulty_hard_for_high_scores(agent):
    student = make_student(0.85)
    assert agent.get_adaptive_difficulty(student) == 3


def test_generate_questions_schema_valid(agent):
    student = make_student(0.50)
    questions = agent.generate_questions(student, "Algebra", n=5)
    assert len(questions) > 0
    for q in questions:
        assert q.question_id
        assert len(q.options) == 4
        assert 0 <= q.correct_index <= 3
        assert q.explanation_en
        assert 1 <= q.difficulty <= 3


def test_session_start_returns_first_question(agent):
    student = make_student(0.50)
    result = agent.start_session(student, "Algebra")
    assert "session_id" in result
    assert result["first_question"] is not None
    assert "options" in result["first_question"]


def test_correct_answer_evaluation(agent):
    student = make_student(0.50)
    session = agent.start_session(student, "Algebra")
    session_id = session["session_id"]
    q = session["first_question"]
    correct_idx = q["correct_index"]
    result = agent.evaluate_answer(session_id, q["question_id"], correct_idx)
    assert result["correct"] is True
    assert result["score"] == 1


def test_wrong_answer_evaluation(agent):
    student = make_student(0.50)
    session = agent.start_session(student, "Algebra")
    session_id = session["session_id"]
    q = session["first_question"]
    wrong_idx = (q["correct_index"] + 1) % 4
    result = agent.evaluate_answer(session_id, q["question_id"], wrong_idx)
    assert result["correct"] is False
    assert result["score"] == 0


def test_session_tracks_progress(agent):
    student = make_student(0.50)
    session = agent.start_session(student, "Algebra")
    session_id = session["session_id"]
    q = session["first_question"]
    result = agent.evaluate_answer(session_id, q["question_id"], q["correct_index"])
    assert result["answered"] == 1
    assert result["total"] > 0
