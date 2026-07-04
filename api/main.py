from __future__ import annotations
import json
import logging
import os
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel

from agents.orchestrator import OrchestratorAgent
from agents.diagnostic_agent import DiagnosticAgent
from agents.assessment_agent import AssessmentAgent
from agents.progress_agent import ProgressAgent
from api.auth import GoogleOAuth
from api.middleware import issue_token, require_auth
from api.routes import student as student_routes
from api.routes import session as session_routes
from api.routes import progress as progress_routes
from api.routes import auth_routes
from api.routes import admin as admin_routes
from api.routes import mentor as mentor_routes
from api.routes import dabbu_routes
from api.routes import practice_routes
from api.routes import progress_routes as new_progress_routes
from api.routes import mock_routes
from models.student import StudentProfile, Language

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = os.getenv("DATABASE_URL", "sqlite:///./vidyabot.db").replace("sqlite:///", "")
DEV_MODE = not os.getenv("GOOGLE_CLIENT_ID")

_students: dict[str, StudentProfile] = {}
_save_student_fn = None   # set after _save_student_to_db is defined; imported by practice_routes
_orchestrator: OrchestratorAgent | None = None
_diagnostic: DiagnosticAgent | None = None
_assessment: AssessmentAgent | None = None
_progress: ProgressAgent | None = None
_oauth: GoogleOAuth | None = None


def _init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS students (
            student_id TEXT PRIMARY KEY,
            google_sub_encrypted TEXT,
            exam_target TEXT,
            preferred_language TEXT,
            diagnostic_done INTEGER DEFAULT 0,
            weakness_map_json TEXT DEFAULT '[]',
            created_at TEXT,
            study_streak_days INTEGER DEFAULT 0,
            total_questions_attempted INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            student_id TEXT,
            session_type TEXT,
            started_at TEXT,
            last_active TEXT,
            data_json TEXT DEFAULT '{}'
        );
    """)
    # Migration: add columns added after initial schema (safe to re-run)
    for col_def in [
        "trade TEXT DEFAULT ''",
        "engineering_discipline TEXT DEFAULT ''",
    ]:
        try:
            conn.execute(f"ALTER TABLE students ADD COLUMN {col_def}")
        except sqlite3.OperationalError:
            pass  # column already exists
    conn.commit()
    conn.close()


def _load_student_from_db(student_id: str) -> StudentProfile | None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("SELECT * FROM students WHERE student_id = ?", (student_id,))
    row = cur.fetchone()
    col_names = [desc[0] for desc in cur.description] if cur.description else []
    conn.close()
    if not row:
        return None
    d = dict(zip(col_names, row))
    from datetime import datetime
    from models.student import WeaknessMap
    weakness_map = [WeaknessMap.from_dict(w) for w in json.loads(d.get("weakness_map_json") or "[]")]
    return StudentProfile(
        student_id=d["student_id"],
        google_sub=d.get("google_sub_encrypted") or "",
        exam_target=d["exam_target"],
        preferred_language=Language(d["preferred_language"]),
        diagnostic_done=bool(d.get("diagnostic_done", 0)),
        weakness_map=weakness_map,
        created_at=datetime.fromisoformat(d["created_at"]),
        study_streak_days=d.get("study_streak_days", 0),
        total_questions_attempted=d.get("total_questions_attempted", 0),
        trade=d.get("trade") or "",
        engineering_discipline=d.get("engineering_discipline") or "",
    )


def _save_student_to_db(student: StudentProfile):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT OR REPLACE INTO students
        (student_id, google_sub_encrypted, exam_target, preferred_language, diagnostic_done,
         weakness_map_json, created_at, study_streak_days, total_questions_attempted,
         trade, engineering_discipline)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (
        student.student_id,
        student.google_sub,
        student.exam_target,
        student.preferred_language.value,
        int(student.diagnostic_done),
        json.dumps([w.to_dict() for w in student.weakness_map]),
        student.created_at.isoformat(),
        student.study_streak_days,
        student.total_questions_attempted,
        student.trade,
        student.engineering_discipline,
    ))
    conn.commit()
    conn.close()
    _students[student.student_id] = student


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _orchestrator, _diagnostic, _assessment, _progress, _oauth, _save_student_fn
    _init_db()
    _orchestrator = OrchestratorAgent()
    _diagnostic = DiagnosticAgent()
    _assessment = AssessmentAgent()
    _progress = ProgressAgent()
    _oauth = GoogleOAuth()
    _save_student_fn = _save_student_to_db
    student_routes.set_students_store(_students)
    session_routes.setup_agents(_students, _orchestrator, _diagnostic, _assessment,
                                load_fn=_load_student_from_db, save_fn=_save_student_to_db)
    progress_routes.setup_progress(_students, _progress)
    auth_routes.setup_auth_store(_students, _save_student_to_db, _load_student_from_db)
    mentor_routes.setup_mentor(_students)
    from scripts.mock_scheduler import start_scheduler
    start_scheduler()
    logger.info(f"VidyaBot started | dev_mode={DEV_MODE} | MockScheduler running")
    yield
    logger.info("VidyaBot shutting down")


app = FastAPI(title="VidyaBot API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(student_routes.router)
app.include_router(session_routes.router)
app.include_router(progress_routes.router)
app.include_router(admin_routes.router)
app.include_router(mentor_routes.router)
app.include_router(dabbu_routes.router)
app.include_router(practice_routes.router)
app.include_router(new_progress_routes.router)
app.include_router(new_progress_routes.intervention_router)
app.include_router(mock_routes.router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0", "dev_mode": DEV_MODE}


class DemoLoginRequest(BaseModel):
    exam_target: str = "rrb_ntpc"
    preferred_language: str = "en"
    name: str = "Demo Student"


@app.post("/api/student/demo")
async def demo_login(req: DemoLoginRequest):
    student = _oauth.dev_login(req.exam_target, req.preferred_language, req.name)
    _save_student_to_db(student)
    token = issue_token(student.student_id)
    return {**student.to_dict(), "access_token": token, "token_type": "bearer"}


@app.get("/auth/login")
async def auth_login():
    if DEV_MODE:
        return {"message": "OAuth not configured. Use /api/student/demo for demo login."}
    url, state = _oauth.get_authorization_url()
    return RedirectResponse(url)


@app.get("/auth/callback")
async def auth_callback(code: str, state: str, exam_target: str = "rrb_ntpc", language: str = "en"):
    if DEV_MODE:
        raise HTTPException(400, "OAuth not configured")
    try:
        _, user_info = _oauth.handle_callback(code, state)
        student = _oauth.create_or_get_student(user_info, exam_target, language)
        existing = _load_student_from_db(student.student_id)
        if existing:
            student = existing
        _save_student_to_db(student)
        token = issue_token(student.student_id)
        return RedirectResponse(
            f"{os.getenv('FRONTEND_URL', 'http://localhost:8501')}?student_id={student.student_id}&token={token}"
        )
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        raise HTTPException(500, str(e))
