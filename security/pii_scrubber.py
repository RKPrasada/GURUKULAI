import re

# Patterns compiled with correct flags.
# PAN and Voter ID use IGNORECASE so lowercase inputs are caught.
# Phone handles +91 / 91 / 0 country-code prefixes.
# Aadhaar is guarded against math false-positives — see _scrub_aadhaar().
PATTERNS = {
    "phone":    (re.compile(r"(?:(?:\+91|91|0)[- ]?)?[6-9]\d{9}\b"), "[PHONE_REDACTED]"),
    "email":    (re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"), "[EMAIL_REDACTED]"),
    "pan":      (re.compile(r"\b[A-Za-z]{5}[0-9]{4}[A-Za-z]\b"), "[PAN_REDACTED]"),
    "voter_id": (re.compile(r"\b[A-Za-z]{3}[0-9]{7}\b"), "[VOTER_ID_REDACTED]"),
}

# Aadhaar compiled separately — applied with context validation
_AADHAAR_RE = re.compile(r"\b(\d{4})[ ]?(\d{4})[ ]?(\d{4})\b")

# Digits that look like Aadhaar but appear next to math operators are almost
# certainly not PII (e.g. "1234 5678 9012" inside "x = 1234 5678 9012 + 3")
_MATH_CONTEXT_RE = re.compile(r"[\+\-\*/=<>^%]")


def _is_valid_aadhaar(digits: str) -> bool:
    """
    Verhoeff checksum validation for Aadhaar numbers.
    Returns True only if the 12-digit string passes the Verhoeff check,
    reducing false positives on arbitrary 12-digit sequences in math problems.
    """
    D = [
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
        [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
        [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
        [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
        [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
        [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
        [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
        [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
        [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
    ]
    P = [
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
        [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
        [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
        [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
        [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
        [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
        [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
    ]
    INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]
    c = 0
    rev = list(reversed(digits))
    for i, ch in enumerate(rev):
        c = D[c][P[i % 8][int(ch)]]
    return INV[c] == 0


def _scrub_aadhaar(text: str) -> tuple[str, bool]:
    """Scrub Aadhaar numbers with context and Verhoeff validation."""
    found = False
    result = text

    def _replace(m: re.Match) -> str:
        nonlocal found
        digits = m.group(1) + m.group(2) + m.group(3)
        # Skip if surrounded by math operators (likely a computation, not PII)
        start = max(0, m.start() - 10)
        end = min(len(text), m.end() + 10)
        context = text[start:end]
        if _MATH_CONTEXT_RE.search(context):
            return m.group(0)
        # Skip if it doesn't pass the Verhoeff checksum
        if not _is_valid_aadhaar(digits):
            return m.group(0)
        found = True
        return "[AADHAAR_REDACTED]"

    result = _AADHAAR_RE.sub(_replace, result)
    return result, found


class PIIScrubber:
    def scrub(self, text: str) -> tuple[str, list[str]]:
        found: list[str] = []
        result = text

        for pii_type, (pattern, replacement) in PATTERNS.items():
            if pattern.search(result):
                result = pattern.sub(replacement, result)
                found.append(pii_type)

        result, had_aadhaar = _scrub_aadhaar(result)
        if had_aadhaar:
            found.append("aadhaar")

        return result, found

    def has_pii(self, text: str) -> bool:
        _, found = self.scrub(text)
        return bool(found)
