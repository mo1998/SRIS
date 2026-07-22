# Smart Remote Interview System (SRIS)

SRIS is a production-oriented remote interview platform for structured hiring workflows. It supports employer organizations, role-based interview creation, candidate invitations, candidate response collection, local-first evaluation, evidence-linked reports, operational health checks, and release-readiness automation.

This README is written for future coding tools and agents. It explains what has already been implemented, how the project is structured, what methodology was used, and which rules must be preserved when continuing development.

Current status: implementation is complete through the Phase 6 release-hardening milestone. The remaining release work is environment-gated rehearsal: approved local LLM runtime smoke, real SMTP smoke, backup/restore rehearsal, and production-like Docker product smoke. Those gates are documented in [PHASE6_RELEASE_RUNBOOK.md](PHASE6_RELEASE_RUNBOOK.md).

## Product Scope Implemented

### Authentication, Accounts, And Organizations

- User registration and login with JWT access/refresh tokens.
- Token refresh and token-version revocation after password changes.
- Password complexity validation.
- Failed-login rate limiting with retry headers.
- Employer registration creates an organization and owner membership.
- Team membership roles: owner, admin, recruiter, reviewer.
- Organization-scoped authorization for interviews, invitations, responses, reports, evaluations, and audit logs.
- Account profile and password update endpoints.

### Interview Builder And Templates

- Interview CRUD for employer organizations.
- Draft, active, completed, and cancelled interview statuses.
- Built-in interview templates.
- Question weights, expected answers, and rubric criteria.
- Interview activation guard requiring at least one question.
- Organization member visibility and manager-only mutation controls.

### Invitations And Candidate Pipeline

- Single and bulk invitations.
- Invitation status lifecycle: pending/sent/accepted/completed/expired/revoked.
- Public invitation token verification.
- Invitation email preview.
- Resend cooldown and retry-after behavior.
- Revoke flow that prevents token use.
- Bulk invitation size limit.
- Email health endpoint and SMTP configuration checks.

### Candidate Response Experience

- Candidate response start flow with max-attempt enforcement.
- Text answer submission and optional audio upload.
- Audio upload extension, size, and content-signature validation.
- Quality metric submission.
- Emotion/confidence data capture as operational metadata.
- Completion flow that queues evaluation and updates invitation status.
- Candidate self-access to own response/report.

Important: emotion and quality fields exist as metadata, but hiring-critical scoring is driven by rubric/evaluation evidence. Do not expand emotion/personality traits into candidate scoring.

### Evaluation Engine

- Local-first evaluation provider architecture.
- `local_vllm` OpenAI-compatible provider configuration.
- Deterministic rubric-aware fallback evaluator.
- Persisted `EvaluationRun` records with provider, model, prompt version, config hash, status, timestamps, raw summary, and errors.
- Persisted `EvaluationScore` records with per-answer scores, bilingual feedback, and evidence JSON.
- Single candidate re-evaluation and batch interview re-evaluation.
- Evaluation health endpoint with fallback status.
- Interview-level evaluation analytics.
- Redis/RQ worker support for durable evaluation jobs.

No model weights may be downloaded or run without explicit user approval. See the model approval rules below.

### Reports And Exports

- Employer interview report with ranking, pass rate, provider/model metadata, and evaluation state.
- Candidate report with question-level answers, feedback, evidence, and evaluation metadata.
- Evaluation audit history endpoint per candidate response.
- PDF report generation.
- Access control for employer, organization member, candidate, and cross-organization cases.

### Audit, Security, And Operations

- Durable audit logs for sensitive actions.
- Audit log listing endpoint at `GET /api/audit-logs/`.
- Audit visibility restricted to system admins and organization owners/admins.
- Audit filters for action, target type/id, actor, organization, skip, and limit.
- Audit coverage includes password changes, team membership changes, interview activation/completion/deletion, invitation creation/bulk creation/resend/revoke, response deletion, and evaluation queueing.
- Request IDs and process timing headers.
- Security headers on API responses.
- No-store cache headers on health endpoints.
- Configurable max request body size.
- Production configuration guardrails when `DEBUG=False`.
- Backup dry-run and verification support.
- Load-test CLI for local HTTP smoke tests.
- Release readiness script for local validation.

## Architecture

### Backend

- FastAPI application in [backend/app](backend/app).
- SQLAlchemy models in [backend/app/models.py](backend/app/models.py).
- Alembic migrations in [backend/alembic/versions](backend/alembic/versions).
- Pydantic schemas in [backend/app/schemas.py](backend/app/schemas.py).
- Modular routers in [backend/app/api](backend/app/api).
- Business services in [backend/app/services](backend/app/services).
- RQ worker entrypoint in [backend/app/worker.py](backend/app/worker.py).
- PostgreSQL is the production source of truth.
- SQLite is used for local/CI migration validation and backend tests.
- Redis/RQ is required for production evaluation queueing.

### Frontend

- React 18 + TypeScript + Vite in [frontend](frontend).
- React Router for page routing.
- Zustand for auth state.
- Axios API client with auth behavior.
- React Bootstrap-based UI currently in place.
- Vitest and Testing Library for component/page tests.
- Playwright release-candidate E2E smoke using mocked API responses.

### CI/CD And Release Checks

- GitHub Actions workflow in [.github/workflows/ci.yml](.github/workflows/ci.yml).
- CI jobs:
  - backend tests
  - Alembic migration validation
  - frontend tests and production build
  - Playwright release-candidate E2E smoke
  - Docker Compose config validation
- Local release bundle: [scripts/release_check.sh](scripts/release_check.sh).
- Release-candidate environment gates: [PHASE6_RELEASE_RUNBOOK.md](PHASE6_RELEASE_RUNBOOK.md).

## Development Methodology Used

The project was built in small production-style slices:

1. Start from a concrete failing behavior, feature gap, or hardening requirement.
2. Read only the local code path needed to form a falsifiable hypothesis.
3. Implement the smallest useful change.
4. Immediately run the focused test or command that can disprove the change.
5. Expand tests only after the focused check passes.
6. Run the full release bundle before committing significant slices.
7. Commit to a feature branch.
8. Push, open a PR, wait for CI, merge only when green, and sync `main`.

This methodology should continue. Avoid broad rewrites unless a phase explicitly calls for them.

## Hard Rules For Future Agents

- Do not download, install, or run model weights without explicit user approval.
- Do not add cloud AI dependencies for release-critical evaluation without approval.
- Keep local AI optional and behind provider/service interfaces.
- AI decisions must be explainable, auditable, and human-reviewable.
- Do not use emotion, personality, voice traits, or biometric inference for hiring scores.
- Use Alembic migrations for schema changes. Do not rely on production `create_all`.
- Preserve organization-scoped authorization on every protected route.
- Add or update tests for every behavior change.
- Run focused validation immediately after edits, then full validation before PRs.
- Keep release claims aligned with implemented behavior.
- Do not commit secrets or real `.env` files.
- Do not revert unrelated user or agent changes unless explicitly asked.

## Model Approval Gate

Before any model is downloaded or run, ask the user for explicit approval and include:

- Model name and source.
- License.
- Approximate download size.
- Expected CPU/GPU/RAM requirements.
- Purpose in SRIS.
- Whether it sends telemetry or needs account tokens.
- How to disable or remove it.

Current configured local LLM path:

```bash
export EVALUATION_PROVIDER=local_vllm
export EVALUATION_QUEUE_BACKEND=rq
export EVALUATION_QUEUE_NAME=evaluation
export LOCAL_LLM_BASE_URL=http://localhost:8100/v1
export LOCAL_LLM_MODEL=qwen3-8b-awq
export EVALUATION_PROMPT_VERSION=rubric-v1
```

The vLLM process should only be started after the selected model is approved and already available locally.

## Repository Structure

```text
SRIS/
├── backend/
│   ├── alembic/                 # Alembic env and migration versions
│   ├── app/
│   │   ├── api/                 # FastAPI routers
│   │   ├── services/            # Email, evaluation, audit, report services
│   │   ├── config.py            # Settings and production guardrails
│   │   ├── database.py          # Engine/session setup
│   │   ├── main.py              # FastAPI app, middleware, health
│   │   ├── models.py            # SQLAlchemy models
│   │   ├── schemas.py           # Pydantic schemas
│   │   └── worker.py            # RQ worker entrypoint
│   ├── requirements-dev.txt
│   └── requirements.txt
├── frontend/
│   ├── e2e/                     # Playwright release smoke
│   ├── src/                     # React app
│   ├── package.json
│   └── vite.config.ts
├── scripts/
│   ├── load_test.py
│   └── release_check.sh
├── docker/
├── .github/workflows/ci.yml
├── DEPLOYMENT.md
├── PHASE6_RELEASE_RUNBOOK.md
├── PROJECT_BUILD_PLAN.md
├── backup.sh
├── deploy.sh
├── docker-compose.yml
└── docker-compose.prod.yml
```

## Local Setup

### Backend

Use the existing Conda environment:

```bash
conda activate sris
python -m pip install -r backend/requirements-dev.txt
python -m pytest backend/tests -q
```

Tests set their own SQLite database URL through [backend/tests/conftest.py](backend/tests/conftest.py).

### Frontend

```bash
npm install --prefix frontend
npm run test:run --prefix frontend
npm run build --prefix frontend
```

Run Playwright E2E smoke when browsers are installed:

```bash
npm run test:e2e --prefix frontend
```

### Full Local Release Check

```bash
scripts/release_check.sh
```

Add local E2E when Playwright browsers are available:

```bash
scripts/release_check.sh --with-e2e
```

The release check currently validates:

- backend tests
- environment templates
- Alembic migration chain with SQLite
- frontend unit tests
- frontend production build
- load-test CLI help/syntax
- Docker Compose config
- backup dry-run
- optional Playwright E2E smoke

## Useful Commands

### Git And PR Workflow

```bash
git status --short --branch
git switch -c feature/<slice-name>
# edit, test, commit
git push -u origin feature/<slice-name>
conda run -n sris gh pr create --repo mo1998/SRIS --base main --head feature/<slice-name> --title "<Title>" --body "<Body>"
conda run -n sris gh pr checks <PR_NUMBER> --repo mo1998/SRIS --watch
conda run -n sris gh pr merge <PR_NUMBER> --repo mo1998/SRIS --merge --delete-branch
git switch main
git pull --ff-only
git fetch origin --prune
```

The GitHub CLI is installed in the `sris` Conda environment, so use `conda run -n sris gh ...`.

### Migration Check

```bash
DEBUG=True SECRET_KEY=test-secret-key DATABASE_URL=sqlite:////tmp/sris-migration-check.db \
  conda run -n sris python -m alembic -c backend/alembic.ini upgrade head
```

### Docker Compose Validation

```bash
docker compose config
docker compose -f docker-compose.prod.yml config
```

### Backup Checks

```bash
./backup.sh --dry-run
./backup.sh --verify backups/<backup-directory>
```

### Load Smoke

```bash
python scripts/load_test.py --base-url http://localhost:8000 --candidates 20 --concurrency 5
```

## API Areas

- `/api/auth`: register, login, refresh, current user.
- `/api/users`: profile, password, organization membership, admin user access.
- `/api/interviews`: interview CRUD, templates, status transitions, questions.
- `/api/invitations`: single/bulk invite, preview, verify, revoke, resend.
- `/api/responses`: candidate response lifecycle, answers, quality, emotion, completion, deletion.
- `/api/reports`: reports, PDFs, evaluation health, email health, evaluation audit, analytics, re-evaluation.
- `/api/audit-logs`: filtered audit log listing for admins and organization owners/admins.
- `/health`: operational health with no-store cache and security/request headers.

## Environment Configuration

Use [.env.example](.env.example) for local development and [.env.production.example](.env.production.example) for production-style deployments.

Important settings:

- `DEBUG`
- `SECRET_KEY`
- `DATABASE_URL`
- `REDIS_URL`
- `ALLOWED_ORIGINS`
- `FRONTEND_URL`
- `EVALUATION_PROVIDER`
- `EVALUATION_QUEUE_BACKEND`
- `LOCAL_LLM_BASE_URL`
- `LOCAL_LLM_MODEL`
- `EVALUATION_PROMPT_VERSION`
- `MAIL_FROM`, `MAIL_PASSWORD`, `MAIL_SERVER`, `MAIL_PORT`, `MAIL_TLS`, `MAIL_SSL`
- `MAX_REQUEST_BODY_SIZE`
- `MAX_BULK_INVITATIONS`
- `INVITATION_RESEND_COOLDOWN_SECONDS`

When `DEBUG=False`, startup validates production guardrails:

- `SECRET_KEY` must be unique and at least 32 characters.
- `ALLOWED_ORIGINS` must not include wildcard or localhost origins.
- `EVALUATION_QUEUE_BACKEND` must be `rq`.

## Testing Map

Backend tests live in [backend/tests](backend/tests):

- [backend/tests/test_smoke.py](backend/tests/test_smoke.py): API, authorization, lifecycle, security, reports, audit, upload, and release smoke coverage.
- [backend/tests/test_evaluation_service.py](backend/tests/test_evaluation_service.py): scoring/provider behavior.
- [backend/tests/test_email_service.py](backend/tests/test_email_service.py): email rendering and health.
- [backend/tests/test_report_service.py](backend/tests/test_report_service.py): report generation helpers.
- [backend/tests/test_config.py](backend/tests/test_config.py): production settings guardrails.
- [backend/tests/test_performance_smoke.py](backend/tests/test_performance_smoke.py): CI-safe performance smoke.

Frontend tests live beside pages/components under [frontend/src](frontend/src). E2E smoke lives in [frontend/e2e/release-candidate.spec.ts](frontend/e2e/release-candidate.spec.ts).

## Release State

Code, docs, tests, and CI are complete through Phase 6 release hardening.

Completed PR sequence includes:

- Request observability and security headers.
- Login rate limiting and password complexity.
- Production config guardrails.
- Audio upload validation.
- Invitation resend throttle and bulk limits.
- Token revocation after password change.
- Backup dry-run and verification.
- Email and evaluation health endpoints.
- Candidate response deletion.
- Migration validation.
- Environment template readiness.
- Health cache-control.
- Request body size limiting.
- Durable audit logs.
- Audit log visibility and expanded audit coverage.
- Audio content signature validation.
- Phase 6 release runbook.

Environment-gated checks still require real infrastructure or explicit permission:

- approved local LLM/vLLM runtime smoke
- real SMTP smoke
- backup/restore rehearsal into a clean target
- production-like Docker product smoke

Follow [PHASE6_RELEASE_RUNBOOK.md](PHASE6_RELEASE_RUNBOOK.md) for those gates.

## Roadmap Context

[PROJECT_BUILD_PLAN.md](PROJECT_BUILD_PLAN.md) remains the strategic roadmap. Some future roadmap items are still not fully implemented, especially deeper transcription provider work, reviewer scorecards, data retention workflows, integrations, and a full modern UI rebuild. Future agents should treat the plan as direction, not as a claim that every later phase is complete.

Recommended next code phases after release rehearsal:

1. Transcription provider interface and fake-provider contract tests.
2. Transcript review/edit in reports.
3. Reviewer scorecards and human decision states.
4. Data retention policy and candidate export/delete workflows.
5. Modern UI rebuild with domain-specific SaaS design tokens.
6. Webhooks and integration automation.

Keep each slice small, tested, PR-based, and aligned with the approval gates above.
