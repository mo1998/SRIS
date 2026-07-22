"""
Pydantic schemas for API validation
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum


# User schemas
class UserRoleEnum(str, Enum):
    employer = "employer"
    employee = "employee"
    admin = "admin"


class TeamRoleEnum(str, Enum):
    owner = "owner"
    admin = "admin"
    recruiter = "recruiter"
    reviewer = "reviewer"


class OrganizationResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TeamMembershipResponse(BaseModel):
    id: int
    organization_id: int
    user_id: int
    role: TeamRoleEnum
    created_at: datetime
    organization: Optional[OrganizationResponse] = None

    class Config:
        from_attributes = True


class TeamMembershipCreate(BaseModel):
    email: EmailStr
    role: TeamRoleEnum = TeamRoleEnum.reviewer


class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: UserRoleEnum = UserRoleEnum.employee
    company_name: Optional[str] = None
    phone: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

    @field_validator("password")
    @classmethod
    def validate_password_complexity(cls, password: str) -> str:
        return validate_password_strength(password)


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1)
    phone: Optional[str] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_new_password_complexity(cls, password: str) -> str:
        return validate_password_strength(password)


def validate_password_strength(password: str) -> str:
    if not any(character.islower() for character in password):
        raise ValueError("Password must include a lowercase letter")
    if not any(character.isupper() for character in password):
        raise ValueError("Password must include an uppercase letter")
    if not any(character.isdigit() for character in password):
        raise ValueError("Password must include a number")
    return password


class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# Interview schemas
class InterviewStatusEnum(str, Enum):
    draft = "draft"
    active = "active"
    completed = "completed"
    cancelled = "cancelled"


class QuestionBase(BaseModel):
    question_text: str
    expected_answer: Optional[str] = None
    question_type: str = "text"
    options: Optional[str] = None
    weight: float = 1.0
    order_index: int = 0


class RubricCriterionBase(BaseModel):
    name: str
    description: Optional[str] = None
    weight: float = 1.0
    order_index: int = 0


class RubricCriterionCreate(RubricCriterionBase):
    pass


class RubricCriterionResponse(RubricCriterionBase):
    id: int
    question_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class TemplateRubricCriterionResponse(RubricCriterionBase):
    id: int
    template_question_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class QuestionCreate(QuestionBase):
    rubric_criteria: List[RubricCriterionCreate] = []


class QuestionResponse(QuestionBase):
    id: int
    interview_id: int
    created_at: datetime
    rubric_criteria: List[RubricCriterionResponse] = []

    class Config:
        from_attributes = True


class InterviewBase(BaseModel):
    title: str
    description: Optional[str] = None
    duration_minutes: int = 30
    max_attempts: int = 1
    pass_score: float = 70.0


class InterviewCreate(InterviewBase):
    questions: List[QuestionCreate] = []


class InterviewUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    duration_minutes: Optional[int] = None
    max_attempts: Optional[int] = None
    pass_score: Optional[float] = None
    questions: Optional[List[QuestionCreate]] = None


class InterviewFromTemplateCreate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    duration_minutes: Optional[int] = None
    max_attempts: int = 1
    pass_score: Optional[float] = None


class InterviewResponse(InterviewBase):
    id: int
    employer_id: int
    organization_id: Optional[int] = None
    status: InterviewStatusEnum
    created_at: datetime
    updated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    questions: List[QuestionResponse] = []

    class Config:
        from_attributes = True


class TemplateQuestionResponse(QuestionBase):
    id: int
    template_id: int
    created_at: datetime
    rubric_criteria: List[TemplateRubricCriterionResponse] = []

    class Config:
        from_attributes = True


class InterviewTemplateResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    role_category: str
    duration_minutes: int
    pass_score: float
    is_active: bool
    created_at: datetime
    questions: List[TemplateQuestionResponse] = []

    class Config:
        from_attributes = True


# Invitation schemas
class InvitationStatusEnum(str, Enum):
    pending = "pending"
    sent = "sent"
    accepted = "accepted"
    completed = "completed"
    expired = "expired"
    revoked = "revoked"


class ReviewerDecisionEnum(str, Enum):
    pending = "pending"
    shortlisted = "shortlisted"
    rejected = "rejected"
    needs_review = "needs_review"
    hired = "hired"


class InvitationCreate(BaseModel):
    interview_id: int
    candidate_email: EmailStr
    candidate_name: str
    custom_message: Optional[str] = Field(None, max_length=1000)


class InvitationPreviewRequest(BaseModel):
    candidate_name: str = "Candidate Name"
    custom_message: Optional[str] = Field(None, max_length=1000)


class InvitationEmailPreview(BaseModel):
    subject: str
    html_body: str
    interview_link: str
    expires_at: datetime


class InvitationResponse(BaseModel):
    id: int
    interview_id: int
    candidate_email: str
    candidate_name: str
    unique_token: str
    status: InvitationStatusEnum
    sent_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PublicInterviewQuestionResponse(BaseModel):
    id: int
    question_text: str
    question_type: str
    options: Optional[str] = None
    weight: float
    order_index: int

    class Config:
        from_attributes = True


class PublicInterviewResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    duration_minutes: int
    max_attempts: int
    questions: List[PublicInterviewQuestionResponse] = []

    class Config:
        from_attributes = True


class InvitationVerificationResponse(InvitationResponse):
    interview: PublicInterviewResponse


# Candidate response schemas
class QuestionAnswerSchema(BaseModel):
    question_id: int
    answer_text: Optional[str] = None
    audio_file_path: Optional[str] = None
    score: Optional[float] = None
    feedback: Optional[str] = None
    feedback_en: Optional[str] = None
    feedback_ar: Optional[str] = None
    evidence: Optional[dict] = None
    emotion_during_answer: Optional[str] = None
    time_taken_seconds: Optional[int] = None


class ReportQuestionAnswerSchema(QuestionAnswerSchema):
    question: Optional[str] = None
    expected_answer: Optional[str] = None
    emotion: Optional[str] = None


class CandidateResponseCreate(BaseModel):
    interview_id: int
    candidate_email: EmailStr
    candidate_name: str
    invitation_token: Optional[str] = None


class CandidateResponseSummary(BaseModel):
    id: int
    interview_id: int
    candidate_email: str
    candidate_name: str
    voice_quality_score: Optional[float] = None
    background_quality_score: Optional[float] = None
    face_visibility_score: Optional[float] = None
    lighting_score: Optional[float] = None
    dominant_emotion: Optional[str] = None
    confidence_score: Optional[float] = None
    total_score: Optional[float] = None
    passed: Optional[bool] = None
    status: str
    reviewer_decision: Optional[ReviewerDecisionEnum] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    question_answers: List[QuestionAnswerSchema] = []

    class Config:
        from_attributes = True


# Quality check schemas
class QualityCheckResult(BaseModel):
    voice_quality: float
    background_quality: float
    face_visibility: float
    lighting: float
    overall_score: float
    recommendations: List[str] = []


class EmotionRecord(BaseModel):
    emotion: str
    confidence: float
    timestamp: float


# Reviewer schemas
class ReviewerDecisionUpdate(BaseModel):
    decision: ReviewerDecisionEnum


class ReviewerScorecardCreate(BaseModel):
    overall_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    strengths: Optional[str] = Field(None, max_length=5000)
    weaknesses: Optional[str] = Field(None, max_length=5000)
    overall_comment: Optional[str] = Field(None, max_length=5000)


class ReviewerScorecardResponse(BaseModel):
    id: int
    response_id: int
    reviewer_id: int
    overall_score: Optional[float] = None
    strengths: Optional[str] = None
    weaknesses: Optional[str] = None
    overall_comment: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Report schemas
class InterviewReportCandidate(BaseModel):
    response_id: int
    rank: int
    name: str
    email: str
    total_score: float
    passed: bool
    confidence_score: float
    voice_quality: float
    face_visibility: float
    dominant_emotion: str
    reviewer_decision: Optional[ReviewerDecisionEnum] = None
    completed_at: Optional[datetime] = None
    evaluation_provider: Optional[str] = None
    evaluation_model: Optional[str] = None
    evaluation_status: Optional[str] = None
    evaluation_completed_at: Optional[datetime] = None


class InterviewReport(BaseModel):
    interview_id: int
    interview_title: str
    total_candidates: int
    average_score: float
    pass_rate: float
    candidates: List[InterviewReportCandidate]
    generated_at: datetime


class CandidateReport(BaseModel):
    response_id: int
    candidate_name: str
    candidate_email: str
    interview_title: str
    total_score: float
    passed: bool
    voice_quality: float
    background_quality: float
    face_visibility: float
    lighting: float
    dominant_emotion: str
    confidence_score: float
    reviewer_decision: Optional[ReviewerDecisionEnum] = None
    answers: List[ReportQuestionAnswerSchema]
    feedback: str
    evaluation_provider: Optional[str] = None
    evaluation_model: Optional[str] = None
    evaluation_status: Optional[str] = None
    evaluation_completed_at: Optional[datetime] = None
    generated_at: datetime


class EvaluationScoreAudit(BaseModel):
    id: int
    question_answer_id: int
    question_id: int
    question: Optional[str] = None
    score: float
    feedback_en: Optional[str] = None
    feedback_ar: Optional[str] = None
    evidence: Optional[dict] = None
    created_at: Optional[datetime] = None


class EvaluationRunAudit(BaseModel):
    id: int
    response_id: int
    provider: str
    provider_version: Optional[str] = None
    model_name: Optional[str] = None
    config_hash: Optional[str] = None
    status: str
    raw_summary: Optional[dict] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    scores: List[EvaluationScoreAudit] = []


class EvaluationHealth(BaseModel):
    provider: str
    provider_version: Optional[str] = None
    prompt_version: Optional[str] = None
    config_hash: Optional[str] = None
    model_name: Optional[str] = None
    base_url: Optional[str] = None
    healthy: bool
    status: str
    fallback_provider: Optional[str] = None
    last_error: Optional[str] = None
    checked_at: datetime


class EmailHealth(BaseModel):
    configured: bool
    status: str
    provider: str
    mail_from: str
    mail_from_name: str
    mailpit_api_url: str
    missing_settings: List[str] = []
    checked_at: datetime


class EvaluationAnalytics(BaseModel):
    interview_id: int
    completed_responses: int
    total_evaluation_runs: int
    queued_runs: int
    running_runs: int
    completed_runs: int
    failed_runs: int
    average_latest_score: float
    fallback_count: int
    provider_counts: Dict[str, int]
    generated_at: datetime


class AuditLogResponse(BaseModel):
    id: int
    actor_user_id: Optional[int] = None
    action: str
    target_type: str
    target_id: Optional[int] = None
    organization_id: Optional[int] = None
    details: Optional[Dict] = None
    created_at: datetime
