# Phase 6 Release Runbook

Use this runbook for the final release-candidate verification of SRIS. Commands assume the repository root and the `sris` Conda environment are available.

## 1. Code Quality Gate

Run the full local release bundle:

```bash
scripts/release_check.sh
```

When Playwright browsers are installed locally, run:

```bash
scripts/release_check.sh --with-e2e
```

Expected result: backend tests, environment template validation, Alembic migration chain, frontend tests/build, load-test CLI validation, Docker Compose config, and backup dry-run pass.

## 2. Production-Like Docker Candidate

Create a production-style environment file:

```bash
cp .env.production.example .env
```

Set production values before starting services:

- `DEBUG=False`
- unique `SECRET_KEY` of at least 32 characters
- non-local `FRONTEND_URL`
- non-local `ALLOWED_ORIGINS`
- strong `POSTGRES_PASSWORD`
- strong `REDIS_PASSWORD`
- `EVALUATION_QUEUE_BACKEND=rq`
- approved `LOCAL_LLM_BASE_URL` and `LOCAL_LLM_MODEL`
- real SMTP settings if email smoke is in scope

Start the stack:

```bash
docker compose -f docker-compose.prod.yml config
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml logs -f backend evaluation-worker
```

Verify:

```bash
curl -i http://localhost:8000/health
```

Expected result: HTTP 200 with `Cache-Control: no-store`, `X-Request-ID`, process timing, and security headers.

## 3. Product Smoke

Using the frontend or API docs, verify this flow:

1. Register an employer.
2. Create and activate an interview.
3. Send one invitation.
4. Verify the invitation link.
5. Start a candidate response.
6. Submit at least one answer.
7. Complete the response.
8. Confirm an evaluation run is queued and processed by the worker.
9. View candidate report, interview report, evaluation audit, evaluation analytics, and audit logs.
10. Download PDF report.

Expected result: the response is completed, evaluation metadata is persisted, reports render, and audit logs show sensitive actions.

## 4. Local LLM Gate

Do not download or run model weights until the model has been explicitly approved.

After approval and once the model is already available locally, configure:

```bash
export EVALUATION_PROVIDER=local_vllm
export EVALUATION_QUEUE_BACKEND=rq
export EVALUATION_QUEUE_NAME=evaluation
export LOCAL_LLM_BASE_URL=http://localhost:8100/v1
export LOCAL_LLM_MODEL=qwen3-8b-awq
export EVALUATION_PROMPT_VERSION=rubric-v1
```

Start the approved OpenAI-compatible local endpoint, then verify:

```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/reports/evaluation/health
```

Expected result: provider health reports the intended provider/model/config hash. A completed interview response produces an `evaluation_runs` row with model metadata, score evidence, and prompt/config metadata.

Failure behavior check: stop the local LLM endpoint and complete or re-evaluate a response. Expected result: SRIS records deterministic fallback evaluation evidence instead of losing the evaluation.

## 5. SMTP Gate

With real or staging SMTP settings configured, verify:

1. `GET /api/reports/email/health` reports configured status.
2. Single invitation email sends successfully.
3. Resend works after cooldown and is rate-limited before cooldown.
4. Completion email failures do not break candidate completion.

Expected result: email health is accurate, sends are observable in logs/provider dashboard, and failed sends do not corrupt application state.

## 6. Backup And Restore Rehearsal

Create a non-empty dataset first, including at least one employer, interview, invitation, response, uploaded audio file, evaluation run, report data, and audit log.

Create and verify backup:

```bash
./backup.sh
./backup.sh --verify backups/<backup-directory>
```

Restore into a clean environment, then verify:

1. Backend starts.
2. Migrations are at head.
3. Employer can log in.
4. Interview/report/evaluation/audit data exists.
5. Uploaded files referenced by answers exist.

Expected result: restored system is usable and data is internally consistent.

## 7. Release Decision

Release is ready when:

- `scripts/release_check.sh` passes.
- CI passes on the release PR.
- Production-like Docker candidate boots with guardrails enabled.
- Product smoke passes.
- Approved local LLM smoke passes or fallback-only release is explicitly accepted.
- SMTP smoke passes or email delivery is explicitly deferred.
- Backup/restore rehearsal passes.
- Audit logs are visible only to system admins and organization owners/admins.
