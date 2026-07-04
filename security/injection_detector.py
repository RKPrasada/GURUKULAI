from __future__ import annotations
import re

PATTERNS = [
    # ── Role override ─────────────────────────────────────────────────────────
    (r"ignore (previous|all|your) instructions",                 "role_override"),
    (r"forget (everything|what|your)",                           "role_override"),
    (r"you are now",                                             "role_override"),
    (r"pretend (you are|to be)",                                 "role_override"),
    (r"act as (if|a|an)",                                        "role_override"),
    (r"disregard (your|all|previous)",                           "role_override"),
    (r"the (following|above) instructions? (override|supersede|replace)", "role_override"),
    (r"\bignore\b.{0,20}\binstructions?\b",                     "role_override"),
    (r"roleplay as|simulate being|impersonate",                  "role_override"),
    (r"your (real|true|actual) (self|purpose|goal|instructions)", "prompt_extraction"),

    # ── Prompt extraction ──────────────────────────────────────────────────────
    (r"reveal (your|the) (system|hidden|secret) prompt",         "prompt_extraction"),
    (r"what (are|were) your instructions",                        "prompt_extraction"),
    (r"show me your (prompt|instructions|rules)",                 "prompt_extraction"),
    (r"(print|display|output|dump) (your |the )?(system |)prompt", "prompt_extraction"),

    # ── Jailbreak ─────────────────────────────────────────────────────────────
    (r"DAN|do anything now",                                     "jailbreak"),
    (r"\bjailbreak\b",                                           "jailbreak"),
    (r"developer mode",                                          "jailbreak"),
    (r"bypass|circumvent|override (safety|filter|restriction)",  "jailbreak"),
    (r"ignore (all|your|our|the|every).{0,20}(safety|guideline|rule|policy|filter)", "jailbreak"),
    (r"as (an|a) (unrestricted|uncensored|unfiltered) (ai|model|assistant)", "jailbreak"),

    # ── Scope violation ────────────────────────────────────────────────────────
    (r"(hack|cheat|exploit) (the|this) (exam|system|app)",       "scope_violation"),
    (r"give me (the |all |all the )?answers",                    "scope_violation"),

    # ── Injection markers (template / token injection) ─────────────────────────
    (r"\[SYSTEM\]|\[INST\]|\[HUMAN\]",                           "injection_marker"),
    (r"new (system|override|master) (prompt|instructions?)",     "injection_marker"),
    (r"<\|im_start\|>|<\|im_end\|>|\[INST\]|\[/INST\]",         "injection_marker"),

    # ── Assistant emulation (indirect injection) ───────────────────────────────
    (r"^assistant\s*:",                                          "indirect_injection"),
    (r"\nassistant\s*:",                                         "indirect_injection"),
    (r"(my|the) teacher said (you should|to) ignore",            "indirect_injection"),
    (r"(the |a )?previous (response|message|output) said",       "indirect_injection"),

    # ── Obfuscation / separator tricks ────────────────────────────────────────
    # Catches i.g.n.o.r.e / i-g-n-o-r-e / i g n o r e
    (r"i[\.\-_ ]g[\.\-_ ]n[\.\-_ ]o[\.\-_ ]r[\.\-_ ]e",        "role_override"),
    # Catches j.a.i.l.b.r.e.a.k
    (r"j[\.\-_ ]a[\.\-_ ]i[\.\-_ ]l[\.\-_ ]b[\.\-_ ]r[\.\-_ ]e[\.\-_ ]a[\.\-_ ]k", "jailbreak"),

    # ── Base64 / Encoding obfuscation ─────────────────────────────────────────
    # Detects long base64 strings (at least 40 chars) which are suspicious, and common encoded attack words
    (r"(?:[A-Za-z0-9+/]{4}){10,}(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?", "base64_obfuscation"),
    (r"aWdub3Jl|amFpbGJyZWFr|c3lzdGVtIHByb21wdA|Zm9yZ2V0", "base64_obfuscation"),

    # ── Hindi / Devanagari injection patterns ─────────────────────────────────
    # "forget old rules" / "ignore previous rules"
    (r"(पुराने|पिछले|सभी) (नियमों|निर्देशों) को (भूल|अनदेखा|नज़रअंदाज़) (जाओ|करो|कर)", "role_override"),
    # "show system prompt"
    (r"सिस्टम प्रॉम्प्ट (दिखाओ|बताओ|प्रिंट करो)",               "prompt_extraction"),
    # "you are now" in Hindi
    (r"अब तुम .{0,20} हो",                                      "role_override"),
    # "ignore instructions" in Hindi
    (r"(निर्देशों|नियमों) को (अनदेखा|नज़रअंदाज़) करो",            "role_override"),
    # "pretend you are" in Hindi
    (r"(दिखावा|नाटक) करो (कि|जैसे) तुम",                       "role_override"),
    # Hinglish: "instructions ignore karo / bhool jao"
    (r"instructions (ignore|bhool|forget) (karo|kar|do)",        "role_override"),
    # "jailbreak" transliterated
    (r"jailbreak\s*(karo|kar|karna)",                             "jailbreak"),
    # "give me answers" in Hindi
    (r"(सभी |सारे )?(जवाब|उत्तर) (दो|बताओ|दे दो)",              "scope_violation"),
]

COMPILED = [(re.compile(p, re.IGNORECASE | re.MULTILINE), t) for p, t in PATTERNS]


class InjectionDetector:
    def detect(self, text: str) -> str | None:
        for pattern, threat_type in COMPILED:
            if pattern.search(text):
                return threat_type
        return None

    def detect_all(self, text: str) -> list[str]:
        found = []
        for pattern, threat_type in COMPILED:
            if pattern.search(text) and threat_type not in found:
                found.append(threat_type)
        return found

    def clean(self, text: str) -> tuple[str, str | None]:
        threat = self.detect(text)
        return text, threat
