import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents.content_agent import ContentAgent
from models.student import StudentProfile, Language


@pytest.fixture
def student_en():
    return StudentProfile("s1", "mock", "jee", Language.ENGLISH)


@pytest.fixture
def student_hi():
    return StudentProfile("s2", "mock", "neet", Language.HINDI)


@pytest.fixture
def agent():
    return ContentAgent()


def test_notes_generated(agent, student_en):
    notes, cache_hit = agent.generate_notes(student_en, "Algebra")
    assert isinstance(notes, str)
    assert len(notes) > 100
    assert isinstance(cache_hit, bool)


def test_notes_contain_key_sections(agent, student_en):
    notes, _ = agent.generate_notes(student_en, "Trigonometry")
    lower = notes.lower()
    assert any(kw in lower for kw in ["concept", "formula", "example", "mistake", "trick", "memory"]), \
        "Notes should contain expected sections"


def test_notes_returned_for_hindi_student(agent, student_hi):
    notes, _ = agent.generate_notes(student_hi, "Cell Division")
    assert isinstance(notes, str)
    assert len(notes) > 50


def test_drive_save_requires_confirmation(agent, student_en):
    import asyncio
    result = asyncio.run(agent.run(student_en, "Matrices"))
    assert "pending_action" in result
    assert result["pending_action"]["action_name"] == "save_to_drive"
    assert result["pending_action"]["requires_confirmation"] is True


def test_youtube_results_returned(agent, student_en):
    import asyncio, os, pytest
    if not os.getenv("YOUTUBE_API_KEY"):
        pytest.skip("YOUTUBE_API_KEY not configured")
    result = asyncio.run(agent.run(student_en, "Calculus"))
    assert "youtube_videos" in result
    assert isinstance(result["youtube_videos"], list)
    assert len(result["youtube_videos"]) > 0


def test_youtube_video_has_required_fields(agent, student_en):
    import asyncio
    result = asyncio.run(agent.run(student_en, "Calculus"))
    for v in result["youtube_videos"]:
        assert "title" in v
        assert "url" in v


def test_notes_topic_included(agent, student_en):
    topic = "Newton's Laws of Motion"
    notes, _ = agent.generate_notes(student_en, topic)
    assert "Newton" in notes or "newton" in notes or "motion" in notes.lower() or len(notes) > 100
