"""
Configuration settings for the application
"""

from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Smart Remote Interview System"
    DEBUG: bool = True
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Observability
    METRICS_ENABLED: bool = os.getenv("METRICS_ENABLED", "true").lower() == "true"
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/sris_db")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # JWT Authentication
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    LOGIN_RATE_LIMIT_ATTEMPTS: int = int(os.getenv("LOGIN_RATE_LIMIT_ATTEMPTS", "5"))
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = int(os.getenv("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "300"))
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("PASSWORD_RESET_TOKEN_EXPIRE_MINUTES", "30"))
    PASSWORD_RESET_RATE_LIMIT_PER_HOUR: int = int(os.getenv("PASSWORD_RESET_RATE_LIMIT_PER_HOUR", "5"))

    # Candidate submission rate limiting (per response / per IP)
    RESPONSE_SUBMISSION_RATE_LIMIT: int = int(os.getenv("RESPONSE_SUBMISSION_RATE_LIMIT", "60"))
    RESPONSE_SUBMISSION_RATE_WINDOW_SECONDS: int = int(os.getenv("RESPONSE_SUBMISSION_RATE_WINDOW_SECONDS", "60"))
    RESPONSE_START_RATE_LIMIT: int = int(os.getenv("RESPONSE_START_RATE_LIMIT", "30"))
    RESPONSE_START_RATE_WINDOW_SECONDS: int = int(os.getenv("RESPONSE_START_RATE_WINDOW_SECONDS", "60"))
    
    # Email
    EMAIL_PROVIDER: str = os.getenv("EMAIL_PROVIDER", "mailpit")
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
    MAIL_FROM: str = os.getenv("MAIL_FROM", "noreply@sris.com")
    MAIL_FROM_NAME: str = os.getenv("MAIL_FROM_NAME", "SRIS")
    MAILPIT_API_URL: str = os.getenv("MAILPIT_API_URL", "http://localhost:8025/api/v1/send")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    INVITATION_RESEND_COOLDOWN_SECONDS: int = int(os.getenv("INVITATION_RESEND_COOLDOWN_SECONDS", "300"))
    MAX_BULK_INVITATIONS: int = int(os.getenv("MAX_BULK_INVITATIONS", "100"))
    INVITATION_EXPIRY_DAYS: int = int(os.getenv("INVITATION_EXPIRY_DAYS", "7"))
    INVITATION_REMINDER_AFTER_HOURS: int = int(os.getenv("INVITATION_REMINDER_AFTER_HOURS", "24"))
    INVITATION_REMINDER_MAX: int = int(os.getenv("INVITATION_REMINDER_MAX", "2"))
    INVITATION_REMINDER_COOLDOWN_HOURS: int = int(os.getenv("INVITATION_REMINDER_COOLDOWN_HOURS", "48"))
    MAINTENANCE_ENABLED: bool = os.getenv("MAINTENANCE_ENABLED", "true").lower() == "true"
    MAINTENANCE_INTERVAL_SECONDS: int = int(os.getenv("MAINTENANCE_INTERVAL_SECONDS", "3600"))
    
    # Evaluation
    EVALUATION_QUEUE_BACKEND: str = os.getenv("EVALUATION_QUEUE_BACKEND", "background")
    EVALUATION_QUEUE_NAME: str = os.getenv("EVALUATION_QUEUE_NAME", "evaluation")
    EVALUATION_PROMPT_VERSION: str = os.getenv("EVALUATION_PROMPT_VERSION", "rubric-v1")
    EVALUATION_MAX_TOKENS: int = int(os.getenv("EVALUATION_MAX_TOKENS", "512"))
    # Provider endpoints are configured per organization from the UI (not env).

    # OpenAI (legacy; local providers are preferred)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # File Uploads
    UPLOAD_DIR: str = "uploads"
    MAX_REQUEST_BODY_SIZE: int = int(os.getenv("MAX_REQUEST_BODY_SIZE", str(110 * 1024 * 1024)))
    MAX_AUDIO_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_AUDIO_EXTENSIONS: List[str] = [".wav", ".mp3", ".webm", ".m4a", ".ogg"]
    MAX_VIDEO_SIZE: int = 100 * 1024 * 1024  # 100MB
    ALLOWED_VIDEO_EXTENSIONS: List[str] = [".webm", ".mp4", ".mov"]
    
    # Interview Settings
    DEFAULT_INTERVIEW_DURATION: int = 30  # minutes
    MAX_INTERVIEW_ATTEMPTS: int = 3
    
    # Transcription
    TRANSCRIPTION_PROVIDER: str = os.getenv("TRANSCRIPTION_PROVIDER", "fake")
    TRANSCRIPTION_QUEUE_BACKEND: str = os.getenv("TRANSCRIPTION_QUEUE_BACKEND", "background")
    TRANSCRIPTION_QUEUE_NAME: str = os.getenv("TRANSCRIPTION_QUEUE_NAME", "transcription")
    WHISPER_MODEL_SIZE: str = os.getenv("WHISPER_MODEL_SIZE", "small")
    WHISPER_DEVICE: str = os.getenv("WHISPER_DEVICE", "cpu")
    WHISPER_COMPUTE_TYPE: str = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
    WHISPER_VAD_FILTER: bool = os.getenv("WHISPER_VAD_FILTER", "true").lower() == "true"

    # Emotion Analysis
    EMOTION_ANALYSIS_PROVIDER: str = os.getenv("EMOTION_ANALYSIS_PROVIDER", "disabled")
    EMOTION_FRAME_SAMPLE_SECONDS: float = float(os.getenv("EMOTION_FRAME_SAMPLE_SECONDS", "1.0"))
    EMOTION_MAX_FRAMES: int = int(os.getenv("EMOTION_MAX_FRAMES", "60"))
    EMOTION_ANALYSIS_TIMEOUT_SECONDS: int = int(os.getenv("EMOTION_ANALYSIS_TIMEOUT_SECONDS", "120"))
    EMOTION_ANALYSIS_PARALLEL: bool = os.getenv("EMOTION_ANALYSIS_PARALLEL", "true").lower() == "true"

    # Quality Thresholds
    MIN_VOICE_CONFIDENCE: float = 0.7
    MIN_FACE_VISIBILITY: float = 0.8
    MIN_LIGHTING_SCORE: float = 0.6
    MAX_BACKGROUND_NOISE: float = 0.3

    # Integrity / anti-cheating
    INTEGRITY_TRACKING_ENABLED: bool = os.getenv("INTEGRITY_TRACKING_ENABLED", "true").lower() == "true"
    INTEGRITY_BLOCK_CLIPBOARD: bool = os.getenv("INTEGRITY_BLOCK_CLIPBOARD", "true").lower() == "true"
    INTEGRITY_ENFORCE_FULLSCREEN: bool = os.getenv("INTEGRITY_ENFORCE_FULLSCREEN", "false").lower() == "true"
    INTERVIEW_DURATION_GRACE_SECONDS: int = int(os.getenv("INTERVIEW_DURATION_GRACE_SECONDS", "60"))

    # Scoring weights (applied when a quality/emotion value is present)
    SCORING_QUALITY_WEIGHT: float = float(os.getenv("SCORING_QUALITY_WEIGHT", "0.1"))
    SCORING_EMOTION_WEIGHT: float = float(os.getenv("SCORING_EMOTION_WEIGHT", "0.05"))
    
    model_config = {"env_file": ".env", "case_sensitive": True, "extra": "ignore"}


settings = Settings()


INSECURE_SECRET_KEYS = {
    "your-secret-key-change-in-production",
    "your-super-secret-key-change-this-in-production",
    "test-secret-key",
    "",
}


def validate_production_settings(active_settings: Settings) -> None:
    if active_settings.DEBUG:
        return

    errors = []
    if active_settings.SECRET_KEY in INSECURE_SECRET_KEYS or len(active_settings.SECRET_KEY) < 32:
        errors.append("SECRET_KEY must be unique and at least 32 characters when DEBUG=False")

    if "*" in active_settings.ALLOWED_ORIGINS:
        errors.append("ALLOWED_ORIGINS must not contain '*' when DEBUG=False")

    local_origins = [origin for origin in active_settings.ALLOWED_ORIGINS if "localhost" in origin or "127.0.0.1" in origin]
    if local_origins:
        errors.append("ALLOWED_ORIGINS must not contain localhost origins when DEBUG=False")

    if active_settings.EVALUATION_QUEUE_BACKEND != "rq":
        errors.append("EVALUATION_QUEUE_BACKEND must be 'rq' when DEBUG=False")

    if errors:
        raise RuntimeError("Unsafe production configuration: " + "; ".join(errors))


validate_production_settings(settings)
