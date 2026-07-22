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
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/sris_db")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # JWT Authentication
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    LOGIN_RATE_LIMIT_ATTEMPTS: int = int(os.getenv("LOGIN_RATE_LIMIT_ATTEMPTS", "5"))
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = int(os.getenv("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "300"))
    
    # Email (Mailpit)
    MAIL_FROM: str = os.getenv("MAIL_FROM", "noreply@sris.com")
    MAIL_FROM_NAME: str = os.getenv("MAIL_FROM_NAME", "SRIS")
    MAILPIT_API_URL: str = os.getenv("MAILPIT_API_URL", "http://localhost:8025/api/v1/send")
    INVITATION_RESEND_COOLDOWN_SECONDS: int = int(os.getenv("INVITATION_RESEND_COOLDOWN_SECONDS", "300"))
    MAX_BULK_INVITATIONS: int = int(os.getenv("MAX_BULK_INVITATIONS", "100"))
    
    # Evaluation
    EVALUATION_PROVIDER: str = os.getenv("EVALUATION_PROVIDER", "local_vllm")
    EVALUATION_QUEUE_BACKEND: str = os.getenv("EVALUATION_QUEUE_BACKEND", "background")
    EVALUATION_QUEUE_NAME: str = os.getenv("EVALUATION_QUEUE_NAME", "evaluation")
    EVALUATION_PROMPT_VERSION: str = os.getenv("EVALUATION_PROMPT_VERSION", "rubric-v1")
    LOCAL_LLM_BASE_URL: str = os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:8100/v1")
    LOCAL_LLM_MODEL: str = os.getenv("LOCAL_LLM_MODEL", "qwen3-8b-awq")
    LOCAL_LLM_TIMEOUT_SECONDS: float = float(os.getenv("LOCAL_LLM_TIMEOUT_SECONDS", "5"))

    # OpenAI (legacy; local providers are preferred)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # File Uploads
    UPLOAD_DIR: str = "uploads"
    MAX_REQUEST_BODY_SIZE: int = int(os.getenv("MAX_REQUEST_BODY_SIZE", str(20 * 1024 * 1024)))
    MAX_AUDIO_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_AUDIO_EXTENSIONS: List[str] = [".wav", ".mp3", ".webm", ".m4a", ".ogg"]
    MAX_VIDEO_SIZE: int = 100 * 1024 * 1024  # 100MB
    
    # Interview Settings
    DEFAULT_INTERVIEW_DURATION: int = 30  # minutes
    MAX_INTERVIEW_ATTEMPTS: int = 3
    
    # Transcription
    TRANSCRIPTION_PROVIDER: str = os.getenv("TRANSCRIPTION_PROVIDER", "fake")
    TRANSCRIPTION_QUEUE_BACKEND: str = os.getenv("TRANSCRIPTION_QUEUE_BACKEND", "background")
    TRANSCRIPTION_QUEUE_NAME: str = os.getenv("TRANSCRIPTION_QUEUE_NAME", "transcription")

    # Quality Thresholds
    MIN_VOICE_CONFIDENCE: float = 0.7
    MIN_FACE_VISIBILITY: float = 0.8
    MIN_LIGHTING_SCORE: float = 0.6
    MAX_BACKGROUND_NOISE: float = 0.3
    
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
