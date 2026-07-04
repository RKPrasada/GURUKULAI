from __future__ import annotations
import re
from security.injection_detector import InjectionDetector
from security.pii_scrubber import PIIScrubber

FORBIDDEN_OUTPUT = [
    r"system prompt",
    r"ignore (previous|all) instructions",
    r"my real instructions",
    r"internal agent",
    r"architecture",
    r"secret key",
    r"api[_ ]key",
]
COMPILED_FORBIDDEN = [re.compile(p, re.IGNORECASE) for p in FORBIDDEN_OUTPUT]

SAFE_REDIRECT_EN = "I'm here to help you study! What topic would you like to explore?"
SAFE_REDIRECT_HI = "मैं आपकी पढ़ाई में मदद करने के लिए यहाँ हूँ! आप कौन सा विषय पढ़ना चाहते हैं?"


class InputGuard:
    def __init__(self):
        self._detector = InjectionDetector()
        self._scrubber = PIIScrubber()

    def process(self, text: str) -> tuple[str, str | None]:
        threat = self._detector.detect(text)
        clean, _ = self._scrubber.scrub(text)
        return clean, threat


class OutputGuard:
    def __init__(self):
        self._scrubber = PIIScrubber()

    def process(self, response: str, language: str = "en") -> str:
        # Block forbidden content leakage
        for pattern in COMPILED_FORBIDDEN:
            if pattern.search(response):
                return SAFE_REDIRECT_HI if language == "hi" else SAFE_REDIRECT_EN
        # Scrub any PII that the LLM may have hallucinated into the response
        clean, _ = self._scrubber.scrub(response)
        return clean
