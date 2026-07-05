# Gurukul AI — Architecture Reference

## Overview

Gurukul AI is a multi-platform adaptive tutoring system built on a FastAPI backend shared by a React 18 web app and a Flutter mobile app. All AI calls route through OpenRouter's free-tier LLM cascade. Every student-facing action passes through a 7-layer security stack before reaching the LLM and again before returning to the client.

---

## Platform Layer

```
┌─────────────────────────┐   ┌──────────────────────────┐
│   React 18 Web (:3001)  │   │  Flutter Mobile (Android) │
│   Vite + Tailwind CSS   │   │  gurukulai.apk            │
│   Zustand auth store    │   │  Provider state mgmt      │
│   Axios + Bearer token  │   │  http + flutter_dotenv    │
└────────────┬────────────┘   └──────────────┬────────────┘
             │                               │
             └──────── HTTPS + Bearer ───────┘
                              │
              ┌───────────────▼──────────────┐
              │   FastAPI Backend (:8000)     │
              │   Google Cloud Run (prod)     │
              │   gurukulai-backend-ekbh2if4xa-el.a.run.app
              └───────────────────────────────┘
```

**Mobile backend URL** is set in `mobile_app/.env`:
```
API_BASE_URL=https://gurukulai-backend-ekbh2if4xa-el.a.run.app
```

---

## Security Stack (7 layers — never bypass)

Every request through `/api/session/*` passes this pipeline:

```
Raw user input
     │
  InputGuard.process()
  ├── InjectionDetector   — 40+ patterns: role override, jailbreak, extraction, Hindi, obfuscation, base64
  └── PIIScrubber         — Aadhaar, PAN, phone, email, voter ID redacted
     │
  (threat?) ──yes──► log_threat() → QuarantineManager.record_threat() → safe rejection
     │ no
  Agent runs
     │
  OutputGuard.process()
  ├── Forbidden content   — blocks system prompt leakage, architecture leakage
  └── PIIScrubber         — strips PII the LLM may hallucinate
     │
  AuditLogger.log_interaction()   — append-only JSONL with SHA-256 hash chain
     │
  Response to client
```

| Layer | File | What it stops |
|---|---|---|
| InjectionDetector | `security/injection_detector.py` | 40+ prompt injection patterns |
| PIIScrubber | `security/pii_scrubber.py` | Aadhaar, PAN, phone, email on input + output |
| InputGuard | `security/guardrails.py` | Combines injection + PII before any agent |
| OutputGuard | `security/guardrails.py` | System prompt leakage, PII in LLM output |
| QuarantineManager | `security/quarantine.py` | 3 threats/10min → 30-min block |
| VibeDiff | `security/vibe_diff.py` | Irreversible actions need explicit `/confirm` |
| AuditLogger | `security/audit_logger.py` | SHA-256 chain — detects tampering + truncation |

**Rule:** every endpoint that accepts free-text input to an LLM must apply all three: `InputGuard` → `OutputGuard` → `AuditLogger`. This applies equally to `/chat` and `/content` — there are no shortcuts even for "direct" agent calls.

---

## Agent Architecture

```
OrchestratorAgent  (api/routes/session.py → agents/orchestrator.py)
  │
  ├── InputGuard ──────────────────────────────────────────────────────┐
  │                                                                    │
  ├── AgentRegistry.route(message)   agents/registry.py               │
  │     keyword scoring → best AgentCard.handler                      │
  │     ├── DiagnosticAgent   — placement test, weakness_map          │
  │     ├── ContentAgent      — study notes, Drive upload             │
  │     ├── AssessmentAgent   — adaptive MCQs                         │
  │     ├── FeedbackAgent     — wrong-answer explanations             │
  │     ├── ProgressAgent     — study plan from weakness_map          │
  │     ├── ScheduleAgent     — weekly/monthly schedule               │
  │     └── NagaAgent         — student ↔ NAGA interactions          │
  │                                                                    │
  ├── OutputGuard (recursive over all strings in result dict) ────────┘
  └── AuditLogger

DabbuAgent  (agents/dabbu_agent.py — autonomous, not in registry)
  ├── propose_study_plan()           → data/study_plans/{id}_proposed.json
  ├── propose_notes()                → data/dabbu/notes_queue.jsonl
  ├── curate_videos()                → content filter → NAGA queue
  └── propose_progress_intervention() → data/dabbu/interventions.jsonl

MockScheduler  (scripts/mock_scheduler.py — daemon thread)
  └── fires Saturday 15:00 → MockPaperGenerator → data/mock_banks/
```

### Agent contract

Every agent implements: `async run(student: StudentProfile, message: str) -> dict`

All responses are tagged with `_card_type` and `_agent` via `models/ui_schema.py:tag()`.

Skill context injected by orchestrator before passing to agents (`agents/skill_loader.py`). Agents never load skills themselves.

---

## Identity System

Two stores, one UUID:

```
UserAuth  (data/users.jsonl)          StudentProfile  (vidyabot.db SQLite)
  username, password_hash               weakness_map, diagnostic_done
  email, exam_target                    streak, trade, engineering_discipline
  last_login                            SM-2 fields per topic
       │                                        │
       └──────── same UUID (student_id) ─────────┘
```

- `auth_routes.register()` creates both stores atomically
- `session._get_student()` lazy-loads from SQLite, caches in memory
- `_load_student_from_db` uses `dict(zip(col_names, row))` with live column names — automatically picks up new columns without code changes

---

## Data Persistence

| Store | Format | What's in it |
|---|---|---|
| `data/users.jsonl` | JSONL | UserAuth records |
| `vidyabot.db` | SQLite | StudentProfile (weakness_map, SM-2, streaks) |
| `data/audit.jsonl` | JSONL + SHA-256 chain | Immutable interaction log |
| `data/mentor/` | JSONL (4 files) | Questions, classes, meetings, notifications |
| `data/study_plans/` | JSON | `{id}_active.json` + `{id}_proposed.json` |
| `data/mock_banks/` | JSON | `{exam}/current_paper.json` + `archive/` |
| `data/mock_sessions/` | JSON | Per-student mock session state |
| `data/progress/{id}/` | JSONL (4 files) | Snapshots, sessions, activity, completions |
| `data/dabbu/` | JSONL + JSON | Interventions, content keywords, blacklist |

### Defensive enum deserialization

JSONL files outlive code deployments. Any `from_dict` that calls `EnumClass(value)` directly will crash if the stored value was written by older code. All enum deserialization uses `safe_enum()` from `models/enum_utils.py`:

```python
status = safe_enum(PlanStatus, d.get("status", "proposed"), PlanStatus.PROPOSED)
```

Applied to: `NotificationType`, `QuestionStatus`, `ClassType`, `MeetingRequestStatus`, `SessionType`, `PlanStatus`.

---

## LLM Layer

All agents call `agents/base.py:call_gemini(prompt, system)` — name is historical, routes through **OpenRouter** not Gemini directly.

**5-model fallback chain** (tried in order until 200 response):
1. `nvidia/nemotron-3-ultra-550b-a55b:free`
2. `nvidia/nemotron-3-super-120b-a12b:free`
3. `google/gemma-4-26b-a4b-it:free`
4. `openai/gpt-oss-20b:free`
5. `liquid/lfm-2.5-1.2b-instruct:free`

All free-tier — no LLM cost at current scale.

---

## NAGA — Human Mentor

Single named human mentor, not a bot.

- **Login:** `username=naga` / `password=naga@vidyabot`
- Auto-seeded to `data/users.jsonl` on every startup via `mentor_routes._seed_naga_user()`
- NAGA-specific sidebar gated on `student.user_id === 'naga'` in `Layout.tsx`
- **Dashboard tabs:** Overview / Approvals / Meetings / Schedule
- **Approvals tab covers:** Dabbu study plans + notes + videos + progress interventions + content keyword blocklist

---

## Dabbu → NAGA → Student pipeline

```
Progress analysis flags medium/high severity
         │
DabbuAgent.propose_*()  ──saves──► data/dabbu/  or  data/study_plans/
         │
Notification to NAGA (actionable)
Notification to Student (fyi_only: True — student sees "Dabbu noticed..." only)
         │
NAGA reviews in Approvals tab
         │
approve / amend / dismiss
         │
Student sees final output (study plan, notes, intervention)
```

Students never see raw Dabbu output. NAGA is always in the loop.

---

## Mock Test System

```
Saturday 14:50 — MockScheduler polls (every 10 min)
Saturday 15:00 — generate_paper(exam_key, date)
  └── LLM generates section by section
  └── 9-check validation per question
  └── save to data/mock_banks/{exam}/current_paper.json
  └── archive to data/mock_banks/{exam}/archive/YYYY-MM-DD.json
  └── notify all students: NotificationType.MOCK_TEST_READY

Saturday 16:00 — students start the mock
  ├── countdown timer, autosave every 30s
  ├── section tabs + question navigator grid
  └── submit → negative marking → weakness_map update → snapshot → log_session()
```

---

## Evals

```bash
pytest evals/ -v                  # all tests
pytest evals/test_security.py -v  # 76 security tests — must all pass
python evals/eval_runner.py        # LLM-as-Judge quality scores
```

| Suite | Count | Covers |
|---|---|---|
| Security | 76 | Injection (EN/HI/obfuscated), PII scrub, output guard, quarantine, audit chain, content endpoint security |
| Assessment | 8 | Difficulty adaptation, MCQ schema, session tracking |
| Content | 7 | Note generation, bilingual, Drive |
| Diagnostic | 7 | Placement paper, weakness map accuracy |
| Quality | 11 | LLM-as-Judge: relevance, accuracy, language match, safety |
| Feedback | 4 | Wrong-answer explanations, Hindi |
| Progress | 7 | Study plan, schedule, digest |

---

## Deployment

| Target | How |
|---|---|
| Local dev | `python launcher_react.py` (starts API :8000 + React :3001) |
| Network dev | `uvicorn api.main:app --host 0.0.0.0 --port 8000` |
| Cloud (prod) | Google Cloud Run — `gurukulai-backend-ekbh2if4xa-el.a.run.app` — scales to zero, free tier |
| Android APK | `gurukulai.apk` in project root — sideload, no Play Store needed |
| Play Store | Needs release keystore (currently signed with debug key) |

---

## React Frontend Conventions

- `@/` → `web/src/`
- Zustand auth store (`web/src/store/auth.ts`) persisted to localStorage
- Axios interceptor: attach Bearer token, 401 → auto-logout
- Notification bell polls `/api/mentor/notifications` every 30s
- Brand: **Gurukul AI** in UI, `vidyabot` in codebase

## Flutter Conventions

- Provider pattern for `AuthProvider` + `SessionProvider`
- `ApiService` singleton, token stored in instance, `flutter_dotenv` for base URL
- `WeaknessMap` typed Dart model: `.scorePct`, `.topic`, `.subject`
- Loading states use cycling phrases (1600ms interval) — not a plain spinner
