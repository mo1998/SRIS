"""
Database Models
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database import Base


class UserRole(enum.Enum):
    EMPLOYER = "employer"
    EMPLOYEE = "employee"
    ADMIN = "admin"


class InterviewStatus(enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class InvitationStatus(enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    ACCEPTED = "accepted"
    COMPLETED = "completed"
    EXPIRED = "expired"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.EMPLOYEE)
    company_name = Column(String(255), nullable=True)  # For employers
    phone = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    created_interviews = relationship("Interview", back_populates="employer", foreign_keys="Interview.employer_id")
    responses = relationship("CandidateResponse", back_populates="candidate")


class Interview(Base):
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    employer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(InterviewStatus), default=InterviewStatus.DRAFT)
    duration_minutes = Column(Integer, default=30)
    max_attempts = Column(Integer, default=1)
    pass_score = Column(Float, default=70.0)  # Minimum score to pass
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    # Relationships
    employer = relationship("User", back_populates="created_interviews", foreign_keys=[employer_id])
    questions = relationship("InterviewQuestion", back_populates="interview", cascade="all, delete-orphan")
    invitations = relationship("Invitation", back_populates="interview", cascade="all, delete-orphan")
    responses = relationship("CandidateResponse", back_populates="interview", cascade="all, delete-orphan")


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"), nullable=False)
    question_text = Column(Text, nullable=False)
    expected_answer = Column(Text, nullable=True)  # Reference answer for evaluation
    question_type = Column(String(50), default="text")  # text, multiple_choice, coding
    options = Column(Text, nullable=True)  # JSON for multiple choice options
    weight = Column(Float, default=1.0)  # Weight for scoring
    order_index = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    interview = relationship("Interview", back_populates="questions")


class Invitation(Base):
    __tablename__ = "invitations"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"), nullable=False)
    candidate_email = Column(String(255), nullable=False)
    candidate_name = Column(String(255), nullable=False)
    unique_token = Column(String(255), unique=True, index=True, nullable=False)
    status = Column(Enum(InvitationStatus), default=InvitationStatus.PENDING)
    sent_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    interview = relationship("Interview", back_populates="invitations")


class CandidateResponse(Base):
    __tablename__ = "candidate_responses"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"), nullable=False)
    candidate_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Null if not registered
    candidate_email = Column(String(255), nullable=False)
    candidate_name = Column(String(255), nullable=False)
    invitation_id = Column(Integer, ForeignKey("invitations.id"), nullable=True)
    
    # Quality metrics
    voice_quality_score = Column(Float, nullable=True)
    background_quality_score = Column(Float, nullable=True)
    face_visibility_score = Column(Float, nullable=True)
    lighting_score = Column(Float, nullable=True)
    
    # Emotion tracking
    dominant_emotion = Column(String(50), nullable=True)
    emotion_timeline = Column(Text, nullable=True)  # JSON of emotions over time
    confidence_score = Column(Float, nullable=True)
    
    # Scoring
    total_score = Column(Float, nullable=True)
    passed = Column(Boolean, nullable=True)
    status = Column(String(50), default="in_progress")  # in_progress, completed, failed
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    interview = relationship("Interview", back_populates="responses")
    candidate = relationship("User", back_populates="responses")
    invitation = relationship("Invitation")
    question_answers = relationship("QuestionAnswer", back_populates="response", cascade="all, delete-orphan")


class QuestionAnswer(Base):
    __tablename__ = "question_answers"

    id = Column(Integer, primary_key=True, index=True)
    response_id = Column(Integer, ForeignKey("candidate_responses.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("interview_questions.id"), nullable=False)
    answer_text = Column(Text, nullable=True)  # Transcribed text answer
    audio_file_path = Column(String(500), nullable=True)
    score = Column(Float, nullable=True)  # Score for this answer
    feedback = Column(Text, nullable=True)  # AI feedback
    emotion_during_answer = Column(String(100), nullable=True)
    time_taken_seconds = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    response = relationship("CandidateResponse", back_populates="question_answers")
    question = relationship("InterviewQuestion")
