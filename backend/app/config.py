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
    
    # Email (for invitations)
    MAIL_FROM: str = os.getenv("MAIL_FROM", "noreply@sris.com")
    MAIL_PASSWORD: str = os.getenv("MAIL_PASSWORD", "")
    MAIL_SERVER: str = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT: int = 587
    MAIL_TLS: bool = True
    MAIL_SSL: bool = False
    
    # OpenAI (for answer evaluation)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # File Uploads
    UPLOAD_DIR: str = "uploads"
    MAX_AUDIO_SIZE: int = 10 * 1024 * 1024  # 10MB
    MAX_VIDEO_SIZE: int = 100 * 1024 * 1024  # 100MB
    
    # Interview Settings
    DEFAULT_INTERVIEW_DURATION: int = 30  # minutes
    MAX_INTERVIEW_ATTEMPTS: int = 3
    
    # Quality Thresholds
    MIN_VOICE_CONFIDENCE: float = 0.7
    MIN_FACE_VISIBILITY: float = 0.8
    MIN_LIGHTING_SCORE: float = 0.6
    MAX_BACKGROUND_NOISE: float = 0.3
    
    model_config = {"env_file": ".env", "case_sensitive": True}


settings = Settings()
