# Gurukul AI — System Architecture

Gurukul AI (codebase: vidyabot) is an adaptive, bilingual (English + Hindi) AI tutor for Indian competitive exams: RRB NTPC · RRB ALP · RRB Group D · RRB Technician · RRB JE · NDA · JEE · NEET.

Built on the principles of agentic engineering: Agent = Model + Harness, Context Engineering, A2A, A2UI, Vibe Diff, 7-Pillar Security, and EDD.

---

## 1. System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                          CLIENT LAYER                                │
│                                                                      │
│  React 18 Web (web/)     Flutter Mobile        Desktop App           │
│  Vite + Tailwind CSS     (mobile_app/)         (launcher_react.py)   │
│  port :3001              Android + iOS         Opens React :3001     │
└───────────────────────────────┬──────────────────────────────────────┘
                                │ HTTPS + Bearer Token
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         IAM MIDDLEWARE                               │
│  api/middleware.py                                                   │
│  HMAC-SHA256 tokens · 7-day TTL · require_auth() FastAPI dep         │
│  Whitelisted: /health /auth/* /docs /openapi.json                    │
└───────────────────────────────┬──────────────────────────────────────┘
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      FASTAPI BACKEND (api/)                          │
│                                                                      │
│  main.py ─── routes/auth_routes.py      (register, login, passwords) │
│          ├── routes/session.py          (diagnostic, assessment, chat)│
│          ├── routes/mentor.py           (NAGA Q&A, classes, meetings) │
│          ├── routes/admin.py            (YouTube channel CRUD)        │
│          ├── routes/student.py          (profile endpoints)           │
│          ├── routes/progress.py         (legacy plan, calendar)       │
│          ├── routes/progress_routes.py  (progress tracking, Dabbu)   │
│          ├── routes/dabbu_routes.py     (study plan, approvals, kws)  │
│          ├── routes/practice_routes.py  (topic practice sessions)     │
│          └── routes/mock_routes.py      (mock test — full lifecycle)  │
│                                                                      │
│  Two identity stores (same UUID bridges them):                       │
│  UserAuth → data/users.jsonl          (credentials)                  │
│  StudentProfile → vidyabot.db SQLite  (learning data)               │
│    + trade, engineering_discipline (columns added July 2026)         │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    3-LAYER SECURITY PIPELINE                         │
│                                                                      │
│  INPUT ──► [Layer 1: InputGuard]                                     │
│               InjectionDetector  (24+ compiled regex patterns)       │
│               PIIScrubber        (Aadhaar, PAN, phone, email)        │
│               ↓ threat detected?                                     │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │  QuarantineManager (security/quarantine.py)                 │     │
│  │  SQLite-backed · 3 attempts / 10 min → 30 min block         │     │
│  └─────────────────────────────────────────────────────────────┘     │
│               ↓ clean input                                          │
│  ORCHESTRATOR ► [Layer 2: Policy Enforcement]                        │
│               SYSTEM_PROMPT rules · A2A registry routing             │
│               Dynamic skill context injection (skills/)              │
│               ↓ response text                                        │
│  OUTPUT ──► [Layer 3: OutputGuard]                                   │
│               Blocks: system prompt, api key, architecture leaks     │
│               ↓                                                      │
│  AuditLogger  SHA-256 chain · append-only JSONL · tamper-detect      │
└───────────────────────────────┬──────────────────────────────────────┘
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       A2A AGENT REGISTRY                             │
│  agents/registry.py                                                  │
│                                                                      │
│  AgentCard: name · capabilities · trigger_keywords · priority        │
│  route(message) → keyword scoring → best AgentCard                   │
│                                                                      │
│  Priority: diagnostic(10) > assessment(9) > content(8)               │
│            > feedback(7) > progress(6)                               │
│                                                                      │
│  DabbuAgent — NOT in registry; called directly by routes             │
│  Autonomous proposals → NAGA queue → student after approval          │
└──┬──────┬──────┬──────┬──────┬──────┬─────────────────────────────┘
   ▼      ▼      ▼      ▼      ▼      ▼
 Diag  Content  Assess  Feed  Progress  Dabbu
 Agent  Agent   Agent  Agent   Agent    Agent
   │      │       │              │        │
   │      ▼       │              ▼        ▼
   │  MCP Tools   │          VibeDiff   NAGA
   │  Drive       │          (irrevers)  Queue
   │  YouTube     │           actions)    │
   │  Calendar    ▼                      ▼
   │  Gmail  [Dynamic Context]     interventions
   │         skill_loader.py       study plans
   │         skills/exam_*.md      notes
   │         skills/subject_*.md   video curation
   │         skills/teaching.md
   │
   ▼
MockPaperGenerator (agents/mock_paper_generator.py)
   └── data/mock_banks/{exam_key}/current_paper.json
   └── data/mock_banks/{exam_key}/archive/YYYY-MM-DD.json

MockScheduler (scripts/mock_scheduler.py)
   └── daemon thread · polls every 10min · fires at Saturday 15:00
```

---

## 2. NAGA — Human Mentor System

NAGA is a named human mentor role (not a bot). It sits alongside Dabbu and provides human judgment, live teaching, and community moderation.

```
Student                              NAGA (Human Mentor)
  │                                        │
  ├─ Post question ──────────────► Review → Approve/Reject
  │                                        │
  │  ◄─ Notification ─────────────── Answer question
  │
  ├─ Request 1-to-1 meeting ──────► Accept/Decline + set time
  │  ◄─ Notification + Meet link ──────────┘
  │
  ├─ Browse class calendar ────────────────────────────────┐
  │  RSVP → receive Meet link                              │
  │                                                        │
  │                              NAGA schedules class ─────┘
  │                              → auto-notifies all students
  │
  ├─ "Ask Dabbu to Review" (ProgressPage)
  │         │
  │         ▼
  │    Dabbu analyzes → if medium/high severity → proposes intervention
  │         │
  │         ▼
  │    NAGA Approvals tab → approve/amend/dismiss
  │         │
  │  ◄─── FYI notification (fyi_only: True)
  │         │
  │  ◄─── Full detail after NAGA approves
  │
  └─ Upvote / mark resolved
```

**NAGA Dashboard tabs:**
- **Overview** — summary stats, recent activity
- **Approvals** — pending Dabbu plans, notes, videos, progress interventions; keyword blocklist manager
- **Meetings** — 1-to-1 meeting requests + accept/decline
- **Schedule** — upcoming classes, schedule new class

**Data stores (JSONL under data/mentor/):**
- `questions.jsonl` — student questions + NAGA answers + approval status
- `classes.jsonl` — scheduled group sessions with Meet links + RSVPs
- `meeting_requests.jsonl` — 1-to-1 requests + NAGA responses
- `notifications.jsonl` — per-user notification feed (polled every 30s)

**Login:** `username=naga` / `password=naga@vidyabot` (auto-seeded on startup)

---

## 3. Dabbu — Autonomous AI Agent

Dabbu watches student progress and proposes actions. All proposals must be approved by NAGA before students see them (except `fyi_only` notifications).

```
Progress data + weakness_map
         │
         ▼
analyze_for_dabbu(student, active_plan)
         │
         ├── flags: stagnant_topics, declining_topics, critical_stuck,
         │         overdue_reviews, low_plan_completion, inactive_7d
         │
         ▼ (if severity medium or high)
DabbuAgent.propose_progress_intervention(student, analysis)
         │
         ├── Builds action list:
         │   critical_stuck   → extra_practice block
         │   stagnant         → approach_change note
         │   declining        → urgent_review session
         │   overdue SM-2     → sm2_catch_up plan
         │   inactive_7d      → inactivity_alert message
         │   low_completion   → plan_catch_up suggestion
         │
         ├── Saves to data/dabbu/interventions.jsonl
         │
         ├── Notifies NAGA (actionable)
         └── Notifies student (fyi_only: True)
```

**Proposal types:**
- Study plan (`data/study_plans/`) → `propose_study_plan()`
- Study notes → `propose_notes()`
- Video curation → `curate_videos()` with keyword blocklist filter
- Progress interventions → `propose_progress_intervention()`

---

## 4. Content Filter

`agents/content_filter.py` — keyword-only filter (no LLM call).

```
Video metadata (title + channel + description)
         │
         ▼
classify_video(video) → string match against two tiers
         │
         ├── BLOCKED tier (~30 terms): adult, political, gambling, entertainment...
         │   → silently dropped, not shown to NAGA
         │
         └── FLAGGED tier (~12 terms): shorts, memes, news, motivation...
             → sent to NAGA review queue
             → NAGA approves → student sees | NAGA rejects → dropped

Keywords stored in: data/dabbu/content_keywords.json
NAGA can edit via: GET/POST /api/dabbu/naga/keywords (add/remove)
Separate blacklist: data/dabbu/blacklist.json (per-video/channel permanent ban)
```

---

## 5. Mock Test System

```
Saturday 15:00 (1hr advance)
         │
         ▼
MockScheduler (daemon thread, polls every 10min)
         │ (also triggerable by NAGA: POST /api/mock/generate/{exam_key})
         ▼
MockPaperGenerator.generate_paper(exam_key, scheduled_date)
         │
         ├── For each section in EXAM_CONFIGS[exam_key]:
         │   LLM generates questions with 9-check validation guard
         │   if < 80% valid → retry (max 3 attempts)
         │
         ├── SUCCESS → current_paper.json + archive/YYYY-MM-DD.json
         └── FAILURE → fallback to most recent archive
         │
         ▼
_notify_students(exam_key, paper_id)  → notifications.jsonl
         │
         ▼
Student: Saturday 16:00 — starts mock test
         │
         ├── GET /api/mock/paper/{exam_key} → paper WITHOUT answers
         ├── POST /api/mock/session/start → MockSession created
         ├── PUT /api/mock/session/{id} → autosave every 30s
         │   (or page refresh → _active_session() resumes)
         │
         ├── Countdown timer → auto-submit at 0
         │
         └── POST /api/mock/session/{id}/submit
                   │
                   ├── _score_session() → section scores, rank_estimate_pct
                   ├── update weakness_map (section → topic score)
                   ├── log_session() → progress_tracker sessions.jsonl
                   └── take_snapshot(student, "mock_completed")
```

**Negative marking (per official PDF):** All RRB exams −1/3. JEE/NEET −1.0.

---

## 6. Progress Tracking

```
data/progress/{student_id}/
├── snapshots.jsonl      — point-in-time weakness_map snapshots
├── sessions.jsonl       — per-session records (subject, topic, correct, total, duration)
├── activity.jsonl       — daily activity log (for streak heatmap)
└── plan_completions.jsonl — study plan block completions
```

**ProgressPage tabs:**
1. **Overview** — streak heatmap (60 days), triple bar chart (Initial/Current/Target@80%), top topics
2. **SM-2** — ease factor, interval days, next review date per topic; overdue alert banner
3. **Sessions** — practice history with expandable per-topic trend line chart
4. **Plan** — study plan completion stats (% done, by type: STUDY/PRACTICE/MOCK)

**Dabbu analysis flow:**
```
POST /api/progress/dabbu-analyze
  → analyze_for_dabbu(student, active_plan)
  → if severity medium/high: DabbuAgent.propose_progress_intervention()
  → notification to NAGA + FYI to student
  → NAGA acts in Approvals tab
  → POST /api/dabbu/naga/interventions/approve|amend|dismiss
```

---

## 7. Agent = Model + Harness

Each agent is a composition of:

| Component | Implementation |
|-----------|---------------|
| **Model** | OpenRouter via `agents/base.py:call_gemini()` |
| **System prompt** | Static rules in `SYSTEM_PROMPT` per agent |
| **Tools** | MCP clients wrapped as `FunctionTool` |
| **Guardrails** | `InputGuard` → agent → `OutputGuard` |
| **Audit** | `AuditLogger` logs every interaction |
| **Fallback** | `call_gemini` tries 5 models in order; last resort = archived question bank |

---

## 8. Context Engineering

### Static context (always in context window)
- `SYSTEM_PROMPT` in each agent — role, scope, language rules
- `OrchestratorAgent.SYSTEM_PROMPT` — top-level policy (7 rules)

### Dynamic context (loaded per query)
- `agents/skill_loader.py` — reads from `skills/` on demand, cached via `lru_cache`
- `load_for_topic(topic, exam)` injects: exam-specific context + subject context + teaching style
- Prevents context bloat: only the relevant skill file is injected, not all of them

---

## 9. A2A (Agent-to-Agent) Protocol

```
OrchestratorAgent
       │
       ├── AgentRegistry.route("explain percentage")
       │       └── keyword scoring: content_agent wins (score=3)
       │
       ├── AgentRegistry.discover(Capability.STUDY_CONTENT)
       │       └── [content_agent, feedback_agent]  (by priority)
       │
       └── matched.handler(student, topic)  ← calls the agent
```

`AgentCard` fields: `name`, `version`, `capabilities`, `description`, `trigger_keywords`, `handler`, `priority`

---

## 10. Vibe Diff — Confirmation Gate

Prevents irreversible high-stakes actions from executing without explicit user confirmation.

```
Student: "Create my study schedule"
         │
ProgressAgent.generate_plan() → returns plan dict
         │
VibeDiff.register(student_id, "create_calendar_events", description, payload)
         └─ returns PendingAction(token=<urlsafe 16 bytes>, expiry=300s)
         │
         ▼  (API returns token to frontend)
Student sees: "Confirm creating 21 calendar events? [Confirm] [Cancel]"
         │
         ▼  POST /api/session/confirm-action {token}
VibeDiff.confirm(token, student_id)
         └─ executes CalendarClient.create_events(payload)

Risk levels: CRITICAL (delete data) > HIGH (gmail) > MEDIUM (calendar) > LOW (drive)
```

---

## 11. IAM Flow

```
Register / Login
      │
      ▼
auth_routes.py: issue_token(user_id)
      └─ HMAC-SHA256(SECRET_KEY, f"{user_id}:{exp}")
      │
      ▼
Client stores token → sends as Bearer in Authorization header
      │
      ▼
require_auth(request) FastAPI dependency
      └─ decodes token · checks expiry · returns user_id (= student_id)
```

**Identity bridge:** same UUID used as `user_id` (UserAuth) and `student_id` (StudentProfile).

**Registration:** `auth_routes.register()` creates `StudentProfile` directly (not via `_ensure_student_profile`) to capture `trade` and `engineering_discipline` at signup per PDF mandate.

---

## 12. Security Pipeline — 7 Pillars

| Pillar | Implementation |
|--------|---------------|
| **Input validation** | `InjectionDetector` — 24+ compiled regex patterns |
| **PII protection** | `PIIScrubber` — Aadhaar, PAN, phone, email |
| **Authentication** | HMAC-SHA256 session tokens, 7-day TTL |
| **Authorization** | `require_auth()` — every endpoint gated; NAGA routes check user_id |
| **Stateful defense** | `QuarantineManager` — 3 threats/10min → 30min block |
| **Confirmation gate** | `VibeDiff` — irreversible actions need token confirm |
| **Audit trail** | SHA-256 chained JSONL — tamper-detectable |

---

## 13. React Frontend Architecture

```
web/src/
├── App.tsx              Routes: / /login /register /diagnostic /study /study-plan
│                               /test /mock-test /progress /questions /classes
│                               /naga /admin /settings /feedback /help
├── store/auth.ts        Zustand store — Student + token, persisted to localStorage
├── services/api.ts      Axios client — Bearer token interceptor, 401 auto-logout
├── components/
│   ├── Layout.tsx       Sidebar + header; NAGA sidebar if user_id === "naga"; brand = "Gurukul AI"
│   └── NotificationBell.tsx  Red badge; polls /api/mentor/notifications every 30s
└── pages/
    ├── LoginPage.tsx / RegisterPage.tsx / ForgotPasswordPage.tsx
    │   RegisterPage: conditional ITI trade (ALP/Technician) + discipline (JE) selectors
    ├── HomePage.tsx        Dashboard: stats, action cards, weakness list
    ├── DiagnosticPage.tsx  One-at-a-time; submits → updates weakness_map in store
    ├── StudyPage.tsx       Topic search → chat with ContentAgent (notes as Markdown)
    ├── StudyPlanPage.tsx   Dabbu study plan; weekly/daily view; block completion
    ├── TestPage.tsx        Adaptive MCQ; one question at a time; instant feedback
    ├── MockTestPage.tsx    [REBUILT] Landing / Timed exam / Result views
    │                       Countdown timer, section tabs, question navigator grid
    │                       Autosave every 30s, negative marking result card
    ├── ProgressPage.tsx    [REBUILT] 4 tabs: Overview / SM-2 / Sessions / Plan
    │                       Streak heatmap, triple bar chart, SM-2 cards
    │                       "Ask Dabbu to Review" button → intervention flow
    ├── QuestionsPage.tsx   Student Q&A board; NAGA answer in purple box
    ├── ClassesPage.tsx     Calendar; RSVP to unlock Meet link
    ├── NagaDashboard.tsx   4-tab: Overview / Approvals / Meetings / Schedule
    │                       Approvals: Dabbu plans + notes + videos + interventions + keywords
    └── AdminPage.tsx       YouTube channel CRUD per exam
```

**Key patterns:**
- `ContentAgent` returns `{ notes: "markdown string", ... }` — read as `response.data.notes`
- Assessment returns `{ first_question, session_id, total }` — one question at a time via `/assessment/answer`
- Diagnostic submit: `{ answers: { question_id: answer_index } }` dict, backend normalises to list

---

## 14. Exam Configuration System

```
data/exams.json                          — paper patterns for UI (questions, duration, marks)
data/syllabus/{exam_key}.json            — full syllabus tree (subjects → topics → subtopics)
agents/exam_utils.py                     — APPROVED_EXAMS, EXAM_ALIASES, load_syllabus()
models/mock_test.py  EXAM_CONFIGS        — sections + topics for LLM mock paper generation
```

**Exam coverage:**

| Key | Name | PDF corrections |
|---|---|---|
| `rrb_ntpc` | RRB NTPC | CBT-2 question_count 100→**120** |
| `rrb_alp` | RRB ALP | negative_marking 1/4→**1/3** |
| `rrb_group_d` | RRB Group D | duration 120→**90 min** |
| `rrb_technician` | RRB Technician | **New** — CBT1 75Q + CBT2-A 100Q + CBT2-B qualifying |
| `rrb_je` | RRB JE | **New** — CBT1 100Q + CBT2 150Q technical |
| `nda` | NDA | no change |
| `jee` | JEE Mains | no change |
| `neet` | NEET UG | no change |

**Per-PDF registration rules:**
- `rrb_alp` + `rrb_technician` → student selects `trade` (ITI trade) at registration
- `rrb_je` → student selects `engineering_discipline` at registration (Civil/Electrical/Mechanical/Electronics)

---

## 15. Evaluation-Driven Development (EDD)

| Suite | Tests | Coverage |
|-------|-------|----------|
| Security (`test_security.py`) | 45 | Injection (22 cases), PII (5), output guard (4), audit chain |
| Diagnostic (`test_diagnostic.py`) | 10 | Placement paper, weakness map, bilingual |
| Assessment (`test_assessment.py`) | 8 | Adaptive difficulty (1/2/3), session flow |
| Content (`test_content.py`) | 7 | Notes generation, YouTube, Drive mock |
| Quality — LLM-as-Judge (`test_quality.py`) | 12 | Relevance, accuracy, language match, safety, helpfulness |
| **Total** | **82** | |

### LLM-as-Judge rubric (`evals/llm_judge.py`)

Evaluates each `(query, response)` pair on 5 dimensions (1–5):
- **relevance** — does the response address the query?
- **accuracy** — factually correct for the exam?
- **language_match** — English or Hindi as requested?
- **safety** — no harmful/off-topic content?
- **helpfulness** — would this help a student pass?

PASS threshold: `overall ≥ 3.5`.

---

## 16. Data Flow — Full Request Lifecycle

```
1. Student types: "Explain percentage for RRB NTPC"
2. React → POST /api/session/chat {message}  (Bearer token in header)
3. middleware.py: require_auth() → validates token → returns user_id
4. session.py: QuarantineManager.is_quarantined(user_id) → False → proceed
5. OrchestratorAgent.handle(student, message)
   a. InputGuard.process(message) → clean, threat=None
   b. student.diagnostic_done=True → skip diagnostic
   c. AgentRegistry.route("Explain percentage for RRB NTPC")
      → content_agent (score: "explain"=1, "percentage"=1)
   d. skill_loader.load_for_topic("Percentage", "rrb_ntpc")
      → loads exam_rrb_ntpc.md + subject_math.md + teaching_style.md
   e. ContentAgent.run(student, enriched_topic)
      → { notes: "# Percentage\n\n...", drive_url, youtube_videos }
   f. OutputGuard.process(notes) → safe (no leaks)
   g. AuditLogger.log_interaction(...)
6. Response: { notes, drive_url, youtube_videos, _card_type, _agent }
7. React StudyPage: renders notes as Markdown, shows video links
```

---

## 17. Directory Structure

```
vidyabot/
├── agents/
│   ├── base.py               # call_gemini() → OpenRouter with 5-model fallback
│   ├── registry.py           # A2A AgentRegistry + AgentCard
│   ├── skill_loader.py       # Dynamic context injection (lru_cache)
│   ├── orchestrator.py       # Central router (uses registry)
│   ├── exam_utils.py         # APPROVED_EXAMS, EXAM_ALIASES, load_syllabus()
│   ├── content_filter.py     # Keyword blocklist filter (BLOCKED/FLAGGED tiers)
│   ├── progress_tracker.py   # Snapshots, sessions, activity, SM-2, streak heatmap
│   ├── dabbu_agent.py        # Autonomous AI agent — proposals → NAGA queue
│   ├── mock_paper_generator.py # LLM paper generation with 9-check validation
│   ├── mock_question_bank.py # Fallback MCQs for offline mode
│   ├── diagnostic_agent.py
│   ├── content_agent.py
│   ├── assessment_agent.py
│   ├── feedback_agent.py
│   └── progress_agent.py
├── api/
│   ├── middleware.py          # IAM: HMAC tokens + require_auth
│   ├── main.py                # App lifespan, DB init/migration, router include
│   └── routes/
│       ├── auth_routes.py     # Register (+ trade/discipline), login, password
│       ├── session.py         # Diagnostic, assessment, chat
│       ├── mentor.py          # NAGA Q&A, classes, meetings, notifications
│       ├── admin.py           # YouTube channel CRUD
│       ├── student.py         # Profile endpoints
│       ├── progress.py        # Legacy plan, calendar, digest
│       ├── progress_routes.py # Progress tracking + Dabbu interventions
│       ├── dabbu_routes.py    # Study plan, NAGA approvals, keyword management
│       ├── practice_routes.py # Topic practice sessions (logs to progress_tracker)
│       └── mock_routes.py     # Mock test full lifecycle
├── scripts/
│   └── mock_scheduler.py      # Daemon thread: Saturday 15:00 trigger
├── security/
│   ├── injection_detector.py
│   ├── pii_scrubber.py
│   ├── guardrails.py          # InputGuard + OutputGuard
│   ├── audit_logger.py        # SHA-256 chain
│   ├── quarantine.py
│   └── vibe_diff.py
├── models/
│   ├── student.py             # StudentProfile (+ trade, engineering_discipline), WeaknessMap (SM-2)
│   ├── auth.py                # UserAuth
│   ├── question.py
│   ├── mock_test.py           # EXAM_CONFIGS, MockQuestion, MockPaper, MockSession
│   ├── mentor.py
│   └── session.py
├── skills/
│   ├── teaching_style.md
│   ├── exam_rrb_ntpc.md
│   ├── exam_jee.md
│   ├── exam_neet.md
│   ├── exam_nda.md
│   └── subject_math.md
├── mcp/
│   ├── drive_client.py
│   ├── calendar_client.py
│   ├── gmail_client.py
│   └── youtube_client.py
├── web/                       # React 18 frontend
│   └── src/
│       ├── App.tsx
│       ├── pages/             # LoginPage, RegisterPage, HomePage, DiagnosticPage,
│       │                      # StudyPage, StudyPlanPage, TestPage, MockTestPage,
│       │                      # ProgressPage, QuestionsPage, ClassesPage,
│       │                      # NagaDashboard, AdminPage, SettingsPage, ...
│       ├── components/        # Layout.tsx, NotificationBell.tsx, AuthForm.tsx, ...
│       ├── services/api.ts    # Full Axios API client
│       └── store/auth.ts      # Zustand auth store
├── mobile_app/                # Flutter (Android + iOS)
├── data/
│   ├── users.jsonl            # UserAuth records (incl. NAGA)
│   ├── exams.json             # Paper patterns for all 8 exams
│   ├── syllabus/              # rrb_ntpc.json, rrb_alp.json, rrb_group_d.json,
│   │                          # rrb_technician.json, rrb_je.json, nda.json, jee.json, neet.json
│   ├── mentor/                # questions, classes, meetings, notifications JSONL
│   ├── dabbu/                 # study_plans proposals, content_keywords.json, blacklist.json,
│   │                          # interventions.jsonl
│   ├── study_plans/           # {student_id}_active.json, {student_id}_proposed.json
│   ├── progress/              # {student_id}/snapshots.jsonl, sessions.jsonl, activity.jsonl,
│   │                          # plan_completions.jsonl
│   ├── mock_banks/            # {exam_key}/current_paper.json, archive/YYYY-MM-DD.json
│   ├── mock_sessions/         # {student_id}/{session_id}.json
│   ├── question_banks/        # fallback MCQs per exam
│   ├── youtube_channels.json  # Curated YouTube channels per exam
│   └── vidyabot.db            # SQLite: students, sessions, quarantine
├── evals/
│   ├── test_security.py
│   ├── test_diagnostic.py
│   ├── test_assessment.py
│   ├── test_content.py
│   ├── test_quality.py
│   ├── llm_judge.py
│   └── eval_runner.py
├── docs/
│   └── architecture.md        # This file
├── launcher_react.py          # Starts API :8000 + React :3001
├── CLAUDE.md                  # Project instructions for Claude Code
└── AGENTS.md                  # Top-level agent rules
```
