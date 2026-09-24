# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

SETU is an AI-powered emergency response platform: it ingests distress reports (via webhook/Google Forms), classifies them with an LLM (severity + trust scoring), and matches them to the nearest eligible volunteer or NGO. Backend is FastAPI + PostgreSQL (Supabase); frontend is static HTML/CSS/JS.

## Commands

Run everything from the **repository root** — the backend uses package-relative imports (`from backend.routes...`, `from database...`).

```bash
# Setup
python -m venv venv
venv\Scripts\activate                       # Windows
pip install -r requirements.txt
copy config\.env.example config\.env        # then fill in real values
python database/init_schema.py              # deploy schema to Supabase Postgres

# Run backend (must be run from repo root)
uvicorn backend.main:app --host 0.0.0.0 --port 8080 --reload

# Run frontend (static site in frontendnew/)
python -m http.server 3000 --directory frontendnew

# Tests
python database/reset_db.py                                  # truncate tables first
pytest                                                         # full unit suite (pytest.ini scopes to backend/, database/, tests/)
pytest backend/test_backend.py -v                              # single file
pytest backend/test_backend.py::test_name -v                   # single test
pytest -m integration                                          # integration tests (require live backend + SETU_BASE_URL/SECRET_TOKEN)
python tests/test_ngo.py                                       # standalone integration script
python test.py                                                 # ad hoc integration script at repo root
```

Unit tests default to excluding integration tests (`addopts = -m "not integration"` in `pytest.ini`). CI (`.github/workflows/ci.yml`) writes a placeholder `config/.env` from GitHub Secrets and runs `pytest tests/ --ignore=tests/test_ngo.py`; the NGO integration test and any test needing a live backend only run when `SETU_BASE_URL` secret is configured.

All DB, Gemini, and other external I/O is mocked in `backend/test_backend.py` and `database/test_database.py`; only files under `tests/` and root-level scripts (`test.py`, `full_test.py`) hit a live server/DB.

## Architecture

### Request flow: report intake → dispatch

1. **Ingestion** — `POST /webhook` (Google Forms → need) or `POST /need` map raw payloads into `NeedInput` (`backend/models.py`), then call `process_and_save_need` in `backend/routes/need.py`.
2. **AI classification** — `ai_processing/gemini_processor.py::process_need_text` sends the description to Gemini (`google-genai` SDK); on failure it falls back to Groq (`llama-3.3-70b-versatile`), then to a safe static default (`category=other, severity=medium, consistency=5`). Prompts and the strict output schema (`VALID_CATEGORIES`, `VALID_SEVERITIES`) live in `ai_processing/prompts.py`. `process_and_save_need` then normalizes the AI category through `CATEGORY_NORMALIZATION`.
3. **Geocoding** — `database/geocoding.py::get_coordinates` tries Google Maps first, falls back to OpenStreetMap/Nominatim. A need with unresolvable coordinates is a **hard failure** (`HTTPException 400`) — never silently defaults to `(0, 0)`.
4. **Trust scoring** — `database/verification.py` is a layered scorer:
   - `run_common_validation` — baseline checks (valid phone, valid non-zero coords), always run.
   - Non high-stakes reports (`is_high_stakes_disaster` is false) short-circuit to a common-only pass-through score (`build_common_only_trust_result`) — complex layers are skipped intentionally, not a bug.
   - High-stakes reports (category=`rescue` or disaster keywords like flood/earthquake/collapse/fire) go through `calculate_trust_score`: spam check (duplicate phone + "Video Connected" within 1hr), AI consistency (up to 30 pts), weather-API corroboration (up to 20 pts, needs `WEATHER_API`), and nearby-report corroboration (up to 40 pts).
   - Trust score buckets into `dispatch_action`: `≤30` rejected, `31–75` triggers `secondary_review` (a second Gemini/Groq pass via `secondary_review()` that nudges the score), `>75` is `auto_dispatch`.
5. **Auto-dispatch** — if `dispatch_action == "auto_dispatch"`, background tasks run `_auto_match_for_need` (assigns via `find_best_volunteer`) and `notifications/gmail_alert.py::send_alert`.
6. **Manual matching** — `GET /match` (`backend/routes/match.py`) is the batch matcher: sorts all open needs by severity, then for each need filters volunteers by availability (< 3 active assignments), skill compatibility (`SKILL_MAP` canonical categories), and — for "sensitive" cases — Tier 1 (NGO-verified) requirement, then scores candidates by `severity_weight / (distance_km + 1) + tier_bonus - availability_penalty` (haversine distance, `MAX_DISPATCH_KM = 50`).
7. **Volunteer self-claim** — `POST /assignment/volunteer/{need_id}` lets a volunteer claim a need directly, re-running the same sensitivity/skill/availability checks plus identity/impersonation guards.

### The "sensitive case" / tiered volunteer system

This is the platform's core safety mechanism, threaded through `match.py`, `need.py`, and `assignment.py`:
- `is_sensitive_case()` returns true for medical/rescue categories, disaster keywords, or **whenever classification is ambiguous/missing** — it fails safe toward requiring verification, it does not default to "allow".
- Sensitive cases can only be dispatched to **Tier 1 volunteers** (`ngo_verified == True`); if none are available the need is left for **Manual Escalation** rather than assigned to an unverified (Tier 2) volunteer.
- A volunteer can only become Tier 1 via an authenticated NGO creating them (`backend/routes/volunteer.py` forces `ngo_id`/`ngo_verified` from the JWT, not from client input) or an NGO verifying an existing volunteer. The public `/volunteer_webhook` intentionally **never** auto-verifies, even if a valid `ngo_id` is supplied.

### Auth model

- `backend/auth.py::verify_token` is the shared FastAPI dependency (`Depends(verify_token)`) on nearly every protected route. It accepts either:
  - the static `SECRET_TOKEN` (treated as role `system` — used by tests, cron/matching jobs), or
  - a JWT signed with `JWT_SECRET` (falls back to `SECRET_TOKEN` if `JWT_SECRET` unset), carrying `{sub, uid, role, email}`.
- Routes do their own role/ownership checks after `verify_token` (e.g. `assignment.py` checks that a `volunteer` caller's `uid` matches the assignment's `volunteer_id`, and that an `ngo` caller only manages volunteers with matching `ngo_id`). There is no centralized RBAC decorator — authorization logic is inline per-route.
- OTP login (`backend/routes/volunteer_auth.py`) is passwordless: `/auth/send-otp` emails a 6-digit code (rate-limited to 1/60s per email, stored via `database/otp_db.py`, expires in 10 min, single-use), `/auth/verify-otp` enforces 5 attempts then a 15-minute lockout, and determines role (`ngo` vs `volunteer`) by checking `ngos`/`volunteers_auth`/`volunteers` tables in that order.

### Database layer

- `database/postgres_client.py` owns a single `ThreadedConnectionPool` (module-level singleton, lazily initialized) against Supabase, parsed from `SUPABASE_DB_URL`. It has a fallback path: if the pooler host fails, it retries against the direct `db.<project-ref>.supabase.co` host.
- All DB access goes through `get_db_cursor(commit=..., dict_cursor=...)` (a contextmanager yielding a `RealDictCursor` by default), never raw connections.
- Table-specific modules (`needs_db.py`, `volunteers_db.py`, `ngos_db.py`, `assignments_db.py`, `otp_db.py`) wrap SQL for their table; schema is defined in `database/schema.sql` and documented in `database/schema.md`. `database/reset_db.py` truncates tables for test isolation; `database/init_schema.py` applies the schema.
- Note: `future_plan.md` and some `__pycache__` artifacts reference a `firestore_client.py` / Firestore emulator setup from an earlier architecture iteration — **the current, actual persistence layer is PostgreSQL/Supabase**, not Firestore. Don't assume Firestore code exists.

### Frontend

`frontendnew/` is a static multi-page site (no build step) served directly by FastAPI's `StaticFiles` mount in `backend/main.py` (also served by any static file server for local dev). Pages fetch the Google Maps key at runtime from `GET /config/public` rather than embedding it. `js/api.js` / `js/config.js` centralize the backend base URL and fetch wrappers used by the other page-specific JS files.

### WebSocket

`backend/main.py` maintains a single in-process `WebSocketManager` (`/ws` endpoint, token-authenticated the same way as REST) and broadcasts JSON events (e.g. `NEW_VOLUNTEER`) to all connected clients — used for the live dashboard. Broadcast payloads are deliberately stripped of PII (phone/email) before sending.

## Environment configuration

Config is loaded via `load_dotenv(dotenv_path="config/.env")` in multiple modules (not just once at startup) — always run commands from the repo root so this relative path resolves. Required vars are documented in `config/.env.example`: `GEMINI_API_KEY`, `GROQ_API_KEY`, `GOOGLE_MAPS_KEY`, `SUPABASE_DB_URL`, `GMAIL_SENDER`, `GMAIL_APP_PASSWORD`, `WEATHER_API`, `SECRET_TOKEN`, `JWT_SECRET`, `SETU_BASE_URL`/`SETU_API_BASE_URL`.
