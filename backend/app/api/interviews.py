"""
Interview management routes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.database import get_db
from app.models import User, Interview, InterviewQuestion, InterviewStatus, InterviewTemplate, RubricCriterion, TeamMembership, TeamRole, UserRole
from app.schemas import InterviewCreate, InterviewFromTemplateCreate, InterviewResponse, InterviewTemplateResponse, QuestionResponse
from app.api.auth import get_current_user, require_role

router = APIRouter()

INTERVIEW_MANAGER_ROLES = {TeamRole.OWNER, TeamRole.ADMIN, TeamRole.RECRUITER}


def get_primary_membership(user: User, db: Session) -> TeamMembership:
    membership = (
        db.query(TeamMembership)
        .filter(TeamMembership.user_id == user.id)
        .order_by(TeamMembership.created_at.asc())
        .first()
    )
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization membership required")
    return membership


def get_interview_or_404(interview_id: int, db: Session) -> Interview:
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    return interview


def require_interview_membership(interview: Interview, user: User, db: Session) -> TeamMembership:
    if user.role == UserRole.ADMIN:
        return None

    membership = (
        db.query(TeamMembership)
        .filter(
            TeamMembership.user_id == user.id,
            TeamMembership.organization_id == interview.organization_id,
        )
        .first()
    )
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return membership


def require_interview_manager(interview: Interview, user: User, db: Session) -> None:
    membership = require_interview_membership(interview, user, db)
    if membership and membership.role not in INTERVIEW_MANAGER_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient organization permissions")


def add_questions_to_interview(interview_id: int, questions: List, db: Session) -> None:
    for idx, q_data in enumerate(questions):
        order_index = q_data.order_index if q_data.order_index else idx
        question = InterviewQuestion(
            interview_id=interview_id,
            question_text=q_data.question_text,
            expected_answer=q_data.expected_answer,
            question_type=q_data.question_type,
            options=q_data.options,
            weight=q_data.weight,
            order_index=order_index,
        )
        db.add(question)
        db.flush()

        for criterion_idx, criterion_data in enumerate(getattr(q_data, "rubric_criteria", [])):
            criterion_order = criterion_data.order_index if criterion_data.order_index else criterion_idx
            db.add(RubricCriterion(
                question_id=question.id,
                name=criterion_data.name,
                description=criterion_data.description,
                weight=criterion_data.weight,
                order_index=criterion_order,
            ))


@router.post("/", response_model=InterviewResponse, status_code=status.HTTP_201_CREATED)
async def create_interview(
    interview_data: InterviewCreate,
    current_user: User = Depends(require_role(UserRole.EMPLOYER)),
    db: Session = Depends(get_db)
):
    """Create a new interview with questions"""
    membership = get_primary_membership(current_user, db)
    
    interview = Interview(
        title=interview_data.title,
        description=interview_data.description,
        employer_id=current_user.id,
        organization_id=membership.organization_id,
        duration_minutes=interview_data.duration_minutes,
        max_attempts=interview_data.max_attempts,
        pass_score=interview_data.pass_score
    )
    
    db.add(interview)
    db.flush()  # Get interview ID
    
    add_questions_to_interview(interview.id, interview_data.questions, db)
    
    db.commit()
    db.refresh(interview)
    
    return interview


@router.get("/templates", response_model=List[InterviewTemplateResponse])
async def list_interview_templates(
    db: Session = Depends(get_db)
):
    """List active built-in interview templates"""
    return (
        db.query(InterviewTemplate)
        .filter(InterviewTemplate.is_active == True)
        .order_by(InterviewTemplate.role_category, InterviewTemplate.name)
        .all()
    )


@router.get("/templates/{template_id}", response_model=InterviewTemplateResponse)
async def get_interview_template(
    template_id: int,
    db: Session = Depends(get_db)
):
    """Get a built-in interview template"""
    template = (
        db.query(InterviewTemplate)
        .filter(InterviewTemplate.id == template_id, InterviewTemplate.is_active == True)
        .first()
    )
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    return template


@router.post("/templates/{template_id}/interviews", response_model=InterviewResponse, status_code=status.HTTP_201_CREATED)
async def create_interview_from_template(
    template_id: int,
    interview_data: InterviewFromTemplateCreate,
    current_user: User = Depends(require_role(UserRole.EMPLOYER)),
    db: Session = Depends(get_db)
):
    """Create a draft interview from a built-in template"""
    membership = get_primary_membership(current_user, db)
    template = (
        db.query(InterviewTemplate)
        .filter(InterviewTemplate.id == template_id, InterviewTemplate.is_active == True)
        .first()
    )
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    interview = Interview(
        title=interview_data.title or template.name,
        description=interview_data.description if interview_data.description is not None else template.description,
        employer_id=current_user.id,
        organization_id=membership.organization_id,
        duration_minutes=interview_data.duration_minutes or template.duration_minutes,
        max_attempts=interview_data.max_attempts,
        pass_score=interview_data.pass_score if interview_data.pass_score is not None else template.pass_score,
    )
    db.add(interview)
    db.flush()
    add_questions_to_interview(interview.id, template.questions, db)
    db.commit()
    db.refresh(interview)

    return interview


@router.get("/", response_model=List[InterviewResponse])
async def list_employer_interviews(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_role(UserRole.EMPLOYER)),
    db: Session = Depends(get_db)
):
    """List all interviews for current employer organization"""
    membership = get_primary_membership(current_user, db)
    interviews = (
        db.query(Interview)
        .filter(Interview.organization_id == membership.organization_id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return interviews


@router.get("/{interview_id}", response_model=InterviewResponse)
async def get_interview(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get interview details"""
    interview = get_interview_or_404(interview_id, db)
    require_interview_membership(interview, current_user, db)
    
    return interview


@router.put("/{interview_id}", response_model=InterviewResponse)
async def update_interview(
    interview_id: int,
    title: str = None,
    description: str = None,
    duration_minutes: int = None,
    max_attempts: int = None,
    pass_score: float = None,
    current_user: User = Depends(require_role(UserRole.EMPLOYER)),
    db: Session = Depends(get_db)
):
    """Update interview details"""
    interview = get_interview_or_404(interview_id, db)
    require_interview_manager(interview, current_user, db)
    
    if interview.status != InterviewStatus.DRAFT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Can only update draft interviews")
    
    if title:
        interview.title = title
    if description is not None:
        interview.description = description
    if duration_minutes:
        interview.duration_minutes = duration_minutes
    if max_attempts:
        interview.max_attempts = max_attempts
    if pass_score:
        interview.pass_score = pass_score
    
    db.commit()
    db.refresh(interview)
    
    return interview


@router.post("/{interview_id}/activate", response_model=InterviewResponse)
async def activate_interview(
    interview_id: int,
    current_user: User = Depends(require_role(UserRole.EMPLOYER)),
    db: Session = Depends(get_db)
):
    """Activate interview (make it available for candidates)"""
    interview = get_interview_or_404(interview_id, db)
    require_interview_manager(interview, current_user, db)
    
    if interview.status != InterviewStatus.DRAFT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Interview must be in draft status")
    
    interview.status = InterviewStatus.ACTIVE
    db.commit()
    db.refresh(interview)
    
    return interview


@router.post("/{interview_id}/complete", response_model=InterviewResponse)
async def complete_interview(
    interview_id: int,
    current_user: User = Depends(require_role(UserRole.EMPLOYER)),
    db: Session = Depends(get_db)
):
    """Complete interview (no more candidates can join)"""
    interview = get_interview_or_404(interview_id, db)
    require_interview_manager(interview, current_user, db)
    
    interview.status = InterviewStatus.COMPLETED
    db.commit()
    db.refresh(interview)
    
    return interview


@router.delete("/{interview_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_interview(
    interview_id: int,
    current_user: User = Depends(require_role(UserRole.EMPLOYER)),
    db: Session = Depends(get_db)
):
    """Delete an interview"""
    interview = get_interview_or_404(interview_id, db)
    require_interview_manager(interview, current_user, db)
    
    db.delete(interview)
    db.commit()


# Question management
@router.post("/{interview_id}/questions", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
async def add_question(
    interview_id: int,
    question_data: QuestionResponse,
    current_user: User = Depends(require_role(UserRole.EMPLOYER)),
    db: Session = Depends(get_db)
):
    """Add a question to an interview"""
    interview = get_interview_or_404(interview_id, db)
    require_interview_manager(interview, current_user, db)
    
    if interview.status != InterviewStatus.DRAFT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Can only add questions to draft interviews")
    
    question = InterviewQuestion(
        interview_id=interview_id,
        question_text=question_data.question_text,
        expected_answer=question_data.expected_answer,
        question_type=question_data.question_type,
        options=question_data.options,
        weight=question_data.weight,
        order_index=question_data.order_index
    )
    
    db.add(question)
    db.commit()
    db.refresh(question)
    
    return question


@router.get("/{interview_id}/questions", response_model=List[QuestionResponse])
async def list_questions(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all questions for an interview"""
    interview = get_interview_or_404(interview_id, db)
    require_interview_membership(interview, current_user, db)
    
    questions = (
        db.query(InterviewQuestion)
        .filter(InterviewQuestion.interview_id == interview_id)
        .order_by(InterviewQuestion.order_index)
        .all()
    )
    
    return questions
