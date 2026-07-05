# Gurukul AI — Adaptive Bilingual AI Tutor for Indian Competitive Exams

## The Problem

India runs some of the world's most competitive public examinations. The **Railway Recruitment Board (RRB)** exams receive over **2.5 crore (25 million) applications** for each cycle. NDA, JEE, and NEET together see tens of millions more. Most applicants come from towns and villages where quality coaching is either unavailable or costs ₹60,000–₹2,00,000 per year — equivalent to a family's entire annual savings.

The result: exam outcome is dictated more by zip code and family income than by ability.

**Gurukul AI** is a free, bilingual (English + Hindi) AI tutor that gives every aspirant access to the kind of personalised, adaptive preparation that was previously only available to students who could afford expensive coaching centres.

---

## What I Built

Gurukul AI is a **multi-agent AI system** with three interfaces:
- **React 18 web app** (full-featured dashboard)
- **Flutter Android app** (54.8 MB APK, offline-capable)
- **FastAPI backend** with 8 specialised AI agents

It supports **8 exams**: RRB NTPC · RRB ALP · RRB Group D · RRB Technician · RRB JE · NDA · JEE · NEET

---

## Agent Architecture

The system is built around a central **OrchestratorAgent** that routes incoming student messages to the most relevant specialist agent using keyword scoring:

```
Student message
      │
      ▼
OrchestratorAgent
  (keyword scoring → AgentRegistry)
      │
      ├── DiagnosticAgent    — 3-stage adaptive placement test
      ├── ContentAgent       — study notes + curated YouTube videos
      ├── AssessmentAgent    — adaptive MCQs (difficulty from weakness_map)
      ├── FeedbackAgent      — wrong-answer explanations, bilingual
      ├── ProgressAgent      — personalised study plan generation
      ├── ScheduleAgent      — weekly/monthly calendar creation
      └── NagaAgent          — student ↔ human mentor interactions
```

**DabbuAgent** (autonomous, runs in background):
```
DabbuAgent
  ├── propose_study_plan()             → writes to study_plans/{id}_proposed.json
  ├── propose_notes()                  → writes to notes/{exam}/ (status=pending)
  ├── curate_videos()                  → YouTube search + content filter
  └── propose_progress_intervention()  → saves to dabbu/interventions.jsonl
```

### The Human-in-the-Loop: NAGA

**Dabbu** (the AI agent) never directly modifies student data. Every proposal goes through **NAGA**, a named human mentor who reviews, approves, or amends Dabbu's suggestions before students see them. This is the core safety design:

```
Dabbu proposes → NAGA reviews → Student sees (approved only)
```

NAGA has a dedicated dashboard with:
- **Approvals tab**: pending study plans, notes, video curations, progress interventions, keyword blocklist management
- **Classes tab**: schedule group sessions that Dabbu identifies are needed
- **Meetings tab**: student meeting requests

---

## Key Features

### 1. Adaptive Diagnostic (3-Stage)
Students begin with a placement test. DiagnosticAgent runs three stages — broad subjects → topic drill-down → atomic concepts — building a `weakness_map` that scores every topic 0–1. All subsequent content, MCQs, and study plans are derived from this map.

### 2. SM-2 Spaced Repetition
Every topic tracks `ease_factor`, `interval_days`, `next_review_date`, and `overdue` status following the SM-2 algorithm. The Progress page shows a review schedule sorted by urgency, with overdue topics highlighted in red.

### 3. Saturday Mock Tests (Auto-Generated)
A background scheduler fires every Saturday at 15:00. `MockPaperGenerator` calls the LLM section-by-section to produce a full exam paper (100–180 questions depending on exam). The system validates each question through 9 checks. Papers are cached; if LLM fails, the previous week's archive is used as fallback.

Features: countdown timer, auto-submit at zero, autosave every 30 seconds (resume on refresh), section tabs, question navigator grid (green=answered, orange=flagged), negative marking (all RRB: −1/3, JEE: −1, NEET: −1).

### 4. 60-Day Streak Heatmap
The Progress screen shows a GitHub-style activity grid of the last 60 days, with four intensity levels based on sessions completed. Daily activity is logged to `data/progress/{student_id}/activity.jsonl`.

### 5. Triple Bar Chart (Initial / Current / Target@80%)
The overview chart shows three bars per topic: the student's score at first diagnostic, their current score, and the 80% target line — making improvement visually concrete.

### 6. Bilingual (English + Hindi)
Every screen, alert, label, and agent response is fully bilingual. Language preference is stored in the student profile and applies across both web and mobile.

### 7. Content Safety Filter
A two-tier keyword filter (BLOCKED / FLAGGED) screens all curated YouTube videos before they reach students. The blocklist is NAGA-editable from the dashboard. There is no LLM call in the content filter — it is fast, deterministic, and auditable.

---

## Technical Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI (Python), SQLite, JSONL flat files |
| LLM | OpenRouter (free-tier: NVIDIA Nemotron, Gemma 4, GPT-OSS) |
| Web frontend | React 18 + Vite + Recharts + Zustand + Tailwind |
| Mobile | Flutter (Dart) → Android APK + fl_chart + Provider |
| Auth | HMAC JWT tokens, bcrypt hashed passwords |
| Deployment | Google Cloud Run (backend), Vercel-ready (web) |

**Codebase scale:**
- 20 Python agent/utility modules
- 11 FastAPI route files (2,900+ lines of routes alone)
- 30 React/TypeScript components and pages
- 19 Flutter/Dart screens and services
- Full audit trail: every API call logged to `data/audit.jsonl` with SHA-256 chain

---

## Security Architecture

Security was designed from day one, not bolted on:

1. **InputGuard / OutputGuard** — all agent inputs and outputs pass through sanitisation layers
2. **AuditLogger** — every interaction logged with SHA-256 chaining (tamper-evident)
3. **VibeDiff** — irreversible actions (calendar events, email, delete) require a `pending_token` confirmed in a separate `/confirm` call
4. **No endpoint skips auth** — whitelist is only `/health`, `/auth/*`, `/docs`, `/openapi.json`
5. **Content filter** — deterministic keyword matching, NAGA-controlled, no LLM in the filter path

---

## How I Built This with Vibe Coding

This project was built entirely using **Claude Code** (AI-assisted coding). The workflow:

1. Described the overall architecture and problem domain in natural language
2. Claude Code generated the initial FastAPI skeleton, agent classes, and React pages
3. Each iteration: describe a feature → Claude generates → I review for correctness, safety, and exam-domain accuracy
4. Security architecture was co-designed: described the threat model, Claude implemented the guard layers
5. The Flutter app was built in parallel — all 19 screens generated from descriptions of the web app's features

The AI handled the volume of boilerplate (JSONL persistence, auth middleware, chart components, Flutter state management) while I focused on domain correctness: verifying exam configs against official PDFs, checking negative marking rules, validating syllabus coverage.

**Key vibe coding insight**: the most valuable use of AI coding assistance is not writing CRUD — it is implementing safety and consistency patterns uniformly across a large codebase. The InputGuard/OutputGuard pattern, for example, was applied consistently to all 8 agents and 11 route files because Claude Code could propagate it everywhere at once.

---

## Impact & Social Good

- **Target users**: Government job aspirants in tier-2 and tier-3 Indian cities, students who cannot afford ₹60,000/year coaching
- **Languages**: English and Hindi (covering ~90% of RRB exam aspirants)
- **Accessibility**: Android APK deployable without any cloud dependency — works with local backend on a shared community device
- **8 exams**: Covers the entire RRB ecosystem (NTPC, ALP, Group D, Technician, JE) plus NDA, JEE, NEET — a student can use the same app across exam cycles
- **Human oversight**: The NAGA/Dabbu architecture ensures a human mentor reviews every AI-generated piece of content before students see it

---

## Demo

**Video demo**: [Link to be added — recording in progress]

**GitHub**: [https://github.com/RKPrasada/GURUKULAI](https://github.com/RKPrasada/GURUKULAI)

**Android APK**: Available in `/mobile_app/build/app/outputs/flutter-apk/app-release.apk` in the repository

---

## What's Next

- Deploy backend to Google Cloud Run (Dockerfile already written)
- Hindi-language diagnostic questions via LLM
- Voice input for rural users with low literacy
- Offline question bank for areas with intermittent connectivity
- RRB CBT-2 discipline-specific mock tests (JE Technical, ALP Part B)

---

*Built for the Kaggle × Google 5-Day AI Agents Intensive Vibe Coding Capstone, July 2026.*
*Author: Ravi Kumar Prasada (rkprasada@gmail.com)*
