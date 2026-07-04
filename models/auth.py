"""User authentication model for registration and login."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum





class Language(str, Enum):
    ENGLISH = "en"
    HINDI = "hi"


@dataclass
class UserAuth:
    """Stores registration credentials — separate from StudentProfile for security."""
    user_id: str  # UUID
    username: str
    email: str
    password_hash: str  # bcrypt or similar
    full_name: str
    exam_target: str
    preferred_language: Language
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_login: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "exam_target": self.exam_target,
            "preferred_language": self.preferred_language.value,
            "created_at": self.created_at.isoformat(),
            "last_login": self.last_login.isoformat(),
            "is_active": self.is_active,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "UserAuth":
        return cls(
            user_id=d["user_id"],
            username=d["username"],
            email=d["email"],
            password_hash=d["password_hash"],
            full_name=d["full_name"],
            exam_target=d["exam_target"],
            preferred_language=Language(d["preferred_language"]),
            created_at=datetime.fromisoformat(d.get("created_at", datetime.utcnow().isoformat())),
            last_login=datetime.fromisoformat(d.get("last_login") or datetime.utcnow().isoformat()),
            is_active=d.get("is_active", True),
        )
