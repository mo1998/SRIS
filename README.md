# Smart Remote Interview System (SRIS)

An AI-powered remote interview platform that enables employers to create interviews, invite candidates, and receive AI-evaluated results with emotion detection, voice denoising, and quality assessment.

## Features

### For Employers
- ✅ Create interviews with custom questions and expected answers
- ✅ Set interview duration, pass scores, and maximum attempts
- ✅ Invite candidates via email (single or bulk invitations)
- ✅ Real-time candidate ranking and performance reports
- ✅ PDF report generation for interview results
- ✅ View quality metrics (voice, background, face visibility, lighting)
- ✅ Emotion and confidence analysis for each candidate

### For Candidates/Employees
- ✅ Receive interview invitations via email with unique links
- ✅ AI-conducted interviews with real-time quality feedback
- ✅ Voice recording and text answer submission
- ✅ Real-time quality metrics display (voice, background, face, lighting)
- ✅ Emotion detection and confidence tracking
- ✅ Personal performance reports after completion

### AI/ML Features
- 🤖 **Answer Evaluation**: OpenAI-powered semantic answer scoring
- 🎤 **Voice Denoising**: Audio quality enhancement using noisereduce
- 😊 **Emotion Detection**: Real-time facial emotion analysis
- 📹 **Face Detection**: Face visibility and positioning validation
- 🌅 **Background Quality**: Background appropriateness assessment
- 💡 **Lighting Detection**: Environment lighting quality checks

## Technology Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL
- **Cache**: Redis
- **AI/ML**: OpenAI API, OpenCV, MediaPipe, DeepFace, noisereduce
- **Authentication**: JWT with python-jose
- **Email**: FastAPI-mail
- **PDF Generation**: ReportLab

### Frontend
- **Framework**: React + TypeScript
- **Build Tool**: Vite
- **UI Library**: React-Bootstrap
- **State Management**: Zustand
- **Routing**: React Router v6
- **Video/Audio**: WebRTC, MediaRecorder API
- **Charts**: Chart.js + react-chartjs-2

## Project Structure

```
SRIS/
├── backend/
│   ├── app/
│   │   ├── api/              # API routes
│   │   │   ├── auth.py       # Authentication endpoints
│   │   │   ├── users.py      # User management
│   │   │   ├── interviews.py # Interview CRUD
│   │   │   ├── invitations.py # Invitation system
│   │   │   ├── responses.py  # Candidate responses
│   │   │   ├── reports.py    # Report generation
│   │   │   └── router.py     # Router configuration
│   │   ├── services/         # Business logic
│   │   │   ├── email_service.py
│   │   │   ├── evaluation_service.py
│   │   │   └── report_service.py
│   │   ├── main.py           # FastAPI app
│   │   ├── models.py         # SQLAlchemy models
│   │   ├── schemas.py        # Pydantic schemas
│   │   ├── database.py       # DB configuration
│   │   └── config.py         # App settings
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   │   └── Navbar.tsx
│   │   ├── pages/            # Page components
│   │   │   ├── Login.tsx
│   │   │   ├── Register.tsx
│   │   │   ├── EmployerDashboard.tsx
│   │   │   ├── CreateInterview.tsx
│   │   │   ├── InterviewDetail.tsx
│   │   │   ├── InterviewRoom.tsx
│   │   │   ├── CandidateReport.tsx
│   │   │   └── MyResults.tsx
│   │   ├── services/         # API service
│   │   │   └── api.ts
│   │   ├── store/            # State management
│   │   │   └── authStore.ts
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css
│   ├── package.json
│   ├── vite.config.ts
│   └── index.html
└── README.md
```

## Setup Instructions

### Prerequisites

**For Local Development:**
- Python 3.10+
- Node.js 18+
- PostgreSQL 14+
- Redis (optional)

**For Docker Deployment (Recommended):**
- Docker 24+
- Docker Compose V2+
- 4GB+ RAM
- 20GB+ disk space

---

### 🐳 Option 1: Docker Deployment (Production Ready)

This is the **recommended** way to deploy the Smart Remote Interview System.

#### Quick Start (Development)

1. **Clone and configure**:
```bash
git clone <repository-url>
cd SRIS
cp .env.example .env
```

2. **Edit `.env` file** with your settings:
```bash
# Required settings
SECRET_KEY=your-super-secret-key  # Run: openssl rand -hex 32
OPENAI_API_KEY=your-openai-key    # For AI answer evaluation

# Email (for sending invitations)
MAIL_FROM=noreply@yourdomain.com
MAIL_PASSWORD=your-email-password
```

3. **Deploy with one command**:
```bash
./deploy.sh
```

That's it! The system will:
- ✅ Build all Docker images
- ✅ Start PostgreSQL, Redis, Backend, and Frontend
- ✅ Run database migrations automatically
- ✅ Health check all services

**Access the application:**
- Frontend: http://localhost
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

#### Production Deployment

1. **Update `.env` for production**:
```bash
# Generate secure keys
openssl rand -hex 32  # For SECRET_KEY
openssl rand -hex 16  # For POSTGRES_PASSWORD, REDIS_PASSWORD

# Update .env with production values
SECRET_KEY=<generated-key>
POSTGRES_PASSWORD=<strong-password>
REDIS_PASSWORD=<strong-password>
OPENAI_API_KEY=<your-key>
FRONTEND_URL=https://yourdomain.com
ALLOWED_ORIGINS=["https://yourdomain.com"]
```

2. **Setup SSL certificate** (Let's Encrypt recommended):
```bash
# Install certbot
sudo apt install certbot

# Generate certificate
sudo certbot certonly --standalone -d yourdomain.com

# Copy certificates to docker directory
mkdir -p docker/nginx/ssl
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem docker/nginx/ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem docker/nginx/ssl/
sudo chmod 644 docker/nginx/ssl/*.pem
```

3. **Deploy to production**:
```bash
./deploy.sh production
```

This will:
- ✅ Build optimized production images
- ✅ Enable SSL/HTTPS
- ✅ Start multiple backend replicas for load balancing
- ✅ Configure resource limits
- ✅ Enable auto-restart

**Access the application:**
- Frontend: https://yourdomain.com
- Backend API: https://yourdomain.com/api
- API Documentation: https://yourdomain.com/api/docs

#### Docker Services Overview

| Service | Container Name | Port | Description |
|---------|---------------|------|-------------|
| PostgreSQL | sris-postgres | 5432 | Primary database |
| Redis | sris-redis | 6379 | Cache and session storage |
| Backend | sris-backend | 8000 | FastAPI application |
| Frontend | sris-frontend | 80/443 | React app with Nginx |
| Migration | sris-migrate | - | Database migrations |

#### Docker Management Commands

**View logs**:
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f frontend
```

**Stop services**:
```bash
docker compose down
```

**Restart services**:
```bash
docker compose restart
```

**Rebuild after code changes**:
```bash
./deploy.sh  # or ./deploy.sh production
```

**Database backup**:
```bash
./backup.sh
```

**Database restore**:
```bash
gunzip -c backups/YYYYMMDD_HHMMSS/database.sql.gz | \
  docker compose exec -T postgres psql -U postgres sris_db
```

**Run database migrations manually**:
```bash
docker compose up db-migrate
```

**Scale backend** (production only):
```bash
docker compose -f docker-compose.prod.yml up -d --scale backend=4
```

**Update to latest version**:
```bash
git pull
./deploy.sh production
```

#### Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | **Required** | JWT signing key (use `openssl rand -hex 32`) |
| `DATABASE_URL` | Auto-set | PostgreSQL connection string |
| `REDIS_URL` | Auto-set | Redis connection string |
| `OPENAI_API_KEY` | **Required** | OpenAI API key for answer evaluation |
| `MAIL_FROM` | noreply@sris.com | Email sender address |
| `MAIL_PASSWORD` | - | SMTP password |
| `MAIL_SERVER` | smtp.gmail.com | SMTP server |
| `MAIL_PORT` | 587 | SMTP port |
| `FRONTEND_URL` | http://localhost | Frontend URL for CORS |
| `DEBUG` | False | Enable debug mode |
| `POSTGRES_USER` | postgres | Database username |
| `POSTGRES_PASSWORD` | **Change me** | Database password |
| `REDIS_PASSWORD` | **Change me** | Redis password |

---

### Option 2: Local Development Setup

### Backend Setup

1. **Create virtual environment**:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Setup PostgreSQL**:
```sql
CREATE DATABASE sris_db;
CREATE USER postgres WITH PASSWORD 'postgres';
GRANT ALL PRIVILEGES ON DATABASE sris_db TO postgres;
```

4. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your settings:
# - DATABASE_URL
# - OPENAI_API_KEY (for AI evaluation)
# - Email settings
```

5. **Run the backend**:
```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`
API Documentation: `http://localhost:8000/docs`

### Frontend Setup

1. **Install dependencies**:
```bash
cd frontend
npm install
```

2. **Run development server**:
```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login (OAuth2 compatible)
- `GET /api/auth/me` - Get current user
- `POST /api/auth/refresh` - Refresh access token

### Interviews
- `POST /api/interviews/` - Create interview
- `GET /api/interviews/` - List employer's interviews
- `GET /api/interviews/{id}` - Get interview details
- `PUT /api/interviews/{id}` - Update interview
- `POST /api/interviews/{id}/activate` - Activate interview
- `POST /api/interviews/{id}/complete` - Complete interview
- `DELETE /api/interviews/{id}` - Delete interview
- `GET /api/interviews/{id}/questions` - Get questions
- `POST /api/interviews/{id}/questions` - Add question

### Invitations
- `POST /api/invitations/` - Create invitation
- `POST /api/invitations/bulk` - Bulk create invitations
- `GET /api/invitations/{interview_id}` - List invitations
- `GET /api/invitations/verify/{token}` - Verify invitation token
- `POST /api/invitations/{id}/resend` - Resend invitation

### Responses
- `POST /api/responses/` - Start interview response
- `POST /api/responses/{id}/answer` - Submit answer
- `POST /api/responses/{id}/quality` - Submit quality metrics
- `POST /api/responses/{id}/emotion` - Submit emotion data
- `POST /api/responses/{id}/complete` - Complete interview
- `GET /api/responses/interview/{id}` - List responses (employer)
- `GET /api/responses/{id}` - Get response details

### Reports
- `GET /api/reports/interview/{id}` - Get interview report
- `GET /api/reports/candidate/{id}` - Get candidate report
- `GET /api/reports/interview/{id}/pdf` - Download interview PDF
- `GET /api/reports/candidate/{id}/pdf` - Download candidate PDF
- `GET /api/reports/my-results` - Get employee's results

## Usage Guide

### For Employers

1. **Register** as an employer
2. **Create Interview**:
   - Set title, description, duration
   - Add questions with expected answers
   - Configure pass score and max attempts
3. **Activate Interview** to make it available
4. **Invite Candidates**:
   - Single invitation via email
   - Bulk upload (CSV format: email, name)
5. **Monitor Progress**: View real-time candidate responses
6. **View Reports**: 
   - Ranked candidate list
   - Individual performance reports
   - Download PDF reports

### For Candidates

1. **Receive Invitation** via email
2. **Click Interview Link** to start
3. **Setup Check**: Ensure camera, microphone, lighting, background
4. **Answer Questions**:
   - Type or record audio answers
   - View real-time quality metrics
   - See emotion detection feedback
5. **Complete Interview**: AI evaluates all responses
6. **View Results**: Access personal performance report

## AI Evaluation System

### Answer Scoring
- Uses OpenAI GPT-3.5-turbo for semantic answer evaluation
- Compares candidate answers to expected answers
- Considers: key points, accuracy, completeness, clarity
- Returns score (0-100) with detailed feedback

### Quality Metrics
1. **Voice Quality** (0-100):
   - Audio clarity
   - Background noise level
   - Speech consistency

2. **Background Quality** (0-100):
   - Professional appropriateness
   - Distractions
   - Cleanliness

3. **Face Visibility** (0-100):
   - Face detection confidence
   - Positioning (centered)
   - Size in frame

4. **Lighting** (0-100):
   - Brightness level
   - Evenness
   - No harsh shadows

### Emotion Detection
- Real-time facial expression analysis
- Emotions tracked: happy, neutral, confident, nervous, stressed
- Timeline recording throughout interview
- Dominant emotion extraction
- Confidence score calculation

## Configuration

### Environment Variables

```bash
# Application
SECRET_KEY=your-secret-key
DEBUG=True

# Database
DATABASE_URL=postgresql://user:pass@localhost/sris_db
REDIS_URL=redis://localhost:6379

# Email
MAIL_FROM=noreply@sris.com
MAIL_PASSWORD=your-password
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587

# OpenAI
OPENAI_API_KEY=your-openai-key

# Frontend
FRONTEND_URL=http://localhost:3000
```

### Quality Thresholds

```python
MIN_VOICE_CONFIDENCE = 0.7
MIN_FACE_VISIBILITY = 0.8
MIN_LIGHTING_SCORE = 0.6
MAX_BACKGROUND_NOISE = 0.3
```

## Database Models

- **User**: Employers, employees, admins
- **Interview**: Interview configuration
- **InterviewQuestion**: Questions with expected answers
- **Invitation**: Candidate invitations with tokens
- **CandidateResponse**: Interview responses with metrics
- **QuestionAnswer**: Individual question answers

## Security Features

- JWT-based authentication
- Password hashing with bcrypt
- Role-based access control
- Secure invitation tokens (UUID)
- CORS protection
- Input validation with Pydantic

## Future Enhancements

- [ ] Real-time video streaming with WebRTC
- [ ] Advanced voice denoising with deep learning
- [ ] Live proctoring features
- [ ] Multi-language support
- [ ] Coding question evaluation
- [ ] Interview question templates
- [ ] Advanced analytics dashboard
- [ ] Mobile app (React Native)
- [ ] Integration with ATS systems
- [ ] Automated scheduling

## Troubleshooting

### Docker Issues

**Build fails**:
```bash
# Clean Docker cache
docker system prune -a

# Rebuild without cache
docker compose build --no-cache
```

**Container won't start**:
```bash
# Check logs
docker compose logs backend

# Verify .env file exists
ls -la .env

# Check Docker is running
docker info
```

**Database connection errors**:
```bash
# Restart PostgreSQL
docker compose restart postgres

# Check PostgreSQL is ready
docker compose exec postgres pg_isready -U postgres
```

**Port already in use**:
```bash
# Find what's using the port
sudo lsof -i :8000  # or :80, :5432

# Stop the conflicting service
# Or change port in .env file
```

### Backend Issues
- **Database connection error**: Check DATABASE_URL and PostgreSQL is running
- **Email not sending**: Verify SMTP credentials in .env
- **OpenAI errors**: Ensure OPENAI_API_KEY is set and has credits

### Frontend Issues
- **API connection error**: Ensure backend is running on port 8000
- **Camera/mic not working**: Check browser permissions and HTTPS
- **Build errors**: Run `npm install` and check Node.js version

## Monitoring & Logging

### View Real-time Logs
```bash
docker compose logs -f
```

### Check Service Health
```bash
docker compose ps
```

### Resource Usage
```bash
docker stats
```

### Database Queries
```bash
docker compose exec postgres psql -U postgres sris_db -c "SELECT * FROM users;"
```

## License

MIT License

## Support

For issues, questions, or contributions, please open a GitHub issue.

---

**Built with ❤️ using FastAPI, React, and AI**
