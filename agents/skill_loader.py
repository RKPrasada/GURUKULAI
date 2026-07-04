"""
Dynamic Skill Loader — loads skill context on-demand.

Skills are Markdown files in the skills/ directory.
Rather than stuffing all syllabus content into every prompt (context bloat),
the orchestrator loads only the relevant skill for the current query.
This implements the "dynamic context" half of Context Engineering.
"""

import logging
import os
import re
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).parent.parent / "skills"


@lru_cache(maxsize=128)
def load_skill(skill_name: str) -> str:
    """Load a skill file by name (without .md extension). Cached after first read."""
    path = SKILLS_DIR / f"{skill_name}.md"
    if not path.exists():
        logger.debug(f"Skill not found: {skill_name}")
        return ""
    return path.read_text(encoding="utf-8")


def load_for_topic(topic: str, exam: str) -> str:
    """
    Dynamically select and load the most relevant skill context for a topic.
    Returns combined skill text to inject into the agent's prompt.
    """
    chunks: list[str] = []

    # 1. Exam-specific skill
    exam_skill = load_skill(f"exam_{exam.lower()}")
    if exam_skill:
        chunks.append(f"## Exam Context: {exam.upper()}\n{exam_skill}")

    # 2. Subject-specific skill (inferred from topic keywords)
    topic_lower = topic.lower()
    subject_map = {
        "math": ["algebra", "trigonometry", "calculus", "geometry", "statistics", "number", "arithmetic"],
        "physics": ["motion", "force", "energy", "optics", "electricity", "magnetism", "thermodynamics"],
        "chemistry": ["organic", "inorganic", "reaction", "element", "compound", "acid", "base"],
        "biology": ["cell", "photosynthesis", "respiration", "genetics", "evolution", "ecology", "anatomy"],
        "reasoning": ["coding", "decoding", "blood relation", "syllogism", "direction", "series", "analogy"],
        "general_awareness": ["history", "geography", "polity", "economics", "current"],
    }
    for subject, keywords in subject_map.items():
        if any(kw in topic_lower for kw in keywords):
            subj_skill = load_skill(f"subject_{subject}")
            if subj_skill:
                chunks.append(f"## Subject Guidelines: {subject.title()}\n{subj_skill}")
            break

    # 3. Teaching style skill (always loaded)
    teaching_skill = load_skill("teaching_style")
    if teaching_skill:
        chunks.append(teaching_skill)

    return "\n\n".join(chunks)


def list_skills() -> list[str]:
    """Return names of all available skills."""
    if not SKILLS_DIR.exists():
        return []
    return [p.stem for p in SKILLS_DIR.glob("*.md")]
