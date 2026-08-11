# Smart Remote Interview System (SRIS)

SRIS is a production-oriented remote interviewing platform for structured hiring workflows. Employers create role-based interviews with weighted questions and rubrics, invite candidates by email, collect answers with optional audio and environment-quality capture, and get transparent AI-assisted evaluation with evidence-linked reports — all self-hosted and local-first.

The system is containerized with Docker Compose (PostgreSQL, Redis, FastAPI, React, Mailpit, optional local LLM and RQ worker) and ships with an automated CI pipeline, deployment and backup tooling, and a documented release checklist.

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
- Email preview and SMTP health endpoint

### Candidate Response Experience

- Start flow with max-attempt enforcement
- Typed answers with optional audio upload (extension, size, and content-signature validation)
- Environment quality metrics (voice, background, face visibility, lighting) and emotion/confidence capture as operational metadata
- Completion flow that queues evaluation and updates invitation status

### Evaluation Engine

- Local-first evaluation with an OpenAI-compatible `local_vllm` provider
- Deterministic rubric-aware fallback evaluator so evaluations never block on the LLM
- Persisted evaluation runs (provider, model, prompt version, config hash, status, errors) and per-answer scores with bilingual feedback and evidence JSON
- Single and batch re-evaluation; evaluation health endpoint; interview-level analytics
- Durable background evaluation via Redis/RQ worker

Evaluation drives scoring from rubric criteria and evidence, not from emotion or personality signals.

### Reports and Exports

- Employer interview report with candidate ranking and evaluation metadata
- Candidate report limited to candidate information, environment quality, overall score, and emotion & confidence analysis
- Question-by-question breakdown with bilingual feedback, criteria badges, and evidence
- Evaluation audit history with per-run score deltas
- PDF report generation and CSV export

### Webhooks

- Per-organization webhook registration with signed deliveries
- Events: interview.completed, evaluation.completed, invitation.sent, invitation.accepted, invitation.completed
- Exponential-backoff retry (up to 3 attempts) and per-attempt delivery logs

### Compliance and Operations

- GDPR data export/delete request workflow with approval lifecycle
- Reviewer decisions (pass / fail / review) with notes
- Transcript storage and retrieval
- Durable audit logs for sensitive actions
- Login rate limiting, password complexity, token revocation on password change
- Request IDs, process timing, security headers, configurable request body limits
- Production configuration guardrails when `DEBUG=False`
- Backup dry-run and verification; release readiness script

## Architecture

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, SQLAlchemy, Alembic, Pydantic, PostgreSQL (prod) / SQLite (local, CI) |
| Background jobs | Redis + RQ worker |
| Frontend | React 18, TypeScript, Vite, React Bootstrap, Zustand, Axios |
| Serving | Gunicorn + Uvicorn (backend), Nginx (frontend) |
| Local AI | vLLM OpenAI-compatible server (profile-gated, GPU) |
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

A production variant ([docker-compose.prod.yml](docker-compose.prod.yml)) adds SSL support, resource limits, and horizontal scaling of backend and evaluation-worker replicas.

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
| `EVALUATION_PROVIDER` | `local_vllm` (or fallback) |
| `EVALUATION_QUEUE_BACKEND` | `rq` in production |
| `LOCAL_LLM_BASE_URL`, `LOCAL_LLM_MODEL` | OpenAI-compatible local LLM endpoint and model |
| `MAIL_*` | SMTP server, credentials, TLS/SSL |
| `MAX_REQUEST_BODY_SIZE` | Upload/request limit |
| `MAX_BULK_INVITATIONS`, `INVITATION_RESEND_COOLDOWN_SECONDS` | Invitation limits |

## AI Evaluation

Evaluation runs through a provider interface with a deterministic rubric-aware fallback, so scoring continues even when the local LLM is unavailable. Health and fallback status are exposed at `GET /api/reports/evaluation/health` and on the employer dashboard.

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

- `/api/auth` — register, login, refresh, current user
- `/api/users` — profile, password, team membership
- `/api/interviews` — interview CRUD, templates, questions, status transitions
- `/api/invitations` — single/bulk invite, preview, verify, revoke, resend
- `/api/responses` — response lifecycle, answers, quality, emotion, completion, decisions, transcripts
- `/api/reports` — employer/candidate reports, PDFs, evaluation audit, analytics, health, re-evaluation
- `/api/audit-logs` — filtered audit log listing for admins and organization owners/admins
- `/api/data-requests` — GDPR export/delete workflow
- `/api/webhooks` — webhook CRUD and delivery logs
- `/health` — operational health

Interactive documentation is available at `/docs` when the backend is running.

## Repository Structure

```text
SRIS/
├── backend/
│   ├── alembic/                 # Migration versions
│   ├── app/
│   │   ├── api/                 # FastAPI routers
│   │   ├── services/            # Email, evaluation, audit, report, webhook, transcription
│   │   ├── main.py              # App entrypoint, middleware, health
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
│   │   ├── pages/               # Page components
│   │   ├── services/            # API client
│   │   ├── store/               # Zustand auth state
│   │   └── styles/              # Design system CSS
│   ├── e2e/                     # Playwright release smoke
│   ├── Dockerfile
│   └── nginx.conf
├── docker/
│   ├── nginx/                   # Production Nginx config with SSL
│   └── postgres/init.sql
├── scripts/
│   ├── load_test.py
│   └── release_check.sh
├── models/                      # Local model weights (user-approved)
├── .github/workflows/ci.yml
├── docker-compose.yml
├── docker-compose.prod.yml
├── deploy.sh
├── backup.sh
├── DEPLOYMENT.md
└── README.md
```
