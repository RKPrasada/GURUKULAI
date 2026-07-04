"""Admin routes for managing system configuration."""

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.middleware import require_auth

router = APIRouter(prefix="/api/admin", tags=["admin"])

CHANNELS_FILE = Path("data/youtube_channels.json")


class YouTubeChannel(BaseModel):
    channel_id: str
    name: str
    description: str = ""
    priority: int = 1


def _require_admin(auth_id: str = Depends(require_auth)) -> str:
    """For now, only the first registered user (Ravi Kumar) can admin.
    In production, check a proper admin flag in the database."""
    # TODO: check if auth_id has admin=True in database
    return auth_id


def _load_channels() -> dict:
    """Load YouTube channels config from file."""
    if not CHANNELS_FILE.exists():
        return {}
    with open(CHANNELS_FILE) as f:
        return json.load(f)


def _save_channels(data: dict) -> None:
    """Save YouTube channels config to file."""
    CHANNELS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CHANNELS_FILE, "w") as f:
        json.dump(data, f, indent=2)


@router.get("/youtube-channels")
async def list_youtube_channels(auth_id: str = Depends(require_auth)):
    """List all curated YouTube channels per exam."""
    return _load_channels()


@router.get("/youtube-channels/{exam_target}")
async def list_exam_channels(exam_target: str, auth_id: str = Depends(require_auth)):
    """List channels for a specific exam."""
    channels = _load_channels()
    if exam_target not in channels:
        raise HTTPException(status_code=404, detail=f"No channels configured for {exam_target}")
    return {"exam_target": exam_target, "channels": channels[exam_target]}


@router.post("/youtube-channels/{exam_target}")
async def add_channel(
    exam_target: str,
    channel: YouTubeChannel,
    admin_id: str = Depends(_require_admin),
):
    """Add a YouTube channel to curated list for an exam."""
    channels = _load_channels()
    if exam_target not in channels:
        channels[exam_target] = []

    # Check if channel already exists
    if any(c["channel_id"] == channel.channel_id for c in channels[exam_target]):
        raise HTTPException(status_code=409, detail="Channel already exists for this exam")

    channels[exam_target].append(channel.dict())
    # Sort by priority
    channels[exam_target].sort(key=lambda x: x["priority"])
    _save_channels(channels)

    return {"message": "Channel added", "channel": channel.dict()}


@router.put("/youtube-channels/{exam_target}/{channel_id}")
async def update_channel(
    exam_target: str,
    channel_id: str,
    channel: YouTubeChannel,
    admin_id: str = Depends(_require_admin),
):
    """Update a YouTube channel in the curated list."""
    channels = _load_channels()
    if exam_target not in channels:
        raise HTTPException(status_code=404, detail=f"No channels for {exam_target}")

    # Find and update
    for i, c in enumerate(channels[exam_target]):
        if c["channel_id"] == channel_id:
            channels[exam_target][i] = channel.dict()
            channels[exam_target].sort(key=lambda x: x["priority"])
            _save_channels(channels)
            return {"message": "Channel updated", "channel": channel.dict()}

    raise HTTPException(status_code=404, detail="Channel not found")


@router.delete("/youtube-channels/{exam_target}/{channel_id}")
async def delete_channel(
    exam_target: str,
    channel_id: str,
    admin_id: str = Depends(_require_admin),
):
    """Remove a YouTube channel from the curated list."""
    channels = _load_channels()
    if exam_target not in channels:
        raise HTTPException(status_code=404, detail=f"No channels for {exam_target}")

    channels[exam_target] = [c for c in channels[exam_target] if c["channel_id"] != channel_id]
    if not channels[exam_target]:
        del channels[exam_target]

    _save_channels(channels)
    return {"message": "Channel deleted"}
