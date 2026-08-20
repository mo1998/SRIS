# Smart Remote Interview System - Quick Deployment Guide

## 🚀 One-Command Deployment

```bash
# 1. Clone and configure
git clone <repository-url> && cd SRIS
cp .env.example .env                  # Local/development
# or: cp .env.production.example .env # Production
# Edit .env with your settings before deploying

# 2. Deploy
./deploy.sh
```

**Access:** http://localhost (Frontend) | http://localhost:8000/docs (API)

---

## 📋 File Structure

```
SRIS/
├── backend/                  # FastAPI Backend
│   ├── Dockerfile           # Production Docker image
│   ├── .dockerignore        # Docker ignore rules
│   ├── alembic/             # Database migrations
│   │   ├── env.py
│   │   └── versions/
│   │       └── 001_initial.py
│   └── alembic.ini
│
├── frontend/                # React Frontend
│   ├── Dockerfile          # Production Docker image
│   ├── .dockerignore       # Docker ignore rules
│   └── nginx.conf          # Nginx configuration
│
├── docker/
│   ├── postgres/
│   │   └── init.sql        # Database initialization
│   └── nginx/
│       └── nginx-prod.conf # Production SSL config
│
├── docker-compose.yml       # Development compose
├── docker-compose.prod.yml  # Production compose
├── .env.example            # Environment template
├── .env.production.example # Production environment template
├── deploy.sh               # Deployment script
└── backup.sh               # Backup script
```

---

## 🔧 Common Commands

### Development
```bash
./deploy.sh                      # Build and start
docker compose logs -f           # View logs
docker compose down              # Stop
docker compose restart           # Restart
docker compose config            # Validate compose files
scripts/release_check.sh         # Backend, frontend, build, load CLI, compose checks
DEBUG=True SECRET_KEY=test-secret-key DATABASE_URL=sqlite:////tmp/sris-migration-check.db conda run -n sris python -m alembic -c backend/alembic.ini upgrade head
python scripts/load_test.py --base-url http://localhost:8000 --candidates 20 --concurrency 5
npm run test:e2e --prefix frontend
```

### Release Verification

Before a production release, run the local release bundle and confirm the environment gates below:

```bash
scripts/release_check.sh
scripts/release_check.sh --with-e2e   # when Playwright browsers are available
```

Production-like Docker candidate with `DEBUG=False` (guardrails active): boot the stack, confirm `GET /health` returns HTTP 200 with `Cache-Control: no-store`, request/security headers, and the backend and `evaluation-worker` logs stay clean.

Product smoke: register an employer, create and activate an interview, send one invitation, complete a candidate response, confirm an evaluation run is queued and processed, and verify reports, evaluation audit, analytics, and PDF export render.

Local LLM gate (only after model weights are explicitly approved): start the OpenAI-compatible endpoint, confirm `/api/reports/evaluation/health` reports the intended provider/model, and verify fallback evaluation evidence is recorded when the endpoint is unavailable.

SMTP gate: with real or staging SMTP configured, confirm `/api/reports/email/health` reports configured status, invitations send, resend is rate-limited, and send failures do not break candidate completion.

Backup/restore rehearsal: with a non-empty dataset, run `./backup.sh` and `./backup.sh --verify backups/<directory>`, then restore into a clean environment and confirm the employer can log in and interview/report/evaluation/audit data plus uploaded files are intact.

Release is ready when `scripts/release_check.sh` and CI pass, the production-like candidate boots with guardrails enabled, the product smoke passes, and the local LLM, SMTP, and backup/restore gates pass or are explicitly deferred.

### Production
```bash
./deploy.sh production           # Deploy with SSL
docker compose -f docker-compose.prod.yml logs -f
docker compose -f docker-compose.prod.yml up -d --scale backend=4
```

### Database
```bash
./backup.sh                      # Backup database + uploads
./backup.sh --dry-run            # Check backup prerequisites without writing files
./backup.sh --verify backups/YYYYMMDD_HHMMSS
docker compose up db-migrate     # Run migrations
docker compose exec postgres psql -U postgres sris_db
```

### LLM Evaluation (per-organization)
LLM endpoints are configured per organization from the Employer Dashboard
(Dashboard → AI Provider): provider, base URL, model, and API key. Tuning knobs only:

```bash
export EVALUATION_QUEUE_BACKEND=rq
export EVALUATION_QUEUE_NAME=evaluation
export EVALUATION_PROMPT_VERSION=rubric-v2
```

Organizations without a configured provider hold evaluations until one is set and
reachable. Health and fallback status are available in the Employer Dashboard and via:

```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/reports/evaluation/health
```

Do not download or run model weights until the model has been explicitly approved.

Docker deployments include an `evaluation-worker` service that consumes Redis/RQ jobs. Scale it independently when evaluations become a bottleneck:

```bash
docker compose up -d --scale evaluation-worker=2
docker compose -f docker-compose.prod.yml up -d --scale evaluation-worker=${EVALUATION_WORKER_REPLICAS:-2}
```

---

## 🔐 Security Checklist

- [ ] Change `SECRET_KEY` (use `openssl rand -hex 32`)
- [ ] Confirm `DEBUG=False` only after production secrets, non-local CORS origins, and Redis/RQ evaluation queue are configured
- [ ] Change `POSTGRES_PASSWORD` (strong password)
- [ ] Change `REDIS_PASSWORD` (strong password)
- [ ] Configure per-org LLM provider (base URL, model, API key) in the Employer Dashboard and confirm health shows `available`
- [ ] Confirm LLM health endpoint reports expected provider/model/status
- [ ] Configure email SMTP settings
- [ ] Setup SSL certificates for production
- [ ] Update `FRONTEND_URL` and `ALLOWED_ORIGINS`
- [ ] Confirm `MAX_REQUEST_BODY_SIZE` matches expected upload/request limits
- [ ] Test backup script works

---

## 📊 System Requirements

| Environment | RAM | CPU | Storage |
|-------------|-----|-----|---------|
| Development | 4GB | 2 cores | 20GB |
| Production (small) | 8GB | 4 cores | 50GB |
| Production (large) | 16GB | 8 cores | 100GB |

---

## 🆘 Troubleshooting

| Problem | Solution |
|---------|----------|
| Build fails | `docker system prune -a && ./deploy.sh` |
| Port in use | Change port in `.env` or stop conflicting service |
| DB connection error | `docker compose restart postgres` |
| Container won't start | `docker compose logs <service-name>` |
| Evaluations use fallback | Check `/api/reports/evaluation/health`, vLLM process, model name, and the org's provider base URL |
| Evaluation appears pending | Check candidate audit trail and org provider config; pending runs are held until the LLM is configured and reachable |
| Evaluation queue is stuck | Check `docker compose logs evaluation-worker`, Redis health, and `EVALUATION_QUEUE_BACKEND` |
| Backend exits on startup | Check production guardrail errors for `SECRET_KEY`, `ALLOWED_ORIGINS`, and `EVALUATION_QUEUE_BACKEND` |

---

## 📚 Next Steps

1. Register as employer: http://localhost/register
2. Create your first interview
3. Invite candidates via email
4. Monitor responses and download reports
5. Verify evaluation audit trail, health status, and PDF evidence before release

**Full documentation:** See README.md
