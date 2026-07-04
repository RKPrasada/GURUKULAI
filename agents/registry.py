from __future__ import annotations
"""
A2A Agent Registry — Agent-to-Agent discovery and delegation.

Every specialist agent registers an AgentCard describing its capabilities.
The orchestrator queries the registry to route tasks instead of hardcoding
conditionals. This makes agents swappable and independently testable.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Awaitable, Any


class Capability(str, Enum):
    DIAGNOSTIC    = "diagnostic"     # placement test + weakness mapping
    STUDY_CONTENT = "study_content"  # generate notes + fetch resources
    ASSESSMENT    = "assessment"     # adaptive MCQ generation + evaluation
    FEEDBACK      = "feedback"       # wrong-answer explanation
    PROGRESS      = "progress"       # study plan + calendar + digest
    ORCHESTRATION = "orchestration"  # routes to other agents
    SCHEDULE      = "schedule"       # full syllabus schedule
    MENTOR        = "mentor"         # naga interactions


@dataclass
class AgentCard:
    name: str
    version: str
    capabilities: list[Capability]
    description: str
    trigger_keywords: list[str]
    handler: Callable[..., Awaitable[Any]]
    priority: int = 0  # higher = preferred when multiple agents match


class AgentRegistry:
    """Registry of all available agents and their capabilities."""

    def __init__(self):
        self._agents: dict[str, AgentCard] = {}

    def register(self, card: AgentCard) -> None:
        self._agents[card.name] = card

    def get(self, name: str) -> AgentCard | None:
        return self._agents.get(name)

    def discover(self, capability: Capability) -> list[AgentCard]:
        """Return all agents that support a given capability, sorted by priority."""
        return sorted(
            [a for a in self._agents.values() if capability in a.capabilities],
            key=lambda a: -a.priority,
        )

    def route(self, message: str) -> AgentCard | None:
        """Return the best-matching agent for a free-text message."""
        msg_lower = message.lower()
        scored: list[tuple[int, AgentCard]] = []
        for agent in self._agents.values():
            score = sum(1 for kw in agent.trigger_keywords if kw in msg_lower)
            if score > 0:
                scored.append((score + agent.priority, agent))
        if not scored:
            return None
        scored.sort(key=lambda x: -x[0])
        return scored[0][1]

    def list_all(self) -> list[dict]:
        return [
            {
                "name": a.name,
                "version": a.version,
                "capabilities": [c.value for c in a.capabilities],
                "description": a.description,
            }
            for a in self._agents.values()
        ]


def build_registry(diagnostic, content, assessment, feedback, progress, naga) -> AgentRegistry:
    """Wire all agents into the registry at startup."""
    registry = AgentRegistry()

    registry.register(AgentCard(
        name="diagnostic",
        version="1.0",
        capabilities=[Capability.DIAGNOSTIC],
        description="30-question placement test that maps student weaknesses by topic",
        trigger_keywords=["diagnos", "placement", "test my level", "where am i", "start learning"],
        handler=diagnostic.run,
        priority=10,
    ))

    registry.register(AgentCard(
        name="content",
        version="1.0",
        capabilities=[Capability.STUDY_CONTENT],
        description="Generates bilingual study notes, saves to Drive, fetches YouTube videos",
        trigger_keywords=["explain", "notes", "teach", "what is", "tell me about", "define",
                          "describe", "concept", "summarize", "revise", "learn"],
        handler=content.run,
        priority=8,
    ))

    registry.register(AgentCard(
        name="assessment",
        version="1.0",
        capabilities=[Capability.ASSESSMENT],
        description="Adaptive MCQ sessions with difficulty adjustment based on performance",
        trigger_keywords=["test me", "quiz", "practice", "mcq", "questions", "assess",
                          "evaluate", "mock test", "question paper"],
        handler=assessment.run,
        priority=9,
    ))

    registry.register(AgentCard(
        name="feedback",
        version="1.0",
        capabilities=[Capability.FEEDBACK],
        description="Explains wrong answers with step-by-step solutions in EN or HI",
        trigger_keywords=["why", "how", "wrong", "didn't understand", "confused",
                          "explain again", "not clear", "mistake"],
        handler=feedback.explain_wrong_answer,
        priority=7,
    ))

    registry.register(AgentCard(
        name="progress",
        version="1.0",
        capabilities=[Capability.PROGRESS],
        description="Generates long-term study plans, syllabus schedules, Calendar events, sends Gmail digest",
        trigger_keywords=["progress", "plan", "streak", "digest", "performance",
                          "report", "calendar", "email", "weekly", "schedule", "syllabus", "timetable", "full syllabus"],
        handler=progress.run,
        priority=6,
    ))

    registry.register(AgentCard(
        name="naga",
        version="1.0",
        capabilities=[Capability.MENTOR],
        description="Human mentor routing: handles 1-on-1 meeting requests, Q&A doubts.",
        trigger_keywords=["1 on 1", "one on one", "meeting", "ask naga", "doubt", "question", "help me naga"],
        handler=naga.run,
        priority=11,
    ))

    return registry
