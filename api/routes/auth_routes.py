from __future__ import annotations
"""User registration and login routes."""

import hashlib
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field

from api.middleware import issue_token
from models.auth import UserAuth, Language

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Injected by main.py lifespan so auth can create StudentProfiles
_students_store: dict = {}
_save_student_fn: Callable | None = None
_load_student_fn: Callable | None = None


def setup_auth_store(students: dict, save_fn: Callable, load_fn: Callable) -> None:
    global _students_store, _save_student_fn, _load_student_fn
    _students_store = students
    _save_student_fn = save_fn
    _load_student_fn = load_fn


def _ensure_student_profile(user: UserAuth) -> None:
    """Create or reload a StudentProfile in the in-memory store for this user."""
    if _save_student_fn is None:
        return
    if user.user_id in _students_store:
        return
    # Try loading existing profile from DB first
    existing = _load_student_fn(user.user_id) if _load_student_fn else None
    if existing:
        _students_store[user.user_id] = existing
        return
    # First login — create a fresh StudentProfile in DB
    from models.student import StudentProfile, Language as SL
    from datetime import datetime as dt
    student = StudentProfile(
        student_id=user.user_id,
        google_sub=user.email,
        exam_target=user.exam_target,
        preferred_language=SL(user.preferred_language.value),
        diagnostic_done=False,
        weakness_map=[],
        created_at=dt.utcnow(),
        study_streak_days=0,
        total_questions_attempted=0,
    )
    _save_student_fn(student)

# Use a simple JSON file as database for user credentials (in production, use proper DB)
USERS_DB_PATH = Path("data/users.jsonl")
USERS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _hash_password(password: str) -> str:
    """Hash password with bcrypt."""
    try:
        import bcrypt
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    except ImportError:
        # Fallback to SHA-256 if bcrypt not available (less secure, but functional)
        return hashlib.sha256(password.encode()).hexdigest()


def _verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash."""
    try:
        import bcrypt
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ImportError:
        # Fallback to SHA-256
        return hashlib.sha256(password.encode()).hexdigest() == password_hash


def _load_user_by_username(username: str) -> UserAuth | None:
    """Load user from database by username."""
    if not USERS_DB_PATH.exists():
        return None
    with open(USERS_DB_PATH) as f:
        for line in f:
            if not line.strip():
                continue
            user_dict = json.loads(line)
            if user_dict["username"] == username:
                return UserAuth.from_dict(user_dict)
    return None


def _load_user_by_email(email: str) -> UserAuth | None:
    """Load user from database by email."""
    if not USERS_DB_PATH.exists():
        return None
    with open(USERS_DB_PATH) as f:
        for line in f:
            if not line.strip():
                continue
            user_dict = json.loads(line)
            if user_dict["email"] == email:
                return UserAuth.from_dict(user_dict)
    return None


def _save_user(user: UserAuth) -> None:
    """Save user to database."""
    user_dict = user.to_dict()
    user_dict["password_hash"] = user.password_hash
    with open(USERS_DB_PATH, "a") as f:
        f.write(json.dumps(user_dict) + "\n")


# ────────────────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    email: EmailStr = Field(..., description="Valid email address")
    password: str = Field(..., min_length=8, description="Password (min 8 chars)")
    confirm_password: str = Field(..., description="Confirm password")
    full_name: str = Field(..., min_length=2, max_length=100, description="Full name")
    exam_target: str = Field(..., description="Exam target: rrb_ntpc, rrb_alp, rrb_group_d, rrb_technician, rrb_je, nda, jee, neet")
    preferred_language: str = Field(default="en", description="Language: en or hi")
    trade: str = Field(default="", description="ITI trade (for rrb_alp and rrb_technician)")
    engineering_discipline: str = Field(default="", description="Engineering discipline (for rrb_je)")


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3)
    password: str = Field(...)


@router.post("/register")
async def register(req: RegisterRequest):
    """Register a new student."""
    # Validate input
    if req.password != req.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    if len(req.username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")

    # Check if username already exists
    if _load_user_by_username(req.username):
        raise HTTPException(status_code=409, detail="Username already taken")

    # Check if email already exists
    if _load_user_by_email(req.email):
        raise HTTPException(status_code=409, detail="Email already registered")

    # Validate exam target
    try:
        exam = req.exam_target
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid exam target: {req.exam_target}")

    # Validate language
    try:
        lang = Language(req.preferred_language)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid language: {req.preferred_language}")

    # Create user
    user_id = str(uuid.uuid4())
    password_hash = _hash_password(req.password)
    user = UserAuth(
        user_id=user_id,
        username=req.username,
        email=req.email,
        password_hash=password_hash,
        full_name=req.full_name,
        exam_target=exam,
        preferred_language=lang,
    )
    _save_user(user)

    # Create StudentProfile with trade/discipline captured at registration
    if _save_student_fn:
        from models.student import StudentProfile, Language as SL
        from datetime import datetime as dt
        student = StudentProfile(
            student_id=user_id,
            google_sub=req.email,
            exam_target=req.exam_target,
            preferred_language=SL(req.preferred_language),
            diagnostic_done=False,
            weakness_map=[],
            created_at=dt.utcnow(),
            study_streak_days=0,
            total_questions_attempted=0,
            trade=req.trade,
            engineering_discipline=req.engineering_discipline,
        )
        _save_student_fn(student)
        _students_store[user_id] = student
    else:
        _ensure_student_profile(user)

    # Issue token
    token = issue_token(user_id)
    return {
        "user_id": user_id,
        "username": req.username,
        "full_name": req.full_name,
        "email": req.email,
        "exam_target": req.exam_target,
        "preferred_language": req.preferred_language,
        "trade": req.trade,
        "engineering_discipline": req.engineering_discipline,
        "diagnostic_done": False,
        "weakness_map": [],
        "study_streak_days": 0,
        "total_questions_attempted": 0,
        "access_token": token,
        "token_type": "bearer",
    }


@router.post("/login")
async def login(req: LoginRequest):
    """Login with username and password."""
    user = _load_user_by_username(req.username)
    if not user or not _verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is inactive")

    # Update last login
    user.last_login = datetime.utcnow()

    _ensure_student_profile(user)

    # Issue token
    token = issue_token(user.user_id)

    # Load latest StudentProfile to include diagnostic status in response
    student = _students_store.get(user.user_id)
    return {
        "user_id": user.user_id,
        "username": user.username,
        "full_name": user.full_name,
        "email": user.email,
        "exam_target": user.exam_target,
        "preferred_language": user.preferred_language.value,
        "diagnostic_done": student.diagnostic_done if student else False,
        "weakness_map": [w.to_dict() for w in student.weakness_map] if student else [],
        "study_streak_days": student.study_streak_days if student else 0,
        "total_questions_attempted": student.total_questions_attempted if student else 0,
        "access_token": token,
        "token_type": "bearer",
    }


@router.post("/forgot-password")
async def forgot_password(email: str):
    """Request password reset. Generates a reset token."""
    user = _load_user_by_email(email)
    if not user:
        # Don't reveal if email exists (security best practice)
        return {"message": "If email exists, a reset token will be sent."}

    # Generate reset token (valid for 1 hour)
    reset_token = str(uuid.uuid4())
    reset_file = Path(f"data/reset_tokens/{user.user_id}.txt")
    reset_file.parent.mkdir(parents=True, exist_ok=True)

    # Store token with expiry (simple approach - in production use database)
    with open(reset_file, "w") as f:
        f.write(f"{reset_token}\n{(datetime.utcnow() + __import__('datetime').timedelta(hours=1)).isoformat()}")

    return {
        "message": "Password reset instructions sent",
        "reset_token": reset_token,  # For demo purposes; in production send via email
        "user_id": user.user_id,
    }


class ResetPasswordRequest(BaseModel):
    user_id: str
    reset_token: str
    new_password: str
    confirm_password: str


@router.post("/reset-password")
async def reset_password(req: ResetPasswordRequest):
    user_id, reset_token, new_password, confirm_password = (
        req.user_id, req.reset_token, req.new_password, req.confirm_password
    )
    """Reset password using reset token."""
    if new_password != confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    # Verify reset token
    reset_file = Path(f"data/reset_tokens/{user_id}.txt")
    if not reset_file.exists():
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    with open(reset_file) as f:
        lines = f.readlines()
        if len(lines) < 2:
            raise HTTPException(status_code=400, detail="Invalid reset token")
        stored_token = lines[0].strip()
        expiry = datetime.fromisoformat(lines[1].strip())

    if reset_token != stored_token or datetime.utcnow() > expiry:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    # Update password in database
    if not USERS_DB_PATH.exists():
        raise HTTPException(status_code=404, detail="User not found")

    new_password_hash = _hash_password(new_password)
    users = []
    with open(USERS_DB_PATH) as f:
        for line in f:
            if not line.strip():
                continue
            user_dict = json.loads(line)
            if user_dict["user_id"] == user_id:
                user_dict["password_hash"] = new_password_hash
            users.append(user_dict)

    # Rewrite database with updated password
    with open(USERS_DB_PATH, "w") as f:
        for u in users:
            f.write(json.dumps(u) + "\n")

    # Delete reset token
    reset_file.unlink()

    return {"message": "Password reset successfully"}


@router.post("/change-password")
async def change_password(user_id: str, old_password: str, new_password: str, confirm_password: str):
    """Change password for logged-in user."""
    if new_password != confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    # Verify old password
    if not USERS_DB_PATH.exists():
        raise HTTPException(status_code=404, detail="User not found")

    user = None
    with open(USERS_DB_PATH) as f:
        for line in f:
            if not line.strip():
                continue
            user_dict = json.loads(line)
            if user_dict["user_id"] == user_id:
                user = user_dict
                break

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not _verify_password(old_password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect current password")

    # Update password
    new_password_hash = _hash_password(new_password)
    users = []
    with open(USERS_DB_PATH) as f:
        for line in f:
            if not line.strip():
                continue
            user_dict = json.loads(line)
            if user_dict["user_id"] == user_id:
                user_dict["password_hash"] = new_password_hash
            users.append(user_dict)

    # Rewrite database with updated password
    with open(USERS_DB_PATH, "w") as f:
        for u in users:
            f.write(json.dumps(u) + "\n")

    return {"message": "Password changed successfully"}
