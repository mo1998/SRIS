# Smart Remote Interview System - Quick Deployment Guide

## 🚀 One-Command Deployment

```bash
# 1. Clone and configure
git clone <repository-url> && cd SRIS
cp .env.example .env
# Edit .env with your settings (at minimum: SECRET_KEY and local LLM evaluation settings)

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
```

### Production
```bash
./deploy.sh production           # Deploy with SSL
docker compose -f docker-compose.prod.yml logs -f
docker compose -f docker-compose.prod.yml up -d --scale backend=4
```

### Database
```bash
./backup.sh                      # Backup database + uploads
docker compose up db-migrate     # Run migrations
docker compose exec postgres psql -U postgres sris_db
```

### Local LLM Evaluation
```bash
export EVALUATION_PROVIDER=local_vllm
export LOCAL_LLM_BASE_URL=http://localhost:8100/v1
export LOCAL_LLM_MODEL=qwen3-8b-awq
export EVALUATION_PROMPT_VERSION=rubric-v1
```

Health and fallback status are available in the Employer Dashboard and via:

```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/reports/evaluation/health
```

Do not download or run model weights until the model has been explicitly approved.

---

## 🔐 Security Checklist

- [ ] Change `SECRET_KEY` (use `openssl rand -hex 32`)
- [ ] Change `POSTGRES_PASSWORD` (strong password)
- [ ] Change `REDIS_PASSWORD` (strong password)
- [ ] Configure `LOCAL_LLM_BASE_URL`, `LOCAL_LLM_MODEL`, and `EVALUATION_PROMPT_VERSION`
- [ ] Confirm local LLM health endpoint reports expected provider/model/fallback status
- [ ] Configure email SMTP settings
- [ ] Setup SSL certificates for production
- [ ] Update `FRONTEND_URL` and `ALLOWED_ORIGINS`
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

---

## 📚 Next Steps

1. Register as employer: http://localhost/register
2. Create your first interview
3. Invite candidates via email
4. Monitor responses and download reports
5. Verify evaluation audit trail, health status, and PDF evidence before release

**Full documentation:** See README.md
