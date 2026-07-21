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

Use `PHASE6_RELEASE_RUNBOOK.md` for the final production-like Docker, local LLM, SMTP, product smoke, backup/restore, and release decision gates.

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

### Local LLM Evaluation
```bash
export EVALUATION_PROVIDER=local_vllm
export EVALUATION_QUEUE_BACKEND=rq
export EVALUATION_QUEUE_NAME=evaluation
export LOCAL_LLM_BASE_URL=http://localhost:8100/v1
export LOCAL_LLM_MODEL=qwen3-8b-awq
export EVALUATION_PROMPT_VERSION=rubric-v1
```

Health and fallback status are available in the Employer Dashboard and via:

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
- [ ] Configure `LOCAL_LLM_BASE_URL`, `LOCAL_LLM_MODEL`, and `EVALUATION_PROMPT_VERSION`
- [ ] Confirm local LLM health endpoint reports expected provider/model/fallback status
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
| Evaluations use fallback | Check `/api/reports/evaluation/health`, vLLM process, model name, and `LOCAL_LLM_BASE_URL` |
| Evaluation appears pending | Check candidate audit trail for queued/running/failed runs and backend logs |
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
