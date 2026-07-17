# Smart Remote Interview System - Quick Deployment Guide

## 🚀 One-Command Deployment

```bash
# 1. Clone and configure
git clone <repository-url> && cd SRIS
cp .env.example .env
# Edit .env with your settings (at minimum: SECRET_KEY, OPENAI_API_KEY)

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

---

## 🔐 Security Checklist

- [ ] Change `SECRET_KEY` (use `openssl rand -hex 32`)
- [ ] Change `POSTGRES_PASSWORD` (strong password)
- [ ] Change `REDIS_PASSWORD` (strong password)
- [ ] Set `OPENAI_API_KEY` (your API key)
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

---

## 📚 Next Steps

1. Register as employer: http://localhost/register
2. Create your first interview
3. Invite candidates via email
4. Monitor responses and download reports

**Full documentation:** See README.md
