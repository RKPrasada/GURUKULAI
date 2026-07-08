# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**Gurukul AI** (codebase: vidyabot) — adaptive bilingual (EN + HI) AI tutor for Indian competitive exams.

**Exams supported:** RRB NTPC · RRB ALP · RRB Group D · RRB Technician · RRB JE · NDA · JEE · NEET

**Stack:** FastAPI (:8000) + React 18 / Vite (:3000) + Flutter (mobile) + OpenRouter LLM API.

## Commands

```bash
# Backend
uvicorn api.main:app --reload --port 8000

# React frontend (separate terminal)
cd web && npm run dev                     # vite.config.ts has port: 3000

# Combined launcher
python launcher_react.py                  # starts both, opens browser

# Tests
pytest evals/ -v
pytest evals/test_security.py -v         # 76 tests — must all pass
python evals/eval_runner.py              # formatted summary
```

## LLM Layer — OpenRouter

All agents call `agents/base.py:call_gemini(prompt, system)` — the name is historical, it now calls **OpenRouter** not Gemini directly. Set `OPENROUTER_API_KEY` in `.env`.

`call_gemini` tries models in order until one responds 200:
1. `nvidia/nemotron-3-ultra-550b-a55b:free`
2. `nvidia/nemotron-3-super-120b-a12b:free`
3. `google/gemma-4-26b-a4b-it:free`
4. `openai/gpt-oss-20b:free`
5. `liquid/lfm-2.5-1.2b-instruct:free`

Free-tier models on OpenRouter rotate availability — if one returns 404/429 the next is tried automatically. To add/swap models edit `_MODELS` in `agents/base.py`.

## Identity System — Two Stores, One UUID

- **UserAuth** (`data/users.jsonl`) — credentials: username, password_hash, email, exam_target
- **StudentProfile** (`vidyabot.db` SQLite) — learning state: weakness_map, diagnostic_done, streak, trade, engineering_discipline
- Same UUID is used as both `user_id` (auth) and `student_id` (profile)
- `auth_routes.register()` creates the StudentProfile directly at registration (not via `_ensure_student_profile`) so `trade` and `engineering_discipline` are captured
- `session._get_student()` lazy-loads from SQLite on cache miss
- `session.submit_diagnostic` calls `_save_student_fn(student)` immediately to persist weakness_map — without this, diagnostic results reset on server restart

### Dabbu Study Plan (July 2026)
- `GET /api/dabbu/study-plan` — returns active plan (if NAGA-approved) or proposed plan
- `GET /api/dabbu/study-plan/proposed` — pending plan awaiting NAGA review
- `POST /api/dabbu/study-plan` — generate a new plan (requires `diagnostic_done`)
- Plan generator: `_DAILY_SLOTS = [7, 9, 11, 14, 16]` — five 2-hour slots per day
- Data: `data/study_plans/{student_id}_active.json` + `{student_id}_proposed.json`
- `diagnostic_done` auto-heal: if `weakness_map` is non-empty but flag is `False`, auto-set and persist to SQLite
- **Web:** `StudyPlanPage.tsx` — year overview calendar (stacked per-slot bars), week strip, `DayTimeline` with time column + dot connector + colored left-border card
- **Mobile:** `study_plan_screen.dart` — linked from HomeScreen card + quick-action grid

### New StudentProfile fields (July 2026)
- `trade: str` — ITI trade (e.g. "Electrician") — required for RRB ALP and RRB Technician
- `engineering_discipline: str` — e.g. "Civil", "Electrical" — required for RRB JE
- DB columns added via `ALTER TABLE IF NOT EXISTS` migration in `_init_db()`
- `_load_student_from_db` uses `dict(zip(col_names, row))` with live column names — safe against schema changes

## NAGA — Human Mentor Role

Single named human mentor account, not a bot.
- **Login:** `username=naga` / `password=<set via NAGA_PASSWORD env var>`
- Auto-seeded to `data/users.jsonl` on startup via `mentor_routes._seed_naga_user()`
- `Layout.tsx` shows NAGA-specific sidebar when `student.user_id === 'naga'`
- Data stored in JSONL files under `data/mentor/` (questions, classes, meetings, notifications)
- `naga_agent.py` handles student-facing NAGA interactions (question posting, meeting requests)
- **NAGA Dashboard tabs:** Overview / Approvals (Dabbu plans + notes + videos + progress interventions + keyword blocklist) / Meetings / Schedule

## Dabbu — Autonomous AI Agent

Dabbu is the AI agent that acts autonomously and proposes actions. NAGA (human) reviews and approves/amends.

- `agents/dabbu_agent.py` — main agent; proposes study plans, notes, video curation, progress interventions
- All Dabbu proposals land in a queue → NAGA sees them in the Approvals tab → student sees only after NAGA signs off
- **`propose_progress_intervention(student, analysis)`** — called when progress analysis flags medium/high severity; saves to `data/dabbu/interventions.jsonl`
- **Notifications:** NAGA gets actionable notification; student gets `fyi_only: True` notification
- Study plan: `data/study_plans/{student_id}_active.json` (approved) + `{student_id}_proposed.json` (pending)

## Agent Architecture

```
OrchestratorAgent
  └── AgentRegistry.route(message) → keyword scoring → best AgentCard
        ├── DiagnosticAgent   — 3-stage placement test, builds weakness_map
        ├── ContentAgent      — study notes → returns { notes, drive_url, youtube_videos }
        ├── AssessmentAgent   — adaptive MCQs (difficulty 1/2/3 from weakness_map avg)
        ├── FeedbackAgent     — wrong-answer explanations, bilingual
        ├── ProgressAgent     — study plan from weakness_map + Gemini
        ├── ScheduleAgent     — weekly/monthly schedule generation
        └── NagaAgent         — student↔NAGA interactions

DabbuAgent (autonomous, not in registry — called directly by routes)
  ├── propose_study_plan()
  ├── propose_notes()
  ├── curate_videos()
  └── propose_progress_intervention()
```

Every agent: `async run(student: StudentProfile, message: str) -> dict`
All responses tagged with `_card_type` and `_agent` via `models/ui_schema.py:tag()`.

Skill context is injected by the orchestrator via `skill_loader.load_for_topic()` before passing to agents. Agents must not load skills themselves.

## Content Filter — Keyword Blocklist

`agents/content_filter.py` — replaces old LLM-based video classification with fast keyword matching.

- **Two tiers:** `BLOCKED` (silent drop) and `FLAGGED` (sent to NAGA review queue)
- Default lists in `_DEFAULT_BLOCKED` (30+ terms) and `_DEFAULT_FLAGGED` (12 terms) stored in `data/dabbu/content_keywords.json`
- NAGA can edit lists from the Approvals tab → `GET/POST /api/dabbu/naga/keywords`
- `filter_videos(videos, topic)` → returns only SAFE videos
- Separate from `data/dabbu/blacklist.json` (per-video/channel permanent blacklist)

## Progress Tracking

`agents/progress_tracker.py` — all progress data stored under `data/progress/{student_id}/`

- **`snapshots.jsonl`** — point-in-time score snapshots (taken after mock, on demand, weekly)
- **`sessions.jsonl`** — per-practice-session records (subject, topic, correct, total, duration, type)
- **`activity.jsonl`** — daily activity log (for 60-day streak heatmap)
- **`plan_completions.jsonl`** — study plan block completions

**Key functions:**
- `take_snapshot(student, label)` — saves a full weakness_map snapshot
- `log_session(student_id, ...)` — called by practice_routes + mock_routes on every submit
- `analyze_for_dabbu(student, active_plan)` — returns severity + flags for stagnant/declining/critical/overdue topics
- `get_progress_data(student, active_plan)` — full payload for ProgressPage (snapshots, SM-2, sessions, plan stats, streak calendar)

**Progress routes:** `api/routes/progress_routes.py`
- `GET /api/progress` — full progress data for current student
- `GET /api/progress/due-reviews` — SM-2 topics with `next_review_date <= today`; drives home-page banner
- `POST /api/progress/snapshot` — force a snapshot
- `POST /api/progress/dabbu-analyze` — trigger Dabbu analysis → saves intervention if severity medium+
- `GET /api/progress/interventions` — student's own interventions (FYI)

**SM-2 auto-review banner:**
- Web `HomePage.tsx` calls `GET /api/progress/due-reviews` on every load; shows amber bell banner listing due topics
- Flutter `_HomeTab` (`home_screen.dart`) does the same via `getDueReviews()` in `initState()`
- Both link to the Study Plan page/screen
- Manual "Ask Dabbu to Review" button on ProgressPage still available anytime
- `DabbuAgent._topic_weights()` boosts SM-2 overdue topics to `weight=4` / `priority=critical` during plan generation

**Intervention routes (intervention_router at /api/dabbu):**
- `GET /api/dabbu/naga/interventions?status=pending`
- `POST /api/dabbu/naga/interventions/approve|amend|dismiss`

## Mock Test System

`models/mock_test.py`, `agents/mock_paper_generator.py`, `scripts/mock_scheduler.py`, `api/routes/mock_routes.py`

**Pattern:** LLM generates a full paper 1 hour before every Saturday mock session (16:00).

- `EXAM_CONFIGS` in `models/mock_test.py` — question counts, sections, topics, negative marking per exam
- `generate_paper(exam_key, scheduled_date)` — calls LLM section-by-section; 9-check question validation; falls back to archived paper if LLM fails
- **Bank:** `data/mock_banks/{exam_key}/current_paper.json` + `archive/YYYY-MM-DD.json` (no buffer limit)
- **Scheduler:** daemon thread in `scripts/mock_scheduler.py`, polls every 10 min, fires at Saturday 15:00, dedupes by date
- **Session:** `data/mock_sessions/{student_id}/{session_id}.json` — stores answers, flagged, submitted state
- **Resume:** `_active_session()` finds in-progress session on page refresh (seconds_remaining > 0, not submitted)
- **Scoring:** negative marking per question `negative_marks` field (all RRB exams: 1/3), updates weakness_map + calls `log_session()` + `take_snapshot()` on submit
- NAGA can trigger manual generation: `POST /api/mock/generate/{exam_key}`

**Exam configs in `EXAM_CONFIGS`:**
- `rrb_ntpc` — 100Q, 90min, −1/3 (CBT-1 pattern)
- `rrb_alp` — 75Q, 60min, −1/3 ← **was wrongly coded as −1/4, now fixed**
- `rrb_group_d` — 100Q, 90min, −1/3
- `rrb_technician` — 100Q, 90min, −1/3 (CBT-2 Part A pattern for mock)
- `rrb_je` — 100Q, 90min, −1/3 (CBT-1 pattern for mock)
- `nda` — 120Q, 150min (Math paper)
- `jee` — 75Q, 180min, −1.0
- `neet` — 180Q, 200min, −1.0

## Exam Configuration

`data/exams.json` — authoritative paper patterns for UI display and question count.
`data/syllabus/{exam_key}.json` — full syllabus tree (subjects → topics → subtopics).
`agents/exam_utils.py` — `APPROVED_EXAMS`, `EXAM_ALIASES`, `load_syllabus()`, `compact_syllabus()`.

**All 8 exams now in APPROVED_EXAMS:** rrb_ntpc, rrb_alp, rrb_group_d, rrb_technician, rrb_je, nda, jee, neet

**Per-PDF corrections (July 2026):**
- `rrb_ntpc` CBT 2: 100 → **120 questions**
- `rrb_group_d`: 120 → **90 minutes**
- All RRB exams: negative marking = **1/3** (not 1/4 for ALP as was previously coded)

**Registration rules (per PDF page 5):**
- RRB ALP + RRB Technician: student selects ITI `trade` at registration (16 options)
- RRB JE: student selects `engineering_discipline` at registration (Civil / Electrical / Mechanical / Electronics)

## Diagnostic Flow

`DiagnosticAgent` supports 3 stages (set on `student.diagnostic_stage`):
- Stage 1: broad subject questions (100Q paper)
- Stage 2: topic-level drill-down based on Stage 1 weaknesses
- Stage 3: atomic concept questions

Questions come from Gemini/OpenRouter first; `data/question_banks/{exam}.json` is a **fallback only** when the LLM returns unparseable JSON. The question bank files currently contain placeholder data — if the LLM is unavailable the diagnostic returns an error message rather than fake questions.

## Security Rules (never violate)

1. All agent inputs through `InputGuard.process()` before reaching any agent.
2. All agent outputs through `OutputGuard.process()` before returning to client.
3. Every interaction logged via `AuditLogger`. Never remove audit calls.
4. No endpoint may skip `require_auth` — whitelist only `/health`, `/auth/*`, `/docs`, `/openapi.json`.
5. Irreversible actions (calendar, gmail, delete) must go through `VibeDiff.register()` first — return pending token to frontend, execute only on `/confirm`.
6. `data/audit.jsonl` SHA-256 chain must never be modified or deleted.
7. **"Direct agent call" is not an exemption.** `/api/session/content` bypasses orchestrator routing but must still apply InputGuard → OutputGuard → AuditLogger. Every endpoint that sends user text to an LLM carries this obligation.

## React Frontend

- Port **3000** (vite.config.ts)
- `@/` alias → `web/src/`
- Zustand auth store (`web/src/store/auth.ts`) persisted to localStorage; Axios interceptor attaches Bearer token, 401 → auto-logout
- `ContentAgent` returns `{ notes: "markdown string", ... }` — `StudyPage` reads `response.data.notes`, not an array
- Notification bell polls `/api/mentor/notifications` every 30 s
- Brand name in UI: **Gurukul AI** (see `Layout.tsx` header)

### Pages added / rebuilt (July 2026)
- `ProgressPage.tsx` — fully rebuilt: 4 tabs (overview / SM-2 / sessions / plan), streak heatmap, triple bar chart (Initial/Current/Target@80%), SM-2 cards, "Ask Dabbu to Review" button
- `MockTestPage.tsx` — fully rebuilt: landing / test / result views; countdown timer auto-submit; section tabs; question navigator grid; autosave every 30s; negative marking result card
- `NagaDashboard.tsx` — Approvals tab expanded: progress interventions (approve/amend/dismiss) + keyword blocklist manager (add/remove chips)
- `RegisterPage.tsx` — conditional `trade` dropdown for ALP/Technician; conditional `engineering_discipline` dropdown for JE
- `StudyPlanPage.tsx` — Dabbu study plan calendar: year overview of color-coded daily slots, week strip, hour-by-hour `DayTimeline`; `BlockCard` uses `<a href>` (not `useNavigate()`) for cross-page nav — `useNavigate()` in nested sub-components fails silently
- `TestPage.tsx` — added `AiChatPanel` below each question (calls `/api/session/chat`); chat button label is **"Ask Naga about this question"**; guardrail rejections shown as amber bubble with shield label
- `QuestionsPage.tsx` — separate `submitError` state shown in red box; guardrail rejections no longer appear green
- `HomePage.tsx` — SM-2 due-reviews amber banner (Bell icon) shown above welcome banner when `GET /api/progress/due-reviews` returns `count > 0`

### Mobile screens added (July 2026)
- `study_plan_screen.dart` — full study plan UI: diagnostic gate, generate flow, proposed/active plan views, 7-day strip, `_DayScheduleView` timeline
- `test_screen.dart` — added `_AiChatSheet` bottom sheet via brain-icon FAB; per-message guardrail colouring
- `study_screen.dart` — detects `agent=guardrail` / `threat` fields in `/content` response; shows amber shield card instead of silent blank
- `naga_screen.dart` — parses `ApiException` JSON body to surface human-readable guardrail message in amber snackbar
- `home_screen.dart` (`_HomeTab`) — SM-2 due-reviews amber banner; `_HomeTab` converted to `StatefulWidget`; `initState()` calls `getDueReviews()`; taps through to `StudyPlanScreen`

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `OPENROUTER_API_KEY` | Required — LLM calls via OpenRouter |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | OAuth login (skipped in dev) |
| `SECRET_KEY` | HMAC token signing (has insecure default — set in prod) |
| `DATABASE_URL` | SQLite path (default: `vidyabot.db`) |

## Defensive Enum Deserialization

JSONL files outlive code deployments. Never call `EnumClass(value)` directly in a `from_dict`. Use `safe_enum()` from `models/enum_utils.py`:

```python
from models.enum_utils import safe_enum
status = safe_enum(PlanStatus, d.get("status", "proposed"), PlanStatus.PROPOSED)
```

Applied to: `NotificationType`, `QuestionStatus`, `ClassType`, `MeetingRequestStatus` (`models/mentor.py`), `SessionType`, `PlanStatus` (`models/study_plan.py`).

Root cause: mock scheduler wrote `type: "mock_test_ready"` notifications before `MOCK_TEST_READY` was in `NotificationType`. Every 30-second notification poll returned HTTP 500 until fixed.

## Mobile App

- **Flutter** in `mobile_app/` — Android APK + iOS (untested)
- Backend URL in `mobile_app/.env` → `API_BASE_URL`
- **Production URL (APK default):** `https://gurukulai-backend-242694625313.asia-south1.run.app` (Mumbai — lower latency for India)
- **Also deployed:** `https://gurukulai-backend-242694625313.us-central1.run.app` (us-central1)
- **Local dev:** `http://192.168.0.12:8000` — requires `uvicorn --host 0.0.0.0`
- **APK:** `gurukulai.apk` in project root — sideloadable, debug-signed (not Play Store ready)
- Rebuild APK: `cd mobile_app && flutter build apk --release && cp build/app/outputs/flutter-apk/app-release.apk ../gurukulai.apk`

### Cold-start warm-up
`_WarmUpOnStart` widget in `main.dart` fires a `GET /health` ping immediately on app open via `AuthProvider.warmUp()`. This warms the Cloud Run instance during the onboarding screen so the user doesn't wait 10–15 s on Login. `isWarmingUp` getter drives the "Connecting to server…" message in `onboarding_screen.dart`.

## Guardrail Coverage (all chat entry points)

Every surface that accepts free text from a student must apply InputGuard before any processing:

| Surface | Endpoint | Guard applied |
|---|---|---|
| AI Tutor (chat mode) | `/api/session/chat` | Orchestrator InputGuard |
| AI Tutor (notes mode) | `/api/session/content` | InputGuard inline in route |
| Practice Test chat | `/api/session/chat` | Orchestrator InputGuard |
| Ask NAGA question | `/api/mentor/questions` | `_input_guard` in `mentor.py` |

Response handling: all three frontends detect `{agent: "guardrail", response: "...", threat: "..."}` and render an amber shield card / snackbar — never silent blank.

## NAGA Trusted Upload Path

`POST /api/dabbu/naga/upload-content` → extracts questions from PDF/DOCX, calls `add_questions(trusted=True)`.

`trusted=True` bypasses the length guard-rail in `_append()` that rejects short option strings (e.g. "3/4", "6"). The guard exists for LLM-generated questions (which must have full option text); NAGA-uploaded content from official PDFs may have legitimate short numeric options. Without `trusted=True`, the upload returns `{"added": 0}` silently.

## Known Architecture Decisions

- `call_gemini()` is named for Gemini but routes through OpenRouter — kept for import compatibility across all agents.
- `UserAuth.from_dict` uses `d.get("last_login") or fallback` not `.get(key, fallback)` — `dict.get` returns `None` (not the default) when the key exists with a null value. This caused a 500 on NAGA login.
- `DiagnosticAgent.submit_answers` has no MIN_ATTEMPTS guard — diagnostic is 1 question per topic by design; aggregating to subject level loses all useful granularity.
- `api/main.py` has its own `MOCK_MODE = not os.getenv("GOOGLE_CLIENT_ID")` — this is for OAuth routing only, unrelated to LLM calls.
- `_load_student_from_db` now uses `dict(zip(col_names, row))` with live column names from `conn.description` — this means new DB columns appear automatically without changing the load function.
- Mock test negative marking: **all RRB exams use 1/3**, not 1/4 (corrected per official PDF).
- `rrb_technician` mock uses CBT-2 Part A pattern (100Q merit exam), not CBT-1 screening. CBT-2 Part B (trade qualifying) is future work.
- `rrb_je` mock uses CBT-1 pattern; CBT-2 Technical (discipline-specific) is future work.
- Dabbu proposes → NAGA approves/amends → student sees. Students never see unapproved Dabbu output except `fyi_only` notifications.
- Content filter is keyword-only (no LLM call) — fast and NAGA-editable. LLM classification was dropped after it proved inconsistent on Indian educational content.
- `/api/session/content` calls ContentAgent directly (skips orchestrator routing) but still applies the full 3-layer security stack. Bypassing routing ≠ bypassing security.

## Adding a New Agent

1. Create `agents/my_agent.py` — implement `async run(student, message) -> dict`.
2. Register in `agents/registry.py:build_registry()` with an `AgentCard` and `trigger_keywords`.
3. Add eval suite: `evals/test_my_agent.py`.

## Adding a New API Endpoint

1. Add route in `api/routes/*.py` with `Depends(require_auth)`.
2. If irreversible, call `VibeDiff.register()` and return the pending token. Add a `/confirm` counterpart.

## Adding a New Exam

1. Add to `data/exams.json` (paper patterns).
2. Create `data/syllabus/{exam_key}.json` (subjects → topics → subtopics).
3. Add to `EXAM_CONFIGS` in `models/mock_test.py` (sections for mock paper generation).
4. Add to `APPROVED_EXAMS` and `EXAM_ALIASES` in `agents/exam_utils.py`.
5. Add to exam dropdown in `web/src/pages/RegisterPage.tsx`.
6. Add to `EXAM_LABEL` in `web/src/components/Layout.tsx`.
7. Add any registration-time conditional fields (trade, discipline) to RegisterPage and `models/student.py`.
