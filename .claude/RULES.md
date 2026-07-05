# Gurukul AI — Engineering Rules & Good Practices

These rules capture patterns that were discovered, debated, and validated while building this codebase. Apply them when extending or maintaining the project.

---

## Security Rules (non-negotiable)

### 1. Every free-text-to-LLM endpoint must apply the full 3-layer stack

```python
clean, threat = orchestrator.input_guard.process(raw_input)   # layer 1
if threat: log + return safe rejection
result = await agent.run(student, clean)                       # agent runs on clean input
result = apply_output_guard(result, lang)                      # layer 2
logger.log_interaction(student_id, clean, str(result)[:200])   # layer 3
```

This applies to `/chat`, `/content`, and any new endpoint that accepts a message and calls an LLM. "Direct agent call" is not an exemption — `/api/session/content` bypassed all 3 and was a critical vulnerability.

### 1a. Every user-submitted text route must apply InputGuard — even without LLM

InputGuard is not optional for non-LLM routes. Example: `POST /api/mentor/questions` saves to JSONL and notifies a human reviewer — no LLM involved. But without InputGuard, injection payloads, PII, and harassment reach NAGA's queue. Apply `InputGuard.process()` and raise HTTP 400 on threat.

```python
_, threat = _input_guard.process(req.content)
if threat:
    raise HTTPException(status_code=400, detail=SAFE_REDIRECT_EN)
```

**Guardrail rejection must always be visible in the UI.** Never silently discard. All chat surfaces detect `agent === "guardrail"` or `threat` fields and render an amber warning card — never a silent blank.

### 2. Never bypass require_auth

Every route must have `Depends(require_auth)`. Only these paths are whitelisted: `/health`, `/auth/*`, `/docs`, `/openapi.json`. Adding a new "public" endpoint requires explicit justification.

### 3. Irreversible actions use VibeDiff

Calendar creates, Gmail sends, any delete — call `VibeDiff.register()` first and return a pending token. Only execute on the matching `/confirm` call. The frontend must show what will happen before the user confirms.

### 4. AuditLogger is append-only — never delete or modify data/audit.jsonl

The SHA-256 chain means any modification or deletion is detectable. This is intentional. Do not add code that writes to, truncates, or rotates this file.

### 5. Security tests must all pass before any commit touching agents or routes

```bash
pytest evals/test_security.py -v   # 76 tests — all must pass
```

If you add a new agent or a new endpoint that accepts user text, add parametrized security test cases for it.

---

## Data Persistence Rules

### 6. Never use bare EnumClass(value) in from_dict

JSONL files outlive deployments. A value written by old code will crash new readers.

```python
# WRONG — crashes if stored value isn't in current enum
status = PlanStatus(d.get("status", "proposed"))

# RIGHT — degrades gracefully, logs a warning
from models.enum_utils import safe_enum
status = safe_enum(PlanStatus, d.get("status", "proposed"), PlanStatus.PROPOSED)
```

Applies to every `from_dict` that reads an enum from a JSONL or JSON file.

### 7. Use dict(zip(col_names, row)) for SQLite reads

```python
cursor.execute("SELECT * FROM students WHERE student_id = ?", (student_id,))
row = cursor.fetchone()
col_names = [d[0] for d in cursor.description]
data = dict(zip(col_names, row))
```

This picks up new columns automatically without changing the load function. Never hard-code column positions or list column names manually in SELECT.

### 8. d.get("key") or default — not d.get("key", default) when key can be stored as null

```python
# WRONG — returns None when key exists with null value, ignoring the default
last_login = d.get("last_login", datetime.utcnow().isoformat())

# RIGHT — falls back to default even when stored as null
last_login = d.get("last_login") or datetime.utcnow().isoformat()
```

---

## Agent Architecture Rules

### 9. Students only see NAGA-approved Dabbu output

Dabbu proposes → NAGA reviews → student sees. No exceptions. The only student-facing Dabbu output before approval is `fyi_only: True` notifications ("Dabbu noticed...").

### 10. Agents don't load their own skills

Skill context is injected by the orchestrator via `skill_loader.load_for_topic()` before calling any agent. If an agent needs exam/subject context, it comes from the student profile or the injected skill — never from a `skill_loader` call inside the agent.

### 11. All agent responses tagged with _card_type and _agent

Use `models/ui_schema.py:tag(result, CardType.X)`. The frontend switches on `_card_type` to render the right component. Never return a plain dict without tagging it.

### 12. LLM calls use the 5-model fallback chain

All LLM calls go through `agents/base.py:call_gemini()`. Never call OpenRouter directly from a route or model. If a model returns 404 or 429, the chain tries the next one automatically.

---

## API Design Rules

### 13. Pydantic models for all request bodies

Never read from `request.body()` or `request.json()` directly. Define a `class XRequest(BaseModel)` for every POST body. Pydantic gives you free validation, schema docs, and type safety.

### 14. _resolve_student_id for backward compatibility

```python
def _resolve_student_id(auth_id: str, req_id: str | None) -> str:
    return auth_id if auth_id else (req_id or "")
```

The auth token's student_id is authoritative. The request body's `student_id` is only a legacy fallback. Never trust the body field over the token.

### 15. Use safe_enum, d.get() with defaults, and None-safe isoformat everywhere in from_dict

```python
answered_at=datetime.fromisoformat(d["answered_at"]) if d.get("answered_at") else None,
```

Stored data may be missing optional fields, especially in records written before the field existed.

---

## Frontend Rules (React)

### 16. Loading states use informative cycling messages

Do not show a blank spinner for operations that take >2 seconds. Use a `LOADING_STAGES` array and cycle with `setInterval(1800ms)`. This applies to diagnostic start, study notes, study plan generation, and mock test start.

### 17. Axios interceptor handles all auth — never add Authorization headers manually

The interceptor in `web/src/store/auth.ts` attaches Bearer tokens to every request. 401 responses auto-logout. Never add `headers: { Authorization: ... }` to individual API calls.

### 18. NAGA sidebar gated on user_id === 'naga'

`Layout.tsx` shows the NAGA-specific sidebar items only when `student.user_id === 'naga'`. Any new NAGA-only route must also be gated here, not just on the backend.

---

## Flutter Rules

### 19. Backend URL in .env — never hardcode

`mobile_app/.env` → `API_BASE_URL`. The APK reads this via `flutter_dotenv`. To switch between local dev (`http://192.168.0.x:8000`) and Cloud Run, edit `.env` and rebuild — don't change the code.

### 20. Typed Dart models — never cast Map<String, dynamic> inline

```dart
// WRONG — crashes on null or wrong type at runtime
final pct = weakTopics[i]['score_pct'] as double;

// RIGHT — use the typed model
final w = weakTopics[i];  // WeaknessMap
final pct = w.scorePct;
```

### 21. Loading states in Flutter use cycling phrases

Same principle as rule 16. Use a `Timer.periodic` or recursive `Future.delayed` to cycle through `loadingPhrases` at 1600ms. Don't block the UI with a plain `CircularProgressIndicator` on slow network calls.

---

## Testing Rules

### 22. Parametrize injection tests — cover EN + HI + Hinglish + obfuscated

```python
@pytest.mark.parametrize("text,expected", INJECTION_CASES)
def test_injection_detected(text, expected):
    ...
```

`INJECTION_CASES` must include: English role overrides, Hindi Devanagari variants, Hinglish (mixed), separator-obfuscated (`i.g.n.o.r.e`), and base64-encoded attack strings.

### 23. Audit chain tests must cover tamper AND truncation

A tampered entry changes the hash → `verify_chain()` returns False.
A deleted entry creates a sequence_id gap → `verify_chain()` also returns False.
Both must be tested. The SHA-256 chain is only meaningful if both attacks are caught.

### 24. Test the security contract of every endpoint that touches LLM

When a new route calls an agent, add tests that prove:
- Injection attempts in request body are blocked
- Legitimate inputs pass through
- PII is scrubbed from output
- An audit log entry is written

---

## Deployment Rules

### 25. Cloud Run: start with --host 0.0.0.0 for network access

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

Default `127.0.0.1` only accepts loopback. Mobile devices and Cloud Run health checks both need `0.0.0.0`.

### 26. APK is sideloadable but currently debug-signed

`android/app/build.gradle.kts` uses `signingConfigs.getByName("debug")` for release builds. This is fine for testing and sideloading. To publish to Play Store, generate a release keystore and configure signing before building.

### 27. Mock scheduler writes MOCK_TEST_READY notifications

`scripts/mock_scheduler.py` writes `type: "mock_test_ready"` to the notifications JSONL. This enum value must exist in `NotificationType`. Learned the hard way — missing enum value + JSONL persistence = 500 on every notification poll until fixed.

---

## Patterns to Reuse in New Projects

| Pattern | Where | Why it works |
|---|---|---|
| `safe_enum(cls, value, default)` | `models/enum_utils.py` | JSONL + code diverge over time; this prevents crashes |
| `dict(zip(col_names, row))` | `_load_student_from_db` | Schema-safe SQLite reads without migration code |
| 5-model LLM fallback chain | `agents/base.py` | Free-tier models go down; chain keeps the app alive |
| InputGuard → Agent → OutputGuard → AuditLogger | `agents/orchestrator.py` | One pipeline for all LLM endpoints — no gaps |
| InputGuard on non-LLM text routes | `mentor.py` | Stops PII + injection from reaching human reviewers |
| `d.get("key") or default` | `UserAuth.from_dict` | Handles both missing keys and stored nulls |
| VibeDiff pending token + /confirm | `security/vibe_diff.py` | User sees what will happen before it happens |
| SHA-256 hash chain on audit log | `security/audit_logger.py` | Tamper-evident — detects edits AND deletions |
| Dabbu proposes → NAGA approves | whole system | AI suggests, human decides — safe for students |
| Cycling loading phrases | `DiagnosticPage`, `StudyPage` | Reduces perceived wait time on slow LLM calls |
| Fire-and-forget warm-up ping | `main.dart` → `AuthProvider.warmUp()` | Cloud Run cold start (10–15 s) is hidden behind onboarding screen |
| Guardrail response detection | All three chat UIs | `agent==="guardrail"` or `threat` field → amber card; never silent blank |
| `diagnostic_done` auto-heal | `dabbu_routes.py` | `weakness_map` non-empty is authoritative proof diagnostic ran; patches stale flag |
