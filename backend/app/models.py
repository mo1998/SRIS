"""
Database Models
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database import Base


def enum_values(enum_class):
    return [item.value for item in enum_class]


class UserRole(enum.Enum):
    EMPLOYER = "employer"
    EMPLOYEE = "employee"
    ADMIN = "admin"


class TeamRole(enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    RECRUITER = "recruiter"
    REVIEWER = "reviewer"


class InterviewStatus(enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ReviewerDecision(enum.Enum):
    PENDING = "pending"
    SHORTLISTED = "shortlisted"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"
    HIRED = "hired"


class InvitationStatus(enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    ACCEPTED = "accepted"
    COMPLETED = "completed"
    EXPIRED = "expired"
    REVOKED = "revoked"


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    memberships = relationship("TeamMembership", back_populates="organization", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole, values_callable=enum_values), default=UserRole.EMPLOYEE)
    company_name = Column(String(255), nullable=True)  # For employers
    phone = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    token_version = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    created_interviews = relationship("Interview", back_populates="employer", foreign_keys="Interview.employer_id")
    responses = relationship("CandidateResponse", back_populates="candidate", foreign_keys="CandidateResponse.candidate_id")
    team_memberships = relationship("TeamMembership", back_populates="user", cascade="all, delete-orphan")


class TeamMembership(Base):
    __tablename__ = "team_memberships"
    __table_args__ = (UniqueConstraint("organization_id", "user_id", name="uq_team_membership_org_user"),)

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(Enum(TeamRole, values_callable=enum_values), default=TeamRole.REVIEWER, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="memberships")
    user = relationship("User", back_populates="team_memberships")


class Interview(Base):
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    employer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    status = Column(Enum(InterviewStatus, values_callable=enum_values), default=InterviewStatus.DRAFT)
    duration_minutes = Column(Integer, default=30)
    max_attempts = Column(Integer, default=1)
    pass_score = Column(Float, default=70.0)  # Minimum score to pass
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    # Relationships
    employer = relationship("User", back_populates="created_interviews", foreign_keys=[employer_id])
    organization = relationship("Organization")
    questions = relationship("InterviewQuestion", back_populates="interview", cascade="all, delete-orphan")
    invitations = relationship("Invitation", back_populates="interview", cascade="all, delete-orphan")
    responses = relationship("CandidateResponse", back_populates="interview", cascade="all, delete-orphan")


class InterviewTemplate(Base):
    __tablename__ = "interview_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    role_category = Column(String(100), nullable=False)
    duration_minutes = Column(Integer, default=30)
    pass_score = Column(Float, default=70.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    questions = relationship("TemplateQuestion", back_populates="template", cascade="all, delete-orphan")


class TemplateQuestion(Base):
    __tablename__ = "template_questions"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("interview_templates.id"), nullable=False)
    question_text = Column(Text, nullable=False)
    expected_answer = Column(Text, nullable=True)
    question_type = Column(String(50), default="text")
    options = Column(Text, nullable=True)
    weight = Column(Float, default=1.0)
    order_index = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    template = relationship("InterviewTemplate", back_populates="questions")
    rubric_criteria = relationship("TemplateRubricCriterion", back_populates="template_question", cascade="all, delete-orphan")


class TemplateRubricCriterion(Base):
    __tablename__ = "template_rubric_criteria"

    id = Column(Integer, primary_key=True, index=True)
    template_question_id = Column(Integer, ForeignKey("template_questions.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    weight = Column(Float, default=1.0)
    order_index = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    template_question = relationship("TemplateQuestion", back_populates="rubric_criteria")


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
    rubric_criteria = relationship("RubricCriterion", back_populates="question", cascade="all, delete-orphan")


class RubricCriterion(Base):
    __tablename__ = "rubric_criteria"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("interview_questions.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    weight = Column(Float, default=1.0)
    order_index = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    question = relationship("InterviewQuestion", back_populates="rubric_criteria")


class Invitation(Base):
    __tablename__ = "invitations"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"), nullable=False)
    candidate_email = Column(String(255), nullable=False)
    candidate_name = Column(String(255), nullable=False)
    unique_token = Column(String(255), unique=True, index=True, nullable=False)
    status = Column(Enum(InvitationStatus, values_callable=enum_values), default=InvitationStatus.PENDING)
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
    
    # Reviewer decision
    reviewer_decision = Column(Enum(ReviewerDecision, values_callable=enum_values), default=ReviewerDecision.PENDING)
    reviewer_decision_at = Column(DateTime, nullable=True)
    reviewer_decision_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Scoring
    total_score = Column(Float, nullable=True)
    passed = Column(Boolean, nullable=True)
    status = Column(String(50), default="in_progress")  # in_progress, completed, failed
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    interview = relationship("Interview", back_populates="responses")
    candidate = relationship("User", back_populates="responses", foreign_keys=[candidate_id])
    invitation = relationship("Invitation")
    question_answers = relationship("QuestionAnswer", back_populates="response", cascade="all, delete-orphan")
    evaluation_runs = relationship("EvaluationRun", back_populates="response", cascade="all, delete-orphan")


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
    evaluation_scores = relationship("EvaluationScore", back_populates="question_answer", cascade="all, delete-orphan")


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id = Column(Integer, primary_key=True, index=True)
    response_id = Column(Integer, ForeignKey("candidate_responses.id"), nullable=False, index=True)
    provider = Column(String(100), nullable=False)
    provider_version = Column(String(50), nullable=True)
    model_name = Column(String(255), nullable=True)
    config_hash = Column(String(100), nullable=True)
    status = Column(String(50), default="running", nullable=False)
    raw_summary = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    response = relationship("CandidateResponse", back_populates="evaluation_runs")
    scores = relationship("EvaluationScore", back_populates="evaluation_run", cascade="all, delete-orphan")


class EvaluationScore(Base):
    __tablename__ = "evaluation_scores"

    id = Column(Integer, primary_key=True, index=True)
    evaluation_run_id = Column(Integer, ForeignKey("evaluation_runs.id"), nullable=False, index=True)
    question_answer_id = Column(Integer, ForeignKey("question_answers.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("interview_questions.id"), nullable=False)
    score = Column(Float, nullable=False)
    feedback_en = Column(Text, nullable=True)
    feedback_ar = Column(Text, nullable=True)
    evidence_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    evaluation_run = relationship("EvaluationRun", back_populates="scores")
    question_answer = relationship("QuestionAnswer", back_populates="evaluation_scores")
    question = relationship("InterviewQuestion")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)
    target_type = Column(String(100), nullable=False, index=True)
    target_id = Column(Integer, nullable=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    actor = relationship("User")
    organization = relationship("Organization")


class ReviewerScorecard(Base):
    __tablename__ = "reviewer_scorecards"

    id = Column(Integer, primary_key=True, index=True)
    response_id = Column(Integer, ForeignKey("candidate_responses.id"), nullable=False, unique=True, index=True)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    overall_score = Column(Float, nullable=True)
    strengths = Column(Text, nullable=True)
    weaknesses = Column(Text, nullable=True)
    overall_comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    response = relationship("CandidateResponse")
    reviewer = relationship("User", foreign_keys=[reviewer_id])
