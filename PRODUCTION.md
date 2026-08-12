# SRIS Production Hardening Plan

Status: **partially implemented.** Phase 0 shipped (deploy/env/compose/SSL).
Phase 1 shipped (Resend email provider + retry/backoff + health reporting).
Phase 2 shipped (hybrid LLM: local vLLM → cloud → deterministic, config-driven).
Phases 3-7 pending. Read before continuing implementation.

## Decisions (locked)

- **Email provider:** Resend
- **LLM evaluation:** Hybrid — local vLLM first, cloud OpenAI-compatible fallback, deterministic baseline last
- **Hosting:** Single VPS + Docker Compose + certbot SSL
- **Observability:** Full stack — Prometheus + Grafana + Loki
- **CI/CD:** GitHub Actions
- **Scope:** Production-hardening only. Single-tenant. No multi-tenancy, no SSO/SAML, no K8s, no object-storage migration.

## Current state (audit date 2026-08-11)

### Critical blockers

1. **Email dead on arrival** — `backend/app/services/email_service.py:123` POSTs to
   `MAILPIT_API_URL` (Mailpit = dev catch-all only). No real SMTP/HTTP provider, so
   candidates never receive invitations, reminders, reset links, or results.
2. **Prod LLM cannot run** — `docker-compose.prod.yml` has no `local-model` service,
   but `.env.production.example` sets `EVALUATION_PROVIDER=local_vllm` and
   `LOCAL_LLM_BASE_URL=http://localhost:8100/v1`. `localhost` does not resolve inside
   containers; provider chain silently degrades to `deterministic_baseline`.
3. **deploy.sh env bug** — `deploy.sh:22` copies `.env.example` (`DEBUG=True`, placeholder
   keys) for **every** environment including production. The guardrail at
   `backend/app/config.py:134` would then refuse to start, so the first production
   deploy fails.
4. **SSL untested/mismatched** — compose mounts `./docker/nginx/ssl/{fullchain,privkey}.pem`,
   while `.env.production.example` references letsencrypt paths nothing uses. No certbot
   or auto-renew. `docker/nginx/nginx-prod.conf:4` hardcodes `yourdomain.com`.

### High priority

5. No rate limiting at the edge, no CSP header, single postgres, backups without
   retention/offsite/automation/restore-test, no failed-job handling for RQ.
6. Zero observability — no metrics, error tracking, or alerting. Container healthchecks only.
7. `--no-cache` + `up -d` deploys cause downtime; single-host scaling ceiling (shared volumes).
8. Media on local volumes only (no S3); transcription (whisper int8 CPU) and emotion
   analysis slow but functional.

## Phases

### Phase 0 — Deploy & config fixes (unblocks everything)

- **deploy.sh**: select env correctly — `production` must use `.env.production.example`.
  Add preflight: refuse to run on `CHANGE_ME`/placeholder values; assert `DEBUG=False`.
- **`.env.production.example`**: rewrite — drop Mailpit, add `RESEND_API_KEY`, cloud LLM
  vars, set `LOCAL_LLM_BASE_URL=http://local-model:8100/v1`.
- **docker-compose.prod.yml**: add `local-model` vLLM service (GPU passthrough,
  `runtime: nvidia`), toggled by `ENABLE_LOCAL_LLM` so it can be skipped on GPU-less hosts.
  Fix worker/backend LLM base URL. Pass Resend + cloud LLM envs to backend and
  `evaluation-worker`.
- **SSL**: certbot via compose service (or host systemd timer) with auto-renew; mount live
  certs into nginx; replace hardcoded `yourdomain.com` in `docker/nginx/nginx-prod.conf`.

### Phase 1 — Resend email (critical)

- `email_service.py` — introduce `EmailProvider` protocol. `ResendEmailProvider`
  (httpx POST `https://api.resend.com/emails`, Bearer key; same payload shape as current
  Mailpit call). Keep `MailpitEmailProvider` for dev/tests. New config key
  `EMAIL_PROVIDER` (`resend|mailpit|disabled`) and `RESEND_API_KEY`.
- `get_email_health()` (`email_service.py:23`) — report provider + key presence.
- Rate-limit bulk sends (`MAX_BULK_INVITATIONS=100`): bounded concurrency, retry with
  backoff, per-send error logging.
- Update `backend/tests/test_email_service.py` mocks for the provider abstraction.

### Phase 2 — Hybrid LLM evaluation

- New `CloudLLMEvaluationProvider` mirroring `LocalVLLMEvaluationProvider`
  (`evaluation_service.py:101`) payload/parse, OpenAI-compatible base URL. New config:
  `CLOUD_LLM_BASE_URL` (default `https://api.openai.com/v1`), `CLOUD_LLM_MODEL`,
  `CLOUD_LLM_API_KEY`, `CLOUD_LLM_TIMEOUT_SECONDS`.
- Chain at `evaluation_service.py:200-207`: `EVALUATION_PROVIDER=hybrid` ⇒
  `local_vllm` → `cloud` → `deterministic_baseline`, reusing the existing fallback
  pattern (fallback evidence already records reason/model at lines 161-167).
- Toggles `LOCAL_LLM_ENABLED` / `CLOUD_LLM_ENABLED`; health reports both endpoints.
- Worker (`docker-compose.prod.yml:91`) gets the new envs.

### Phase 3 — Security hardening

- **nginx-prod.conf**: add CSP header, `limit_req` on `/api/auth/*`, `server_tokens off`.
- **Backend**: `slowapi` rate limits on auth endpoints (login/reset limits already exist
  at `config.py:25-28`); extend to registration and general API abuse. Extend
  `validate_production_settings` (`config.py:112`) to reject placeholder Resend key and
  `EMAIL_PROVIDER=mailpit` when `DEBUG=False`.
- Optional: refresh-token rotation on reuse detection.

### Phase 4 — Observability (Prometheus + Grafana + Loki)

- Backend `/metrics` endpoint (prometheus-fastapi-instrumentator; new dependency) exposing
  HTTP latency/errors, RQ queue depth, LLM fallback counter, email failure counter.
- Compose services: `prometheus` (scrape backend + node-exporter), `loki` + `promtail`
  (container logs), `grafana` (provisioned datasources + dashboards).
- Alerts: email failure rate, evaluation queue backlog, 5xx spike, dead worker. Notify via
  Slack/webhook.

### Phase 5 — Backups & DR

- Automate `backup.sh` via host cron/systemd timer; add retention (keep N), offsite copy
  (`rclone` → S3 or second host), encrypt backups (`age`).
- Add `scripts/restore_verify.sh` — monthly restore into a disposable compose env.
- Document RTO/RPO in runbook.

### Phase 6 — CI/CD (GitHub Actions)

- **CI (PR)**: backend `pytest` (via Docker), frontend `vitest` + build,
  `scripts/release_check.sh` (compose validation + migrations). Add `ruff` for lint
  (none currently configured; backend has only `requirements.txt` + `requirements-dev.txt`).
- **CD (main)**: build → push GHCR → ssh to VPS → `docker compose pull && up -d`;
  run DB migrations via the existing `db-migrate` service before app restart.

### Phase 7 — Docs & runbook

- Rewrite `DEPLOYMENT.md`: real one-command flow, secrets management, SSL renewal,
  backup/restore runbook, incident runbook (service down / queue stuck / LLM fallback
  storm), monitoring how-to, first-run validation checklist.

## Reference notes

- Backend test runner: `pytest` + `pytest-asyncio` (`backend/requirements-dev.txt`).
- Release gate: `scripts/release_check.sh` (E2E optional `--with-e2e`, compose check,
  load-test help check, alembic migration validation).
- Email payload shape (Mailpit) at `email_service.py:117-124` — keep `From`/`To`/
  `Subject`/`HTML` shape for Resend compatibility.
