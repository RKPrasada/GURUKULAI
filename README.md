# Gurukul AI — Adaptive AI Tutor for Indian Competitive Exams

Personalized, bilingual (EN + HI) AI tutor for **RRB NTPC · RRB ALP · RRB Group D · RRB Technician · RRB JE · NDA · JEE · NEET**.

[![Download APK](https://img.shields.io/badge/Download-Android%20APK-green?style=for-the-badge&logo=android)](https://github.com/RKPrasada/GURUKULAI/releases/tag/v1.0-kaggle)

Built with **OpenRouter LLM · FastAPI · React 18 (Vite) · Flutter · Google ADK**

Submitted to: [Kaggle Agents for Good 2026](https://www.kaggle.com/competitions/agents-for-good)

---

## The Problem

12 million+ students appear for RRB/NDA/JEE/NEET every year. Private coaching costs ₹5,000–₹20,000/month — unaffordable for Tier 2/3 families. Gurukul AI is a zero-cost adaptive AI tutor that:

- Identifies each student's exact weak topics (not just "weak in Maths" — "weak in Number System")
- Adapts question difficulty to the student's current level
- Responds in English or Hindi throughout
- Connects students with a human mentor (NAGA) for live classes and Q&A
- Runs weekly Saturday mock tests with LLM-generated question papers
- Tracks progress over time with SM-2 spaced repetition and streak heatmaps
- Has an autonomous AI agent (Dabbu) that proposes interventions — reviewed and approved by NAGA before students see them

---

## Quick Start

**Only one API key required:** get a free [OpenRouter](https://openrouter.ai) key.

```bash
git clone https://github.com/rkprasada/vidyabot
cd vidyabot

# Python backend
pip install -r requirements.txt
cp .env.example .env
# Add your OPENROUTER_API_KEY to .env

# Start everything
python launcher_react.py        # starts API :8000 + React :3001, opens browser
```

Or start manually:
```bash
# Terminal 1 — FastAPI backend
uvicorn api.main:app --reload --port 8000

# Terminal 2 — React frontend (port 3001)
cd web && npm run dev
```

Open http://localhost:3001 — click **Try Demo** to start without Google login.

---

## How It Works

### 1. Diagnostic (100 Questions)

Gurukul AI administers a full exam-pattern paper. Questions are generated live by the LLM, split by subject and generated in parallel. Every topic is scored individually — so the weakness map says **"Number System: 20%"** not just "Mathematics: weak".

### 2. Adaptive Study Loop

```
Weakness Map → ContentAgent (study notes) → AssessmentAgent (MCQs at your level)
     ↑                                                   |
     └──────── FeedbackAgent (wrong answer explanations) ┘
```

Difficulty adjusts per session: avg score < 40% → easy, 40–70% → medium, > 70% → hard.

### 3. Dabbu — Autonomous AI Agent + Study Planner

Dabbu watches your progress and proposes actions:
- If you're stagnant on a topic for 2 weeks → proposes a different study approach
- If your SM-2 reviews are overdue → proposes a catch-up session
- If you've been inactive for 7 days → sends an inactivity alert

Dabbu also generates your **personal study plan**: a week-by-week calendar with 5 two-hour study slots per day (07:00, 09:00, 11:00, 14:00, 16:00). Each slot is colour-coded — Study (blue), Practice (fuchsia), Mock (red), Revision (amber). Click any day to see an hour-by-hour timeline.

All Dabbu proposals go through **NAGA** (human mentor) for review before you see them.

### 4. NAGA — Human Mentor

NAGA is a real human mentor role built into the system:
- Approves/amends all Dabbu proposals (study plans, notes, video curation, interventions)
- Posts answers to student questions (purple answer card in UI)
- Schedules group classes with Google Meet links — all enrolled students notified instantly
- Accepts 1-to-1 meeting requests
- Manages the content filter keyword blocklist

Login: `username=naga` / `password=naga@vidyabot` (auto-seeded on startup)

### 5. Weekly Mock Test (Every Saturday 16:00)

- LLM generates a fresh full-length exam paper at 15:00 every Saturday (1 hour advance)
- Students are notified 1 hour before
- Full timed exam UI: countdown timer, section navigation, question navigator grid, autosave every 30s
- Negative marking: all RRB exams −1/3, JEE/NEET −1.0
- Results: score, section breakdown, estimated rank percentile, collapsible answer review with explanations
- Every mock attempt updates the weakness map and feeds the progress tracker

### 6. Progress Tracking

- **60-day streak heatmap** — daily activity calendar
- **SM-2 spaced repetition** — ease factor, interval days, next review date per topic
- **Week-over-week history** — triple bar chart: Initial score / Current score / Target (80%)
- **Study plan completion** — blocks done vs planned
- **Dabbu analysis button** — triggers an AI review of your progress → NAGA-approved intervention

---

## Supported Exams

| Exam | Papers | Questions | Duration | Negative |
|---|---|---|---|---|
| RRB NTPC | CBT-1 (100Q) + CBT-2 (120Q) | 100 / 120 | 90 min each | −1/3 |
| RRB ALP | CBT-1 (75Q) + CBT-2 Part A (100Q) + Part B Trade (75Q) | varies | 60/90/60 min | −1/3 |
| RRB Group D | CBT (100Q) | 100 | 90 min | −1/3 |
| RRB Technician | CBT-1 (75Q) + CBT-2 Part A (100Q) + Part B Trade (75Q qualifying) | varies | 60/90/60 min | −1/3 |
| RRB JE | CBT-1 (100Q) + CBT-2 Technical (150Q) | 100 / 150 | 90/120 min | −1/3 |
| NDA | Mathematics (120Q) + GAT (150Q) | 120 / 150 | 150 min each | varies |
| JEE Mains | Paper 1 (75Q) | 75 | 180 min | −1.0 |
| NEET | 200Q | 200 | 200 min | −1.0 |

> RRB ALP and Technician: students select their **ITI trade** at registration.
> RRB JE: students select their **engineering discipline** (Civil / Electrical / Mechanical / Electronics) at registration.

---

## Architecture

```
React 18 Web (:3001)          Flutter Mobile
     │                             │
     └──────── HTTPS + Bearer ─────┘
                    │
          FastAPI Backend (:8000)
                    │
        ┌───────────┴────────────┐
        │    OrchestratorAgent   │
        │  InputGuard → route    │
        │   → OutputGuard        │
        │   → AuditLogger        │
        └───┬───┬───┬───┬───┬───┘
            │   │   │   │   │
       Diag Cont Asmt Fbk Prog
            │
       OpenRouter LLM
       (5-model fallback chain)
            │
    ┌───────┴─────────────────┐
    │  DabbuAgent (autonomous)│
    │  proposes → NAGA queue  │
    └─────────────────────────┘
            │
    ┌───────┴───────┐
    │  MCP Clients  │
    │ Drive Calendar│
    │  Gmail  YT    │
    └───────────────┘
```

### Agent Registry

| Agent | Responsibility |
|---|---|
| DiagnosticAgent | 100Q placement test, topic-level weakness map, multi-stage progression |
| ContentAgent | Bilingual study notes → Google Drive |
| AssessmentAgent | Adaptive MCQs, difficulty from weakness map |
| FeedbackAgent | Wrong-answer explanations in EN/HI |
| ProgressAgent | Study plan from weakness map |
| ScheduleAgent | Weekly/monthly schedule generation |
| NagaAgent | Student ↔ human mentor interactions |
| DabbuAgent | Autonomous proposals: study plans, notes, videos, progress interventions |

### Security (7 layers)

| Layer | What it does |
|---|---|
| InjectionDetector | 40+ prompt injection patterns blocked at input |
| PIIScrubber | Strips Aadhaar, PAN, phone, email, voter ID |
| InputGuard | Combines injection + PII before any agent sees input |
| OutputGuard | Blocks system prompt leakage in responses |
| VibeDiff | Irreversible actions (calendar create, email send, delete) need explicit `/confirm` |
| Quarantine | 3 threats in 10 min → 30-min block |
| AuditLogger | Append-only JSONL with SHA-256 hash chain |

InputGuard is applied to **every** surface that accepts free text — including the Ask NAGA question form. Guardrail rejections are always surfaced visibly in the UI (amber card / snackbar) — never silent.

---

## Evals

```bash
pytest evals/ -v                  # all tests
pytest evals/test_security.py -v  # 76 security tests — all must pass
python evals/eval_runner.py        # formatted summary with LLM-as-Judge scores
```

| Suite | Tests | What it covers |
|---|---|---|
| Security | 76 | Injection (EN/HI/obfuscated/base64), PII scrub, output guard, quarantine, audit chain, content endpoint security |
| Assessment | 8 | Difficulty adaptation, MCQ schema, session tracking |
| Content | 7 | Note generation, bilingual, Drive integration |
| Diagnostic | 7 | Placement paper, weakness map accuracy, topic granularity |
| Quality | 11 | LLM-as-Judge: relevance, accuracy, language match, safety |
| Feedback | 4 | Wrong-answer explanations, Hindi support |
| Progress | 7 | Study plan generation, schedule, digest |

---

## Environment Variables

Copy `.env.example` to `.env`. Only `OPENROUTER_API_KEY` is required to run.

| Variable | Required | Purpose |
|---|---|---|
| `OPENROUTER_API_KEY` | **Yes** | LLM calls for all agents |
| `ENCRYPTION_KEY` | Recommended | Encrypts Google sub IDs in DB |
| `APP_SECRET_KEY` | Recommended | Signs JWT tokens |
| `GOOGLE_CLIENT_ID/SECRET` | No | Google OAuth (demo login works without) |
| `YOUTUBE_API_KEY` | No | YouTube video search |
| `GOOGLE_DRIVE/CALENDAR/GMAIL_CREDENTIALS_JSON` | No | Google Workspace integration |

---

## Demo Script

| Scene | What to show |
|---|---|
| 1. Onboarding | Register → select RRB NTPC → 100Q diagnostic → view topic-level weakness map |
| 2. Study loop | Ask about Number System → study notes → MCQ practice → wrong answer → Hindi explanation |
| 3. Study plan | Study Plan page → Dabbu-generated week calendar → click day → hour-by-hour 5-slot timeline |
| 4. Progress | Progress page → streak heatmap → SM-2 cards → "Ask Dabbu" → Dabbu intervention → NAGA approves |
| 5. Mock test | Saturday mock test → timed exam UI → result card with rank estimate |
| 6. NAGA | Post question → login as NAGA → approve + answer → back to student, see notification |
| 7. Security | Show injection blocked live (phone number input → amber guardrail card) → show SHA-256 audit log |

---

## Platforms

| Platform | Command / File |
|---|---|
| Web (React 18) | `python launcher_react.py` → http://localhost:3001 |
| Flutter Mobile (dev) | `cd mobile_app && flutter run` |
| Android APK (sideload) | [Download from GitHub Releases](https://github.com/RKPrasada/GURUKULAI/releases/tag/v1.0-kaggle) |
| Rebuild APK | `cd mobile_app && flutter build apk --release` |
| macOS .app | `bash packaging/build_mac.sh` |

**Backend (production):** Google Cloud Run — `https://gurukulai-backend-242694625313.us-central1.run.app` — scales to zero, free tier.

**Backend URL for APK:** set in `mobile_app/.env` → `API_BASE_URL`. Edit and rebuild to switch between local and cloud.

---

## License

MIT
