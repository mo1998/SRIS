# Smart Remote Interview System (SRIS)

SRIS is a production-oriented remote interviewing platform for structured hiring workflows. Employers create role-based interviews with weighted questions and rubrics, invite candidates by email, collect answers with optional audio and video capture, and get transparent AI-assisted evaluation with evidence-linked reports — all self-hosted and local-first.

The system is containerized with Docker Compose (PostgreSQL, Redis, FastAPI, React, Mailpit, optional local LLM, transcription and emotion-analysis workers) and ships with real-time WebSocket updates, in-app notifications, automatic speech-to-text transcription, facial emotion analysis, scheduled invitation maintenance, an automated CI pipeline, and deployment, backup, and observability tooling.

## Features

### Organizations, Teams, and Roles

- Employer registration with automatic organization and owner membership
- Team roles: owner, admin, recruiter, reviewer
- Organization-scoped authorization across interviews, invitations, responses, reports, evaluations, and audit logs
- Candidate (employee) accounts with self-access to their own results

### Interview Builder and Templates

- Interview CRUD with draft / active / completed / cancelled lifecycle
- Built-in interview templates
- Weighted questions, expected answers, and rubric criteria
- Activation guard requiring at least one question
- Manager-only mutation controls; member visibility

### Invitations and Candidate Pipeline

- Single and bulk invitations with resend cooldown and bulk limits
- Lifecycle: pending / sent / accepted / completed / expired / revoked
- Token verification for public invitation access, revoke prevents token use
- Scheduled expiry sweep and automatic reminder emails (configurable after-hours trigger, cooldown, and max reminder count)
- Email preview and SMTP health endpoint
- Manual maintenance trigger for employers (`POST /api/maintenance/run`)

### Authentication and Account Management

- JWT access/refresh tokens with token-version revocation on password change
- Login rate limiting with retry-after headers and password reset rate limiting
- Forgot / reset password flow with one-time hashed tokens (expiry, single-use, non-enumerable responses)
- Password complexity enforcement; deactivated accounts cannot authenticate

### Candidate Response Experience

- Start flow with max-attempt enforcement and token-validated invitation access
- Server-authoritative interview timer with configurable grace period (client clocks cannot extend the interview)
- Typed answers with optional audio and video upload (extension, size, and content-signature validation)
- Answer retake while the response is in progress, with media replacement and score/transcript invalidation
- Environment quality metrics (voice, background, face visibility, lighting) with configurable scoring weights
- Anti-cheating integrity tracking: tab switches, window blur/focus, context-menu events, and timer overruns recorded per response
- Anti-cheating enforcement: clipboard blocking (copy/paste disabled during the interview), right-click blocking, optional fullscreen enforcement, and candidate-facing warnings recorded as integrity events
- Completion flow that queues evaluation and transcription, updates invitation status, and emits webhooks and notifications

### Transcription

- Automatic speech-to-text after completion for answers with audio or video
- Multilingual Whisper provider (faster-whisper, 99 languages including Arabic and English) with VAD filtering and int8 CPU quantization
- Transcript storage per answer with confidence and detected language; review/edit via API
- Background queue (in-process or Redis/RQ) and provider health endpoint

### Emotion and Face Analysis

- Optional facial emotion analysis of recorded video via DeepFace (open-source, MIT)
- Seven emotion classes (angry, disgust, fear, happy, sad, surprise, neutral) with dominant emotion, confidence, and frame timeline
- Language-independent so Arabic and English interviews are supported
- Bounded in-process caching keyed by file mtime; timeout-bounded, non-blocking analysis
- Analysis is operational metadata only — evaluation scoring is driven by rubric criteria and evidence, not emotion or personality signals

### Evaluation Engine

- Local-first evaluation with an OpenAI-compatible `local_vllm` provider
- Optional cloud LLM provider (OpenAI-compatible) as a hybrid alternative or complement
- Per-organization provider selection: employers pick local, cloud, hybrid, or deterministic evaluation from the dashboard — no `.env` or deployment changes required (overrides stored on the organization; clear them to fall back to the system default)
- Deterministic rubric-aware fallback evaluator so evaluations never block on the LLM
- Persisted evaluation runs (provider, model, prompt version, config hash, status, errors) and per-answer scores with bilingual feedback and evidence JSON
- Single and batch re-evaluation; evaluation health endpoint; interview-level analytics
- Durable background evaluation via Redis/RQ worker

Evaluation drives scoring from rubric criteria and evidence, not from emotion or personality signals.

### Reviewer Workflow

- Reviewer decisions (pass / fail / review) with notes, actor attribution, and audit trail
- Reviewer scorecards: overall score, strengths, weaknesses, and overall comment per response
- Real-time decision/scorecard updates via WebSocket

### Reports and Exports

- Employer interview report with candidate ranking and evaluation metadata
- Candidate report limited to candidate information, environment quality, overall score, and emotion & confidence analysis
- Question-by-question breakdown with bilingual feedback, criteria badges, and evidence
- Evaluation audit history with per-run score deltas
- PDF report generation and CSV export

### Webhooks

- Per-organization webhook registration with signed deliveries
- Events: interview.completed, evaluation.completed, invitation.sent, invitation.accepted, invitation.completed, response.completed, reviewer.decision_made
- Exponential-backoff retry (up to 3 attempts) and per-attempt delivery logs

### Real-Time Updates and Notifications

- WebSocket endpoint (`/api/ws`) authenticated with the same bearer token as HTTP
- Redis pub/sub fan-out across processes (RQ worker events reach browser clients); in-process fallback when Redis is down
- Live UI updates without page refresh for notifications, response completion, evaluations, decisions, and interview state changes
- In-app notifications with unread count, per-notification read state, and mark-all-read

### Compliance and Operations

- GDPR data export/delete request workflow with approval lifecycle
- Transcript storage, review, and retrieval
- Durable audit logs for sensitive actions
- Login rate limiting, password complexity, token revocation on password change
- Request IDs, process timing, security headers, configurable request body limits
- Production configuration guardrails when `DEBUG=False`
- Prometheus metrics (`/metrics`), RQ/LLM/email custom metrics, and a production observability stack (Prometheus, Alertmanager, Loki, Grafana, node-exporter)
- Backup dry-run and verification; release readiness script; load-test CLI

## Architecture

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, SQLAlchemy, Alembic, Pydantic, PostgreSQL (prod) / SQLite (local, CI) |
| Background jobs | Redis + RQ worker (evaluation, transcription) |
| Frontend | React 18, TypeScript, Vite, React Bootstrap, Zustand, Axios |
| Real-time | WebSocket + Redis pub/sub |
| Serving | Gunicorn + Uvicorn (backend), Nginx (frontend) |
| Local AI | vLLM OpenAI-compatible server (profile-gated, GPU) |
| Speech-to-text | faster-whisper (multilingual, int8 CPU) |
| Emotion analysis | DeepFace / OpenCV (optional, video) |
| Observability (prod) | Prometheus, Alertmanager, Loki, Grafana, node-exporter |
| Testing | pytest (backend), Vitest + Testing Library (frontend), Playwright (E2E), GitHub Actions (CI) |

### Docker Compose Services

- `postgres` — PostgreSQL 15 with health check and persistent volume
- `redis` — Redis 7 with AOF persistence and password protection
- `backend` — FastAPI via Gunicorn + Uvicorn, health-checked
- `db-migrate` — one-off Alembic migration runner on startup
- `frontend` — React production build served via Nginx, health-checked
- `mailpit` — SMTP server and web UI for email testing (development)
- `local-model` (`--profile model`) — vLLM OpenAI-compatible local LLM server
- `evaluation-worker` (`--profile worker`) — RQ worker for durable evaluations

A production variant ([docker-compose.prod.yml](docker-compose.prod.yml)) adds SSL support, resource limits, horizontal scaling of backend and evaluation-worker replicas, and an observability stack (Prometheus + Alertmanager, Loki + Promtail, Grafana, node-exporter).

## Quick Start (Docker)

```bash
cp .env.example .env          # edit settings before starting
docker compose up -d
```

Services start and migrations run automatically. Access:

- Frontend: http://localhost (or `FRONTEND_PORT`)
- API docs: http://localhost:8000/docs
- Mailpit UI: http://localhost:8025

Optional services:

```bash
docker compose --profile worker up -d      # durable evaluation worker
LOCAL_MODEL_PATH=./models/qwen3-8b-awq \
docker compose --profile model up -d local-model   # local LLM (GPU + approved weights)
```

## Local Development

### Backend

```bash
conda activate sris
python -m pip install -r backend/requirements-dev.txt
python -m uvicorn app.main:app --app-dir backend --reload --port 8000
python -m pytest backend/tests -q
```

### Frontend

```bash
npm install --prefix frontend
npm run dev --prefix frontend
npm run test:run --prefix frontend
npm run typecheck --prefix frontend
npm run build --prefix frontend
```

### Release Check

```bash
scripts/release_check.sh
scripts/release_check.sh --with-e2e    # adds Playwright E2E smoke
```

Validates backend tests, environment templates, Alembic migration chain, frontend tests and production build, load-test CLI, Docker Compose config, and backup dry-run.

## Configuration

Environment templates: [.env.example](.env.example) for local development, [.env.production.example](.env.production.example) for production.

Key settings:

| Variable | Purpose |
|----------|---------|
| `DEBUG` | Development mode; production guardrails enforced when `False` |
| `SECRET_KEY` | JWT signing; must be unique and >= 32 chars in production |
| `DATABASE_URL` | SQLAlchemy database URL |
| `REDIS_URL` | Redis connection for RQ evaluation queue |
| `ALLOWED_ORIGINS` | CORS allowlist; no wildcard/localhost in production |
| `FRONTEND_URL` | Frontend origin used in emails and CORS |
| `EVALUATION_QUEUE_BACKEND` | `rq` in production |
| `EVALUATION_QUEUE_NAME` | RQ queue name for evaluation jobs |
| `EVALUATION_PROMPT_VERSION` | Scoring prompt version recorded on each run |
| `EVALUATION_STRUCTURED_OUTPUT_ENABLED` | Send `response_format` and enforce the output schema; degrades to plain JSON on HTTP 400/422 |
| `EVALUATION_PII_MASKING_ENABLED` | Mask candidate PII (emails/phones/name) before payload reaches any LLM; fail-closed |
| `TRANSCRIPTION_PROVIDER`, `WHISPER_*` | `whisper`/`fake` transcription provider and model/device settings |
| `EMOTION_ANALYSIS_PROVIDER` | `deepface`/`disabled`/`fake` facial emotion analysis |
| `MAIL_*`, `EMAIL_PROVIDER` | SMTP / Mailpit / Resend email delivery |
| `MAX_REQUEST_BODY_SIZE` | Upload/request limit |
| `MAX_AUDIO_SIZE`, `MAX_VIDEO_SIZE`, `ALLOWED_*` | Upload type and size limits |
| `MAX_BULK_INVITATIONS`, `INVITATION_RESEND_COOLDOWN_SECONDS` | Invitation limits |
| `INVITATION_EXPIRY_DAYS`, `INVITATION_REMINDER_*` | Invitation expiry and reminder scheduling |
| `MAINTENANCE_ENABLED`, `MAINTENANCE_INTERVAL_SECONDS` | Scheduled expiry/reminder jobs |
| `INTEGRITY_TRACKING_ENABLED` | Client-side anti-cheating event capture |
| `INTEGRITY_BLOCK_CLIPBOARD` | Block copy/paste/right-click during the interview and record attempts |
| `INTEGRITY_ENFORCE_FULLSCREEN` | Require fullscreen during the interview and record exits |
| `METRICS_ENABLED` | Prometheus `/metrics` endpoint |

## AI Evaluation

Evaluation runs through a provider interface with a deterministic rubric-aware fallback, so scoring continues even when the LLM endpoint is unreachable. Health and fallback status are exposed at `GET /api/reports/evaluation/health` and on the employer dashboard.

LLM endpoints are configured per organization — provider (`local_vllm`, `cloud_llm`, or `hybrid`), base URL, model, and API key — from the employer dashboard (`GET /api/users/me/organization/providers`, `PATCH /api/users/me/organization/settings`). No server configuration is required. Organizations without a configured provider hold evaluation runs (`status=pending`) until one is set and reachable; pending runs are re-dispatched automatically after the provider is configured. Each evaluation run records the effective provider and model for auditability.

See [AI_PRODUCTION_ROADMAP.md](AI_PRODUCTION_ROADMAP.md) for the planned best-practice hardening of the AI stack (gateway, structured output, golden evals, guardrails, cost control, tracing).

On completion, media-backed answers are transcribed automatically (multilingual Whisper speech-to-text, configurable provider) and video answers can be analyzed for facial emotion (DeepFace) as operational metadata. Both providers expose health endpoints and queue jobs through the same background mechanism as evaluation.

Model weights are downloaded or run only after explicit approval. Do not download or start model servers without confirming the model source, license, size, hardware requirements, and purpose. Approved-model serving configuration is documented in [DEPLOYMENT.md](DEPLOYMENT.md).

## Testing

Backend tests live in [backend/tests](backend/tests) and cover API, authorization, lifecycle, security, reports, audit, upload, evaluation, email, config guardrails, and transcription contracts.

Frontend unit tests sit beside components and pages under [frontend/src](frontend/src). A Playwright release-candidate smoke against mocked API responses lives in [frontend/e2e/release-candidate.spec.ts](frontend/e2e/release-candidate.spec.ts).

CI ([.github/workflows/ci.yml](.github/workflows/ci.yml)) runs backend tests with SQLite, Alembic migration validation, frontend tests/build and E2E smoke, plus Docker Compose configuration and container smoke tests.

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for the one-command deployment, production variant, security checklist, system requirements, and release verification gates.

See [PRODUCTION.md](PRODUCTION.md) for the production-hardening implementation plan (Resend email, hybrid LLM, SSL, monitoring, backups, CI/CD).

```bash
./deploy.sh                  # build and start
./deploy.sh production       # production variant with SSL
./backup.sh                  # backup database + uploads
```

## API Overview

- `/api/auth` — register, login, refresh, current user, forgot/reset password
- `/api/users` — profile, password, team membership, organization evaluation-provider settings
- `/api/interviews` — interview CRUD, templates, questions, status transitions
- `/api/invitations` — single/bulk invite, preview, verify, revoke, resend
- `/api/responses` — response lifecycle, answers (audio/video), quality, emotion, integrity, timer, completion, retake
- `/api/responses/{id}/decision` and `/scorecard` — reviewer decisions and scorecards
- `/api/responses/{id}/answers/{qid}/transcript` — transcript review and retrieval
- `/api/reports` — employer/candidate reports, PDFs, evaluation audit, analytics, health, re-evaluation
- `/api/audit-logs` — filtered audit log listing for admins and organization owners/admins
- `/api/data-requests` — GDPR export/delete workflow
- `/api/webhooks` — webhook CRUD and delivery logs
- `/api/notifications` — in-app notifications, unread count, read/mark-all-read
- `/api/maintenance` — manual trigger of invitation expiry/reminder jobs
- `/api/ws` — authenticated WebSocket for real-time data-change events
- `/metrics` — Prometheus metrics endpoint (internal scrape)
- `/health` — operational health

Interactive documentation is available at `/docs` when the backend is running.

## Repository Structure

```text
SRIS/
├── backend/
│   ├── alembic/                 # Migration versions
│   ├── app/
│   │   ├── api/                 # FastAPI routers (auth, interviews, responses, reports, webhooks, notifications, maintenance, ws, ...)
│   │   ├── services/            # Email, evaluation, audit, report, webhook, transcription, emotion, notification, maintenance, realtime
│   │   ├── main.py              # App entrypoint, middleware, health, metrics
│   │   ├── metrics.py           # Prometheus instrumentation and custom metrics
│   │   ├── models.py            # SQLAlchemy models
│   │   ├── schemas.py           # Pydantic schemas
│   │   ├── config.py            # Settings and production guardrails
│   │   ├── database.py          # Engine/session setup
│   │   └── worker.py            # RQ worker entrypoint
│   ├── tests/
│   ├── Dockerfile
│   └── requirements*.txt
├── frontend/
│   ├── src/
│   │   ├── components/          # Layout and UI components
│   │   ├── pages/               # Page components (Login, Register, InterviewRoom, ResultsPortal, MyResults, ...)
│   │   ├── services/            # API client
│   │   ├── store/               # Zustand auth state
│   │   └── styles/              # Design system CSS
│   ├── e2e/                     # Playwright release smoke
│   ├── Dockerfile
│   └── nginx.conf
├── docker/
│   ├── grafana/                 # Provisioning, dashboards (prod)
│   ├── nginx/                   # Production Nginx config with SSL
│   ├── postgres/init.sql
│   └── prometheus/              # Prometheus config and alert rules (prod)
├── scripts/
│   ├── load_test.py
│   └── release_check.sh
├── models/                      # Local model weights (user-approved)
├── .github/workflows/ci.yml
├── docker-compose.yml
├── docker-compose.prod.yml
├── deploy.sh
├── backup.sh
├── AI_PRODUCTION_ROADMAP.md
├── DEPLOYMENT.md
└── README.md
```
