"""
Keyword-based YouTube content safety filter for Gurukul AI.

Classification (checked against title + channel + description, case-insensitive):
  BLOCKED  — matches a blocked keyword → dropped silently, logged
  FLAGGED  — matches a flagged keyword → queued for NAGA review, not shown to student
  SAFE     — no keyword match, not blacklisted → shown to student

Two-tier keyword lists live in data/dabbu/content_keywords.json so NAGA can
edit them from the dashboard without touching code:
  {
    "blocked": ["sex", "horror", ...],
    "flagged": ["shorts", "comedy", ...]
  }

The defaults below are seeded on first run if the file doesn't exist.

Permanent channel/video blacklist: data/dabbu/blacklist.json
  { "video_ids": [...], "channels": [...] }
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

Path("data/dabbu").mkdir(parents=True, exist_ok=True)

BLACKLIST_PATH   = Path("data/dabbu/blacklist.json")
KEYWORDS_PATH    = Path("data/dabbu/content_keywords.json")
FLAGGED_PATH     = Path("data/dabbu/flagged_videos.jsonl")

_lock = threading.Lock()

# ── Default keyword lists ──────────────────────────────────────────────────────
# Seeded once; NAGA can edit content_keywords.json via the Approvals tab.

_DEFAULT_BLOCKED = [
    # Adult / sexual
    "sex", "sexual", "adult content", "18+", "nsfw", "nude", "nudity", "porn",
    # Horror / gore
    "horror", "gore", "scary", "ghost", "haunted", "jump scare",
    # Political propaganda / parties
    "bjp", "congress", "aap", "aam aadmi", "shiv sena", "election campaign",
    "political rally", "political speech", "vote for", "political party",
    "religious extremism", "jihad", "communal",
    # Pure entertainment
    "movie review", "film review", "trailer reaction", "bollywood gossip",
    "celebrity gossip", "music video", "song lyrics", "dance video",
    "stand up comedy", "comedy show", "roast video",
    "cricket highlights", "ipl highlights", "sports entertainment",
    "gaming", "gameplay", "let's play", "unboxing", "daily vlog",
    # Gambling / betting
    "gambling", "betting", "casino", "satta matka", "lottery tips",
]

_DEFAULT_FLAGGED = [
    # Could be educational but needs a human eye
    "shorts",           # YouTube Shorts are often low-quality
    "funny", "memes", "trending", "viral",
    "reaction video", "commentary",
    "news channel", "breaking news", "live news",
    "motivation", "motivational speech",   # often off-topic filler
    "top 10", "amazing facts",             # may be click-bait trivia
    "comedy", "humor", "entertainment",
]


def _load_keywords() -> tuple[list[str], list[str]]:
    """Load (blocked, flagged) keyword lists, seeding defaults on first run."""
    if not KEYWORDS_PATH.exists():
        _save_keywords(_DEFAULT_BLOCKED, _DEFAULT_FLAGGED)
    try:
        data = json.loads(KEYWORDS_PATH.read_text(encoding="utf-8"))
        return data.get("blocked", _DEFAULT_BLOCKED), data.get("flagged", _DEFAULT_FLAGGED)
    except Exception:
        return _DEFAULT_BLOCKED, _DEFAULT_FLAGGED


def _save_keywords(blocked: list[str], flagged: list[str]) -> None:
    KEYWORDS_PATH.write_text(
        json.dumps({"blocked": blocked, "flagged": flagged}, indent=2, ensure_ascii=False)
    )


def _text_for_video(video: dict) -> str:
    """Concatenate all searchable fields into one lowercase string."""
    parts = [
        video.get("title", ""),
        video.get("channel", ""),
        video.get("description", ""),
    ]
    return " ".join(parts).lower()


def _match_keyword(text: str, keywords: list[str]) -> str | None:
    """Return first matching keyword, or None."""
    for kw in keywords:
        if kw.lower() in text:
            return kw
    return None


# ── Public: blacklist helpers ──────────────────────────────────────────────────

def _load_blacklist() -> dict:
    if not BLACKLIST_PATH.exists():
        return {"video_ids": [], "channels": []}
    try:
        return json.loads(BLACKLIST_PATH.read_text())
    except Exception:
        return {"video_ids": [], "channels": []}


def _save_blacklist(bl: dict) -> None:
    BLACKLIST_PATH.write_text(json.dumps(bl, indent=2, ensure_ascii=False))


def is_blacklisted(video: dict) -> bool:
    bl = _load_blacklist()
    if video.get("video_id") in bl.get("video_ids", []):
        return True
    channel = (video.get("channel") or "").lower()
    return any(b.lower() in channel for b in bl.get("channels", []))


def classify_video(video: dict) -> dict:
    """
    Keyword-based classification. Returns:
      {"verdict": "SAFE"|"FLAGGED"|"BLOCKED", "reason": str, "video": dict}
    """
    text = _text_for_video(video)
    blocked_kws, flagged_kws = _load_keywords()

    hit = _match_keyword(text, blocked_kws)
    if hit:
        return {"verdict": "BLOCKED", "reason": f"Keyword match: '{hit}'", "video": video}

    hit = _match_keyword(text, flagged_kws)
    if hit:
        return {"verdict": "FLAGGED", "reason": f"Keyword match: '{hit}'", "video": video}

    return {"verdict": "SAFE", "reason": "No keyword matches", "video": video}


# ── Public: main filter ────────────────────────────────────────────────────────

def _append_flagged(entry: dict) -> None:
    with open(FLAGGED_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


def filter_videos(videos: list[dict], topic: str = "") -> list[dict]:
    """
    Filter a list of YouTube videos for student safety.
    Returns only SAFE videos; FLAGGED → NAGA queue; BLOCKED → logged and dropped.
    """
    from agents.dabbu_agent import get_dabbu

    safe = []
    for video in videos:
        if is_blacklisted(video):
            logger.info("ContentFilter: blacklisted — '%s'", video.get("title", "")[:60])
            continue

        result = classify_video(video)
        verdict = result["verdict"]
        title = video.get("title", "")[:60]

        if verdict == "SAFE":
            safe.append(video)

        elif verdict == "FLAGGED":
            logger.info("ContentFilter: FLAGGED '%s' — %s", title, result["reason"])
            _append_flagged({**video, "topic": topic, "flag_reason": result["reason"], "status": "pending"})
            get_dabbu().submit_video_for_review(video=video, topic=topic, flag_reason=result["reason"])

        else:  # BLOCKED
            logger.info("ContentFilter: BLOCKED '%s' — %s", title, result["reason"])
            _append_flagged({**video, "topic": topic, "flag_reason": result["reason"], "status": "blocked"})

    return safe


# ── Public: NAGA review actions ────────────────────────────────────────────────

def list_flagged_videos(status: str = "pending") -> list[dict]:
    if not FLAGGED_PATH.exists():
        return []
    results = []
    try:
        with open(FLAGGED_PATH) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if status == "all" or entry.get("status") == status:
                        results.append(entry)
                except Exception:
                    continue
    except Exception:
        pass
    return results


def approve_video(video_id: str) -> bool:
    return _update_flagged_status(video_id, "approved")


def reject_video(video_id: str) -> bool:
    return _update_flagged_status(video_id, "blocked")


def blacklist_channel(channel_name: str) -> None:
    with _lock:
        bl = _load_blacklist()
        if channel_name.lower() not in [c.lower() for c in bl["channels"]]:
            bl["channels"].append(channel_name)
            _save_blacklist(bl)
    logger.info("ContentFilter: channel '%s' permanently blacklisted", channel_name)


def blacklist_video(video_id: str) -> None:
    with _lock:
        bl = _load_blacklist()
        if video_id not in bl["video_ids"]:
            bl["video_ids"].append(video_id)
            _save_blacklist(bl)


def _update_flagged_status(video_id: str, new_status: str) -> bool:
    if not FLAGGED_PATH.exists():
        return False
    entries = list_flagged_videos(status="all")
    updated = False
    with open(FLAGGED_PATH, "w") as f:
        for entry in entries:
            if entry.get("video_id") == video_id:
                entry["status"] = new_status
                updated = True
            f.write(json.dumps(entry) + "\n")
    return updated


# ── Public: keyword management (for NAGA dashboard) ───────────────────────────

def get_keywords() -> dict:
    """Return current keyword lists for display in NAGA dashboard."""
    blocked, flagged = _load_keywords()
    return {"blocked": blocked, "flagged": flagged}


def add_keyword(word: str, tier: str) -> bool:
    """Add a keyword to 'blocked' or 'flagged' tier. Returns False if already present."""
    if tier not in ("blocked", "flagged"):
        return False
    with _lock:
        blocked, flagged = _load_keywords()
        lst = blocked if tier == "blocked" else flagged
        if word.lower() in [k.lower() for k in lst]:
            return False
        lst.append(word.lower())
        _save_keywords(blocked, flagged)
    logger.info("ContentFilter: added '%s' to %s keywords", word, tier)
    return True


def remove_keyword(word: str, tier: str) -> bool:
    """Remove a keyword from 'blocked' or 'flagged' tier."""
    if tier not in ("blocked", "flagged"):
        return False
    with _lock:
        blocked, flagged = _load_keywords()
        lst = blocked if tier == "blocked" else flagged
        lower = [k.lower() for k in lst]
        if word.lower() not in lower:
            return False
        idx = lower.index(word.lower())
        lst.pop(idx)
        _save_keywords(blocked, flagged)
    logger.info("ContentFilter: removed '%s' from %s keywords", word, tier)
    return True
